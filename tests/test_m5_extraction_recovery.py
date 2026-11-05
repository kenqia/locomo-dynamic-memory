"""Offline recovery contract tests with independent synthetic databases."""
from copy import deepcopy
import json
from pathlib import Path
import sqlite3
import sys

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.m5 import extraction_recovery as recovery
from tools.m5.holdout_extraction import POLICY
from tools.m5.offline import sha, write
from locomo_memory.builds import BuildService
from locomo_memory.config import Settings
from locomo_memory.database import Database, backend_ownership
from locomo_memory.imports import import_dataset
from locomo_memory.m5_budget import BudgetTransport
from locomo_memory.model import DeepSeekModel
from locomo_memory.schemas import ImportRequest
from test_builds import completion, draft


@pytest.fixture
def prepared(tmp_path, sample, monkeypatch):
    monkeypatch.setenv('DEEPSEEK_API_KEY', 'synthetic-test-key')
    stage = tmp_path/'stage'
    stage.mkdir()
    settings = Settings(db_path=stage/'memory.sqlite3', fragment_turns=2, model_retries=2)
    db = Database(settings.db_path)
    samples = []
    for conv in ['conv-43', 'conv-44']:
        item = deepcopy(sample[0])
        item['sample_id'] = conv
        samples.append(item)
    dataset = import_dataset(db, ImportRequest(data=samples, version='synthetic', license='test-only'))
    def initial(request):
        payload = json.loads(json.loads(request.content)['messages'][1]['content'])
        if payload['sample_id'] == 'conv-44' and len(payload['sources']) == 1:
            return completion({'memories': []})  # Missing no_facts_reason: invalid output.
        return completion({'memories': [draft([payload['sources'][0]['source_id']])]})
    guard = BudgetTransport(stage/'physical-requests.sqlite3', httpx.MockTransport(initial), **POLICY)
    service = BuildService(db, settings, DeepSeekModel(settings, transport=guard))
    for conv in ['conv-43', 'conv-44']:
        result = service.start(dataset.dataset_id, conv)
        service.run(result['build_id'])
    monkeypatch.setattr(recovery, 'BUILD', result['build_id'])
    monkeypatch.setattr(recovery, 'ORDINAL', 1)
    write(stage/'settings.json', settings.model_dump(mode='json'))
    write(stage/'plan.json', dict(policy=POLICY, settings_sha256=sha(stage/'settings.json'),
        implementation_sha256={'src/locomo_memory/builds.py': sha(recovery.ROOT/'src/locomo_memory/builds.py')}))
    write(stage/'extraction-outcomes.json', {'synthetic': True})
    output = tmp_path/'recovery'
    recovery.prepare(stage, output)
    return stage, output


def authorize(output):
    write(output/'authorization.json', dict(approved=True, scope=recovery.SCOPE,
        build_id=recovery.BUILD, fragment_ordinal=recovery.ORDINAL,
        max_additional_requests=3, max_additional_reserved_usd=recovery.LIMIT_USD,
        plan_sha256=sha(output/'plan.json')))


def count(path):
    with sqlite3.connect(path) as db:
        return db.execute('SELECT COUNT(*) FROM physical_requests').fetchone()[0]


def test_recovery_only_retries_failed_fragment_and_cannot_repeat(prepared):
    stage, output = prepared
    before = count(stage/'physical-requests.sqlite3')
    with sqlite3.connect(stage/'memory.sqlite3') as db:
        accepted = db.execute('SELECT memory_id,memory_json FROM memories ORDER BY memory_id').fetchall()
    authorize(output)
    calls = []
    def success(request):
        payload = json.loads(json.loads(request.content)['messages'][1]['content'])
        calls.append(payload)
        return completion({'memories': [draft([payload['sources'][0]['source_id']])]})
    recovery.execute(output, httpx.MockTransport(success))
    assert len(calls) == 1
    assert calls[0]['sample_id'] == 'conv-44'
    assert len(calls[0]['sources']) == 1
    assert count(stage/'physical-requests.sqlite3') == before+1
    assert count(output/'recovery-reservations.sqlite3') == 1
    with sqlite3.connect(stage/'memory.sqlite3') as db:
        assert all(db.execute('SELECT memory_json FROM memories WHERE memory_id=?', (mid,)).fetchone()[0] == raw
                   for mid, raw in accepted)
        assert db.execute("SELECT COUNT(*) FROM build_versions WHERE status='extracted'").fetchone()[0] == 2
    with pytest.raises((ValueError, FileExistsError)):
        recovery.execute(output, httpx.MockTransport(success))
    assert len(calls) == 1


def test_recovery_retains_failure_and_caps_new_requests_at_three(prepared):
    stage, output = prepared
    before = count(stage/'physical-requests.sqlite3')
    authorize(output)
    with pytest.raises(RuntimeError, match='no_automatic_retry'):
        recovery.execute(output, httpx.MockTransport(lambda r: completion({'memories': []})))
    assert count(stage/'physical-requests.sqlite3') == before+3
    assert count(output/'recovery-reservations.sqlite3') == 3
    assert json.loads((output/'outcome.json').read_text())['outcome']['status'] == 'failed'
    with pytest.raises(FileExistsError):
        recovery.execute(output, httpx.MockTransport(lambda r: pytest.fail('repeat provider call')))


@pytest.mark.parametrize('change', ['no_authority', 'changed_authority', 'changed_database', 'changed_ledger'])
def test_recovery_refuses_missing_authority_or_changed_snapshot_before_mutation(prepared, change):
    stage, output = prepared
    if change != 'no_authority':
        authorize(output)
    if change == 'changed_authority':
        p = output/'authorization.json'
        value = json.loads(p.read_text())
        value['max_additional_requests'] = 4
        p.write_text(json.dumps(value))
    if change == 'changed_database':
        with sqlite3.connect(stage/'memory.sqlite3') as db:
            db.execute("UPDATE build_versions SET updated_at='changed'")
    if change == 'changed_ledger':
        with sqlite3.connect(stage/'physical-requests.sqlite3') as db:
            db.execute("UPDATE physical_requests SET status='transport_unknown'")
    before = recovery.snapshot(stage/'memory.sqlite3')
    with pytest.raises((FileNotFoundError, ValueError)):
        recovery.execute(output, httpx.MockTransport(lambda r: pytest.fail('unauthorized provider call')))
    assert recovery.snapshot(stage/'memory.sqlite3') == before
    assert not (output/'execution-started.json').exists()


def test_recovery_respects_existing_global_budget_even_with_local_capacity(prepared):
    stage, old_output = prepared
    before = count(stage/'physical-requests.sqlite3')
    with sqlite3.connect(stage/'physical-requests.sqlite3') as db:
        db.execute("UPDATE physical_requests SET reserved_usd='18' WHERE id=(SELECT id FROM physical_requests LIMIT 1)")
    output = old_output.parent/'global-exhausted-recovery'
    recovery.prepare(stage, output)
    authorize(output)
    with pytest.raises(RuntimeError, match='no_automatic_retry'):
        recovery.execute(output, httpx.MockTransport(lambda r: pytest.fail('global budget exceeded')))
    assert count(stage/'physical-requests.sqlite3') == before
    assert count(output/'recovery-reservations.sqlite3') == 1
    with sqlite3.connect(stage/'memory.sqlite3') as db:
        metadata = json.loads(db.execute('SELECT model_metadata_json FROM build_fragments WHERE build_id=? AND ordinal=?',
                             (recovery.BUILD, recovery.ORDINAL)).fetchone()[0])
    assert metadata['calls'] == []


def test_recovery_refuses_a_database_owned_by_another_backend(prepared):
    stage, output = prepared
    authorize(output)
    with backend_ownership(stage/'memory.sqlite3'):
        with pytest.raises(RuntimeError, match='Another backend'):
            recovery.execute(output, httpx.MockTransport(lambda r: pytest.fail('competing recovery')))
    assert not (output/'execution-started.json').exists()
