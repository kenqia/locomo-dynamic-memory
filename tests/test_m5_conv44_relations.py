"""Synthetic-only successor indexing, immutable provenance and exact relation gate."""
import json
from pathlib import Path
import sqlite3

import httpx
import pytest

from tools.m5 import conv44_relations as relations
from tools.m5 import conv44_successor as successor
from tools.m5.offline import write
from test_m5_conv44_successor import seeded
from test_m5_extraction_recovery import prepared
from test_builds import completion,draft
from test_retrieval import ControlledEmbedder


@pytest.fixture
def extracted(seeded,monkeypatch,tmp_path):
    _,source,plan=seeded
    write(source/'authorization.json',successor.authorization(source))
    def extract(request):
        payload=json.loads(json.loads(request.content)['messages'][1]['content'])
        return completion({'memories':[draft([payload['sources'][0]['source_id']])]})
    successor.execute(source,httpx.MockTransport(extract))
    terminal=tmp_path/'terminal.json'
    write(terminal,dict(version=successor.VERSION+'-terminal-v1',status='extracted_not_complete',build_id=plan['build_id'],checks={'synthetic':True},
        final_database_logical_snapshot=relations.snapshot(source/'memory.sqlite3'),
        final_ledger_logical_snapshot=relations.snapshot(source/'physical-requests.sqlite3'),
        plan_sha256=relations.sha(source/'plan.json'),authorization_sha256=relations.sha(source/'authorization.json'),
        outcome_sha256=relations.sha(source/'outcome.json')))
    monkeypatch.setattr(relations,'BASE_POLICY',{**relations.BASE_POLICY,'max_output_tokens':8192})
    return source,terminal


@pytest.fixture
def indexed(extracted,tmp_path):
    source,terminal=extracted
    stage=tmp_path/'indexed'
    summary=relations.index(source,terminal,stage,ControlledEmbedder())
    return source,stage,summary


@pytest.fixture
def ready(indexed,tmp_path):
    source,index,summary=indexed
    stage=tmp_path/'relations'
    plan=relations.prepare(index,stage)
    return source,index,stage,plan


def authorize(stage):write(stage/'authorization.json',relations.authorization(stage))


def provider(request):
    body=json.loads(request.content)
    assert body['thinking']=={'type':'disabled'} and 'reasoning_effort' not in body
    payload=json.loads(body['messages'][1]['content']);new=payload['new_memory']
    assert new['sample_id']=='conv-44'
    return completion({'judgments':[dict(old_memory_id=old['memory_id'],new_memory_id=new['memory_id'],
        label='undetermined',reason='Synthetic uncertainty.',source_ids=list(dict.fromkeys(old['source_ids']+new['source_ids'])))
        for old in payload['history']]})


def test_index_copy_only_explicit_successor_and_keeps_source(indexed):
    source,stage,summary=indexed;bid=summary['build_id']
    assert relations.source_identity(source)==summary['source_identity']
    assert summary['provider_requests']==0 and not summary['published']
    assert json.loads((source/'settings.json').read_text())==json.loads((stage/'settings.json').read_text())
    assert (stage.stat().st_mode&0o777)==0o700
    with relations.readonly(stage/'memory.sqlite3') as db:
        assert [r[0] for r in db.execute('SELECT build_id FROM build_indexes')]==[bid]
        assert db.execute('SELECT COUNT(*) FROM index_entries WHERE build_id=?',(bid,)).fetchone()[0]==2
        assert db.execute('SELECT status FROM build_versions WHERE build_id=?',(bid,)).fetchone()[0]=='indexed'
        assert not db.execute("SELECT 1 FROM build_versions WHERE status='complete'").fetchall()
    assert relations.protected(stage/'memory.sqlite3',bid,summary['initial_metadata'],relations.INDEX_MUTABLE)==summary['protected_snapshot']


def test_actual_tasks_determine_independent_budget_and_noauth_refused(ready):
    source,index,stage,plan=ready
    assert plan['relation_tasks']==1
    assert plan['policy']['max_requests']==3
    assert plan['policy']==relations.policy_for(1,relations.settings_at(stage))
    assert 'selection_json' in relations.task_rows(stage/'memory.sqlite3',plan['build_id'])[0]
    with relations.readonly(stage/'physical-requests.sqlite3') as db:
        assert db.execute('SELECT COUNT(*) FROM physical_requests').fetchone()[0]==0
    assert not json.loads((stage/'authorization-template.json').read_text())['approved']
    before=relations.snapshot(stage/'memory.sqlite3')
    with pytest.raises(FileNotFoundError):relations.execute(stage)
    assert relations.snapshot(stage/'memory.sqlite3')==before
    assert not (stage/'execution-started.json').exists()


@pytest.mark.parametrize('kind',['success','invalid','unknown'])
def test_finite_relation_calls_exact_ledger_and_unknown_reservations(ready,kind):
    source,index,stage,plan=ready;authorize(stage);seen=[]
    def generate(request):
        seen.append(True)
        if kind=='unknown':raise httpx.ReadTimeout('synthetic')
        return provider(request) if kind=='success' else completion({'judgments':[]})
    if kind=='success':
        result=relations.execute(stage,httpx.MockTransport(generate))
        assert result['status']=='related' and result['relations']==1
    else:
        with pytest.raises(RuntimeError,match='incomplete_no_automatic_retry'):
            relations.execute(stage,httpx.MockTransport(generate))
        result=json.loads((stage/'outcome.json').read_text())
        assert result['status']=='relations_failed'
    assert len(seen)==result['physical_requests']==(1 if kind=='success' else 3)
    if kind=='unknown':assert result['unknown_usage_requests']==3 and result['unknown_reserved_usd']==result['reserved_usd']
    assert result['inherited_extraction_calls']==1
    assert relations.source_identity(source)==plan['source_identity']
    assert result['protected_state_unchanged'] and not result['published']
    with pytest.raises(ValueError,match='already_started'):relations.execute(stage,httpx.MockTransport(generate))
    assert len(seen)==(1 if kind=='success' else 3)


@pytest.mark.parametrize('target',['authorization','source','copy','ledger','settings','inheritance','summary','task','schema'])
def test_changes_refused_before_marker_or_http(ready,target):
    source,index,stage,plan=ready;authorize(stage)
    if target in {'source','copy','task'}:
        path=(source if target=='source' else stage)/'memory.sqlite3'
        with sqlite3.connect(path) as db:
            if target=='task':db.execute("UPDATE relation_tasks SET selection_json='{}'")
            else:db.execute("UPDATE memories SET content='tampered'")
    elif target=='schema':
        with sqlite3.connect(stage/'memory.sqlite3') as db:db.execute('CREATE INDEX unexpected_index ON memories(content)')
    elif target=='ledger':
        with sqlite3.connect(stage/'physical-requests.sqlite3') as db:db.execute("UPDATE policy SET json='{}'")
    else:
        path=(index/'index-summary.json') if target=='summary' else stage/(target+'.json')
        value=json.loads(path.read_text());value['tampered']=True;path.write_text(json.dumps(value))
    with pytest.raises((ValueError,KeyError)):
        relations.execute(stage,httpx.MockTransport(lambda r:pytest.fail('tampering contacted provider')))
    assert not (stage/'execution-started.json').exists()


def test_actual_helper_change_refused_before_marker(ready,monkeypatch):
    _,_,stage,plan=ready;authorize(stage)
    helper=Path(successor.prior.__file__).resolve()
    assert str(helper.relative_to(relations.ROOT)) in plan['implementation_sha256']
    original=relations.sha
    monkeypatch.setattr(relations,'sha',lambda p:'changed' if Path(p).resolve()==helper else original(p))
    with pytest.raises(ValueError,match='producer_or_plan_changed'):
        relations.execute(stage,httpx.MockTransport(lambda r:pytest.fail('changed helper contacted provider')))
    assert not (stage/'execution-started.json').exists()


def test_annotation_rejected_before_any_full_snapshot(extracted,tmp_path,monkeypatch):
    source,terminal=extracted
    with sqlite3.connect(source/'memory.sqlite3') as db:
        db.execute('UPDATE import_artifacts SET annotations_json=?',(json.dumps([{'sample_id':'conv-44','qa':['forbidden synthetic']}]),))
    monkeypatch.setattr(relations,'snapshot',lambda p:pytest.fail('annotation must not be hashed'))
    with pytest.raises(ValueError,match='nonempty_annotations_forbidden'):
        relations.index(source,terminal,tmp_path/'rejected',ControlledEmbedder())
    assert not (tmp_path/'rejected').exists()


def test_memory_changed_during_relation_is_detected(ready):
    source,index,stage,plan=ready;authorize(stage)
    def mutate(request):
        with sqlite3.connect(stage/'memory.sqlite3') as db:
            db.execute("UPDATE memories SET content='during call' WHERE build_id=?",(plan['build_id'],))
        return provider(request)
    with pytest.raises(ValueError,match='protected_state_changed'):
        relations.execute(stage,httpx.MockTransport(mutate))
    assert relations.source_identity(source)==plan['source_identity']


def test_returned_models_corruption_during_relation_is_detected(ready):
    _,_,stage,plan=ready;authorize(stage)
    # A post-run mutation cannot hide behind the normalized historical prefix.
    run=relations.RelationService.run
    def corrupt(self,bid):
        run(self,bid)
        with self.database.connect() as db:
            metadata=json.loads(db.execute('SELECT model_metadata_json FROM build_versions WHERE build_id=?',(bid,)).fetchone()[0])
            metadata['returned_models']=['corrupt']
            db.execute('UPDATE build_versions SET model_metadata_json=? WHERE build_id=?',(json.dumps(metadata),bid))
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(relations.RelationService,'run',corrupt)
        with pytest.raises(ValueError,match='returned_models_changed'):
            relations.execute(stage,httpx.MockTransport(provider))


def test_index_query_rows_rejected_before_prepare(indexed,tmp_path):
    _,stage,summary=indexed
    with sqlite3.connect(stage/'memory.sqlite3') as db:
        db.execute('INSERT INTO candidate_queries VALUES (?,?,?)',('synthetic-query',summary['build_id'],'{}'))
    with pytest.raises(ValueError,match='queries_forbidden'):
        relations.prepare(stage,tmp_path/'rejected')
    assert not (tmp_path/'rejected').exists()


@pytest.mark.parametrize('corruption',['running_attempt','provider_sql_identity'])
def test_terminal_attempt_and_provider_sql_identity_corruption_rejected(ready,monkeypatch,corruption):
    _,_,stage,_=ready;authorize(stage)
    run=relations.RelationService.run
    def corrupt(self,bid):
        run(self,bid)
        with self.database.connect() as db:
            if corruption=='running_attempt':
                db.execute("UPDATE relation_attempts SET status='running',completed_at=NULL")
            else:
                db.execute('UPDATE relation_provider_calls SET provider_attempt=2')
    monkeypatch.setattr(relations.RelationService,'run',corrupt)
    with pytest.raises(ValueError,match='relation_attempt_identity_or_terminal_changed'):
        relations.execute(stage,httpx.MockTransport(provider))
    assert not (stage/'outcome.json').exists()


def test_local_policy_rejection_keeps_failed_logical_attempt_without_physical_calls(indexed,tmp_path,monkeypatch):
    _,index,_=indexed
    monkeypatch.setattr(relations,'BASE_POLICY',{**relations.BASE_POLICY,'max_input_bytes':1})
    stage=tmp_path/'locally-rejected'
    relations.prepare(index,stage);authorize(stage)
    with pytest.raises(RuntimeError,match='incomplete_no_automatic_retry'):
        relations.execute(stage,httpx.MockTransport(lambda r:pytest.fail('local rejection contacted provider')))
    result=json.loads((stage/'outcome.json').read_text())
    assert result['status']=='relations_failed' and result['physical_requests']==0
    assert result['reserved_usd']=='0' and result['unknown_usage_requests']==0
    with relations.readonly(stage/'memory.sqlite3') as db:
        attempt=db.execute('SELECT * FROM relation_attempts').fetchone()
        assert attempt['status']=='failed' and attempt['completed_at'] is not None
        assert db.execute('SELECT COUNT(*) FROM relation_provider_calls').fetchone()[0]==0


def test_related_build_cannot_hide_joint_failed_task_and_attempt(ready,monkeypatch):
    _,_,stage,_=ready;authorize(stage)
    run=relations.RelationService.run
    def corrupt(self,bid):
        run(self,bid)
        with self.database.connect() as db:
            db.execute("UPDATE relation_tasks SET status='failed',error_code='synthetic_failure' WHERE build_id=?",(bid,))
            db.execute("UPDATE relation_attempts SET status='failed',error_code='synthetic_failure'")
    monkeypatch.setattr(relations.RelationService,'run',corrupt)
    with pytest.raises(ValueError,match='relation_attempt_identity_or_terminal_changed'):
        relations.execute(stage,httpx.MockTransport(provider))
    assert not (stage/'outcome.json').exists()


@pytest.mark.parametrize('corruption',['build_phase','relation_prompt','relation_schema','success_error'])
def test_terminal_phase_contract_corruption_rejected(ready,monkeypatch,corruption):
    _,_,stage,_=ready;authorize(stage)
    run=relations.RelationService.run
    def corrupt(self,bid):
        run(self,bid)
        with self.database.connect() as db:
            if corruption=='build_phase':db.execute("UPDATE build_versions SET phase='indexed' WHERE build_id=?",(bid,))
            elif corruption=='relation_prompt':db.execute("UPDATE relation_phases SET prompt_version='changed' WHERE build_id=?",(bid,))
            elif corruption=='relation_schema':db.execute("UPDATE relation_phases SET schema_version='changed' WHERE build_id=?",(bid,))
            else:db.execute("UPDATE relation_phases SET error_code='synthetic_error' WHERE build_id=?",(bid,))
    monkeypatch.setattr(relations.RelationService,'run',corrupt)
    with pytest.raises(ValueError,match='relation_attempt_identity_or_terminal_changed'):
        relations.execute(stage,httpx.MockTransport(provider))
    assert not (stage/'outcome.json').exists()
