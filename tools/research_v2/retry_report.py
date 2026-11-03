"""Read-only retry report: hashes and measured summaries, never raw provider bodies."""
import argparse
from collections import Counter
import json
from pathlib import Path
import sqlite3

from locomo_memory.experiment import write_json
from tools.research_v2.cache_analysis import rows, aggregate
from tools.research_v2.observer import sha


def report(directory):
    records=rows(directory)
    outcome=json.loads((directory/'execution-outcome.json').read_text())
    identity=json.loads((directory/'execution-identity.json').read_text())
    parent=Path(identity['retry_parent'])
    original=json.loads((parent/'execution-outcome.json').read_text())
    run_path=directory/'runs'/outcome['run_id']/'run.json'
    run=json.loads(run_path.read_text())
    build=json.loads((directory/'builds'/outcome['build_id']/'build.json').read_text())
    with sqlite3.connect((directory/'observer/budget.sqlite3').resolve().as_uri()+'?mode=ro',uri=True) as db:
        policy=json.loads(db.execute('SELECT document FROM policy').fetchone()[0])
    with sqlite3.connect((directory/'memory.sqlite3').resolve().as_uri()+'?mode=ro',uri=True) as db:
        memory_count=db.execute('SELECT COUNT(*) FROM memories WHERE build_id=?',(outcome['build_id'],)).fetchone()[0]
        relations=dict(db.execute('SELECT status,COUNT(*) FROM relation_tasks WHERE build_id=? GROUP BY status',(outcome['build_id'],)))
    finishes=Counter()
    exceeded=[]
    for r in records:
        for field, path_field in [('request_sha256','wire_path'),('response_sha256','response_path')]:
            if r.get(path_field) and sha((directory/'observer'/r[path_field]).read_bytes())!=r[field]:
                raise ValueError('Artifact hash mismatch')
        if r.get('response_path'):
            doc=json.loads((directory/'observer'/r['response_path']).read_text())
            finishes.update(c.get('finish_reason','missing') for c in doc.get('choices',[]))
        if (r['usage'].get('completion_tokens') or 0)>8192:
            exceeded.append({k:r.get(k) for k in ('request_id','stage','task_id','semantic_status','usage','request_sha256','response_sha256')})
    items=[]
    failures=[]
    for item in run['items']:
        result=item['result'];trace=result.get('trace',{})
        record={k:item[k] for k in ('ordinal','qa_index','question_id','sample_id','strategy','status')}
        record.update(run_id=run['run_id'],build_id=outcome['build_id'],attempt_count=len(item['attempts']),
                      error_code=result.get('error',{}).get('code'),qa=result.get('qa'),
                      source_coverage=result.get('source_coverage'),trace_sha256=sha(json.dumps(trace,sort_keys=True).encode()),
                      artifact_path=str(run_path),artifact_sha256=sha(run_path.read_bytes()))
        if item['status']=='failed':
            audit=trace.get('resolution_budgets',{}).get('resolve',{})
            record['budget_audit']={k:audit.get(k) for k in ('input_budget','input_token_count','input_policy_version','within_budget','truncated','omitted_groups')}
            record['source_delivery']={k:audit.get('source_delivery',{}).get(k) for k in ('status','error_code')}
            record['expected_sources']=len(audit.get('source_delivery',{}).get('expected_source_ids',[]))
            record['delivered_sources']=len(audit.get('source_delivery',{}).get('delivered_source_ids',[]))
            record['failure_attribution']='Confirmed pre-provider resolution input budget rejection; no conclusion about model reasoning or extraction semantics.'
            failures.append(record)
        items.append(record)
    retries=[r for r in records if (r.get('attempt') or 0)>1]
    intervals=sorted([(r['reserved_at'],1) for r in records]+[(r.get('response_observed_at',r['reserved_at']),-1) for r in records])
    active=maximum=0
    for _,step in intervals: active+=step; maximum=max(maximum,active)
    known=sum(r['cost_nano_cny'] or 0 for r in records)
    timestamps=[r['reserved_at'] for r in records]
    done=[r.get('response_observed_at',r['reserved_at']) for r in records]
    accepted=(run['status']=='completed' and run['progress']['succeeded']==20
              and outcome.get('structural_acceptance','').startswith('passed'))
    prior_http=original.get('cumulative_physical_requests',original['physical_requests'])
    prior_cost=original.get('cumulative_peak_upper_cny',original['known_peak_upper_cny'])
    return dict(status=run['status'],smoke_accepted=accepted,build_id=outcome['build_id'],run_id=run['run_id'],
        execution_identity_sha256=sha((directory/'execution-identity.json').read_bytes()),frozen_code_files=identity['code_files'],
        runtime_config=identity['config'],build_status=build['status'],memories=memory_count,relations=relations,
        progress=run['progress'],overall=run['overall_summary'],by_strategy=run['summary'],grouped=run['grouped_summary'],
        physical_requests=len(records),prior_physical_requests=prior_http,
        cumulative_physical_requests=len(records)+prior_http,
        known_peak_upper_cny=known/1e9,prior_peak_upper_cny=prior_cost,
        cumulative_peak_upper_cny=known/1e9+prior_cost,
        published_offpeak_calculation_cny=known/2e9,invoice_verified=False,
        unknown_requests=sum(r['status']!='settled' for r in records),retry_requests=len(retries),retry_peak_cny=sum(r['cost_nano_cny'] or 0 for r in retries)/1e9,
        response_finish_reasons=dict(finishes),outputs_above_original_limit=exceeded,max_completion=max(r['usage']['completion_tokens'] or 0 for r in records),
        maximum_physical_concurrency=maximum,original_policy=policy,
        new_physical_window_seconds=max(done)-min(timestamps),original_budget_elapsed_seconds=max(done)-policy['started'],
        by_stage={stage:aggregate([r for r in records if r['stage']==stage]) for stage in ('Extraction','Relation','Query Analysis','Resolution','Answer')},
        failures=failures,items=items,
        evidence_correctness='Not semantically reviewed; source coverage and valid citation IDs are not proof of factual correctness.',
        full_baseline_started=False)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--directory',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    result=report(a.directory.resolve())
    write_json(a.output,result)
    manifest=a.output.with_suffix('.items.jsonl')
    manifest.write_text(''.join(json.dumps(i,sort_keys=True)+'\n' for i in result['items']))
    print(json.dumps({k:result[k] for k in ('status','smoke_accepted','physical_requests','known_peak_upper_cny','cumulative_peak_upper_cny','response_finish_reasons','max_completion','maximum_physical_concurrency')}))
