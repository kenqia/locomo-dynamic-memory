"""Successor identity, strict inheritance and independent paid gate; synthetic only."""
import json
import sqlite3
from pathlib import Path

import httpx
import pytest

from tools.m5 import conv44_successor as successor
from tools.m5 import extraction_recovery as legacy
from tools.m5.offline import write
from test_m5_extraction_recovery import prepared
from test_builds import completion,draft


@pytest.fixture
def seeded(prepared,monkeypatch,tmp_path):
    source,_=prepared
    with sqlite3.connect(source/'memory.sqlite3') as db:
        db.execute("UPDATE import_artifacts SET annotations_json='[]'")
    monkeypatch.setattr(successor,'SOURCE_CODE_ROOT',successor.ROOT)
    monkeypatch.setattr(successor,'POLICY',{**successor.POLICY,'max_output_tokens':8192})
    terminal=tmp_path/'source-terminal.json'
    write(terminal,dict(final_database_logical_snapshot=legacy.snapshot(source/'memory.sqlite3'),final_ledger_logical_snapshot=legacy.snapshot(source/'physical-requests.sqlite3'),plan_sha256=successor.sha(source/'plan.json')))
    stage=tmp_path/'successor'
    plan=successor.prepare(source,terminal,stage)
    return source,stage,plan


def authorize(stage):
    write(stage/'authorization.json',successor.authorization(stage))


def test_prepare_inherits_exact_payloads_and_retains_original_failed_build(seeded):
    source,stage,plan=seeded
    assert plan['inherited_fragments']==plan['inherited_memories']==1
    assert plan['build_id']!=legacy.BUILD
    assert successor.identity(source)==plan['source_identity']
    settings=successor.Settings.model_validate_json((stage/'settings.json').read_text())
    assert all(v=='disabled' for k,v in settings.snapshot().items() if k.endswith('_thinking_effort'))
    assert settings.resolution_input_budget==192000
    provenance=json.loads((stage/'inheritance.json').read_text())
    with successor.prior.readonly(stage/'memory.sqlite3') as db:
        for old_id,new_id in provenance['memory_id_map'].items():
            old=json.loads(db.execute('SELECT memory_json FROM memories WHERE memory_id=?',(old_id,)).fetchone()[0])
            new=json.loads(db.execute('SELECT memory_json FROM memories WHERE memory_id=?',(new_id,)).fetchone()[0])
            assert old_id!=new_id
            assert {k:v for k,v in old.items() if k not in {'memory_id','build_id'}}=={k:v for k,v in new.items() if k not in {'memory_id','build_id'}}
        assert db.execute('SELECT status FROM build_versions WHERE build_id=?',(legacy.BUILD,)).fetchone()[0]=='failed'
        metadata=json.loads(db.execute('SELECT model_metadata_json FROM build_versions WHERE build_id=?',(plan['build_id'],)).fetchone()[0])
        assert metadata['calls']==[] and metadata['inheritance']['mixed_extraction_producers']
    with pytest.raises(FileNotFoundError):successor.execute(stage)
    assert not (stage/'execution-started.json').exists()


@pytest.mark.parametrize('valid',[True,False])
def test_finite_generation_only_targets_original_full_failed_fragment(seeded,valid):
    source,stage,plan=seeded
    authorize(stage)
    seen=[]
    def provider(request):
        body=json.loads(request.content)
        assert body['thinking']=={'type':'disabled'} and 'reasoning_effort' not in body
        payload=json.loads(body['messages'][1]['content'])
        assert payload['sample_id']=='conv-44' and len(payload['sources'])==1
        seen.append(payload)
        return completion({'memories':[draft([payload['sources'][0]['source_id']])]} if valid else {'memories':[]})
    if valid:
        result=successor.execute(stage,httpx.MockTransport(provider))
        assert result['status']=='extracted' and result['new_memories']==1
    else:
        with pytest.raises(RuntimeError,match='incomplete_no_automatic_retry'):
            successor.execute(stage,httpx.MockTransport(provider))
        result=json.loads((stage/'outcome.json').read_text())
        assert result['status']=='failed' and result['new_memories']==0
    assert len(seen)==result['physical_requests']==(1 if valid else 3)
    assert successor.identity(source)==plan['source_identity']
    assert result['parent_and_inherited_rows_unchanged']
    with pytest.raises(ValueError,match='already_started'):successor.execute(stage,httpx.MockTransport(provider))
    assert len(seen)==(1 if valid else 3)


@pytest.mark.parametrize('target',['source','copy','ledger','plan','settings','inheritance','authorization'])
def test_tampering_refused_before_any_provider_request(seeded,target):
    source,stage,plan=seeded
    authorize(stage)
    if target in {'source','copy'}:
        with sqlite3.connect((source if target=='source' else stage)/'memory.sqlite3') as db:
            db.execute("UPDATE memories SET content='tampered'")
    elif target=='ledger':
        with sqlite3.connect(stage/'physical-requests.sqlite3') as db:db.execute("UPDATE policy SET json='{}'")
    else:
        path=stage/(target+'.json')
        value=json.loads(path.read_text());value['tampered']=True;path.write_text(json.dumps(value))
    with pytest.raises((ValueError,KeyError)):
        successor.execute(stage,httpx.MockTransport(lambda r:pytest.fail('tampered stage contacted provider')))
    assert not (stage/'execution-started.json').exists()


def test_unknown_transport_retains_all_reservations_and_stops(seeded):
    source,stage,plan=seeded;authorize(stage)
    def fail(request):raise httpx.ReadTimeout('synthetic')
    with pytest.raises(RuntimeError):successor.execute(stage,httpx.MockTransport(fail))
    result=json.loads((stage/'outcome.json').read_text())
    assert result['unknown_usage_requests']==result['physical_requests']==3
    assert result['unknown_reserved_usd']==result['reserved_usd']
    assert successor.identity(source)==plan['source_identity']


def test_inherited_payload_changed_during_call_is_detected(seeded):
    source,stage,plan=seeded;authorize(stage)
    def provider(request):
        payload=json.loads(json.loads(request.content)['messages'][1]['content'])
        inherited_id=next(iter(json.loads((stage/'inheritance.json').read_text())['memory_id_map'].values()))
        with sqlite3.connect(stage/'memory.sqlite3') as db:
            db.execute("UPDATE memories SET content='changed during call' WHERE memory_id=?",(inherited_id,))
        return completion({'memories':[draft([payload['sources'][0]['source_id']])]})
    with pytest.raises(ValueError,match='inherited_rows_changed'):
        successor.execute(stage,httpx.MockTransport(provider))
    assert successor.identity(source)==plan['source_identity']
    assert (stage/'execution-started.json').exists()


def test_source_annotations_rejected_before_any_full_snapshot(prepared,monkeypatch,tmp_path):
    source,_=prepared
    monkeypatch.setattr(successor.prior.legacy,'snapshot',lambda p:pytest.fail('annotation payload must not be hashed'))
    with pytest.raises(ValueError,match='nonempty_annotations_forbidden'):
        successor.prepare(source,tmp_path/'unused-terminal',tmp_path/'rejected')
    assert not (tmp_path/'rejected').exists()


def test_current_recovery_helper_change_refused_before_marker_or_provider(seeded,monkeypatch):
    source,stage,plan=seeded;authorize(stage)
    helper='tools/m5/isolated_extraction_recovery.py'
    assert helper in plan['implementation_sha256']
    original_sha=successor.sha
    monkeypatch.setattr(successor,'sha',lambda p:'changed' if Path(p).resolve()==Path(successor.prior.__file__).resolve() else original_sha(p))
    with pytest.raises(ValueError,match='successor_producer_changed'):
        successor.execute(stage,httpx.MockTransport(lambda r:pytest.fail('changed helper contacted provider')))
    assert not (stage/'execution-started.json').exists()
