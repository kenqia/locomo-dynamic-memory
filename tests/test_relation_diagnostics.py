"""Durable diagnostics through relation tasks and build usage APIs."""
import json

import httpx
import pytest
from fastapi.testclient import TestClient

from locomo_memory.api import create_app
from locomo_memory.model import DeepSeekModel
from test_builds import completion, draft
from test_relations import relation
from test_retrieval import ControlledEmbedder, build


def test_internal_and_logical_retries_keep_history_after_restart(settings, sample):
    settings = settings.model_copy(update={'model_retries': 2})
    fixed = False
    observed_requests = []

    def provider(request):
        payload = json.loads(json.loads(request.content)['messages'][1]['content'])
        if 'new_memory' not in payload:
            return completion({'memories': [draft([payload['sources'][0]['source_id']]), draft([payload['sources'][2]['source_id']], state_dimension='business')]})
        observed_requests.append(json.loads(request.content))
        if fixed:
            return completion({'judgments': [relation(payload['history'][0], payload['new_memory'])]})
        number = len(observed_requests)
        if number == 1:
            return completion({'judgments': []}, finish='length')
        if number == 2:
            return completion({})
        return completion({'judgments': [relation(payload['history'][0], payload['new_memory'], label='RETAIN')]})

    model = DeepSeekModel(settings, api_key='synthetic', transport=httpx.MockTransport(provider))
    with TestClient(create_app(settings, model=model, embedder=ControlledEmbedder())) as client:
        build_id = build(client, sample)
        client.post(f'/builds/{build_id}/index')
        client.post(f'/builds/{build_id}/relations')
        task = client.get(f'/builds/{build_id}/relation-tasks').json()['items'][0]
        history = task['diagnostic_history']
        calls = history[0]['calls']
        assert [c['error_code'] for c in calls] == ['non_stop_finish_reason', 'missing_field', 'same_state_dimension_required']
        assert calls[-1]['field_path'] == 'judgments[0]'
        assert [c['provider_attempt'] for c in calls] == [1, 2, 3]
        assert all(c['task_id'] == task['task_id'] and c['logical_attempt'] == 1 and c['build_id'] == build_id for c in calls)
        assert history[0]['status'] == 'failed'
        fixed = True
        client.post(f'/builds/{build_id}/relations')
        task = client.get(f'/builds/{build_id}/relation-tasks').json()['items'][0]
        assert task['diagnostic_history'][0] == history[0]
        assert task['diagnostic_history'][1]['calls'][0]['status'] == 'succeeded'
        assert task['diagnostic_history'][1]['calls'][0]['logical_attempt'] == 2
        assert task['diagnostic_history_status'] == 'recorded'
        calls = client.get(f'/builds/{build_id}').json()['model_metadata']['calls']
        assert len(calls) == 5  # One extraction, three failures, one successful retry.
        assert sum(c['usage']['total_tokens'] for c in calls) == 75
        before = task
        from locomo_memory.experiment import Experiment
        directory = settings.db_path.parent / 'snapshot'
        Experiment(client, directory).snapshot_build(build_id)
        exported = json.loads((directory / 'builds' / build_id / 'relation-tasks.json').read_text())
        assert exported == [before]
    with TestClient(create_app(settings, model=model, embedder=ControlledEmbedder())) as client:
        assert client.get(f'/builds/{build_id}/relation-tasks', params={'limit': 1}).json()['items'][0] == before
    assert len(observed_requests) == 4
    assert all(body == observed_requests[0] for body in observed_requests)


def two_memory_provider(request):
    payload = json.loads(json.loads(request.content)['messages'][1]['content'])
    if 'new_memory' not in payload:
        return completion({'memories': [draft([payload['sources'][0]['source_id']]), draft([payload['sources'][2]['source_id']])]})
    return completion({'judgments': [relation(payload['history'][0], payload['new_memory'])]})


@pytest.mark.parametrize('crash_point', ['dispatch', 'response', 'failed_then_dispatch', 'success_before_commit'])
def test_process_exit_keeps_observed_calls_and_unknown_outcome_without_replay(settings, sample, crash_point):
    import subprocess
    import sys
    model = DeepSeekModel(settings, api_key='synthetic', transport=httpx.MockTransport(two_memory_provider))
    with TestClient(create_app(settings, model=model, embedder=ControlledEmbedder())) as client:
        build_id = build(client, sample)
        client.post(f'/builds/{build_id}/index')
    program = r'''
import json, os, sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd() / 'tests'))
import httpx
from fastapi.testclient import TestClient
from locomo_memory.api import create_app
from locomo_memory.config import Settings
from locomo_memory.model import DeepSeekModel
from test_builds import completion
from test_relations import relation
from test_retrieval import ControlledEmbedder
mode, count = sys.argv[3], 0
class CrashModel(DeepSeekModel):
    def generate(self, operation, payload, schema, **kwargs):
        record = kwargs['on_call']
        def observe(call):
            record(call)
            if mode == 'response' and call['status'] == 'response_observed' and call['finish_reason'] == 'stop':
                os._exit(23)
        kwargs['on_call'] = observe
        generated = super().generate(operation, payload, schema, **kwargs)
        if mode == 'success_before_commit':
            os._exit(23)
        return generated

def provider(request):
    global count
    count += 1
    if mode == 'dispatch' or (mode == 'failed_then_dispatch' and count == 2):
        os._exit(23)
    payload = json.loads(json.loads(request.content)['messages'][1]['content'])
    if mode == 'failed_then_dispatch':
        return completion({'judgments': []})
    return completion({'judgments': [relation(payload['history'][0], payload['new_memory'])]})
settings = Settings(db_path=Path(sys.argv[1]), model_retries=2)
model = CrashModel(settings, api_key='synthetic', transport=httpx.MockTransport(provider))
with TestClient(create_app(settings, model=model, embedder=ControlledEmbedder())) as client:
    client.post('/builds/' + sys.argv[2] + '/relations')
'''
    child = subprocess.run([sys.executable, '-c', program, str(settings.db_path), build_id, crash_point], capture_output=True, timeout=15)
    assert child.returncode == 23, child.stderr.decode()
    # Recovery reads local checkpoints only, never calls the model automatically.
    calls_on_restart = []
    def resumed_provider(request):
        calls_on_restart.append(request)
        return two_memory_provider(request)
    model = DeepSeekModel(settings, api_key='synthetic', transport=httpx.MockTransport(resumed_provider))
    with TestClient(create_app(settings, model=model, embedder=ControlledEmbedder())) as client:
        task = client.get(f'/builds/{build_id}/relation-tasks').json()['items'][0]
        assert task['status'] == 'interrupted'
        first = task['diagnostic_history'][0]
        assert first['status'] == 'interrupted' and first['completed_at'] is None
        calls = first['calls']
        assert len(calls) == (2 if crash_point == 'failed_then_dispatch' else 1)
        last = calls[-1]
        if crash_point == 'success_before_commit':
            assert last['status'] == 'succeeded'
        else:
            assert last['status'] == 'interrupted' and 'completed_at' not in last
        if crash_point in {'dispatch', 'failed_then_dispatch'}:
            assert last['usage'] == {} and last['finish_reason'] is None
        else:
            assert last['usage']['total_tokens'] == 15 and last['finish_reason'] == 'stop'
        if crash_point == 'failed_then_dispatch':
            assert calls[0]['error_code'] == 'every_candidate_required'
        build_calls = client.get(f'/builds/{build_id}').json()['model_metadata']['calls']
        assert len(build_calls) == 1 + len(calls)
        assert calls_on_restart == []
        client.post(f'/builds/{build_id}/relations')
        assert client.get(f'/builds/{build_id}/relation-tasks').json()['items'][0]['diagnostic_history'][0] == first
        assert len(calls_on_restart) == 1
    # A second restart cannot append the same interrupted call again.
    with TestClient(create_app(settings, model=model, embedder=ControlledEmbedder())) as client:
        task = client.get(f'/builds/{build_id}/relation-tasks').json()['items'][0]
        assert len(task['diagnostic_history']) == 2
        assert len(client.get(f'/builds/{build_id}').json()['model_metadata']['calls']) == 2 + len(calls)


def test_old_database_records_are_not_backfilled_and_can_retry(settings, sample):
    from locomo_memory.database import Database
    settings = settings.model_copy(update={'model_retries': 0})
    def provider(request):
        payload = json.loads(json.loads(request.content)['messages'][1]['content'])
        return completion({'judgments': []}) if 'new_memory' in payload else two_memory_provider(request)
    model = DeepSeekModel(settings, api_key='synthetic', transport=httpx.MockTransport(provider))
    with TestClient(create_app(settings, model=model, embedder=ControlledEmbedder())) as client:
        build_id = build(client, sample)
        client.post(f'/builds/{build_id}/index')
        client.post(f'/builds/{build_id}/relations')
        task_id = client.get(f'/builds/{build_id}/relation-tasks').json()['items'][0]['task_id']
    # Independent temporary fixture with the pre-diagnostics tables and coarse calls.
    legacy_call = {'attempt': 1, 'outcome': 'invalid_output', 'usage': {}}
    with Database(settings.db_path).connect() as db:
        db.execute('DROP TABLE relation_provider_calls')
        db.execute('DROP TABLE relation_attempts')
        db.execute('UPDATE relation_tasks SET metadata_json=? WHERE task_id=?', (json.dumps({'calls': [legacy_call]}), task_id))
    model = DeepSeekModel(settings, api_key='synthetic', transport=httpx.MockTransport(two_memory_provider))
    with TestClient(create_app(settings, model=model, embedder=ControlledEmbedder())) as client:
        task = client.get(f'/builds/{build_id}/relation-tasks').json()['items'][0]
        assert task['diagnostic_history_status'] == 'legacy_not_recorded'
        assert task['diagnostic_history'] == []
        assert task['model_metadata']['calls'] == [legacy_call]
        assert 'finish_reason' not in task['model_metadata']['calls'][0]
        client.post(f'/builds/{build_id}/relations')
        task = client.get(f'/builds/{build_id}/relation-tasks').json()['items'][0]
        assert task['diagnostic_history_status'] == 'partial_legacy'
        assert [a['logical_attempt'] for a in task['diagnostic_history']] == [2]


def test_sensitive_provider_output_does_not_leak_to_database_api_or_logs(settings, sample, caplog):
    import sqlite3
    marker = 'synthetic-private-marker-DoNotPersist'
    settings = settings.model_copy(update={'model_retries': 1})
    def provider(request):
        payload = json.loads(json.loads(request.content)['messages'][1]['content'])
        if 'new_memory' not in payload:
            return two_memory_provider(request)
        output = relation(payload['history'][0], payload['new_memory'], label=marker, **{marker: marker})
        return completion({'judgments': [output]})
    model = DeepSeekModel(settings, api_key='synthetic', transport=httpx.MockTransport(provider))
    with TestClient(create_app(settings, model=model, embedder=ControlledEmbedder())) as client:
        build_id = build(client, sample)
        client.post(f'/builds/{build_id}/index')
        client.post(f'/builds/{build_id}/relations')
        assert marker not in client.get(f'/builds/{build_id}/relation-tasks').text
        assert marker not in client.get(f'/builds/{build_id}').text
    with sqlite3.connect(settings.db_path) as db:
        assert marker not in '\n'.join(db.iterdump())
    assert marker not in caplog.text


def test_task_pagination_preserves_all_calls_for_each_task(settings, sample):
    def provider(request):
        payload = json.loads(json.loads(request.content)['messages'][1]['content'])
        if 'new_memory' not in payload:
            return completion({'memories': [draft([source['source_id']], state_value=str(i)) for i, source in enumerate(payload['sources'])]})
        return completion({'judgments': [relation(old, payload['new_memory']) for old in payload['history']]})
    model = DeepSeekModel(settings, api_key='synthetic', transport=httpx.MockTransport(provider))
    with TestClient(create_app(settings, model=model, embedder=ControlledEmbedder())) as client:
        build_id = build(client, sample)
        client.post(f'/builds/{build_id}/index')
        client.post(f'/builds/{build_id}/relations')
        pages = [client.get(f'/builds/{build_id}/relation-tasks', params={'limit': 1, 'offset': offset}).json() for offset in range(2)]
        assert all(page['total'] == 2 for page in pages)
        items = [page['items'][0] for page in pages]
        assert len({item['task_id'] for item in items}) == 2
        assert all(len(item['diagnostic_history']) == 1 and len(item['diagnostic_history'][0]['calls']) == 1 for item in items)
        assert all(item['diagnostic_history'][0]['calls'][0]['task_id'] == item['task_id'] for item in items)


@pytest.mark.parametrize('invalid,code', [('blank_reason', 'nonblank_reason_required'),
                                         ('duplicate_sources', 'unique_evidence_required')])
def test_specific_reason_or_evidence_failure_survives_restart(settings, sample, invalid, code):
    settings = settings.model_copy(update={'model_retries': 0})
    def provider(request):
        payload = json.loads(json.loads(request.content)['messages'][1]['content'])
        if 'new_memory' not in payload:
            return two_memory_provider(request)
        judgment = relation(payload['history'][0], payload['new_memory'])
        if invalid == 'blank_reason':
            judgment['reason'] = ' '
        else:
            judgment['source_ids'].append(judgment['source_ids'][0])
        return completion({'judgments': [judgment]})
    model = DeepSeekModel(settings, api_key='synthetic', transport=httpx.MockTransport(provider))
    with TestClient(create_app(settings, model=model, embedder=ControlledEmbedder())) as client:
        build_id = build(client, sample)
        client.post(f'/builds/{build_id}/index')
        client.post(f'/builds/{build_id}/relations')
        task = client.get(f'/builds/{build_id}/relation-tasks').json()['items'][0]
        call = task['diagnostic_history'][0]['calls'][0]
        assert (call['error_code'], call['field_path']) == (code, 'judgments[0]')
        assert call['failure_stage'] == 'domain_validation'
    with TestClient(create_app(settings, model=model, embedder=ControlledEmbedder())) as client:
        assert client.get(f'/builds/{build_id}/relation-tasks').json()['items'][0] == task


def test_preflight_failure_has_no_fabricated_provider_attempt(settings, sample, monkeypatch):
    monkeypatch.delenv('DEEPSEEK_API_KEY', raising=False)
    model = DeepSeekModel(settings, api_key='synthetic', transport=httpx.MockTransport(two_memory_provider))
    with TestClient(create_app(settings, model=model, embedder=ControlledEmbedder())) as client:
        build_id = build(client, sample)
        client.post(f'/builds/{build_id}/index')
    missing_credentials_model = DeepSeekModel(settings, transport=httpx.MockTransport(two_memory_provider))
    with TestClient(create_app(settings, model=missing_credentials_model, embedder=ControlledEmbedder())) as client:
        client.post(f'/builds/{build_id}/relations')
        task = client.get(f'/builds/{build_id}/relation-tasks').json()['items'][0]
        assert task['diagnostic_history'][0]['status'] == 'failed'
        assert task['diagnostic_history'][0]['error_code'] == 'missing_credentials'
        assert task['diagnostic_history'][0]['calls'] == []
