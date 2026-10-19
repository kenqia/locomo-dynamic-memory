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
