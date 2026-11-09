"""Frozen synthetic items, ledgers and sources only; no reference Gold or live API."""
import json
import sqlite3

import httpx
import pytest

from locomo_memory.config import Settings
from tools.m5 import level_e_reporting as report
from tools.m5 import level_e as e
from tools.m5 import level_c_semantic_review as semantic
from test_m5_level_e import final_lock, authorized_prepare
from test_queries import query_provider
from test_retrieval import ControlledEmbedder


def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value))


@pytest.fixture
def frozen(tmp_path,monkeypatch):
    stage=tmp_path/'stage';stage.mkdir()
    settings=Settings(model_max_tokens=32768,resolution_input_budget=192000,
        **{field:'disabled' for field in e.EFFORTS})
    plan=dict(questions=2,planned_items=4,policy=e.policy_for(2,settings))
    lock=dict(exports={conv:dict(dataset_id='synthetic') for conv in e.HOLDOUT})
    items=[]
    for conv in e.HOLDOUT:
        for arm in e.ARMS:
            names=('query_analysis','answer') if arm==e.ARMS[0] else ('query_analysis','resolve','answer')
            operations={name:dict(calls=[dict(attempt=1,status='succeeded',outcome='succeeded',
                elapsed_seconds=.5,usage=dict(prompt_tokens=10,completion_tokens=2,total_tokens=12),
                response_received=True,requested_model='deepseek-flash',thinking={'type':'disabled'},reasoning_effort=None)]) for name in names}
            answer=dict(status='sufficient',answer='PRIVATE_ANSWER',explanation=None,
                citations=[dict(memory_id='memory',source_ids=[conv+'/source'])])
            items.append(dict(question_id=conv+':qa:0',sample_id=conv,qa_index=0,question='PRIVATE_QUESTION',
                arm=arm,outcome='succeeded',prediction='PRIVATE_ANSWER',trace=dict(operations=operations,
                answer=answer,elapsed_seconds=4 if arm==e.ARMS[0] else 6,
                stage_seconds=dict(retrieval=1,expansion=.2,resolve=2,answer=3))))
        with sqlite3.connect(stage/(conv+'.sqlite3')) as db:
            db.execute('CREATE TABLE conversations(dataset_id,sample_id,turn_count)')
            db.execute('INSERT INTO conversations VALUES(?,?,?)',('synthetic',conv,1))
            db.execute('CREATE TABLE source_turns(source_id,dataset_id,sample_id,session_id,dia_id,speaker,session_time,text,position)')
            db.execute('INSERT INTO source_turns VALUES(?,?,?,?,?,?,?,?,?)',
                (conv+'/source','synthetic',conv,'1','D1:1','Alex','2023-01-01','PRIVATE_SOURCE answer evidence',0))
    save(stage/'plan.json',plan);save(stage/'execution-started.json',{'synthetic':True})
    save(stage/'generation-freeze.json',{'synthetic':True})
    e.BudgetTransport(stage/'physical-requests.sqlite3',None,**plan['policy'])
    def ledger():
        with sqlite3.connect(stage/'physical-requests.sqlite3') as db:
            db.execute('DELETE FROM physical_requests')
            for index,(_,_,call) in enumerate(report.records(items)):
                db.execute('INSERT INTO physical_requests VALUES(?,?,?,?)',
                    (str(index),'.01','response_received',json.dumps(call['usage'])))
    ledger()
    monkeypatch.setattr(e,'frozen_items',lambda path:(plan,lock,items))
    return stage,plan,items,ledger


def test_audit_attributes_only_closed_serial_records_and_reports_latency(frozen):
    stage,_,_,_=frozen
    result=report.audit(stage)
    assert result['completed_adapter_records']==result['ledger']['physical_ledger_requests']==10
    assert result['reservation_attribution']=='complete_serial_order_and_usage_verified'
    hybrid=result['groups']['all/'+e.ARMS[0]]
    dynamic=result['groups']['all/dynamic']
    assert hybrid['costs']['all_attempts']['physical_reservations']['reserved_usd']=='0.04'
    assert dynamic['costs']['all_attempts']['physical_reservations']['reserved_usd']=='0.06'
    assert result['dynamic_hybrid_reservation_ratio']=='1.5'
    assert hybrid['elapsed_seconds']['p50']==hybrid['elapsed_seconds']['p95']==4
    assert dynamic['elapsed_seconds']['p50']==6
    assert hybrid['costs']['retries']['adapter_reported']['attempts']==0
    assert result['resources']['cpu_seconds']=='not_measured'
    assert result['storage']['bytes']['stage_total_bytes']>0
    assert all(value not in json.dumps(result) for value in ('PRIVATE_QUESTION','PRIVATE_ANSWER','PRIVATE_SOURCE'))


def test_retries_failed_items_and_partial_usage_keep_reservations(frozen):
    stage,_,items,ledger=frozen
    item=items[0];item['outcome']='failed'
    call=item['trace']['operations']['answer']['calls'][0]
    call.update(outcome='invalid_output',status='invalid_output',attempt=2,usage={'prompt_tokens':10})
    ledger()
    result=report.audit(stage);hybrid=result['groups']['all/'+e.ARMS[0]]
    assert hybrid['failed']==1 and hybrid['planned']==2
    assert hybrid['costs']['retries']['physical_reservations']['physical_requests']==1
    assert hybrid['costs']['failed_attempts']['physical_reservations']['reserved_usd']=='0.01'
    assert hybrid['costs']['failed_item_attempts']['physical_reservations']['physical_requests']==2
    assert result['ledger']['unknown_usage_requests']==1
    assert hybrid['costs']['all_attempts']['physical_reservations']['unknown_reserved_usd']=='0.01'
    assert hybrid['token_efficiency']['reported_tokens_per_successful_item']['prompt_tokens']==40


@pytest.mark.parametrize('kind',['orphan','unknown_item','usage_mismatch','reserved'])
def test_uncertain_attribution_never_guesses_arm_reservations(frozen,kind):
    stage,_,items,_=frozen
    if kind=='unknown_item':items[0]['outcome']='unknown'
    else:
        with sqlite3.connect(stage/'physical-requests.sqlite3') as db:
            if kind=='orphan':db.execute("INSERT INTO physical_requests VALUES('orphan','.03','transport_unknown','null')")
            elif kind=='reserved':db.execute("UPDATE physical_requests SET status='reserved' WHERE id='0'")
            else:db.execute("UPDATE physical_requests SET usage_json='{}' WHERE id='0'")
    result=report.audit(stage)
    assert result['dynamic_hybrid_reservation_ratio']=='not_measured'
    assert result['groups']['all/'+e.ARMS[0]]['costs']['all_attempts']['physical_reservations']=='not_measured'
    assert result['unattributed_physical_requests']==result['ledger']['physical_ledger_requests']
    if kind=='orphan':assert result['ledger']['unknown_usage_reserved_usd']=='0.03'


def test_complete_freeze_gate_runs_before_any_ledger_or_evidence_access(frozen,monkeypatch,tmp_path):
    stage,_,_,_=frozen
    def reject(_):raise ValueError('synthetic_freeze_incomplete')
    monkeypatch.setattr(e,'frozen_items',reject)
    monkeypatch.setattr(e,'readonly',lambda path:pytest.fail('opened evidence before freeze'))
    monkeypatch.setattr(report.runtime,'readonly',lambda path:pytest.fail('opened ledger before freeze'))
    with pytest.raises(ValueError,match='freeze_incomplete'):report.audit(stage)
    with pytest.raises(ValueError,match='freeze_incomplete'):report.prepare_review(stage,tmp_path/'reviews')


def test_whole_process_resource_sidecar_requires_identity_and_scope(frozen,tmp_path):
    stage,_,_,_=frozen
    path=tmp_path/'resources.json'
    data=dict(version='m5-level-e-process-resource-v1',scope='whole_launcher_process_children',
        plan_sha256=e.sha(stage/'plan.json'),execution_started_sha256=e.sha(stage/'execution-started.json'),
        exit_code=0,gpu_sampling='not_measured',wall_seconds=10,children_user_cpu_seconds=2,
        children_system_cpu_seconds=1,children_peak_rss_kib=1024)
    save(path,data);value=report.audit(stage,path)['resources']
    assert value['children_peak_rss_kib']==1024 and value['per_arm_cpu_rss']=='not_measured'
    data['plan_sha256']='different';save(path,data)
    with pytest.raises(ValueError,match='resource_binding_changed'):report.audit(stage,path)


def completed_row(unit):
    return dict(unit_id=unit['unit_id'],reviewer='independent synthetic reviewer',provenance='synthetic',
        review_kind='ai_assisted_independent',independent_of_generation=True,all_factual_claims_checked=True,
        answer_kind='answered',source_support='supported',citation_support='supported',abstention='not_applicable',
        **{field:False for field in semantic.ERRORS},source_quotes=[dict(source_id=unit['conversation_id']+'/source',
            quote='answer evidence',rationale='Synthetic support.',purpose='support',targets=['source_support','citation_support'])],
        rationale='Synthetic review.',full_conversation_checked=True,evidence_gap=None)


def test_review_packets_blind_arm_and_scores_and_require_all_units(frozen,tmp_path):
    stage,_,_,_=frozen;directory=tmp_path/'reviews'
    result=report.prepare_review(stage,directory)
    assert result['planned']==result['unreviewed']==4
    packet=json.loads((directory/'packets.json').read_text())
    assert len(packet['conversations'])==2 and len(packet['units'])==4
    assert not any('arm' in u or 'question_id' in u or 'qa' in u or 'score' in u for u in packet['units'])
    path=directory/'review-template.json'
    pending=report.validate_review(stage,directory,path)
    assert not pending['completed'] and pending['overall']['unreviewed']==4
    with pytest.raises(ValueError,match='complete_independent'):report.validate_review(stage,directory,path,True)
    value=json.loads(path.read_text());value['units']=[completed_row(u) for u in packet['units']];save(path,value)
    scored=report.validate_review(stage,directory,path,True)
    assert scored['completed'] and scored['overall']['source_support']['rate']==1
    assert all(v not in json.dumps(scored) for v in ('PRIVATE_QUESTION','PRIVATE_ANSWER','PRIVATE_SOURCE','answer evidence'))


@pytest.mark.parametrize('kind',['cross_conversation','missing_citation','false_abstention','correct_abstention_without_gap'])
def test_review_requires_verbatim_scoped_evidence_and_abstention_contracts(frozen,tmp_path,kind):
    stage,_,_,_=frozen;directory=tmp_path/'reviews';report.prepare_review(stage,directory)
    packet=json.loads((directory/'packets.json').read_text());path=directory/'review-template.json'
    value=json.loads(path.read_text());value['units']=[completed_row(u) for u in packet['units']]
    row=value['units'][0]
    if kind=='cross_conversation':row['source_quotes'][0]['source_id']='foreign/source'
    elif kind=='missing_citation':row['source_quotes'][0]['targets']=['source_support']
    else:
        row['answer_kind']='abstained';row['abstention']='false' if kind=='false_abstention' else 'correct'
        row['full_conversation_checked']=False
    save(path,value)
    with pytest.raises(ValueError):report.validate_review(stage,directory,path,True)


def test_unknown_execution_is_retained_and_not_given_semantic_success(frozen,tmp_path):
    stage,_,items,_=frozen;items[0].update(outcome='unknown',trace={});directory=tmp_path/'reviews'
    report.prepare_review(stage,directory);packet=json.loads((directory/'packets.json').read_text())
    path=directory/'review-template.json';value=json.loads(path.read_text());rows=[]
    for unit in packet['units']:
        row=completed_row(unit)
        if unit['outcome']=='unknown':
            row.update(answer_kind='failed',source_support='not_applicable',citation_support='not_applicable',
                abstention='not_applicable',source_quotes=[],**{field:None for field in semantic.ERRORS})
        rows.append(row)
    value['units']=rows;save(path,value);result=report.validate_review(stage,directory,path,True)
    assert result['overall']['execution_outcomes']['unknown']==1
    assert result['overall']['source_support']['denominator']==3


def test_report_outputs_cannot_target_execution_stage(frozen):
    stage,_,_,_=frozen
    with pytest.raises(ValueError,match='outside_stage'):report.prepare_review(stage,stage/'reviews')


def test_completed_adapter_records_cannot_exceed_physical_ledger(frozen):
    stage,_,_,_=frozen
    with sqlite3.connect(stage/'physical-requests.sqlite3') as db:
        db.execute("DELETE FROM physical_requests WHERE id='0'")
    with pytest.raises(ValueError,match='adapter_records_exceed'):report.audit(stage)


def test_reporting_integrates_with_actual_synthetic_freeze_and_never_opens_gold(tmp_path,final_lock,monkeypatch):
    stage,_,lock=authorized_prepare(tmp_path,final_lock)
    e.execute(stage,httpx.MockTransport(query_provider),ControlledEmbedder())
    reference=type(stage)(lock['reference']['path'])
    before=e.source_storage_identity(reference)
    real=e.frozen_readonly
    def no_reference(path,identity):
        assert path!=reference,'Gold database opened by reporting'
        return real(path,identity)
    monkeypatch.setattr(e,'frozen_readonly',no_reference)
    result=report.audit(stage)
    assert result['planned_items']==8 and result['ledger']['physical_ledger_requests']==20
    assert result['reservation_attribution']=='complete_serial_order_and_usage_verified'
    assert report.prepare_review(stage,tmp_path/'source-reviews')['planned']==8
    assert e.source_storage_identity(reference)==before


def test_canonical_failed_trace_order_does_not_swap_identical_usage_reservations(frozen):
    stage,_,items,_=frozen
    item=items[1];item['outcome']='failed'
    item['trace']['operations']['answer']['calls'][0].update(status='invalid_output',outcome='invalid_output',attempt=2)
    item['trace']=json.loads(json.dumps(item['trace'],sort_keys=True))
    assert list(item['trace']['operations'])==['answer','query_analysis','resolve']
    # All usage fields are identical, so usage alone cannot detect wrong ordering.
    with sqlite3.connect(stage/'physical-requests.sqlite3') as db:
        db.execute("UPDATE physical_requests SET reserved_usd='.017' WHERE id='4'")
        db.execute("UPDATE physical_requests SET reserved_usd='.011' WHERE id='2'")
    result=report.audit(stage)
    cost=result['groups']['all/dynamic']['costs']
    assert cost['failed_attempts']['physical_reservations']['reserved_usd']=='0.017'
    assert cost['retries']['physical_reservations']['reserved_usd']=='0.017'
    assert cost['failed_item_attempts']['physical_reservations']['reserved_usd']=='0.038'


def test_failed_baseline_operation_follows_prior_query_analysis(frozen):
    stage,_,items,_=frozen
    item=items[0];item['outcome']='failed'
    operations=item['trace']['operations'];operations['failed_operation']=operations.pop('answer')
    operations['failed_operation']['calls'][0].update(status='invalid_output',outcome='invalid_output')
    item['trace']=json.loads(json.dumps(item['trace'],sort_keys=True))
    assert [name for current,name,_ in report.records(items) if current is item]==['query_analysis','failed_operation']
    assert report.audit(stage)['reservation_attribution']=='complete_serial_order_and_usage_verified'


def test_review_manifest_binds_postprocessing_helpers(frozen,tmp_path,monkeypatch):
    stage,_,_,_=frozen;directory=tmp_path/'reviews';report.prepare_review(stage,directory)
    monkeypatch.setattr(report,'implementation_hashes',lambda:{'changed':'postprocessor'})
    with pytest.raises(ValueError,match='review_manifest_changed'):
        report.validate_review(stage,directory,directory/'review-template.json')


def test_query_analysis_failure_is_frozen_as_analysis_and_fallback_keeps_all_costs(tmp_path,final_lock,monkeypatch):
    """Exercise the locked retrieval fallback, not a fabricated retrieval key."""
    stage,_,lock=authorized_prepare(tmp_path,final_lock)
    physical=[]
    def analysis_failure(request):
        body=json.loads(request.content)
        payload=json.loads(body['messages'][1]['content'])
        physical.append(payload.get('operation','query_analysis'))
        if 'operation' not in payload:
            return httpx.Response(200,json={'model':'synthetic-model','usage':{
                'prompt_tokens':10,'completion_tokens':2,'total_tokens':12},
                'choices':[{'finish_reason':'stop','message':{'content':'{"unexpected":true}'}}]})
        return query_provider(request)
    freeze=e.execute(stage,httpx.MockTransport(analysis_failure),ControlledEmbedder())
    assert len(physical)==36 and physical.count('query_analysis')==24
    plan,_,items=e.frozen_items(stage)
    assert plan['planned_items']==len(items)==8
    assert all(item['outcome']=='succeeded' for item in items)
    for item in items:
        operations=item['trace']['operations']
        assert 'retrieval' not in operations
        assert len(operations['query_analysis']['calls'])==3
        assert all(call['outcome']=='invalid_output' for call in operations['query_analysis']['calls'])
    reference=type(stage)(lock['reference']['path']);before=e.source_storage_identity(reference)
    real=e.frozen_readonly
    def no_reference(path,identity):
        assert path!=reference,'reporting opened Gold reference'
        return real(path,identity)
    monkeypatch.setattr(e,'frozen_readonly',no_reference)
    result=report.audit(stage)
    assert result['completed_adapter_records']==result['ledger']['physical_ledger_requests']==36
    assert result['reservation_attribution']=='complete_serial_order_and_usage_verified'
    assert result['ledger']['physical_ledger_requests']==freeze['cost']['physical_requests']
    assert sum(result['groups']['all/'+arm]['costs']['retries']['physical_reservations']['physical_requests']
               for arm in e.ARMS)==16
    assert sum(result['groups']['all/'+arm]['costs']['failed_attempts']['physical_reservations']['physical_requests']
               for arm in e.ARMS)==24
    assert e.source_storage_identity(reference)==before
