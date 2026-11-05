"""Logical-3 recovery regressions; only synthetic stages and MockTransport."""
from copy import deepcopy
import json
import sqlite3

import httpx
import pytest

from locomo_memory.builds import BuildService
from locomo_memory.config import Settings
from locomo_memory.database import Database
from locomo_memory.imports import import_dataset
from locomo_memory.m5_budget import BudgetTransport
from locomo_memory.model import DeepSeekModel
from locomo_memory.relation_schemas import RelationBatch, relation_label_error
from locomo_memory.schemas import ImportRequest
from tools.m5 import conv44_relation_successor as s
from tools.m5 import conv44_successor as extraction
from tools.m5 import extraction_recovery as legacy
from tools.m5.offline import write
from test_m5_conv44_relation_recovery import terminal
from test_m5_conv44_relations import provider
from test_builds import completion,draft
from test_retrieval import ControlledEmbedder


def invalid(request):
    raw=provider(request).json();value=json.loads(raw['choices'][0]['message']['content'])
    value['judgments'][1]['label']='RETAIN'
    return completion(value)


@pytest.fixture
def failed(tmp_path,sample,monkeypatch):
    monkeypatch.setenv('DEEPSEEK_API_KEY','synthetic-test-key')
    source=tmp_path/'initial';source.mkdir();settings=Settings(db_path=source/'memory.sqlite3',fragment_turns=2,model_retries=2,model_max_tokens=32768)
    db=Database(settings.db_path);items=[]
    for conv in ('conv-43','conv-44'):
        item=deepcopy(sample[0]);item['sample_id']=conv;items.append(item)
    dataset=import_dataset(db,ImportRequest(data=items,version='synthetic',license='test-only'))
    def initial(request):
        payload=json.loads(json.loads(request.content)['messages'][1]['content'])
        return completion({'memories':[]}) if payload['sample_id']=='conv-44' and len(payload['sources'])==1 else completion({'memories':[draft([payload['sources'][0]['source_id']])]})
    guard=BudgetTransport(source/'physical-requests.sqlite3',httpx.MockTransport(initial),**legacy.POLICY)
    builds=BuildService(db,settings,DeepSeekModel(settings,transport=guard))
    for conv in ('conv-43','conv-44'):
        build=builds.start(dataset.dataset_id,conv);builds.run(build['build_id'])
    monkeypatch.setattr(legacy,'BUILD',build['build_id']);monkeypatch.setattr(legacy,'ORDINAL',1)
    write(source/'settings.json',settings.snapshot());write(source/'plan.json',dict(policy=legacy.POLICY,settings_sha256=s.sha(source/'settings.json'),
        implementation_sha256={'src/locomo_memory/builds.py':s.sha(s.ROOT/'src/locomo_memory/builds.py')}))
    write(source/'extraction-outcomes.json',{'synthetic':True})
    with sqlite3.connect(source/'memory.sqlite3') as conn:conn.execute("UPDATE import_artifacts SET annotations_json='[]'")
    monkeypatch.setattr(extraction,'SOURCE_CODE_ROOT',s.ROOT)
    extracted_terminal=tmp_path/'pre-extract-terminal.json'
    write(extracted_terminal,dict(final_database_logical_snapshot=s.r.snapshot(source/'memory.sqlite3'),
        final_ledger_logical_snapshot=s.r.snapshot(source/'physical-requests.sqlite3'),plan_sha256=s.sha(source/'plan.json')))
    extracted=tmp_path/'extracted';extraction.prepare(source,extracted_terminal,extracted)
    write(extracted/'authorization.json',extraction.authorization(extracted))
    def extract(request):
        payload=json.loads(json.loads(request.content)['messages'][1]['content']);ids=[payload['sources'][0]['source_id']]
        return completion({'memories':[draft(ids),draft(ids,memory_type='event',statement_type='plan',state_dimension='travel',state_value=None)]})
    extraction.execute(extracted,httpx.MockTransport(extract))
    extracted_terminal=tmp_path/'extracted-terminal.json';terminal(extracted,extracted_terminal,extraction.VERSION+'-terminal-v1','extracted_not_complete')
    index=tmp_path/'indexed';s.r.index(extracted,extracted_terminal,index,ControlledEmbedder())
    parent=tmp_path/'logical-one';s.r.prepare(index,parent);write(parent/'authorization.json',s.r.authorization(parent))
    def partial(request):
        payload=json.loads(json.loads(request.content)['messages'][1]['content'])
        return provider(request) if len(payload['history'])==1 else invalid(request)
    with pytest.raises(RuntimeError):s.r.execute(parent,httpx.MockTransport(partial))
    parent_terminal=tmp_path/'logical-one-terminal.json';terminal(parent,parent_terminal,s.q.PARENT_TERMINAL,'relations_failed_not_complete')
    logical_two=tmp_path/'logical-two';s.q.prepare(parent,parent_terminal,logical_two);write(logical_two/'authorization.json',s.q.authorization(logical_two))
    with pytest.raises(RuntimeError):s.q.execute(logical_two,httpx.MockTransport(invalid))
    final=tmp_path/'logical-two-terminal.json';terminal(logical_two,final,s.q.TERMINAL,'relations_failed_not_complete')
    return logical_two,final


@pytest.fixture
def staged(failed,tmp_path):
    source,final=failed;stage=tmp_path/'logical-three';p=s.prepare(source,final,stage)
    return source,final,stage,p


def authorize(stage):write(stage/'authorization.json',s.authorization(stage))


def test_policy_is_exact_and_prepare_requires_fresh_authorization(staged):
    source,final,stage,p=staged
    assert p['policy']==s.POLICY and p['policy']['max_requests']==3 and p['policy']['max_usd']=='0.2619648'
    assert len(p['failed_tasks'])==1 and p['failed_tasks'][0]['attempts']==2
    assert not p['old_budget_transferred'] and not p['wire_contract_in_build_fingerprint']
    with s.readonly(stage/'memory.sqlite3') as db:
        assert [x[0] for x in db.execute('SELECT status FROM relation_tasks ORDER BY ordinal')]==['succeeded','pending']
        assert [x[0] for x in db.execute('SELECT logical_attempt FROM relation_attempts ORDER BY task_id,logical_attempt')].count(3)==0
    with s.readonly(stage/'physical-requests.sqlite3') as db:assert db.execute('SELECT COUNT(*) FROM physical_requests').fetchone()[0]==0
    before=s.r.source_identity(stage)
    with pytest.raises(FileNotFoundError):s.execute(stage,httpx.MockTransport(lambda req:pytest.fail('unapproved provider')))
    assert s.r.source_identity(stage)==before and not (stage/'execution-started.json').exists()


@pytest.mark.parametrize('kind',['success','invalid','unknown'])
def test_logical_three_keeps_all_history_and_new_independent_accounting(staged,kind):
    source,final,stage,p=staged;authorize(stage);seen=[]
    def generate(request):
        body=json.loads(request.content);payload=json.loads(body['messages'][1]['content']);seen.append(payload)
        assert body['thinking']=={'type':'disabled'} and 'reasoning_effort' not in body
        assert payload['new_memory']['statement_type']=='plan'
        matrix=payload['label_prerequisites_by_old_memory']
        assert set(matrix)=={old['memory_id'] for old in payload['history']}
        for old in payload['history']:
            allowed=[label for label in s.LABELS if relation_label_error(label,old,payload['new_memory']) is None]
            assert matrix[old['memory_id']]['allowed_labels']==allowed==['undetermined']
            assert payload['allowed_labels_by_old_memory'][old['memory_id']]==allowed
        if kind=='unknown':raise httpx.ReadTimeout('synthetic')
        return provider(request) if kind=='success' else invalid(request)
    if kind=='success':outcome=s.execute(stage,httpx.MockTransport(generate));assert outcome['status']=='related'
    else:
        with pytest.raises(RuntimeError,match='incomplete_no_automatic_retry'):s.execute(stage,httpx.MockTransport(generate))
        outcome=json.loads((stage/'outcome.json').read_text())
    assert outcome['physical_requests']==len(seen)==(1 if kind=='success' else 3)
    if kind=='unknown':assert outcome['unknown_usage_requests']==3 and outcome['unknown_reserved_usd']==outcome['reserved_usd']
    with s.readonly(stage/'memory.sqlite3') as db:
        task=p['failed_tasks'][0]['task_id']
        assert [x[0] for x in db.execute('SELECT logical_attempt FROM relation_attempts WHERE task_id=? ORDER BY logical_attempt',(task,))]==[1,2,3]
        calls=json.loads(db.execute('SELECT model_metadata_json FROM build_versions WHERE build_id=?',(p['build_id'],)).fetchone()[0])['calls']
        assert calls[:len(p['initial_metadata']['calls'])]==p['initial_metadata']['calls']
        assert all(call['input_contract_version']==s.INPUT_VERSION for call in calls[len(p['initial_metadata']['calls']):])
    assert s.r.source_identity(source)==p['source_identity'] and s.audit(stage)==outcome
    with pytest.raises(ValueError,match='already_started'):s.execute(stage)


@pytest.mark.parametrize('target',['source','copy_old_attempt','copy_success','ledger','plan','settings','authorization','producer'])
def test_tamper_rejected_before_marker_or_provider(staged,target,monkeypatch):
    source,final,stage,p=staged;authorize(stage)
    if target=='source':
        with sqlite3.connect(source/'memory.sqlite3') as db:db.execute("UPDATE relation_attempts SET error_code='changed' WHERE logical_attempt=1")
    elif target.startswith('copy_'):
        with sqlite3.connect(stage/'memory.sqlite3') as db:
            if target=='copy_old_attempt':db.execute("UPDATE relation_attempts SET error_code='changed' WHERE logical_attempt=2")
            else:db.execute("UPDATE relation_tasks SET metadata_json='{}' WHERE status='succeeded'")
    elif target=='ledger':
        with sqlite3.connect(stage/'physical-requests.sqlite3') as db:db.execute("UPDATE policy SET json='{}'")
    elif target=='producer':monkeypatch.setattr(s,'producers',lambda:{'changed':'producer'})
    else:
        path=stage/(target+'.json');value=json.loads(path.read_text());value['unexpected']=True;path.write_text(json.dumps(value))
    with pytest.raises((ValueError,KeyError)):s.execute(stage,httpx.MockTransport(lambda req:pytest.fail('tampered provider')))
    assert not (stage/'execution-started.json').exists()


def test_strict_export_binds_three_wire_contracts_and_ledgers(staged,tmp_path):
    source,final,stage,p=staged;authorize(stage);s.execute(stage,httpx.MockTransport(provider))
    frozen=tmp_path/'logical-three-terminal.json';terminal(stage,frozen,s.TERMINAL,'related_not_complete')
    before=s.r.source_identity(stage);output=tmp_path/'complete';result=s.complete_export(stage,frozen,output)
    assert result['provider_requests']==0 and result['strict_roundtrip'] and s.r.source_identity(stage)==before
    side=json.loads((output/'exports/conv-44.provenance.json').read_text());history=side['relation_stages']
    assert [x['logical_attempt'] for x in history]==[1,2,3]
    assert [x['input_contract'] for x in history]==['original-core-relation-payload',s.q.INPUT_VERSION,s.INPUT_VERSION]
    assert len({x['ledger_snapshot'] for x in history})==3
    assert history[1]['terminal_sha256']==s.sha(final) and history[2]['terminal_sha256']==s.sha(frozen)


def test_complete_export_rechecks_source_terminal_after_copy(staged,tmp_path,monkeypatch):
    source,final,stage,p=staged;authorize(stage);s.execute(stage,httpx.MockTransport(provider))
    frozen=tmp_path/'logical-three-terminal.json';terminal(stage,frozen,s.TERMINAL,'related_not_complete')
    original=s.ExportService.export
    def swap(self,bid):
        bundle=original(self,bid);value=json.loads(frozen.read_text());value['status']='changed';frozen.write_text(json.dumps(value));return bundle
    monkeypatch.setattr(s.ExportService,'export',swap)
    with pytest.raises(ValueError,match='frozen_terminal_required'):s.complete_export(stage,frozen,tmp_path/'complete')


def test_wrapper_preserves_cross_dimension_update_and_its_evidence_validation():
    old=dict(memory_id='old',state_key='a',memory_type='event',statement_type='plan',source_ids=['s1'])
    new=dict(memory_id='new',state_key='b',memory_type='event',statement_type='plan',source_ids=['s2'])
    context=dict(new_memory=new,history=[old],sources={'s1':{'text':'Synthetic old stage.'},'s2':{'text':'Synthetic new stage.'}});seen={}
    class Capture:
        def generate(self,operation,payload,schema,**kwargs):seen.update(payload);return 'unchanged'
    model=s.EndpointModel(Capture(),[dict(new_memory_id='new',metadata_json=json.dumps({'calls':[{'error_code':'same_state_dimension_required','field_path':'judgments[1]'}]}))],'sha')
    assert model.generate('relate',dict(new_memory=new,history=[old]),RelationBatch,context=context,on_call=lambda c:None)=='unchanged'
    assert seen['label_prerequisites_by_old_memory']['old']['allowed_labels']==['UPDATE','undetermined']
    assert seen['new_memory']==new and seen['history']==[old]
    scoped={**context,'new_memory':{**new,'build_id':'b','dataset_id':'d','sample_id':'c','entity_id':'e'},
        'history':[{**old,'build_id':'b','dataset_id':'d','sample_id':'c','entity_id':'e'}]}
    with pytest.raises(ValueError,match='update_stage_evidence_required'):
        RelationBatch.model_validate(dict(judgments=[dict(old_memory_id='old',new_memory_id='new',label='UPDATE',reason='Synthetic.',source_ids=['s1','s2'])]),context=scoped)
