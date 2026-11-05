"""Synthetic closed failures only; never open a live or frozen experiment stage."""
import json
import sqlite3

import httpx
import pytest

from tools.m5 import conv44_relation_recovery as recovery
from tools.m5 import conv44_relations as r
from tools.m5 import conv44_successor as successor
from tools.m5.offline import write
from test_m5_conv44_successor import seeded
from test_m5_extraction_recovery import prepared
from test_m5_conv44_relations import provider
from test_builds import completion,draft
from test_retrieval import ControlledEmbedder


def terminal(stage,path,version,status):
    plan=json.loads((stage/'plan.json').read_text())
    files=dict(plan_sha256='plan.json',settings_sha256='settings.json',inheritance_sha256='inheritance.json',
        authorization_sha256='authorization.json',outcome_sha256='outcome.json')
    write(path,dict(version=version,status=status,build_id=plan['build_id'],checks={'synthetic':True},
        **{key:r.sha(stage/name) for key,name in files.items()},
        final_database_logical_snapshot=r.snapshot(stage/'memory.sqlite3'),
        final_ledger_logical_snapshot=r.snapshot(stage/'physical-requests.sqlite3')))


@pytest.fixture
def failed(seeded,tmp_path,monkeypatch):
    _,source,plan=seeded
    write(source/'authorization.json',successor.authorization(source))
    def extract(request):
        payload=json.loads(json.loads(request.content)['messages'][1]['content'])
        return completion({'memories':[draft([payload['sources'][0]['source_id']]) for _ in range(2)]})
    successor.execute(source,httpx.MockTransport(extract))
    extracted_terminal=tmp_path/'extracted-terminal.json'
    terminal(source,extracted_terminal,successor.VERSION+'-terminal-v1','extracted_not_complete')
    monkeypatch.setattr(r,'BASE_POLICY',{**r.BASE_POLICY,'max_output_tokens':8192})
    indexed=tmp_path/'index';r.index(source,extracted_terminal,indexed,ControlledEmbedder())
    parent=tmp_path/'parent';r.prepare(indexed,parent);write(parent/'authorization.json',r.authorization(parent))
    def partial(request):
        payload=json.loads(json.loads(request.content)['messages'][1]['content'])
        if len(payload['history'])==1:return provider(request)
        raw=provider(request).json();value=json.loads(raw['choices'][0]['message']['content'])
        value['judgments'][0]['source_ids'].append('unknown-synthetic-id')
        return completion(value)
    with pytest.raises(RuntimeError):r.execute(parent,httpx.MockTransport(partial))
    final=tmp_path/'parent-terminal.json';terminal(parent,final,recovery.PARENT_TERMINAL,'relations_failed_not_complete')
    return parent,final


@pytest.fixture
def staged(failed,tmp_path):
    source,final=failed;stage=tmp_path/'relation-recovery'
    plan=recovery.prepare(source,final,stage)
    return source,final,stage,plan


def authorize(stage):write(stage/'authorization.json',recovery.authorization(stage))


def test_prepare_only_requeues_failed_task_and_independent_zero_budget(staged):
    source,final,stage,p=staged
    assert len(p['failed_tasks'])==1 and p['policy']['max_requests']==3
    assert not p['wire_contract_in_build_fingerprint'] and p['mixed_relation_input_producers']
    assert r.source_identity(source)==p['source_identity']
    with r.readonly(stage/'physical-requests.sqlite3') as db:assert db.execute('SELECT COUNT(*) FROM physical_requests').fetchone()[0]==0
    with r.readonly(stage/'memory.sqlite3') as db:
        assert [x[0] for x in db.execute('SELECT status FROM relation_tasks ORDER BY ordinal')]==['succeeded','pending']
        assert [x[0] for x in db.execute('SELECT logical_attempt FROM relation_attempts')]==[1,1]
    with pytest.raises(FileNotFoundError):recovery.execute(stage)
    assert not (stage/'execution-started.json').exists()


@pytest.mark.parametrize('kind',['success','invalid','unknown'])
def test_logical_two_preserves_failed_one_success_rows_and_exact_new_ledger(staged,kind):
    source,final,stage,p=staged;authorize(stage);seen=[]
    def generate(request):
        payload=json.loads(json.loads(request.content)['messages'][1]['content']);seen.append(payload)
        endpoints=[payload['new_memory'],*payload['history']]
        assert payload['endpoint_source_ids']=={m['memory_id']:m['source_ids'] for m in endpoints}
        assert payload['recovery_feedback']['error_code']=='known_source_required'
        if kind=='unknown':raise httpx.ReadTimeout('synthetic')
        return provider(request) if kind=='success' else completion({'judgments':[]})
    if kind=='success':
        outcome=recovery.execute(stage,httpx.MockTransport(generate));assert outcome['status']=='related'
    else:
        with pytest.raises(RuntimeError,match='incomplete_no_automatic_retry'):recovery.execute(stage,httpx.MockTransport(generate))
        outcome=json.loads((stage/'outcome.json').read_text())
    assert outcome['physical_requests']==len(seen)==(1 if kind=='success' else 3)
    if kind=='unknown':assert outcome['unknown_reserved_usd']==outcome['reserved_usd'] and outcome['unknown_usage_requests']==3
    assert r.source_identity(source)==p['source_identity']
    with r.readonly(stage/'memory.sqlite3') as db:
        failed_id=p['failed_tasks'][0]['task_id']
        assert [(x['logical_attempt'],x['status']) for x in db.execute('SELECT * FROM relation_attempts WHERE task_id=? ORDER BY logical_attempt',(failed_id,))]==[(1,'failed'),(2,'succeeded' if kind=='success' else 'failed')]
        call=json.loads(db.execute('SELECT metadata_json FROM relation_provider_calls WHERE task_id=? AND logical_attempt=2 LIMIT 1',(failed_id,)).fetchone()[0])
        assert call['input_contract_version']==recovery.INPUT_VERSION and call['input_wrapper_sha256']==p['script_sha256']
        allcalls=json.loads(db.execute('SELECT model_metadata_json FROM build_versions WHERE build_id=?',(p['build_id'],)).fetchone()[0])['calls']
        assert allcalls[:len(p['initial_metadata']['calls'])]==p['initial_metadata']['calls']
    with pytest.raises(ValueError,match='already_started'):recovery.execute(stage,httpx.MockTransport(generate))


def test_local_rejection_allows_failed_logical_two_with_no_physical(failed,tmp_path,monkeypatch):
    source,final=failed
    # Limit only the newly prepared transport; the immutable parent's policy remains unchanged.
    original=r.policy_for
    def policy(count,settings):
        value=original(count,settings)
        return {**value,'max_input_bytes':1} if count==1 else value
    monkeypatch.setattr(r,'policy_for',policy)
    stage=tmp_path/'local';recovery.prepare(source,final,stage);authorize(stage)
    with pytest.raises(RuntimeError):recovery.execute(stage,httpx.MockTransport(lambda req:pytest.fail('local rejection contacted provider')))
    outcome=json.loads((stage/'outcome.json').read_text())
    assert outcome['physical_requests']==0 and outcome['reserved_usd']=='0'
    assert recovery.audit(stage)==outcome


@pytest.mark.parametrize('target',['source','copy','ledger','plan','settings','inheritance','authorization','helper'])
def test_tampering_refused_before_marker(staged,monkeypatch,target):
    source,final,stage,p=staged;authorize(stage)
    if target in {'source','copy'}:
        with sqlite3.connect((source if target=='source' else stage)/'memory.sqlite3') as db:db.execute("UPDATE memories SET content='changed'")
    elif target=='ledger':
        with sqlite3.connect(stage/'physical-requests.sqlite3') as db:db.execute("UPDATE policy SET json='{}'")
    elif target=='helper':monkeypatch.setattr(recovery,'producers',lambda:{'changed':'helper'})
    else:
        path=stage/(target+'.json');value=json.loads(path.read_text());value['unexpected']=True;path.write_text(json.dumps(value))
    with pytest.raises((ValueError,KeyError)):recovery.execute(stage,httpx.MockTransport(lambda req:pytest.fail('tampered contacted provider')))
    assert not (stage/'execution-started.json').exists()


def test_strict_export_preserves_both_ledgers_and_full_mixed_provenance(staged,tmp_path):
    source,final,stage,p=staged;authorize(stage)
    recovery.execute(stage,httpx.MockTransport(provider))
    final_recovery=tmp_path/'recovery-terminal.json';terminal(stage,final_recovery,recovery.TERMINAL,'related_not_complete')
    before=r.source_identity(stage);output=tmp_path/'complete'
    result=recovery.complete_export(stage,final_recovery,output)
    bundle=recovery.MemoryExport.model_validate_json((output/'exports/conv-44.json').read_text())
    assert bundle.build.status=='complete' and len(bundle.memories)==3 and len(bundle.relations)==3
    sidecar=json.loads((output/'exports/conv-44.provenance.json').read_text())
    assert sidecar['export_sha256']==r.sha(output/'exports/conv-44.json')
    assert sidecar['logical_attempt_1']['terminal_sha256']==r.sha(final)
    assert sidecar['logical_attempt_1']['ledger_snapshot']==p['source_identity']['ledger']
    assert sidecar['logical_attempt_2']['ledger_snapshot']==before['ledger']
    assert sidecar['mixed_relation_input_producers'] and not sidecar['wire_contract_in_build_fingerprint']
    assert result['provider_requests']==0 and r.source_identity(stage)==before and r.source_identity(source)==p['source_identity']
    with r.readonly(stage/'memory.sqlite3') as db:assert db.execute('SELECT status FROM build_versions WHERE build_id=?',(p['build_id'],)).fetchone()[0]=='related'


@pytest.mark.parametrize('corruption',['success_task','old_attempt','old_provider','old_relation','new_attempt','new_provider'])
def test_preserved_history_and_new_diagnostics_corruption_rejected(staged,monkeypatch,corruption):
    source,final,stage,p=staged;authorize(stage)
    run=recovery.RelationService.run
    def corrupt(self,bid):
        run(self,bid)
        with self.database.connect() as db:
            failed_id=p['failed_tasks'][0]['task_id']
            if corruption=='success_task':db.execute("UPDATE relation_tasks SET metadata_json='{}' WHERE status='succeeded' AND task_id!=?",(failed_id,))
            elif corruption=='old_attempt':db.execute("UPDATE relation_attempts SET status='running',completed_at=NULL WHERE logical_attempt=1")
            elif corruption=='old_provider':db.execute("UPDATE relation_provider_calls SET metadata_json='{}' WHERE logical_attempt=1")
            elif corruption=='old_relation':db.execute("UPDATE memory_relations SET label='CONFLICT' WHERE relation_id=?",(p['old_relation_ids'][0],))
            elif corruption=='new_attempt':db.execute("UPDATE relation_attempts SET status='running',completed_at=NULL WHERE logical_attempt=2")
            else:db.execute('UPDATE relation_provider_calls SET provider_attempt=2 WHERE logical_attempt=2')
    monkeypatch.setattr(recovery.RelationService,'run',corrupt)
    with pytest.raises(ValueError,match='preserved_rows_changed|recovery_attempt_identity_or_terminal_changed'):
        recovery.execute(stage,httpx.MockTransport(provider))
    assert not (stage/'outcome.json').exists()
    assert r.source_identity(source)==p['source_identity']


def test_annotation_rejected_before_any_payload_snapshot(failed,tmp_path,monkeypatch):
    source,final=failed
    with sqlite3.connect(source/'memory.sqlite3') as db:
        db.execute('UPDATE import_artifacts SET annotations_json=?',(json.dumps([{'sample_id':'conv-44','qa':['forbidden synthetic']}]),))
    monkeypatch.setattr(r,'snapshot',lambda path:pytest.fail('annotation hashed'))
    with pytest.raises(ValueError,match='nonempty_annotations_forbidden'):
        recovery.prepare(source,final,tmp_path/'refused')
    assert not (tmp_path/'refused').exists()


def test_interrupted_source_never_queued_as_failed_scope(failed,tmp_path):
    source,final=failed
    with sqlite3.connect(source/'memory.sqlite3') as db:db.execute("UPDATE relation_tasks SET status='interrupted' WHERE status='failed'")
    rebound=tmp_path/'changed-terminal.json';terminal(source,rebound,recovery.PARENT_TERMINAL,'relations_failed_not_complete')
    with pytest.raises(ValueError,match='relation_attempt_identity_or_terminal_changed'):
        recovery.prepare(source,rebound,tmp_path/'refused')
    assert not (tmp_path/'refused').exists()


@pytest.mark.parametrize('path,expected',[('judgments[0]','judgments[0]'),
    ('judgments[12].source_ids[1]','judgments[12].source_ids[1]'),('untrusted text: secret',None)])
def test_wrapper_feedback_path_whitelist_and_precheckpoint_contract(path,expected):
    class Capture:
        def generate(self,operation,payload,schema,*,context,on_call):
            on_call({});return payload
    failed=[dict(new_memory_id='memory-1',metadata_json=json.dumps({'calls':[{'error_code':'known_source_required','field_path':path}]}))]
    memory=dict(memory_id='memory-1',source_ids=['conv-44:session:0001:turn:000001'])
    context=dict(new_memory=memory,history=[],sources={memory['source_ids'][0]:{}})
    observed=[];model=recovery.EndpointModel(Capture(),failed,'wrapper-sha')
    payload=model.generate('relate',{'new_memory':memory},None,context=context,on_call=observed.append)
    assert payload['recovery_feedback']['field_path']==expected
    assert payload['endpoint_source_ids']=={'memory-1':memory['source_ids']}
    assert observed==[dict(input_contract_version=recovery.INPUT_VERSION,input_wrapper_sha256='wrapper-sha')]


@pytest.mark.parametrize('corruption',['policy','zero_reservation','large_reservation','model','output','thinking','effort'])
def test_accounting_rejects_policy_model_output_thinking_and_reservation_corruption(tmp_path,corruption):
    policy=dict(model='deepseek-flash',input_usd_per_million='.30',output_usd_per_million='1.20',
        max_input_bytes=16,max_output_tokens=8,max_requests=1,max_usd='.0000144')
    recovery.BudgetTransport(tmp_path/'physical-requests.sqlite3',None,**policy).close()
    with sqlite3.connect(tmp_path/'physical-requests.sqlite3') as db:
        db.execute("INSERT INTO physical_requests VALUES ('one','.0000123','response_usage_unknown','{}')")
        if corruption=='policy':db.execute("UPDATE policy SET json=json_set(json,'$.input_rate','9')")
        elif corruption=='zero_reservation':db.execute("UPDATE physical_requests SET reserved_usd='0'")
        elif corruption=='large_reservation':db.execute("UPDATE physical_requests SET reserved_usd='1'")
    call=dict(usage={},response_received=True,thinking={'type':'disabled'},reasoning_effort=None,requested_model='deepseek-flash',max_tokens=8)
    if corruption=='model':call['requested_model']='other-model'
    elif corruption=='output':call['max_tokens']=7
    elif corruption=='thinking':call['thinking']={'type':'enabled'}
    elif corruption=='effort':call['reasoning_effort']='high'
    with pytest.raises(ValueError):recovery.accounting(tmp_path,[call],policy)


def test_projection_corruption_cannot_pass_related_audit(staged):
    _,_,stage,p=staged;authorize(stage);recovery.execute(stage,httpx.MockTransport(provider))
    with sqlite3.connect(stage/'memory.sqlite3') as db:
        db.execute("UPDATE current_state_projections SET cutoff='1900-01-01' WHERE build_id=?",(p['build_id'],))
    with pytest.raises(ValueError,match='recovery_projection_changed'):recovery.audit(stage)


def test_duplicate_new_relation_endpoint_rejected_even_by_cursor(staged):
    _,_,stage,p=staged;authorize(stage);recovery.execute(stage,httpx.MockTransport(provider))
    with r.readonly(stage/'memory.sqlite3') as db:
        class Duplicate:
            def execute(self,sql,args=()):
                cursor=db.execute(sql,args)
                if sql.startswith('SELECT * FROM memory_relations WHERE build_id='):
                    rows=list(cursor);extra=next(row for row in rows if row['relation_id'] not in p['old_relation_ids'])
                    return [*rows,extra]
                return cursor
        with pytest.raises(ValueError,match='duplicate_recovery_relation'):recovery.check_relations(Duplicate(),p)


def test_completion_rechecks_source_outcome_terminal_binding(staged,tmp_path,monkeypatch):
    _,_,stage,p=staged;authorize(stage);recovery.execute(stage,httpx.MockTransport(provider))
    final=tmp_path/'recover-terminal.json';terminal(stage,final,recovery.TERMINAL,'related_not_complete')
    publish=recovery.VersionsService.publish
    def corrupt(self,bid):
        completed=publish(self,bid)
        path=stage/'outcome.json';value=json.loads(path.read_text());value['unexpected']=True
        path.write_text(json.dumps(value));return completed
    monkeypatch.setattr(recovery.VersionsService,'publish',corrupt)
    with pytest.raises(ValueError,match='terminal_identity_changed'):
        recovery.complete_export(stage,final,tmp_path/'copy')
    assert not (tmp_path/'copy/summary.json').exists()


@pytest.mark.parametrize('reserved',['.0000001','.03932191'])
def test_unknown_reservation_must_encode_output_cap_and_integral_input_bytes(tmp_path,reserved):
    policy=dict(model='deepseek-flash',input_usd_per_million='.30',output_usd_per_million='1.20',
        max_input_bytes=160000,max_output_tokens=32768,max_requests=1,max_usd='.0873216')
    recovery.BudgetTransport(tmp_path/'physical-requests.sqlite3',None,**policy).close()
    with sqlite3.connect(tmp_path/'physical-requests.sqlite3') as db:
        db.execute("INSERT INTO physical_requests VALUES ('unknown',?,'transport_unknown','null')",(reserved,))
    call=dict(usage={},response_received=False,thinking={'type':'disabled'},reasoning_effort=None,
        requested_model='deepseek-flash',max_tokens=32768)
    with pytest.raises(ValueError,match='physical_call_ledger_mismatch'):
        recovery.accounting(tmp_path,[call],policy)


def test_unknown_exact_reservation_retains_full_output_and_input_bytes(tmp_path):
    policy=dict(model='deepseek-flash',input_usd_per_million='.30',output_usd_per_million='1.20',
        max_input_bytes=160000,max_output_tokens=32768,max_requests=1,max_usd='.0873216')
    recovery.BudgetTransport(tmp_path/'physical-requests.sqlite3',None,**policy).close()
    with sqlite3.connect(tmp_path/'physical-requests.sqlite3') as db:
        db.execute("INSERT INTO physical_requests VALUES ('unknown','.0393243','transport_unknown','null')")
    call=dict(usage={},response_received=False,thinking={'type':'disabled'},reasoning_effort=None,
        requested_model='deepseek-flash',max_tokens=32768)
    result=recovery.accounting(tmp_path,[call],policy)
    assert result['unknown_usage_requests']==1
    assert result['unknown_reserved_usd']==result['reserved_usd']=='0.0393243'


def test_wrapper_preserves_dimension_failure_feedback_without_rewriting_cross_dimension_endpoints():
    class Capture:
        def generate(self,operation,payload,schema,*,context,on_call):
            return payload
    failed=[dict(new_memory_id='new',metadata_json=json.dumps({'calls':[
        {'error_code':'same_state_dimension_required','field_path':'judgments[3]'}]}))]
    new=dict(memory_id='new',state_key='Alex:employment',source_ids=['source-new'])
    old=dict(memory_id='old',state_key='Alex:residence',source_ids=['source-old'])
    context=dict(new_memory=new,history=[old],sources={'source-new':{},'source-old':{}})
    result=recovery.EndpointModel(Capture(),failed,'wrapper-sha').generate(
        'relate',dict(new_memory=new,history=[old]),None,context=context,on_call=lambda c:None)
    assert result['recovery_feedback']['error_code']=='same_state_dimension_required'
    assert result['recovery_feedback']['field_path']=='judgments[3]'
    instruction=result['recovery_feedback']['instruction']
    assert 'Respect allowed_labels_by_old_memory' in instruction
    assert 'RETAIN, SUPERSEDE and CONFLICT require identical state_key' in instruction
    assert 'Never change endpoint identities or state dimensions, or force a label to pass' in instruction
    assert 'undetermined is valid when evidence is insufficient' in instruction
    assert result['new_memory']==new and result['history']==[old]
    assert new['state_key']!=old['state_key']
    assert result['endpoint_source_ids']=={'new':['source-new'],'old':['source-old']}
