"""Offline post-execution verification of frozen wires, money and failures."""
from collections import Counter
import hashlib
import json
import sqlite3
import sys
from pathlib import Path
import re

from run import OUT, read, verify, reader_input, fingerprint, durable_json
from meter import RESERVE_MICRO_CNY
from locomo_memory.diagnostics import validation_diagnostics
from locomo_memory.model import request_messages
from locomo_memory.source_reader import SupportedAnswer, bind_supported_answer
from locomo_memory.query_schemas import EvidenceAnswer


def main():
    plan=verify();report=json.loads((OUT/'execution/report.json').read_text())
    cases={c['id']:c for c in read('cases.json')};scheduled={t['id']:t for t in plan['schedule']}
    with sqlite3.connect((OUT/'execution/ledger.sqlite3').as_uri()+'?mode=ro&immutable=1',uri=True) as db:
        db.row_factory=sqlite3.Row
        calls=[dict(r) for r in db.execute('SELECT * FROM calls ORDER BY id')]
        events=[dict(r) for r in db.execute('SELECT * FROM events ORDER BY id')]
    assert report['stop_reason'] is None and report['unsettled_calls']==0
    assert len(calls)==report['physical_http']<=plan['maximum_http']
    assert [c['id'] for c in calls]==list(range(1,len(calls)+1))
    assert len({c['task'] for c in calls})==len(calls)
    assert len(report['items'])==76 and all(t['outcome']=='completed' for t in report['items'])
    cumulative=0;stage_counts=Counter();body_by_stage={};started=0
    for event in events:
        e=json.loads(event['event_json'])
        started+=e.get('status')=='started'
    assert started==len(calls)
    for c in calls:
        assert c['state']=='settled' and c['reserved']==RESERVE_MICRO_CNY
        assert cumulative+c['reserved']<=plan['money_cap_micro_cny']
        u=json.loads(c['usage_json']);assert u['total_tokens']==u['prompt_tokens']+u['completion_tokens']
        assert c['cost']==u['prompt_tokens']*2+u['completion_tokens']*8
        assert hashlib.sha256(c['body_json'].encode()).hexdigest()==c['body_sha256']
        body=json.loads(c['body_json']);assert body['model']=='deepseek-flash' and body['max_tokens']==8192
        assert c['returned_model']=='deepseek-flash' and body['thinking']=={'type':'disabled'}
        count=len(re.findall(r'\w+|[^\w\s]',json.dumps(body['messages'],ensure_ascii=False)))
        assert count<=24000
        assert c['timestamp']<=plan['deadline_utc']
        assert set(json.loads(c['response_json']))=={'status_code','model','usage','choices'}
        assert 'reasoning_content' not in json.loads(c['response_json'])['choices'][0]['message']
        cumulative+=c['cost'];stage=c['task'].split(':')[-1];stage_counts[stage]+=1;body_by_stage[c['task']]=body
    assert cumulative==report['estimated_upper_micro_cny']
    failures=[];technical=Counter();history_budgets=[];answer_omissions=[]
    for task in report['items']:
        result=json.loads((OUT/'execution'/(task['id']+'.json')).read_text())['result']
        if task['kind']=='history':
            technical['history-'+str(task['budget'])+'-'+result['outcome']]+=1
            if 'evidence_budget' in result:
                budget=result['evidence_budget']
                answer_omissions.append(dict(task=task['id'],omitted_memory_ids=budget.get('omitted_memory_ids',[]),truncated=budget['truncated']))
            if 'resolution_budget' in result:
                a=result['resolution_budget'];assert not a['truncated'] and not a['omitted_groups']
                history_budgets.append(dict(case=task['case'],budget=task['budget'],input_proxy=a['input_token_count'],within=a['within_budget']))
            continue
        case=cases[task['case']];catalog,context,wire=reader_input(case)
        initial=body_by_stage[task['id']+':initial']
        assert initial['messages']==request_messages('source_statements',wire,SupportedAnswer)
        for stage in ('initial','revision'):
            technical['reader-'+stage+'-'+result[stage+'_outcome']]+=1
        if result['initial_outcome']=='technical_pass':
            expected={**wire,'candidate_answer':result['initial_wire']}
            from locomo_memory.revised_source_reader import REFINE
            expected['task_instructions']=REFINE
            assert body_by_stage[task['id']+':revision']['messages']==request_messages('source_statements',expected,SupportedAnswer)
        else:
            assert task['id']+':revision' not in body_by_stage
            try:
                bind_supported_answer(catalog,SupportedAnswer.model_validate(result['initial_wire']),context,source_only=True)
            except Exception as error:
                diagnostics=validation_diagnostics(error,EvidenceAnswer)
                code=diagnostics[0]["error_code"];path=diagnostics[0]["field_path"]
                failures.append(dict(task_id=task['id'],case=task['case'],repeat=task['repeat'],strict_replay_rejected=True,error_type=type(error).__name__,error_code=code,field_path=path,provider_http_count=1,refinement_http_count=0))
            else:
                raise AssertionError('failed_binding_no_longer_rejects')
    result=dict(plan_id=plan['id'],frozen_implementation_and_inputs_match=True,physical_http=len(calls),started_checkpoints=started,physical_stage_counts=dict(stage_counts),all_cost_usage_known=True,reservation_verified_before_each_physical_send=True,maximum_pre_send_reservation_plus_known_cost_cny=max(sum(c['cost'] for c in calls[:i])+RESERVE_MICRO_CNY for i in range(len(calls)))/1000000,estimated_peak_upper_cny=cumulative/1000000,remaining_money_cap_cny=(plan['money_cap_micro_cny']-cumulative)/1000000,all_actual_wires_within_input_budget=True,initial_exact_frozen_wire_and_revision_exact_observed_initial=True,no_retry_no_replacement_no_recovery=True,technical_outcomes=dict(technical),strict_failure_replays=failures,historical_resolution_budgets=history_budgets,historical_answer_omissions=answer_omissions,all_source_omission_lists_empty=all(not a["omitted_memory_ids"] and not a["truncated"] for a in answer_omissions),live_calls_by_this_audit=0,semantic_gain_established=False)
    durable_json(OUT/(sys.argv[1] if len(sys.argv)>1 else 'execution-audit-final.json'),result)
    print(json.dumps({k:v for k,v in result.items() if k not in {'strict_failure_replays','historical_resolution_budgets'}},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
