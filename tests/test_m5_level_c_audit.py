"""Synthetic audit fixtures are not real model or quality results."""
import json
from pathlib import Path
import sqlite3
import sys

import httpx
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools.m5 import level_c as stage
from tools.m5 import level_c_audit as audit
from tools.m5.extraction_recovery import snapshot
from tools.m5.offline import write
from test_m5_level_c import proposal
from test_queries import query_provider
from test_retrieval import ControlledEmbedder


def fake_frozen(output):
    """Write controlled saved metadata; this function makes no provider calls."""
    plan = json.loads((output/'plan.json').read_text())
    inputs = json.loads((output/'inputs.json').read_text())
    hashes, calls = {}, []
    for index, question in enumerate(inputs):
        for arm in stage.ARMS:
            names = ('query_analysis','answer') if arm=='hybrid_no_resolution' else ('query_analysis','resolve','answer')
            trace = dict(build_id=plan['pins'][question['sample_id']],sample_id=question['sample_id'],question=question['question'],
                elapsed_seconds=6 if arm=='dynamic' else 4.25,
                stage_seconds=dict(retrieval=1,expansion=.25,answer=3),operations={},answer=dict(answer='PRIVATE_PREDICTION'))
            if arm=='dynamic':
                trace['stage_seconds']['resolve']=2
            for name in names:
                call = dict(outcome='succeeded',status='succeeded',attempt=1,elapsed_seconds=.5,
                    usage=dict(prompt_tokens=10,completion_tokens=2,total_tokens=12),response_received=True,
                    requested_model='deepseek-flash',returned_model='synthetic-model',max_tokens=32768,
                    thinking=dict(type='disabled'), reasoning_effort=None)
                trace['operations'][name] = dict(calls=[call])
                calls.append(call)
            # One local rejection has no physical resolve or answer attempt.
            rejected = index==0 and arm=='dynamic'
            if rejected:
                calls= calls[:-2]
                trace['operations'].pop('resolve')
                trace['operations'].pop('answer')
                trace['operations']['resolve']=dict(calls=[])
                trace['stage_seconds'].pop('answer')
                trace['stage_seconds']['resolve']=.01
                trace['elapsed_seconds']=1.01
            item = dict(question_id=question['question_id'],sample_id=question['sample_id'],
                stratum=question['stratum'],arm=arm,outcome='failed' if rejected else 'succeeded',
                trace=trace,prediction=None if rejected else 'PRIVATE_PREDICTION')
            if rejected:
                item['error_code']='physical_request_policy_rejected'
            name=f'items/{index:03d}-{arm}.json'
            write(output/name,item)
            hashes[name]=stage.sha(output/name)
    with sqlite3.connect(output/'physical-requests.sqlite3') as db:
        db.executemany('INSERT INTO physical_requests VALUES (?,?,?,?)',[
            (str(i),'.01','response_received',json.dumps(c['usage'])) for i,c in enumerate(calls)])
    write(output/'generation-freeze.json',dict(status='generation_complete',
        plan_sha256=stage.sha(output/'plan.json'),item_hashes=hashes,planned_items=200,
        resources=dict(wall_seconds=123,cpu_seconds=42,process_peak_rss_kib=1000,gpu_used=False)))
    return len(calls)


def test_audit_saved_metadata_keeps_failed_denominator_and_never_reads_gold(proposal,monkeypatch):
    origin,output,_=proposal
    physical=fake_frozen(output)
    before=(snapshot(origin),snapshot(output/'memory.sqlite3'),snapshot(output/'physical-requests.sqlite3'))
    real_readonly=audit.readonly
    def no_gold(path):
        assert path.resolve()!=origin.resolve()
        return real_readonly(path)
    monkeypatch.setattr(audit,'readonly',no_gold)
    result=audit.audit(output)
    after=(snapshot(origin),snapshot(output/'memory.sqlite3'),snapshot(output/'physical-requests.sqlite3'))
    assert before==after
    assert physical==498==result['ledger']['physical_ledger_requests']
    assert result['completed_adapter_attempt_records']==498
    assert result['model_identity']['returned_models']=={'synthetic-model':498}
    assert result['model_identity']['thinking_efforts']==dict(disabled=498)
    group=result['groups']['ordinary/dynamic']
    assert (group['planned'],group['succeeded'],group['failed'],group['local_policy_rejected_items'])==(80,79,1,1)
    assert group['item_elapsed_seconds']['p50']==6
    assert group['item_elapsed_seconds']['p95']==6
    assert group['stage_elapsed_seconds']['answer']['missing']==1
    assert group['operations']['resolve']['completed_adapter_attempt_records']==79
    assert result['ledger']['reported_usage']['prompt_tokens']==4980
    assert result['ledger']['known_complete_usage_peak_cache_miss_upper_usd']=='0.0026892'
    assert result['integrity']['initial_logical_snapshot_reconstructed'] is True
    assert 'PRIVATE_PREDICTION' not in json.dumps(result)
    assert 'HIDDEN_GOLD' not in json.dumps(result)


def test_unknown_ledger_reservations_remain_distinct_from_started_diagnostics(proposal):
    _,output,plan=proposal
    fake_frozen(output)
    with sqlite3.connect(output/'physical-requests.sqlite3') as db:
        db.executemany('INSERT INTO physical_requests VALUES (?,?,?,?)',[
            ('unknown-a','.03','transport_unknown','null'),
            ('unknown-b','.02','reserved','null'),
            ('unknown-c','.04','response_received','{"prompt_tokens":100}'),
            ('unknown-d','.05','response_usage_unknown','{}')])
    result=audit.audit(output)
    ledger=result['ledger']
    assert ledger['physical_ledger_requests']==502
    assert ledger['unknown_usage_requests']==4 and ledger['partial_usage_requests']==1
    assert ledger['unknown_usage_reserved_usd']=='0.14'
    assert ledger['all_reported_fields_peak_cache_miss_upper_usd']=='0.0027192'
    assert ledger['reservations_by_status_usd']['transport_unknown']=='0.03'
    assert result['ledger_requests_without_completed_adapter_record']==4
    fake=dict(arm='dynamic',stratum='ordinary',outcome='failed',error_code='physical_request_policy_rejected',
        trace=dict(operations=dict(resolve=dict(calls=[dict(status='started',response_received=False)]))))
    stats=audit.summaries([fake])['ordinary/dynamic']['operations']['resolve']
    assert stats['completed_adapter_attempt_records']==0 and stats['unresolved_started_records']==1
    assert stats['usage']['generation_calls']==0


@pytest.mark.parametrize('mutation',['memory','source','relation','projection','index','new_table','evaluation'])
def test_protected_data_or_unexpected_tables_rejected(proposal,mutation):
    _,output,_=proposal
    fake_frozen(output)
    statements=dict(memory="UPDATE memories SET content='CHANGED'",
        source="UPDATE source_turns SET text='CHANGED'",relation="UPDATE memory_relations SET label='CONFLICT'",
        projection="UPDATE current_state_projections SET fingerprint='CHANGED'",
        index="UPDATE index_entries SET index_text='CHANGED'",new_table='CREATE TABLE unexpected(payload TEXT)',
        evaluation='CREATE TABLE evaluation_inputs(input_id TEXT,result_json TEXT)')
    with sqlite3.connect(output/'memory.sqlite3') as db:
        db.execute(statements[mutation])
        if mutation=='evaluation':
            db.execute("INSERT INTO evaluation_inputs VALUES ('fake','HIDDEN_GOLD')")
    with pytest.raises(ValueError,match='audit_'):
        audit.audit(output)


def test_progress_needs_no_freeze_and_opens_no_database(proposal,monkeypatch):
    _,output,plan=proposal
    question=json.loads((output/'inputs.json').read_text())[0]
    item=dict(question_id=question['question_id'],sample_id=question['sample_id'],stratum='ordinary',
        arm='hybrid_no_resolution',outcome='failed',error_code='physical_request_budget_exhausted')
    write(output/'items/000-hybrid_no_resolution.json',item)
    (output/'items/000-dynamic.json').write_text('{')
    monkeypatch.setattr(audit,'readonly',lambda path:pytest.fail('progress opened SQLite'))
    result=audit.progress(output)
    assert result['completed_items']==1 and result['incomplete_item_files']==1
    assert result['groups']['ordinary/hybrid_no_resolution']['planned']==80
    assert result['groups']['ordinary/hybrid_no_resolution']['failed']==1
    assert result['groups']['ordinary/dynamic']['pending']==80
    with pytest.raises(FileNotFoundError):
        audit.audit(output)


def test_actual_mock_query_pipeline_and_dynamic_checkpoint_integrity(proposal):
    _,output,_=proposal
    write(output/'authorization.json',stage.expected_authorization(output))
    stage.execute(output,httpx.MockTransport(query_provider),ControlledEmbedder())
    result=audit.audit(output)
    assert result['items']==200 and result['ledger']['physical_ledger_requests']==500
    assert result['integrity']['dynamic_trace_checkpoints_verified']==100
    assert result['integrity']['query_table_counts']==dict(candidate_queries=200,candidate_expansions=200,query_traces=100)
    assert all(g['failed']==0 for g in result['groups'].values())
    with sqlite3.connect(output/'memory.sqlite3') as db:
        saved=db.execute('SELECT query_id,result_json FROM candidate_queries LIMIT 1').fetchone()
        db.execute("UPDATE candidate_queries SET result_json='{}' WHERE query_id=?",(saved[0],))
    with pytest.raises(ValueError,match='audit_candidate_checkpoint_changed'):
        audit.audit(output)
    with sqlite3.connect(output/'memory.sqlite3') as db:
        db.execute('UPDATE candidate_queries SET result_json=? WHERE query_id=?',(saved[1],saved[0]))
        db.execute("UPDATE query_traces SET result_json='{}' WHERE trace_id=(SELECT trace_id FROM query_traces LIMIT 1)")
    with pytest.raises(ValueError,match='audit_dynamic_trace_checkpoint_changed'):
        audit.audit(output)


@pytest.mark.parametrize('mutation',[
    {'question':'DIFFERENT_SYNTHETIC_QUESTION'},
    {'question_id':'conv-26:qa:999'},
    {'strategy':'dynamic_raw_fallback'},
    {'m5_variant':{'adaptive':True,'compression':True}},
    {'initial':{'question':'DIFFERENT_CANDIDATE_QUESTION'}},
    {'retrieval':{'m5_route':{'kind':'state'}}},
    {'expanded':{'m5_graph':{'depth':2}}},
    {'operations':{'answer':{'m5_compression':[]}}},
    {'raw_fallback':{'triggered':False}},
    {'strategy_recovery':{}},
    {'raw_context':[{'source_id':'unexpected-raw-evidence'}]},
])
def test_trace_question_and_strategy_scope_reject_review_reproductions(mutation):
    inputs=[dict(question_id='conv-26:qa:0',sample_id='conv-26',stratum='ordinary',question='Actual fixed question')]
    plan=dict(pins={conv:'build-'+conv for conv in stage.DEV},bonus_enabled=False,holdout_read=False,gold_read=False)
    item=dict(question_id=inputs[0]['question_id'],sample_id='conv-26',stratum='ordinary',arm='hybrid_no_resolution',outcome='failed',trace=dict(mutation))
    with pytest.raises(ValueError,match='audit_'):
        audit.scope_check(plan,[item],inputs)


def test_scope_accepts_baseline_empty_raw_context_and_normal_dynamic_fields():
    inputs=[dict(question_id='conv-26:qa:0',sample_id='conv-26',stratum='ordinary',question='Actual fixed question')]
    plan=dict(pins={conv:'build-'+conv for conv in stage.DEV},bonus_enabled=False,holdout_read=False,gold_read=False)
    trace=dict(question='Actual fixed question',strategy='hybrid_no_resolution',raw_context=[],
        expansion=dict(question='Actual fixed question',state_history_enabled=True,relation_depth=1),
        sources=[dict(caption=dict(question='Caption label, not a query field'))])
    item=dict(question_id=inputs[0]['question_id'],sample_id='conv-26',stratum='ordinary',arm='hybrid_no_resolution',outcome='failed',trace=trace)
    audit.scope_check(plan,[item],inputs)
    item.pop('trace')  # Failure before query initiation has no invented fields.
    audit.scope_check(plan,[item],inputs)
    item['outcome']='succeeded'
    with pytest.raises(ValueError,match='audit_success_without_trace'):
        audit.scope_check(plan,[item],inputs)


def test_model_summary_missing_response_version_and_controlled_names(proposal):
    _,output,_=proposal
    fake_frozen(output)
    path=output/'items/000-hybrid_no_resolution.json'
    item=json.loads(path.read_text())
    item['trace']['operations']['query_analysis']['calls'][0]['returned_model']=None
    item['trace']['operations']['answer']['calls'][0]['returned_model']='DeepSeek-V4.1-Flash-1017'
    path.write_text(json.dumps(item))
    freeze_path=output/'generation-freeze.json'
    freeze=json.loads(freeze_path.read_text())
    freeze['item_hashes']['items/000-hybrid_no_resolution.json']=stage.sha(path)
    freeze_path.write_text(json.dumps(freeze))
    result=audit.audit(output)
    models=result['model_identity']
    assert models['requested_models']=={'deepseek-flash':498}
    assert models['calls_without_returned_model']==1
    assert models['returned_models']=={'synthetic-model':496,'DeepSeek-V4.1-Flash-1017':1}
    assert models['thinking_efforts']==dict(disabled=498)
    item['trace']['operations']['answer']['calls'][0]['returned_model']='PRIVATE VALUE WITH SPACES'
    path.write_text(json.dumps(item))
    freeze['item_hashes']['items/000-hybrid_no_resolution.json']=stage.sha(path)
    freeze_path.write_text(json.dumps(freeze))
    with pytest.raises(ValueError,match='audit_invalid_returned_model'):
        audit.audit(output)


@pytest.mark.parametrize('effort',['low','high'])
@pytest.mark.parametrize('operation',['query_analysis','resolve','answer'])
def test_v2_audit_rejects_enabled_thinking_in_any_saved_operation(proposal,effort,operation):
    _,output,_=proposal
    fake_frozen(output)
    # Index 1 avoids the deliberately rejected Dynamic item at index 0.
    name='items/001-dynamic.json'
    path=output/name
    item=json.loads(path.read_text())
    call=item['trace']['operations'][operation]['calls'][0]
    call.update(thinking=dict(type='enabled'),reasoning_effort=effort)
    path.write_text(json.dumps(item))
    freeze_path=output/'generation-freeze.json'
    freeze=json.loads(freeze_path.read_text())
    freeze['item_hashes'][name]=stage.sha(path)
    freeze_path.write_text(json.dumps(freeze))
    with pytest.raises(ValueError,match='audit_thinking_policy_changed'):
        audit.audit(output)


def test_v2_audit_does_not_accept_disabled_effort_with_enabled_thinking(proposal):
    _,output,_=proposal
    fake_frozen(output)
    name='items/001-dynamic.json'
    path=output/name
    item=json.loads(path.read_text())
    item['trace']['operations']['resolve']['calls'][0].update(
        thinking=dict(type='enabled'),reasoning_effort='disabled')
    path.write_text(json.dumps(item))
    freeze_path=output/'generation-freeze.json'
    freeze=json.loads(freeze_path.read_text())
    freeze['item_hashes'][name]=stage.sha(path)
    freeze_path.write_text(json.dumps(freeze))
    with pytest.raises(ValueError,match='audit_thinking_policy_changed'):
        audit.audit(output)
