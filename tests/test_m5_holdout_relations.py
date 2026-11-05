"""Synthetic authorization and isolation checks; no real holdout or provider."""
from copy import deepcopy
import json
from pathlib import Path
import sqlite3
import sys

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.m5 import holdout_relations as stage
from tools.m5.relation_audit import audit
from tools.m5.extraction_recovery import snapshot
from tools.m5.offline import write
from locomo_memory.builds import BuildService
from locomo_memory.config import Settings
from locomo_memory.database import Database, backend_ownership
from locomo_memory.imports import import_dataset
from locomo_memory.model import DeepSeekModel
from locomo_memory.retrieval import RetrievalService
from locomo_memory.schemas import ImportRequest
from test_builds import completion, draft
from test_relations import relation
from test_retrieval import ControlledEmbedder


@pytest.fixture
def prepared(tmp_path, sample, monkeypatch):
    monkeypatch.setenv('DEEPSEEK_API_KEY', 'synthetic-test-key')
    source = tmp_path/'indexed'
    source.mkdir()
    settings = Settings(db_path=source/'memory.sqlite3', model_max_tokens=32768)
    database = Database(settings.db_path)
    samples = []
    for conv in ('conv-43', 'conv-44'):
        item = deepcopy(sample[0])
        item['sample_id'] = conv
        samples.append(item)
    imported = import_dataset(database, ImportRequest(data=samples, version='synthetic', license='test-only'))
    def provider(request):
        payload = json.loads(json.loads(request.content)['messages'][1]['content'])
        if payload['sample_id'] == 'conv-44':
            return completion({'memories': []})
        return completion({'memories': [draft([s['source_id']]) for s in payload['sources']]})
    model = DeepSeekModel(settings, transport=httpx.MockTransport(provider))
    builds = BuildService(database, settings, model)
    first = builds.start(imported.dataset_id, 'conv-43')['build_id']
    builds.run(first)
    RetrievalService(builds, settings, ControlledEmbedder(), model).create_index(first)
    second = builds.start(imported.dataset_id, 'conv-44')['build_id']
    builds.run(second)
    write(source/'settings.json', settings.snapshot())
    before = snapshot(settings.db_path)
    output = tmp_path/'proposal'
    plan = stage.prepare(source, output)
    assert snapshot(settings.db_path) == before
    assert not (output/'authorization.json').exists()
    assert plan['relation_tasks'] == 2 and plan['comparisons'] == 3
    assert plan['policy']['max_requests'] == 6
    assert plan['policy']['max_usd'] == '0.5239296'
    return source, output, first, second


def count(output):
    with sqlite3.connect(output/'physical-requests.sqlite3') as db:
        return db.execute('SELECT COUNT(*) FROM physical_requests').fetchone()[0]


def test_relation_stage_success_leaves_source_and_conv44_unchanged_and_never_publishes(prepared):
    source, output, first, second = prepared
    original = snapshot(source/'memory.sqlite3')
    with sqlite3.connect(output/'memory.sqlite3') as db:
        untouched = db.execute('SELECT * FROM build_versions WHERE build_id=?', (second,)).fetchone()
    write(output/'authorization.json', stage.authorization(output))
    requests = []
    def provider(request):
        body = json.loads(request.content)
        payload = json.loads(body['messages'][1]['content'])
        assert body['thinking']['type'] == 'enabled'
        assert body['reasoning_effort'] == 'high'
        assert payload['new_memory']['sample_id'] == 'conv-43'
        requests.append(payload)
        return completion({'judgments': [relation(old, payload['new_memory']) for old in payload['history']]})
    result = stage.execute(output, httpx.MockTransport(provider))
    assert result['status'] == 'related' and result['published'] is False
    assert len(requests) == count(output) == 2
    assert snapshot(source/'memory.sqlite3') == original
    with sqlite3.connect(output/'memory.sqlite3') as db:
        assert db.execute('SELECT * FROM build_versions WHERE build_id=?', (second,)).fetchone() == untouched
        assert db.execute('SELECT COUNT(*) FROM memory_relations WHERE build_id=?', (first,)).fetchone()[0] == 3
        assert db.execute("SELECT COUNT(*) FROM build_versions WHERE status='complete'").fetchone()[0] == 0
    with pytest.raises(FileExistsError):
        stage.execute(output, httpx.MockTransport(provider))
    assert count(output) == 2
    summary = audit(output)
    assert summary['terminal'] and summary['status'] == 'related'
    assert summary['projection_contract_verified']
    assert summary['physical_requests'] == 2
    assert summary['stored_relations'] == {'undetermined': 3}
    assert summary['source_memory_fragments_indexes_unchanged']


def test_invalid_relation_outputs_exhaust_exact_attempt_bound_and_preserve_failure(prepared):
    _, output, _, _ = prepared
    write(output/'authorization.json', stage.authorization(output))
    with pytest.raises(RuntimeError, match='no_automatic_retry'):
        stage.execute(output, httpx.MockTransport(lambda r: completion({'judgments': []})))
    assert count(output) == 6
    assert json.loads((output/'outcome.json').read_text())['status'] == 'relations_failed'
    summary = audit(output)
    assert summary['terminal'] and summary['physical_requests'] == 6
    assert summary['unknown_usage_requests'] == 0
    assert summary['relation_tasks'] == {'failed': 2}


@pytest.mark.parametrize('table,sql', [
    ('source', "UPDATE source_turns SET text='changed'"),
    ('other_build', "UPDATE build_versions SET updated_at='changed' WHERE sample_id='conv-44'"),
])
def test_audit_detects_protected_source_or_other_build_mutation(prepared, table, sql):
    _, output, _, _ = prepared
    with sqlite3.connect(output/'memory.sqlite3') as db:
        db.execute(sql)
    before = snapshot(output/'memory.sqlite3')
    with pytest.raises(AssertionError):
        audit(output)
    assert snapshot(output/'memory.sqlite3') == before


@pytest.mark.parametrize('change', ['query_trace', 'expanded_policy', 'common_source_change'])
def test_audit_binds_claims_to_production_query_table_and_frozen_policy_source(prepared, change):
    source, output, _, _ = prepared
    if change == 'query_trace':
        with sqlite3.connect(output/'memory.sqlite3') as db:
            db.execute('CREATE TABLE query_traces(query_id TEXT PRIMARY KEY, result_json TEXT NOT NULL)')
            db.execute("INSERT INTO query_traces VALUES ('synthetic-query','{}')")
    elif change == 'expanded_policy':
        with sqlite3.connect(output/'physical-requests.sqlite3') as db:
            policy = json.loads(db.execute('SELECT json FROM policy').fetchone()[0])
            policy.update(max_requests=6000, max_usd='1000')
            db.execute('UPDATE policy SET json=?', (json.dumps(policy),))
    else:
        for path in (source/'memory.sqlite3', output/'memory.sqlite3'):
            with sqlite3.connect(path) as db:
                db.execute("UPDATE source_turns SET text='common change'")
    before = snapshot(output/'memory.sqlite3')
    with pytest.raises(AssertionError):
        audit(output)
    assert snapshot(output/'memory.sqlite3') == before


@pytest.mark.parametrize('change', ['missing_authority', 'wrong_authority', 'database', 'ledger', 'settings', 'producer'])
def test_changes_or_missing_authority_stop_before_transport_and_marker(prepared, change, monkeypatch):
    _, output, _, _ = prepared
    if change != 'missing_authority':
        authority = stage.authorization(output)
        if change == 'wrong_authority':
            authority['scope'] = 'all holdout'
        write(output/'authorization.json', authority)
    if change == 'database':
        with sqlite3.connect(output/'memory.sqlite3') as db:
            db.execute("UPDATE build_versions SET updated_at='changed'")
    if change == 'ledger':
        with sqlite3.connect(output/'physical-requests.sqlite3') as db:
            db.execute("INSERT INTO physical_requests VALUES ('prior','1','transport_unknown','null')")
    if change == 'settings':
        with (output/'settings.json').open('a') as handle:
            handle.write(' ')
    if change == 'producer':
        monkeypatch.setattr(stage, 'producer_hashes', lambda: {})
    original = snapshot(output/'memory.sqlite3')
    with pytest.raises((FileNotFoundError, ValueError)):
        stage.execute(output, httpx.MockTransport(lambda r: pytest.fail('unauthorized call')))
    assert snapshot(output/'memory.sqlite3') == original
    assert not (output/'execution-started.json').exists()


def test_relation_stage_refuses_competing_backend(prepared):
    _, output, _, _ = prepared
    write(output/'authorization.json', stage.authorization(output))
    with backend_ownership(output/'memory.sqlite3'):
        with pytest.raises(RuntimeError, match='Another backend'):
            stage.execute(output, httpx.MockTransport(lambda r: pytest.fail('competing call')))
    assert count(output) == 0
    assert not (output/'execution-started.json').exists()
