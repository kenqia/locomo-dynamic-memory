"""File isolation and real project export compatibility; providers controlled."""
import hashlib
import json
from copy import deepcopy
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from locomo_memory.api import create_app
from tools.research_v2.sidecar_cli import run_cases
from tools.research_v2.sidecar_io import diagnose_file, input_from_export
from test_versions import complete, model
from test_retrieval import ControlledEmbedder

FIXTURES=Path(__file__).parent/'fixtures'
CASES=json.loads((FIXTURES/'sidecar_cases.json').read_text(encoding='utf-8'))['cases']

def fixture_file(tmp_path):
    p=tmp_path/'old-build.json'
    p.write_text(json.dumps(CASES[10]['input']),encoding='utf-8')
    return p


def test_snapshot_file_preserved_and_no_overwrite(tmp_path):
    path=fixture_file(tmp_path);before=path.read_bytes()
    out=tmp_path/'sidecar'/'new.json'
    result=diagnose_file(path,out,enabled=True)
    assert path.read_bytes()==before
    assert result['input_sha256_before']==result['input_sha256_after']==hashlib.sha256(before).hexdigest()
    assert result['diagnostic']['query']['answer']=='Rome'
    assert json.loads(out.read_text())==result
    old=out.read_bytes()
    with pytest.raises(ValueError):diagnose_file(path,out,enabled=True)
    assert out.read_bytes()==old and path.read_bytes()==before


def test_refuse_input_as_output(tmp_path):
    path=fixture_file(tmp_path);before=path.read_bytes()
    with pytest.raises(ValueError):diagnose_file(path,path,enabled=True)
    assert path.read_bytes()==before


def test_disabled_file_has_no_computed_result(tmp_path):
    result=diagnose_file(fixture_file(tmp_path),tmp_path/'off.json')
    assert result['diagnostic']['record']['enabled'] is False
    assert result['diagnostic']['claims']==[]
    assert result['diagnostic']['query'] is None


def test_snapshot_rejects_bad_sources_without_output(tmp_path):
    path=fixture_file(tmp_path);data=json.loads(path.read_text())
    data['claims'][0]['source_ids']=['outside']
    path.write_text(json.dumps(data));out=tmp_path/'result.json'
    with pytest.raises(ValueError):diagnose_file(path,out,enabled=True)
    assert not out.exists()


def test_manifest_runner_has_no_expected_labels_in_diagnostics(tmp_path):
    path=FIXTURES/'sidecar_cases.json';before=path.read_bytes()
    result=run_cases(path,tmp_path/'cases.json',enabled=True)
    assert len(result['cases'])==16
    assert sum(r['status']=='contract_rejected' for r in result['cases'])==1
    assert result['provider_calls']==0 and result['input_unchanged']
    assert path.read_bytes()==before
    for row in result['cases']:
        assert 'expected_behavior' not in json.dumps(row)


def test_expected_mutation_cannot_change_inference(tmp_path):
    path=FIXTURES/'sidecar_cases.json'
    original=run_cases(path,tmp_path/'original.json',enabled=True)
    data=json.loads(path.read_text())
    for case in data['cases']:
        case['expected_behavior']={'answer':'ATTACK_EXPECTED_ANSWER'}
        case['expected_contract_valid']=False
        case['name']='ATTACK_NAME'
    changed=tmp_path/'alternate.json';changed.write_text(json.dumps(data))
    changed.with_suffix('.sha256').write_text(hashlib.sha256(changed.read_bytes()).hexdigest())
    second=run_cases(changed,tmp_path/'second.json',enabled=True)
    assert original['cases']==second['cases']
    assert 'ATTACK_' not in json.dumps(second['cases'])


def test_manifest_tamper_rejected(tmp_path):
    path=tmp_path/'cases.json';path.write_bytes((FIXTURES/'sidecar_cases.json').read_bytes()+b' ')
    path.with_suffix('.sha256').write_bytes((FIXTURES/'sidecar_cases.sha256').read_bytes())
    with pytest.raises(ValueError):run_cases(path,tmp_path/'out.json',enabled=True)
    assert not (tmp_path/'out.json').exists()


def test_real_project_export_and_sqlite_unchanged(settings,sample,tmp_path):
    # Build a controlled synthetic fixture through the actual public API.
    # No real provider or embedding service is used.
    with TestClient(create_app(settings,model=model(settings),embedder=ControlledEmbedder())) as client:
        build_id=complete(client,sample)
        response=client.get(f'/builds/{build_id}/export')
        assert response.status_code==200
        payload=response.json()
    path=tmp_path/'complete-export.json';path.write_text(json.dumps(payload),encoding='utf-8')
    old_db=settings.db_path.read_bytes();old_export=path.read_bytes()
    result=diagnose_file(path,tmp_path/'sidecar.json',enabled=True,format='export',origin='synthetic')
    prov=result['diagnostic']['record']['snapshot']['provenance']
    assert prov['build_id']==build_id
    assert prov['build_fingerprint']==payload['build']['fingerprint']
    assert result['diagnostic']['retained_memory_ids']==[m['memory_id'] for m in payload['memories']]
    assert settings.db_path.read_bytes()==old_db
    assert path.read_bytes()==old_export
    bad=deepcopy(payload);bad['memories'][0]['build_id']='other-build'
    with pytest.raises(ValueError):input_from_export(bad,origin='synthetic')


def test_export_requires_explicit_origin(tmp_path):
    with pytest.raises(ValueError):
        diagnose_file(fixture_file(tmp_path),tmp_path/'result.json',format='export',enabled=True)


def test_in_progress_input_change_is_detected(tmp_path,monkeypatch):
    import tools.research_v2.sidecar_io as io
    path=fixture_file(tmp_path);real=io.read_frozen;calls=[]
    def changing(p):
        calls.append(p)
        if len(calls)==2:path.write_bytes(path.read_bytes()+b' ')
        return real(p)
    monkeypatch.setattr(io,'read_frozen',changing)
    with pytest.raises(ValueError):io.diagnose_file(path,tmp_path/'out.json',enabled=True)
    assert not (tmp_path/'out.json').exists()
