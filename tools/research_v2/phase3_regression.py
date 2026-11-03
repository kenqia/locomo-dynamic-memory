"""Fixed development diagnosis set with hash-bound original source and wire links."""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path

from .postbaseline import (BASELINE, REPAIR, RUNS, at, file_sha, item_ref, load_ledger,
                          needs_review, readonly, sha, trace_lineage, write)


def wire_payload(runtime, record):
    name=record['wire_path']
    if Path(name).name!=name:raise ValueError('Wire path escapes observer')
    path=runtime/'observer'/name
    raw=path.read_bytes()
    if sha(raw)!=record['request_sha256']:raise ValueError('Wire changed')
    body=json.loads(raw)
    return json.loads(body['messages'][1]['content'])


def run(runtime, atlas, controlled, output):
    runtime,atlas,controlled,output=map(Path,(runtime,atlas,controlled,output))
    case_dir=controlled/'regression';case_dir.mkdir(mode=0o700)
    reviews={r['case_id']:r for r in map(json.loads,(atlas/'reviewed-v3/reviewed-items.jsonl').open())}
    findings=json.loads((atlas/'supported-ai-findings.json').read_text())
    patterns={c['case_id']:f['pattern'] for f in findings for c in f['cases']}
    selected={cid for cid,r in reviews.items() if needs_review(r['primary']) or r.get('crosscheck')}
    selected.update(f'{REPAIR}:{i}' for i in range(8))
    failures=json.loads((output/'dynamic-failures.json').read_text())
    selected.update(f'{BASELINE}:{f["ordinal"]}' for f in failures)
    ledger=load_ledger(runtime/'observer/budget.sqlite3');physical=defaultdict(list)
    for r in ledger:
        if r.get('scope')=='development-query':physical[(r.get('run_id'),r.get('question_id'),r.get('strategy'))].append(r)
    dbpath=runtime/'memory.sqlite3';dbhash=file_sha(dbpath);index=[]
    with readonly(dbpath) as db:
        metas={rid:json.loads(db.execute('SELECT result_json FROM evaluation_runs WHERE run_id=?',(rid,)).fetchone()[0]) for rid in RUNS}
        for cid in sorted(selected):
            rid,ordinal=cid.split(':');ordinal=int(ordinal)
            raw=db.execute('SELECT item_json FROM evaluation_run_items WHERE run_id=? AND ordinal=?',(rid,ordinal)).fetchone()[0]
            item=json.loads(raw);sample=metas[rid]['input']['samples'][item['sample_index']]
            trace=at(item,'/result/trace') or {};wire=physical[(rid,item['question_id'],item['strategy'])]
            review=reviews.get(cid);pattern=patterns.get(cid)
            agreements=(review or {}).get('consensus',{}).get('agreed_fields',{})
            disagreements=(review or {}).get('consensus',{}).get('disagreements',{})
            # Confirmed applies to the engineering error or supported output
            # symptom only, never an inferred upstream semantic root cause.
            status='Confirmed' if item['status']=='failed' or pattern else 'Disputed' if disagreements else 'Suspected' if review else 'Unknown'
            bid=metas[rid]['pins'][sample['sample_id']]
            initial=trace.get('initial') if isinstance(trace.get('initial'),dict) else trace.get('retrieval') or {}
            expanded=trace.get('expanded') if isinstance(trace.get('expanded'),dict) else trace.get('expansion') or {}
            retrieval_mem=[c['memory'] for c in initial.get('initial_candidates',[])]
            initial_mem=trace['initial'] if isinstance(trace.get('initial'),list) else retrieval_mem
            expanded_mem=[c['memory'] for c in expanded.get('candidates',[])]
            if not expanded_mem and isinstance(trace.get('expanded'),list):expanded_mem=trace['expanded']
            stage_sources={s:{sid for m in ms for sid in m.get('source_ids',[])}
                           for s,ms in [('retrieval_pool',retrieval_mem),('initial',initial_mem),('expanded',expanded_mem)]}
            packets=[]
            for r in wire:
                payload=wire_payload(runtime,r)
                # Source availability is a mechanical observation, not proof
                # that every detail was recognized by extraction or generation.
                if r['stage'] in ('Resolution','Answer'):
                    ids={s['source_id'] for s in payload.get('sources',[])}
                    stage_sources.setdefault(r['stage'],set()).update(ids)
                packets.append(dict(request_id=r['request_id'],stage=r['stage'],attempt=r.get('attempt'),
                    semantic_status=r.get('semantic_status'),semantic_error_code=r.get('semantic_error_code'),
                    payload=payload,request_sha256=r['request_sha256'],wire_path=r['wire_path'],
                    response_path=r.get('response_path'),response_sha256=r.get('response_sha256')))
            evidence={}
            for judgment in ('primary','crosscheck'):
                for e in ((review or {}).get(judgment) or {}).get('evidence',[]):evidence[(e['source_id'],e['quote'])]=e
            localization=[]
            for (sid,quote),e in evidence.items():
                saved=db.execute('SELECT text FROM source_turns WHERE source_id=? AND sample_id=?',(sid,sample['sample_id'])).fetchone()
                if not saved or quote not in saved[0]:raise ValueError('Review evidence changed')
                build_memories=[json.loads(r[0]) for r in db.execute('SELECT m.memory_json FROM memories m JOIN memory_sources ms ON m.memory_id=ms.memory_id WHERE m.build_id=? AND ms.source_id=?',(bid,sid))]
                localization.append(dict(source_id=sid,quote=quote,role=e['role'],
                    source_linked_build_memories=build_memories,
                    stages_with_source={s:sid in ids for s,ids in stage_sources.items()},
                    notice='Source linkage/visibility alone does not establish extraction completeness or a semantic root cause.'))
            lineage=trace_lineage(dbpath,dbhash,rid,item,raw,runtime,wire)
            lineage['build_version']['key']['build_id']=bid
            lineage['extracted_memory']['where']['build_id']=bid
            lineage['memory_source_mapping']['where']['build_id']=bid
            case=dict(case_id=cid,status=status,status_scope='Observed engineering/output symptom only; AI-reviewed is not human truth',
                pattern=pattern,question=sample['question'],question_id=item['question_id'],conversation=sample['sample_id'],
                build_id=bid,category=sample['category'],strategy=item['strategy'],run_id=rid,
                original_item=item,original_row_sha256=sha(raw.encode()),source_chain=lineage,
                source_availability=localization,physical_business_packets=packets,independent_ai_review=review,
                confirmed_symptoms=pattern or ((item.get('result') or {}).get('error')),
                upstream_semantic_root_cause='Unknown',
                upstream_engineering_observation=trace.get('error'),
                missing_stages=[s for s in ('Resolution','Answer') if not any(r['stage']==s for r in wire)],
                applicability='Directed development diagnosis; not independent generalization evaluation')
            path=case_dir/(rid+'-'+str(ordinal)+'.json');write(path,case)
            index.append(dict(case_id=cid,question_id=item['question_id'],conversation=sample['sample_id'],
                strategy=item['strategy'],pattern=pattern,status=status,review_disagreements=list(disagreements),
                official_qa=(item.get('result') or {}).get('qa'),upstream_root_cause='Unknown',
                path=str(path.resolve()),sha256=file_sha(path),
                source_chain_availability={s:sorted(ids) for s,ids in stage_sources.items()},
                ai_severe=agreements.get('severe_error'),ai_incorrect_refusal=agreements.get('incorrect_refusal')))
    report=dict(version='phase3-regression-v1',cases=index,status_counts=dict(Counter(r['status'] for r in index)),
        pattern_counts=dict(Counter(r['pattern'] or 'other_review_or_execution_error' for r in index)),
        input_hashes={str(p.resolve()):file_sha(p) for p in (atlas/'supported-ai-findings.json',atlas/'reviewed-v3/reviewed-items.jsonl')},
        notice='Confirmed status refers to frozen observed symptoms. Relative-weekend and letter-count disagreements are preserved verbatim in controlled case files. No score aggregation across Runs.')
    write(output/'failure-regression.json',report)
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('runtime','atlas','controlled','output'):p.add_argument('--'+name,required=True,type=Path)
    result=run(**vars(p.parse_args()));print(json.dumps(dict(cases=len(result['cases']),statuses=result['status_counts'])))
