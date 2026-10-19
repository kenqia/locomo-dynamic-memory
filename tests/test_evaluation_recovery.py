"""Durable evaluation behavior through HTTP and the controlled provider boundary."""
import json
import threading
import time

import httpx
from fastapi.testclient import TestClient

from locomo_memory.api import create_app
from locomo_memory.model import DeepSeekModel
from test_builds import completion
from test_queries import complete_build, query_provider
from test_retrieval import ControlledEmbedder


def wait_run(client, run_id):
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        run = client.get('/evaluation-runs/' + run_id).json()
        if run['status'] != 'running':
            return run
        time.sleep(.01)
    raise AssertionError('evaluation did not finish')


def input_for(client, dataset_id, questions):
    response = client.post('/evaluation-inputs', json={'dataset_id': dataset_id, 'samples': [
        {'sample_id': 'conv-a', 'question': q, 'answer': 'Rome', 'category': 4, 'evidence': ['D2:1']} for q in questions]})
    assert response.status_code == 201, response.text
    return response.json()['input_id']


def test_create_returns_durable_id_while_provider_is_running_and_commits_each_item(settings, sample):
    entered, release = threading.Event(), threading.Event()
    calls = []
    def provider(request):
        payload = json.loads(json.loads(request.content)['messages'][1]['content'])
        if payload.get('operation') == 'answer':
            calls.append(payload['question'])
            if payload['question'] == 'Second question?':
                entered.set()
                assert release.wait(5)
                return httpx.Response(503, json={'error': 'safe controlled failure'})
        return query_provider(request)
    settings = settings.model_copy(update={'model_retries': 0})
    model = DeepSeekModel(settings, api_key='synthetic-test-key', transport=httpx.MockTransport(provider))
    with TestClient(create_app(settings, model=model, embedder=ControlledEmbedder())) as client:
        dataset_id, build_id = complete_build(client, sample)
        input_id = input_for(client, dataset_id, ['First question?', 'Second question?'])
        try:
            response = client.post('/evaluation-runs', json={'input_id': input_id, 'strategies': ['dynamic']})
            assert response.status_code == 201, response.text
            created = response.json()
            assert created['run_id']
            assert entered.wait(3)
            partial = client.get('/evaluation-runs/' + created['run_id']).json()
            assert partial['status'] == 'running'
            assert partial['completed_at'] is None
            assert partial['progress'] == {'total': 2, 'pending': 0, 'running': 1, 'succeeded': 1, 'failed': 0, 'interrupted': 0, 'unknown': 0}
            assert len(partial['results']) == 1
            assert partial['builds']['conv-a']['build_id'] == build_id
            assert partial['input']['input_id'] == input_id
            assert partial['fingerprint']
            conflict = client.post('/evaluation-runs/' + created['run_id'] + '/resume', json={})
            assert conflict.status_code == 409
        finally:
            release.set()
        finished = wait_run(client, created['run_id'])
        assert finished['status'] == 'completed_with_errors'
        assert finished['progress']['succeeded'] == 1
        assert finished['progress']['failed'] == 1
        assert len(finished['results']) == 2
        assert [a['status'] for a in finished['items'][1]['attempts']] == ['failed']
        assert calls == ['First question?', 'Second question?']


def test_failed_retry_is_explicit_and_retains_attempts_while_completed_resume_is_read_only(settings, sample):
    fail = {'enabled': False}
    answers = []
    def provider(request):
        payload = json.loads(json.loads(request.content)['messages'][1]['content'])
        if payload.get('operation') == 'answer':
            answers.append(payload['question'])
            if fail['enabled'] and payload['question'] == 'Retry question?':
                return httpx.Response(503, json={'error': 'do not save provider body'})
        return query_provider(request)
    settings = settings.model_copy(update={'model_retries': 0})
    model = DeepSeekModel(settings, api_key='synthetic-test-key', transport=httpx.MockTransport(provider))
    with TestClient(create_app(settings, model=model, embedder=ControlledEmbedder())) as client:
        dataset_id, _ = complete_build(client, sample)
        input_id = input_for(client, dataset_id, ['Successful question?', 'Retry question?'])
        fail['enabled'] = True
        run = client.post('/evaluation-runs', json={'input_id': input_id, 'strategies': ['dynamic'], 'wait': True}).json()
        assert run['status'] == 'completed_with_errors'
        failed = run['items'][1]['attempts'][0]
        assert failed['result']['error']['code'] == 'model_http_error'
        fail['enabled'] = False
        untouched = client.post('/evaluation-runs/' + run['run_id'] + '/resume', json={'wait': True}).json()
        assert len(answers) == 2
        assert untouched['progress']['failed'] == 1
        retried = client.post('/evaluation-runs/' + run['run_id'] + '/resume', json={'retry_failed': True, 'wait': True})
        assert retried.status_code == 202, retried.text
        done = retried.json()
        assert done['status'] == 'completed'
        assert done['progress']['total'] == 2
        assert len(done['results']) == 2
        assert [a['status'] for a in done['items'][1]['attempts']] == ['failed', 'succeeded']
        assert done['items'][1]['attempts'][0] == failed
        assert done['items'][1]['attempts'][1]['result']['usage_summary']['generation_calls'] > 0
        assert answers == ['Successful question?', 'Retry question?', 'Retry question?']
        assert client.get('/evaluation-runs/' + run['run_id']).json() == done
        assert client.post('/evaluation-runs/' + run['run_id'] + '/resume', json={'retry_failed': True, 'retry_unknown': True}).json() == done
        assert len(answers) == 3
    # A settings change cannot append results to an old immutable experiment.
    changed = settings.model_copy(update={'initial_k': settings.initial_k + 1})
    changed_model = DeepSeekModel(changed, api_key='synthetic-test-key', transport=httpx.MockTransport(provider))
    with TestClient(create_app(changed, model=changed_model, embedder=ControlledEmbedder())) as client:
        response = client.post('/evaluation-runs/' + run['run_id'] + '/resume', json={'retry_failed': True})
        assert response.status_code == 409
        assert response.json()['error']['code'] == 'evaluation_identity_changed'
        assert client.get('/evaluation-runs/' + run['run_id']).json() == done
        assert len(answers) == 3


def test_progress_can_be_polled_without_loading_result_traces(settings, sample):
    model = DeepSeekModel(settings, api_key='synthetic-test-key', transport=httpx.MockTransport(query_provider))
    with TestClient(create_app(settings, model=model, embedder=ControlledEmbedder())) as client:
        dataset_id, _ = complete_build(client, sample)
        input_id = input_for(client, dataset_id, ['Progress question?'])
        run = client.post('/evaluation-runs', json={'input_id': input_id, 'strategies': ['dynamic'], 'wait': True}).json()
        progress = client.get('/evaluation-runs/' + run['run_id'] + '/progress')
        assert progress.status_code == 200
        assert progress.json()['progress'] == {'total': 1, 'pending': 0, 'running': 0, 'succeeded': 1, 'failed': 0, 'interrupted': 0, 'unknown': 0}
        assert progress.json()['status'] == 'completed'
        assert 'items' not in progress.json()
        assert 'results' not in progress.json()
        assert 'input' not in progress.json()


def test_process_crash_preserves_success_and_marks_returned_uncommitted_answer_unknown(settings, sample, tmp_path):
    import os
    import subprocess
    import sys
    from pathlib import Path
    model = DeepSeekModel(settings, api_key='synthetic-test-key', transport=httpx.MockTransport(query_provider))
    with TestClient(create_app(settings, model=model, embedder=ControlledEmbedder())) as client:
        dataset_id, build_id = complete_build(client, sample)
        input_id = input_for(client, dataset_id, ['Persisted question?', 'Uncommitted question?', 'Pending question?'])
    # The child stops at the external model boundary after a successful provider
    # response, before the business operation can commit its returned answer.
    ledger = tmp_path / 'provider-ledger.jsonl'
    run_file = tmp_path / 'run-id.txt'
    program = r'''
import json, os, sys
from pathlib import Path
import httpx
from fastapi.testclient import TestClient
from locomo_memory.api import create_app
from locomo_memory.config import Settings
from locomo_memory.model import DeepSeekModel
from test_queries import query_provider
from test_retrieval import ControlledEmbedder
settings = Settings(db_path=Path(sys.argv[1]))
ledger, run_file = Path(sys.argv[3]), Path(sys.argv[4])
class CrashAfterProviderAnswer(DeepSeekModel):
    def generate(self, operation, payload, schema, **kwargs):
        result = super().generate(operation, payload, schema, **kwargs)
        if operation == 'answer':
            with ledger.open('a') as out:
                out.write(json.dumps(payload['question']) + '\n')
            if payload['question'] == 'Uncommitted question?':
                os._exit(23)
        return result
model = CrashAfterProviderAnswer(settings, api_key='synthetic-test-key', transport=httpx.MockTransport(query_provider))
with TestClient(create_app(settings, model=model, embedder=ControlledEmbedder())) as client:
    # Hold the HTTP boundary on an external provider gate until the ID has been
    # saved, then allow the child worker to reach the deliberate crash.
    import threading
    gate = threading.Event()
    underlying = model.generate
    def gated(operation, *args, **kwargs):
        if operation == 'query_analysis':
            gate.wait(5)
        return underlying(operation, *args, **kwargs)
    model.generate = gated
    response = client.post('/evaluation-runs', json={'input_id': sys.argv[2], 'strategies': ['dynamic']})
    run_file.write_text(response.json()['run_id'])
    gate.set()
    threading.Event().wait(10)
'''
    env = dict(os.environ)
    env['PYTHONPATH'] = os.pathsep.join([str(Path(__file__).resolve().parents[1] / 'src'), str(Path(__file__).resolve().parent)])
    child = subprocess.run([sys.executable, '-c', program, str(settings.db_path), input_id, str(ledger), str(run_file)], env=env, timeout=15, capture_output=True)
    assert child.returncode == 23, child.stderr.decode()
    run_id = run_file.read_text()
    assert [json.loads(line) for line in ledger.read_text().splitlines()] == ['Persisted question?', 'Uncommitted question?']
    resumed_answers = []
    def provider(request):
        payload = json.loads(json.loads(request.content)['messages'][1]['content'])
        if payload.get('operation') == 'answer':
            resumed_answers.append(payload['question'])
        return query_provider(request)
    model = DeepSeekModel(settings, api_key='synthetic-test-key', transport=httpx.MockTransport(provider))
    with TestClient(create_app(settings, model=model, embedder=ControlledEmbedder())) as client:
        interrupted = client.get('/evaluation-runs/' + run_id).json()
        assert interrupted['status'] == 'interrupted'
        assert interrupted['progress']['succeeded'] == 1
        assert interrupted['progress']['unknown'] == 1
        assert interrupted['progress']['interrupted'] == 1
        assert interrupted['items'][1]['attempts'][0]['status'] == 'unknown'
        assert 'billed' in interrupted['billing_notice']
        assert resumed_answers == []
        continued = client.post('/evaluation-runs/' + run_id + '/resume', json={'wait': True})
        assert continued.status_code == 202, continued.text
        assert continued.json()['progress']['succeeded'] == 2
        assert continued.json()['progress']['unknown'] == 1
        assert resumed_answers == ['Pending question?']
        recovered = client.post('/evaluation-runs/' + run_id + '/resume', json={'retry_unknown': True, 'wait': True})
        assert recovered.status_code == 202, recovered.text
        assert recovered.json()['status'] == 'completed'
        assert recovered.json()['progress']['total'] == 3
        assert [a['status'] for a in recovered.json()['items'][1]['attempts']] == ['unknown', 'succeeded']
        assert resumed_answers == ['Pending question?', 'Uncommitted question?']
        assert recovered.json()['builds']['conv-a']['build_id'] == build_id
