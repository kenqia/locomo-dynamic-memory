"""Offline preparation and explicit experiment controls at public boundaries."""
import json

import httpx
from fastapi.testclient import TestClient

from locomo_memory.api import create_app
from locomo_memory.model import DeepSeekModel
from test_retrieval import ControlledEmbedder


def test_preflight_is_read_only_safe_and_does_not_load_models(settings, monkeypatch):
    monkeypatch.setenv('DEEPSEEK_API_KEY', 'test-secret-must-not-appear')
    calls = []
    def provider(request):
        calls.append(request)
        raise AssertionError('Offline inspection must not generate')
    model = DeepSeekModel(settings, transport=httpx.MockTransport(provider))
    with TestClient(create_app(settings, model=model, embedder=ControlledEmbedder())) as client:
        response = client.get('/experiment-preflight')
        assert response.status_code == 200, response.text
        record = response.json()
        assert record['credential_present'] is True
        assert record['embedding']['status'] == 'not_verified'
        assert record['generation']['status'] == 'not_called'
        assert record['database_path'] == str(settings.db_path.resolve())
        assert record['config']['model_name'] == 'deepseek-flash'
        assert record['generation']['controlled_transport'] is True
        assert 'test-secret-must-not-appear' not in response.text
        assert client.get('/datasets').json()['total'] == 0
        assert calls == []


def test_prepare_creates_offline_artifacts_and_reports_missing_live_prerequisites(settings, tmp_path, capsys, monkeypatch):
    from locomo_memory.experiment import main
    monkeypatch.delenv('DEEPSEEK_API_KEY', raising=False)
    directory = settings.db_path.parent
    with TestClient(create_app(settings, embedder=ControlledEmbedder())) as client:
        assert main(['prepare', '--directory', str(directory)], client=client) == 0
        state = json.loads((directory / 'experiment.json').read_text())
        assert state['status'] == 'prepared_offline'
        assert state['live_smoke'] == 'not_run'
        assert state['full_baseline'] == 'not_run'
        assert 'missing_credentials' in state['blockers']
        smoke = json.loads((directory / 'plan-smoke.json').read_text())
        full = json.loads((directory / 'plan-development.json').read_text())
        assert smoke['combination_count'] == 20
        assert full['combination_count'] == 3028
        assert client.get('/datasets').json()['total'] == 1
        assert not state['builds']
        assert main(['prepare', '--directory', str(directory)], client=client) == 0
        assert json.loads((directory / 'plan-smoke.json').read_text()) == smoke
    assert 'prepared_offline' in capsys.readouterr().out


def test_preparation_rejects_wrong_database_before_importing(settings, tmp_path, capsys):
    from locomo_memory.experiment import main
    with TestClient(create_app(settings, embedder=ControlledEmbedder())) as client:
        assert main(['prepare', '--directory', str(tmp_path / 'other')], client=client) == 2
        assert client.get('/datasets').json()['total'] == 0
    assert 'experiment_database_mismatch' in capsys.readouterr().out


def test_embedding_verification_reports_unenforced_length_as_failure(settings):
    with TestClient(create_app(settings, embedder=ControlledEmbedder())) as client:
        record = client.get('/experiment-preflight', params={'verify_embedding': True}).json()
        assert record['embedding']['status'] == 'failed'
        assert record['embedding']['error']['code'] == 'embedding_length_policy_not_enforced'


def test_paid_stage_requires_explicit_flag_before_model_or_build_calls(settings, capsys):
    from locomo_memory.experiment import main
    with TestClient(create_app(settings, embedder=ControlledEmbedder())) as client:
        assert main(['prepare', '--directory', str(settings.db_path.parent)], client=client) == 0
        assert main(['smoke', '--directory', str(settings.db_path.parent)], client=client) == 2
        assert client.get('/builds').json()['total'] == 0
    assert 'paid_opt_in_required' in capsys.readouterr().out


def test_live_smoke_refuses_missing_credential_after_preserving_offline_preparation(settings, capsys, monkeypatch):
    from locomo_memory.experiment import main
    monkeypatch.delenv('DEEPSEEK_API_KEY', raising=False)
    directory = settings.db_path.parent
    with TestClient(create_app(settings, embedder=ControlledEmbedder())) as client:
        assert main(['prepare', '--directory', str(directory)], client=client) == 0
        assert main(['smoke', '--directory', str(directory), '--allow-paid'], client=client) == 2
        assert client.get('/builds').json()['total'] == 0
        assert (directory / 'plan-smoke.json').exists()
    assert 'missing_credentials' in capsys.readouterr().out


def test_live_smoke_requires_contract_record_before_any_generation(settings, tmp_path, capsys, monkeypatch):
    from locomo_memory.experiment import main
    monkeypatch.setenv('DEEPSEEK_API_KEY', 'synthetic-protected-key')
    calls = []
    def provider(request):
        calls.append(request)
        raise AssertionError('Unattested service contract must not generate')
    model = DeepSeekModel(settings, transport=httpx.MockTransport(provider))
    with TestClient(create_app(settings, model=model, embedder=ControlledEmbedder())) as client:
        assert main(['prepare', '--directory', str(tmp_path)], client=client) == 0
        assert main(['smoke', '--directory', str(tmp_path), '--allow-paid'], client=client) == 2
        assert calls == []
        assert client.get('/builds').json()['total'] == 0
    assert 'service_contract_not_recorded' in capsys.readouterr().out


def contract_record(tmp_path):
    path = tmp_path / 'checked-contract.json'
    path.write_text(json.dumps({'checked_date': '2026-10-20', 'source_url': 'https://api-docs.deepseek.com/quick_start/pricing', 'model_name': 'deepseek-flash', 'known_service_version': 'DeepSeek-V4.1-Flash-1017', 'context_window_tokens': 1000000, 'thinking_enabled': False, 'response_format': 'json_object', 'verification_scope': ['official model table'], 'limitations': ['Thinking and JSON guides re-fetch blocked; prior guide settings retained']}))
    return path


def test_smoke_preserves_failed_real_embedding_prerequisite_without_building(settings, tmp_path, capsys, monkeypatch):
    from locomo_memory.experiment import main
    monkeypatch.setenv('DEEPSEEK_API_KEY', 'synthetic-protected-key')
    with TestClient(create_app(settings, embedder=ControlledEmbedder())) as client:
        assert main(['prepare', '--directory', str(tmp_path)], client=client) == 0
        assert main(['smoke', '--directory', str(tmp_path), '--allow-paid', '--contract-record', str(contract_record(tmp_path))], client=client) == 2
        assert client.get('/builds').json()['total'] == 0
    record = json.loads((tmp_path / 'verified-preflight.json').read_text())
    assert record['embedding']['status'] == 'failed'
    assert 'embedding_verification_failed' in capsys.readouterr().out


class LengthCheckedEmbedder(ControlledEmbedder):
    def encode(self, texts):
        from locomo_memory.embeddings import EmbeddingFailure
        if any(len(text.split()) > 256 for text in texts):
            raise EmbeddingFailure('embedding_input_too_long')
        return super().encode(texts)


def test_small_probe_retains_public_build_and_source_proof_without_claiming_real_smoke(settings, tmp_path, monkeypatch):
    from locomo_memory.experiment import main
    from test_builds import completion, draft
    monkeypatch.setenv('DEEPSEEK_API_KEY', 'synthetic-protected-key')
    def provider(request):
        payload = json.loads(json.loads(request.content)['messages'][1]['content'])
        return completion({'memories': [draft([payload['sources'][0]['source_id']])]})
    model = DeepSeekModel(settings, transport=httpx.MockTransport(provider))
    with TestClient(create_app(settings, model=model, embedder=LengthCheckedEmbedder())) as client:
        assert main(['prepare', '--directory', str(tmp_path)], client=client) == 0
        assert main(['probe', '--directory', str(tmp_path), '--allow-paid', '--contract-record', str(contract_record(tmp_path))], client=client) == 0
        state = json.loads((tmp_path / 'experiment.json').read_text())
        assert state['probe']['status'] == 'passed'
        assert state['probe']['real_provider'] is False
        assert state['probe']['source_references_checked'] == 1
        assert state['probe']['returned_models'] == ['deepseek-test']
        assert state['live_smoke'] == 'not_run'
        assert client.get('/builds').json()['total'] == 1
        assert main(['probe', '--directory', str(tmp_path), '--allow-paid'], client=client) == 0
        assert client.get('/builds').json()['total'] == 1


def test_full_development_run_requires_actual_successful_smoke(settings, tmp_path, capsys):
    from locomo_memory.experiment import main
    with TestClient(create_app(settings, embedder=ControlledEmbedder())) as client:
        assert main(['prepare', '--directory', str(tmp_path)], client=client) == 0
        assert main(['full', '--directory', str(tmp_path), '--allow-paid'], client=client) == 2
        assert client.get('/builds').json()['total'] == 0
    assert 'successful_live_smoke_required' in capsys.readouterr().out


def test_offline_status_and_export_are_read_only_and_do_not_claim_completed_evaluation(settings, tmp_path, monkeypatch):
    from locomo_memory.experiment import main
    monkeypatch.delenv('DEEPSEEK_API_KEY', raising=False)
    with TestClient(create_app(settings, embedder=ControlledEmbedder())) as client:
        assert main(['prepare', '--directory', str(tmp_path)], client=client) == 0
        assert main(['status', '--directory', str(tmp_path)], client=client) == 0
        assert main(['export', '--directory', str(tmp_path)], client=client) == 0
        assert client.get('/builds').json()['total'] == 0
    report = (tmp_path / 'report-smoke.md').read_text()
    assert '未启动' in report
    assert '动态准确率未评' in report
    assert '教师隐藏评分' in report


def controlled_experiment_provider(request):
    from test_builds import completion, draft
    from test_relations import relation
    payload = json.loads(json.loads(request.content)['messages'][1]['content'])
    if payload.get('operation') == 'answer':
        citations = [{'memory_id': m['memory_id'], 'source_ids': m['source_ids']} for m in payload['memories']]
        if not citations and payload.get('sources'):
            citations = [{'memory_id': None, 'source_ids': [payload['sources'][0]['source_id']]}]
        return completion({'status': payload['status'], 'answer': 'Not mentioned.', 'citations': citations})
    if payload.get('operation') == 'resolve':
        return completion({'status': 'sufficient', 'effective_memory_ids': [m['memory_id'] for m in payload['memories']], 'decisions': [{'memory_id': m['memory_id'], 'selected': True, 'reason': 'Controlled fixture'} for m in payload['memories']], 'supplemental_relations': [], 'explanation': 'Controlled fixture'})
    if 'new_memory' in payload:
        return completion({'judgments': [relation(old, payload['new_memory']) for old in payload['history']]})
    if 'sources' in payload:
        return completion({'memories': [draft([payload['sources'][0]['source_id']])]})
    return completion({'entities': [], 'topic': None, 'time': None, 'keywords': []})


def wait_for_run(client, run_id):
    import time
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        progress = client.get(f'/evaluation-runs/{run_id}/progress').json()
        if progress['status'] != 'running':
            return client.get('/evaluation-runs/' + run_id).json()
        time.sleep(0.02)
    raise AssertionError('Controlled evaluation did not finish')


def test_smoke_runner_persists_twenty_items_and_reads_without_repeating_successes(settings, tmp_path, monkeypatch, capsys):
    from locomo_memory.experiment import main
    monkeypatch.setenv('DEEPSEEK_API_KEY', 'synthetic-protected-key')
    settings = settings.model_copy(update={'fragment_turns': 1000})
    calls = []
    def provider(request):
        calls.append(request)
        return controlled_experiment_provider(request)
    model = DeepSeekModel(settings, transport=httpx.MockTransport(provider))
    arguments = ['--directory', str(tmp_path)]
    with TestClient(create_app(settings, model=model, embedder=LengthCheckedEmbedder())) as client:
        assert main(['prepare', *arguments], client=client) == 0
        assert main(['smoke', *arguments, '--allow-paid', '--contract-record', str(contract_record(tmp_path))], client=client) == 0
        state = json.loads((tmp_path / 'experiment.json').read_text())
        assert state.get('smoke_run_id'), state
        run = wait_for_run(client, state['smoke_run_id'])
        assert run['progress']['succeeded'] == 20, run['progress']
        count = len(calls)
        assert main(['smoke', *arguments, '--allow-paid'], client=client) == 0
        assert main(['status', *arguments], client=client) == 0
        assert main(['export', *arguments], client=client) == 0
        state = json.loads((tmp_path / 'experiment.json').read_text())
        assert state['live_smoke'] == 'controlled_validation_only'
        assert len(calls) == count
        assert main(['full', *arguments, '--allow-paid'], client=client) == 2
        assert len(calls) == count
        exported = json.loads((tmp_path / 'runs' / run['run_id'] / 'run.json').read_text())
        assert len(exported['items']) == 20
        assert all(len(i['attempts']) == 1 for i in exported['items'])
    assert 'successful_live_smoke_required' in capsys.readouterr().out


def test_resume_requires_explicit_failure_retry_and_preserves_attempts(settings, tmp_path, monkeypatch):
    from locomo_memory.experiment import main
    monkeypatch.setenv('DEEPSEEK_API_KEY', 'synthetic-protected-key')
    settings = settings.model_copy(update={'fragment_turns': 1000, 'model_retries': 0})
    failure = {'enabled': True}
    calls = []
    def provider(request):
        calls.append(request)
        payload = json.loads(json.loads(request.content)['messages'][1]['content'])
        if failure['enabled'] and payload.get('operation') == 'answer':
            return httpx.Response(503, text='private-provider-body-not-retained')
        return controlled_experiment_provider(request)
    model = DeepSeekModel(settings, transport=httpx.MockTransport(provider))
    arguments = ['--directory', str(tmp_path)]
    with TestClient(create_app(settings, model=model, embedder=LengthCheckedEmbedder())) as client:
        assert main(['prepare', *arguments], client=client) == 0
        assert main(['smoke', *arguments, '--allow-paid', '--contract-record', str(contract_record(tmp_path))], client=client) == 0
        run_id = json.loads((tmp_path / 'experiment.json').read_text())['smoke_run_id']
        run = wait_for_run(client, run_id)
        assert run['progress']['failed'] == 20
        count = len(calls)
        failure['enabled'] = False
        assert main(['resume', *arguments, '--allow-paid'], client=client) == 0
        assert len(calls) == count
        assert main(['resume', *arguments, '--allow-paid', '--retry-failed'], client=client) == 0
        run = wait_for_run(client, run_id)
        assert run['progress']['succeeded'] == 20
        assert all([a['status'] for a in i['attempts']] == ['failed', 'succeeded'] for i in run['items'])
        assert main(['export', *arguments], client=client) == 0
        assert 'private-provider-body-not-retained' not in (tmp_path / 'runs' / run_id / 'run.json').read_text()


def test_lost_build_creation_response_is_preserved_as_unknown_without_automatic_duplicate(settings, tmp_path, monkeypatch, capsys):
    from locomo_memory.experiment import main
    monkeypatch.setenv('DEEPSEEK_API_KEY', 'synthetic-protected-key')
    model = DeepSeekModel(settings, transport=httpx.MockTransport(controlled_experiment_provider))
    with TestClient(create_app(settings, model=model, embedder=LengthCheckedEmbedder())) as api:
        def transport(request):
            response = api.request(request.method, str(request.url), content=request.content, headers=request.headers)
            if request.method == 'POST' and request.url.path == '/builds':
                raise httpx.ReadTimeout('Response lost after server accepted build')
            return httpx.Response(response.status_code, content=response.content, headers=response.headers)
        with httpx.Client(base_url='http://localhost', transport=httpx.MockTransport(transport)) as client:
            args = ['--directory', str(tmp_path)]
            assert main(['prepare', *args], client=client) == 0
            assert main(['probe', *args, '--allow-paid', '--contract-record', str(contract_record(tmp_path))], client=client) == 2
            assert api.get('/builds').json()['total'] == 1
            assert main(['probe', *args, '--allow-paid'], client=client) == 2
            assert api.get('/builds').json()['total'] == 1
    assert 'initiation_outcome_unknown' in capsys.readouterr().out
    state = json.loads((tmp_path / 'experiment.json').read_text())
    assert state['pending_initiation']['path'] == '/builds'
