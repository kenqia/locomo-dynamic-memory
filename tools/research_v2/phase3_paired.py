"""Read-only Phase 3 pairing. Stdlib only; never starts application services."""
import argparse
from collections import Counter, defaultdict
import json
import math
import os
from pathlib import Path

from .postbaseline import BASELINE, DEVELOPMENT, STRATEGIES, file_sha, ledger_cost, load_ledger, readonly, sha, write

HYBRID = 'hybrid_no_resolution'


def score(item):
    value = ((item.get('result') or {}).get('qa') or {}).get('value')
    return value if item['status'] == 'succeeded' and type(value) in (float, int) and math.isfinite(value) and 0 <= value <= 1 else None


def pair_state(h, d):
    if h['status'] not in ('succeeded', 'failed') or d['status'] not in ('succeeded', 'failed'):
        return 'unknown'
    return {('succeeded', 'succeeded'): 'both_succeeded', ('succeeded', 'failed'): 'hybrid_only_succeeded',
            ('failed', 'succeeded'): 'dynamic_only_succeeded', ('failed', 'failed'): 'both_failed'}[(h['status'], d['status'])]


def outcome(arms):
    """Keep unknown distinct from a known failure, including denominator bounds."""
    n = len(arms)
    values = [a['qa'] for a in arms if a['qa'] is not None]
    unknown = sum(a['status'] not in ('succeeded', 'failed') or (a['status'] == 'succeeded' and a['qa'] is None) for a in arms)
    total = sum(values)
    return dict(n=n, states=dict(Counter(a['status'] for a in arms)), scorable=len(values),
                success_rate=sum(a['status'] == 'succeeded' for a in arms)/n if n else None,
                successful_qa_mean=total/len(values) if values else None,
                full_denominator_score=total/n if n and not unknown else None,
                full_denominator_bounds=[total/n, (total+unknown)/n] if n else None,
                unknown_score_items=unknown)


def summary(rows):
    comparable = [r for r in rows if r['delta_dynamic_minus_hybrid'] is not None]
    deltas = [r['delta_dynamic_minus_hybrid'] for r in comparable]
    wins = [v for v in deltas if v > 1e-12]
    losses = [v for v in deltas if v < -1e-12]
    return dict(n=len(rows), pair_states=dict(Counter(r['pair_state'] for r in rows)), comparable=len(deltas),
        dynamic_wins=len(wins), hybrid_wins=len(losses), ties=len(deltas)-len(wins)-len(losses),
        mean_dynamic_gain_on_wins=sum(wins)/len(wins) if wins else None,
        mean_dynamic_loss_on_losses=sum(losses)/len(losses) if losses else None,
        mean_paired_delta=sum(deltas)/len(deltas) if deltas else None,
        paired_hybrid_mean=sum(r['hybrid']['qa'] for r in comparable)/len(comparable) if comparable else None,
        paired_dynamic_mean=sum(r['dynamic']['qa'] for r in comparable)/len(comparable) if comparable else None,
        hybrid=outcome([r['hybrid'] for r in rows]), dynamic=outcome([r['dynamic'] for r in rows]),
        costs={arm: {stage: sum(r[arm]['cost_by_stage'][stage]['known_peak_estimate_cny'] for r in rows)
                    for stage in ('Query Analysis', 'Resolution', 'Answer', 'all')} for arm in ('hybrid','dynamic')})


def oracle(rows):
    chosen=[]; choices=Counter(); cost=0
    for row in rows:
        # Unknown outcome cannot be valued by this retrospective oracle.
        if row['pair_state'] == 'unknown':
            chosen.append(dict(status='unknown', qa=None)); choices['unknown']+=1
            continue
        h,d=row['hybrid'],row['dynamic']
        # Prefer completion over failure, then QA; ties go to Hybrid (fixed, not tuned).
        rank=lambda a:(a['status']=='succeeded', a['qa'] if a['qa'] is not None else -1)
        path='dynamic' if rank(d)>rank(h) else 'hybrid'
        chosen.append(row[path]);choices[path]+=1
        cost+=row[path]['cost_by_stage']['all']['known_peak_estimate_cny']
    return dict(outcome=outcome(chosen), choices=dict(choices),
        selected_historical_cost_cny=cost,
        notice='Uses observed scores and downstream failures. Not deployable. Cost is selected historic arm scenario, not actual new billing; unknown pair excluded from cost.')


def run(runtime, atlas, output, controlled):
    os.umask(0o077)
    runtime,atlas,output,controlled=map(Path,(runtime,atlas,output,controlled))
    output.mkdir(parents=True, exist_ok=True);controlled.mkdir(parents=True, exist_ok=True, mode=0o700)
    dbpath=runtime/'memory.sqlite3';ledgerpath=runtime/'observer/budget.sqlite3'
    inputs={str(p.resolve()):file_sha(p) for p in (dbpath,ledgerpath,runtime/'experiment.json')}
    physical=load_ledger(ledgerpath);bykey=defaultdict(list)
    for r in physical:
        if r.get('scope')=='development-query' and r.get('run_id')==BASELINE:
            bykey[(r['question_id'],r['strategy'])].append(r)
    rows=[];pending={};failures=[];feature_file=controlled/'initial-observations.jsonl'
    with readonly(dbpath) as db, feature_file.open('x') as feature_out:
        meta=json.loads(db.execute('SELECT result_json FROM evaluation_runs WHERE run_id=?',(BASELINE,)).fetchone()[0])
        if len(meta['input']['samples'])!=757 or set(meta['pins'])!=set(DEVELOPMENT):
            raise ValueError('Baseline identity changed')
        for ordinal,raw in db.execute('SELECT ordinal,item_json FROM evaluation_run_items WHERE run_id=? ORDER BY ordinal',(BASELINE,)):
            item=json.loads(raw)
            if item['strategy'] not in (HYBRID,'dynamic'): continue
            qid=item['question_id'];arm='hybrid' if item['strategy']==HYBRID else 'dynamic'
            if item['sample_id'] not in DEVELOPMENT: raise ValueError('Development-only boundary')
            sample=meta['input']['samples'][item['sample_index']]
            if sample['sample_id']!=item['sample_id'] or sample['question']!=item['question']:
                raise ValueError('Sample mismatch')
            wire=bykey[(qid,item['strategy'])];trace=(item.get('result') or {}).get('trace') or {}
            cost={stage:ledger_cost([r for r in wire if r['stage']==stage]) for stage in ('Query Analysis','Resolution','Answer')}
            cost['all']=ledger_cost(wire)
            error=(item.get('result') or {}).get('error') or item.get('error') or trace.get('error')
            value=dict(ordinal=ordinal,status=item['status'],qa=score(item),build_id=meta['pins'][item['sample_id']],
                error=error,answer_status=(trace.get('answer') or {}).get('status'),
                row_sha256=sha(raw.encode()),trace_id=trace.get('trace_id'),cost_by_stage=cost)
            row=pending.setdefault(qid,dict(question_id=qid,conversation=item['sample_id'],category=str(sample['category']),
                qa_index=item['qa_index'],sample_index=item['sample_index']))
            if arm in row: raise ValueError('Duplicate strategy outcome')
            row[arm]=value
            if arm=='dynamic':
                # Only initial retrieval is exported. No expansion, resolution, answer or score enters the feature file.
                observation=dict(question_id=qid,conversation=item['sample_id'],question=item['question'],
                    build_id=meta['pins'][item['sample_id']],initial=trace.get('initial'),
                    provenance=dict(run_id=BASELINE,ordinal=ordinal,row_sha256=sha(raw.encode()),pointer='/result/trace/initial'))
                feature_out.write(json.dumps(observation,ensure_ascii=False)+'\n')
                if item['status']=='failed':
                    failures.append(dict(question_id=qid,conversation=item['sample_id'],category=str(sample['category']),
                        ordinal=ordinal,error=error,resolution_budget=(trace.get('resolution_budgets') or {}).get('resolve'),
                        physical_by_stage={s:v['physical_http'] for s,v in cost.items()}))
            if 'hybrid' in row and 'dynamic' in row:
                row['pair_state']=pair_state(row['hybrid'],row['dynamic'])
                h,d=row['hybrid']['qa'],row['dynamic']['qa']
                row['delta_dynamic_minus_hybrid']=d-h if h is not None and d is not None else None
                rows.append(row);del pending[qid]
    if pending or len(rows)!=757 or len({r['question_id'] for r in rows})!=757:
        raise ValueError('Pair denominator mismatch')
    rows.sort(key=lambda r:r['sample_index'])
    write(output/'paired-items.json',rows)
    write(output/'dynamic-failures.json',failures)
    groups={dim:{v:summary([r for r in rows if r[dim]==v]) for v in sorted({r[dim] for r in rows})}
            for dim in ('conversation','category')}
    query=[r for r in physical if r.get('run_id')==BASELINE and r.get('scope')=='development-query']
    report=dict(version='phase3-paired-v1',run_id=BASELINE,inputs=inputs,summary=summary(rows),groups=groups,
        oracle_upper_bound=oracle(rows),all_strategy_physical={s:ledger_cost([r for r in query if r.get('strategy')==s]) for s in STRATEGIES},
        dynamic_errors=dict(Counter((f.get('error') or {}).get('code','not_recorded') for f in failures)),
        shared_build_cost=ledger_cost([r for r in physical if r.get('scope')=='development-build']),
        artifacts={str(p.resolve()):file_sha(p) for p in (output/'paired-items.json',output/'dynamic-failures.json',feature_file)},
        semantic_notice='Official QA difference is not evidence correctness. Existing independent AI review remains a separate artifact; unknown costs are reservations, not zero.',
        historical_code_notice='Pre-existing 47 dirty files match handoff hashes. Frozen follow-up execution identities remain separate; no historic file is staged by Phase 3.')
    after={p:file_sha(p) for p in inputs}
    if inputs!=after: raise ValueError('Historical inputs modified')
    report['input_integrity_unchanged']=True
    write(output/'paired-diagnosis.json',report)
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('runtime','atlas','output','controlled'):p.add_argument('--'+name,required=True,type=Path)
    args=p.parse_args();result=run(**vars(args));print(json.dumps(dict(summary=result['summary'],errors=result['dynamic_errors']),indent=2))
