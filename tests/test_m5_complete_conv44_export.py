"""Synthetic-only sixth export; frozen paid sources are never opened by tests."""
import json
import sqlite3

import httpx
import pytest
from pydantic import ValidationError

from tools.m5 import complete_conv44_export as export
from tools.m5 import conv44_relations as relations
from tools.m5.offline import write
from test_m5_conv44_relations import ready,indexed,extracted,authorize,provider
from test_m5_conv44_successor import seeded
from test_m5_extraction_recovery import prepared


@pytest.fixture
def related(ready,tmp_path):
    _,_,source,plan=ready;authorize(source)
    relations.execute(source,httpx.MockTransport(provider))
    terminal=tmp_path/'related-terminal.json'
    hashes={field:export.sha(source/name) for field,name in dict(plan_sha256='plan.json',settings_sha256='settings.json',
        inheritance_sha256='inheritance.json',authorization_sha256='authorization.json',outcome_sha256='outcome.json').items()}
    write(terminal,dict(version=export.TERMINAL_VERSION,status='related_not_complete',build_id=plan['build_id'],
        checks={'synthetic_complete_terminal':True},**hashes,
        final_database_logical_snapshot=relations.snapshot(source/'memory.sqlite3'),
        final_ledger_logical_snapshot=relations.snapshot(source/'physical-requests.sqlite3')))
    return source,terminal,plan


def test_completes_only_scratch_and_exports_strict_json_with_bound_provenance(related,tmp_path):
    source,terminal,plan=related;output=tmp_path/'sixth'
    before=relations.snapshot(source/'memory.sqlite3');ledger=relations.snapshot(source/'physical-requests.sqlite3')
    result=export.export_copy(source,terminal,output)
    assert result['memories']==2 and result['relations']==1 and result['provider_requests']==0
    assert result['source_and_ledger_unchanged'] and result['all_other_builds_and_tables_unchanged']
    bundle=export.MemoryExport.model_validate_json((output/'exports/conv-44.json').read_text())
    assert bundle.build.status=='complete' and bundle.build.build_id==plan['build_id']
    sidecar=json.loads((output/'exports/conv-44.provenance.json').read_text())
    assert sidecar['export_sha256']==export.sha(output/'exports/conv-44.json')
    assert sidecar['mixed_extraction_producers'] and sidecar['relation_thinking']=='disabled'
    assert sidecar['relation_attempts']['thinking_efforts']=={'disabled':1}
    assert len(sidecar['inheritance']['memory_id_map'])==1
    assert 'inheritance' not in bundle.model_dump()
    with relations.readonly(source/'memory.sqlite3') as db:
        assert db.execute('SELECT status FROM build_versions WHERE build_id=?',(plan['build_id'],)).fetchone()[0]=='related'
        assert not db.execute("SELECT 1 FROM sqlite_master WHERE name='active_versions'").fetchone()
    with relations.readonly(output/'memory.sqlite3') as db:
        assert db.execute('SELECT build_id FROM active_versions').fetchone()[0]==plan['build_id']
        assert db.execute('SELECT COUNT(*) FROM active_versions').fetchone()[0]==1
    assert relations.snapshot(source/'memory.sqlite3')==before
    assert relations.snapshot(source/'physical-requests.sqlite3')==ledger
    assert output.stat().st_mode&0o777==0o700
    with pytest.raises(ValueError,match='preserve_existing_output'):export.export_copy(source,terminal,output)


@pytest.mark.parametrize('corruption',['database','ledger','terminal','settings','inheritance','authorization','producer'])
def test_changed_source_refused_before_output(related,tmp_path,monkeypatch,corruption):
    source,terminal,plan=related;output=tmp_path/'refused'
    if corruption in {'database','ledger'}:
        with sqlite3.connect(source/('memory.sqlite3' if corruption=='database' else 'physical-requests.sqlite3')) as db:
            if corruption=='database':db.execute("UPDATE memories SET content='changed'")
            else:db.execute("UPDATE physical_requests SET usage_json='{}'")
    elif corruption=='producer':
        monkeypatch.setattr(relations,'producer_hashes',lambda:{'changed':'producer'})
    else:
        path=terminal if corruption=='terminal' else source/(corruption+'.json')
        value=json.loads(path.read_text())
        if corruption=='terminal':value['checks']['synthetic_complete_terminal']=False
        else:value['unexpected']=True
        path.write_text(json.dumps(value))
    with pytest.raises(ValueError):export.export_copy(source,terminal,output)
    assert not output.exists()


def test_annotations_refused_in_sql_before_snapshot(related,tmp_path,monkeypatch):
    source,terminal,_=related
    with sqlite3.connect(source/'memory.sqlite3') as db:
        db.execute('UPDATE import_artifacts SET annotations_json=?',(json.dumps([{'sample_id':'conv-44','qa':['synthetic forbidden']}]),))
    monkeypatch.setattr(relations,'snapshot',lambda p:pytest.fail('must reject before hashing annotations'))
    with pytest.raises(ValueError,match='nonempty_annotations_forbidden'):
        export.export_copy(source,terminal,tmp_path/'refused')
    assert not (tmp_path/'refused').exists()


@pytest.mark.parametrize('corruption',['other_build','other_table'])
def test_unexpected_scratch_mutation_cannot_claim_completion(related,tmp_path,monkeypatch,corruption):
    source,terminal,plan=related;before=relations.snapshot(source/'memory.sqlite3')
    publish=export.VersionsService.publish
    def mutate(self,bid):
        completed=publish(self,bid)
        with self.database.connect() as db:
            if corruption=='other_build':db.execute("UPDATE build_versions SET updated_at='changed' WHERE build_id!=?",(bid,))
            else:db.execute("UPDATE conversations SET speaker_a='changed'")
        return completed
    monkeypatch.setattr(export.VersionsService,'publish',mutate)
    with pytest.raises(ValueError,match='other_build_changed|unexpected_table_or_schema_change'):
        export.export_copy(source,terminal,tmp_path/'scratch')
    assert not (tmp_path/'scratch/summary.json').exists()
    assert relations.snapshot(source/'memory.sqlite3')==before


def test_strict_roundtrip_rejects_added_export_fields(related,tmp_path,monkeypatch):
    source,terminal,_=related;original=export.write_new
    def corrupt(path,value):
        if path.name=='conv-44.json':value={**value,'unexpected':'not allowed'}
        original(path,value)
    monkeypatch.setattr(export,'write_new',corrupt)
    with pytest.raises(ValidationError):export.export_copy(source,terminal,tmp_path/'scratch')
    assert not (tmp_path/'scratch/summary.json').exists()
