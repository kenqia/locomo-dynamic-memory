"""LOCO threshold selection with strictly pre-generation feature construction."""
import argparse
from collections import Counter
import json
from pathlib import Path
import time

from .phase3_paired import HYBRID, outcome, summary
from .postbaseline import BASELINE, DEVELOPMENT, file_sha, readonly, write
from .router import QueryComplexityRouter, VERSION, fingerprint

THRESHOLDS=(.5,.75,1.)


def comparable_initial(initial):
    if not initial:return None
    return fingerprint(dict(analysis=(initial.get('analysis') or {}).get('result'),
        candidates=initial.get('initial_candidates'),channels=initial.get('channels'),
        index_fingerprint=initial.get('index_fingerprint')))


def evaluate(rows, decisions):
    selected=[r[decisions[r['question_id']]['path']] for r in rows]
    quality=outcome(selected)
    both=[r for r in rows if r['pair_state']=='both_succeeded' and r['hybrid']['qa'] is not None and r['dynamic']['qa'] is not None]
    return dict(outcome=quality,choices=dict(Counter(decisions[r['question_id']]['path'] for r in rows)),
        hybrid_fraction=sum(decisions[r['question_id']]['path']=='hybrid' for r in rows)/len(rows) if rows else None,
        paired_successful_n=len(both),paired_qa_mean=sum(r[decisions[r['question_id']]['path']]['qa'] for r in both)/len(both) if both else None,
        paired_delta_vs_dynamic=sum(r[decisions[r['question_id']]['path']]['qa']-r['dynamic']['qa'] for r in both)/len(both) if both else None,
        selected_historical_cost_cny=sum(a['cost_by_stage']['all']['known_peak_estimate_cny'] for a in selected),
        selected_unknown_reservation_cny=sum(a['cost_by_stage']['all']['unknown_reservation_cny'] for a in selected),
        notice='Selected historical outcomes and costs; not new execution or measured counterfactual provider billing.')


def select_threshold(training, predictions):
    """Choose only using training conversations. Fixed tie break: stricter gate."""
    dynamic=outcome([r['dynamic'] for r in training]);candidates=[]
    for threshold in THRESHOLDS:
        result=evaluate(training,predictions[threshold])
        # Paired QA and reliability must not decline on training data. Unknowns
        # stay unknown and are not used as fictitious training labels.
        feasible=result['paired_delta_vs_dynamic'] is not None and result['paired_delta_vs_dynamic']>=0 and result['outcome']['success_rate']>=dynamic['success_rate']
        candidates.append(dict(threshold=threshold,feasible=feasible,training=result))
    feasible=[c for c in candidates if c['feasible']]
    selected=min(feasible,key=lambda c:(c['training']['selected_historical_cost_cny'],-c['threshold']))['threshold'] if feasible else None
    return selected,candidates


def run(runtime,controlled,output):
    runtime,controlled,output=map(Path,(runtime,controlled,output))
    rows=json.loads((output/'paired-items.json').read_text())
    # Construct features first. Only the allowlist file and Build-time source/
    # relation snapshot are available at this boundary; outcomes are downstream.
    predictions={t:{} for t in THRESHOLDS};feature_hashes={};initial_hashes={};missing=[];wall=time.perf_counter();cpu=time.process_time()
    with readonly(runtime/'memory.sqlite3') as db:
        pins=json.loads(db.execute('SELECT result_json FROM evaluation_runs WHERE run_id=?',(BASELINE,)).fetchone()[0])['pins']
        relations={sid:[json.loads(r[0]) for r in db.execute('SELECT relation_json FROM memory_relations WHERE build_id=? ORDER BY relation_id',(bid,))] for sid,bid in pins.items()}
        sources={sid:{s['source_id']:s for s in json.loads((runtime/'sources'/f'{sid}.json').read_text())} for sid in DEVELOPMENT}
        with (controlled/'initial-observations.jsonl').open() as stream:
            for line in stream:
                observation=json.loads(line);qid=observation['question_id'];sid=observation['conversation'];initial=observation['initial']
                if not initial:missing.append(qid)
                initial_hashes[qid]=comparable_initial(initial)
                for t in THRESHOLDS:
                    decision=QueryComplexityRouter(t).route(question=observation['question'],initial=initial,sources=sources[sid],relations=relations[sid])
                    predictions[t][qid]=decision.to_dict()
                feature_hashes[qid]=fingerprint(predictions[1.][qid]['observed_features'])
        alignment={}
        for raw, in db.execute("SELECT item_json FROM evaluation_run_items WHERE run_id=? AND json_extract(item_json,'$.strategy')=? ORDER BY ordinal",(BASELINE,HYBRID)):
            item=json.loads(raw);trace=(item.get('result') or {}).get('trace') or {}
            initial=trace.get('retrieval')
            alignment[item['question_id']]=bool(initial and comparable_initial(initial)==initial_hashes[item['question_id']])
    feature_compute=dict(cpu_seconds=time.process_time()-cpu,wall_seconds=time.perf_counter()-wall,
        note='Includes read-only source/relation input loading and three policy passes; original analysis/embedding/expansion local CPU was not recorded per item.')
    folds=[];out_of_fold={}
    for held in sorted(DEVELOPMENT):
        train=[r for r in rows if r['conversation']!=held];test=[r for r in rows if r['conversation']==held]
        threshold,search=select_threshold(train,predictions)
        decisions=predictions[threshold] if threshold is not None else {r['question_id']:dict(path='dynamic',reason_codes=['training_no_feasible_threshold'],router_version=VERSION) for r in rows}
        out_of_fold.update({r['question_id']:decisions[r['question_id']] for r in test})
        folds.append(dict(held_out_conversation=held,training_conversations=sorted(set(DEVELOPMENT)-{held}),
            selected_threshold=threshold,training_search=search,held_out=evaluate(test,decisions)))
    full=evaluate(rows,out_of_fold)
    strict=[r for r in rows if alignment[r['question_id']]]
    decisions=[]
    for row in rows:
        qid=row['question_id'];decision=out_of_fold[qid]
        decisions.append(dict(question_id=qid,conversation=row['conversation'],category=row['category'],
            matched_initial_business_inputs=alignment[qid],decision=decision,
            selected_historical_outcome=row[decision['path']],feature_fingerprint=feature_hashes[qid]))
    write(controlled/'router-decisions.json',decisions)
    # Independent reviews remain independent, and follow-up Runs do not become
    # baseline outcomes. Report exposure to known risks, never a full risk rate.
    regression=json.loads((output/'failure-regression.json').read_text())
    risks=[dict(case_id=c['case_id'],question_id=c['question_id'],original_strategy=c['strategy'],
        original_pattern=c['pattern'],original_run_id=c['case_id'].split(':')[0],
        original_ai_severe=c['ai_severe'],original_ai_incorrect_refusal=c['ai_incorrect_refusal'],
        routed_path=out_of_fold[c['question_id']]['path'] if c['question_id'] in out_of_fold else None,
        notice='Follow-up semantic labels do not label the baseline or new routed answer.') for c in regression['cases'] if c['pattern']]
    result=dict(version=VERSION,threshold_grid=THRESHOLDS,selection_rule='Nonnegative training paired QA delta and no training success-rate decrease; minimize selected historic cost; ties stricter; otherwise Dynamic.',
        exposure_notice='All four development conversations and published aggregate QA were exposed before rule design. LOCO is internal stress testing, not independent generalization validation. After initial replay, synthetic tests tightened source word boundaries, negation and conditional clauses; earlier artifacts retained. No rule or grid was optimized using held-out scores.',
        folds=folds,out_of_fold=full,strict_initial_input_match=dict(n=len(strict),summary=evaluate(strict,out_of_fold)),
        fixed_default_policy_development_replay=evaluate(rows,predictions[.75]),
        fixed_policy_notice='Default .75 was specified before replay; this is fully exposed development data, separate from OOF. It is not an independent estimate.',
        alignment_notice='Only same original Run/question/Build pair is scored. Main replay uses independently sampled analyses; strict subset additionally matches analysis, channels and initial candidates. Exact new answer wire is unmeasured; expanded normalization/time metadata may differ. Both are counterfactual selected-outcome simulations.',
        missing_initial_observations=missing,feature_compute=feature_compute,known_regression_exposure=risks,
        path_counts=dict(Counter(d['decision']['path'] for d in decisions)),
        reason_counts=dict(Counter(reason for d in decisions for reason in d['decision']['reason_codes'])),
        decision_artifact=dict(path=str((controlled/'router-decisions.json').resolve()),sha256=file_sha(controlled/'router-decisions.json')),
        code_sha256={str(p):file_sha(p) for p in (Path(__file__),Path(__file__).with_name('router.py'))},
        semantic_quality='Full-denominator severe errors, incorrect refusals and citation semantics not evaluated; cannot approve production adoption.')
    write(output/'router-simulation.json',result)
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('runtime','controlled','output'):p.add_argument('--'+name,required=True,type=Path)
    result=run(**vars(p.parse_args()));print(json.dumps(dict(result=result['out_of_fold'],alignment=result['strict_initial_input_match'],reasons=result['reason_counts']),indent=2))
