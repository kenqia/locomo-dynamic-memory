"""Offline replay preparation and a hard provider-call budget, without live requests."""
import hashlib
import json
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from locomo_memory.api import create_app
from locomo_memory.model import DeepSeekModel
from locomo_memory.relation_replay import prepare_plan
from test_relation_diagnostics import two_memory_provider
from test_retrieval import ControlledEmbedder, build


def stopped_source(settings, sample):
    model = DeepSeekModel(settings, api_key='synthetic', transport=httpx.MockTransport(two_memory_provider))
    with TestClient(create_app(settings, model=model, embedder=ControlledEmbedder())) as client:
        build_id = build(client, sample)
        client.post(f'/builds/{build_id}/index')
        # The public service schedules tasks without sending provider requests.
        client.app.state.relations.start(build_id)
    return build_id


def test_preparation_freezes_inputs_without_copying_source_text_or_changing_database(settings, sample, tmp_path):
    settings = settings.model_copy(update={'db_path': tmp_path / 'source' / 'memory.sqlite3'})
    build_id = stopped_source(settings, sample)
    before = hashlib.sha256(settings.db_path.read_bytes()).hexdigest()
    plan = prepare_plan(settings.db_path, build_id, [1], tmp_path / 'isolated')
    assert plan['source_database_sha256'] == before
    assert hashlib.sha256(settings.db_path.read_bytes()).hexdigest() == before
    assert plan['settings']['model_retries'] == 0
    assert plan['original_model_retries'] == 2
    assert plan['proposed_call_limit'] == 2
    assert plan['tasks'][0]['history_count'] == 1
    assert plan['tasks'][0]['request_context_estimate']['is_provider_token_count'] is False
    assert 'I live in Paris' not in json.dumps(plan)
    assert 'Alex lives in Paris' not in json.dumps(plan)
    assert not (tmp_path / 'isolated' / 'calls.sqlite3').exists()


def test_approved_budget_is_durable_and_duplicate_command_cannot_replay(settings, sample, tmp_path):
    from locomo_memory.relation_replay import run_phase, read_report
    settings = settings.model_copy(update={'db_path': tmp_path / 'source' / 'memory.sqlite3'})
    build_id = stopped_source(settings, sample)
    directory = tmp_path / 'isolated'
    prepare_plan(settings.db_path, build_id, [1], directory)
    requests = []
    def provider(request):
        requests.append(request)
        return two_memory_provider(request)
    with pytest.raises(Exception, match='paid_approval_required'):
        run_phase(directory, 'before', 1, allow_paid=False, api_key='synthetic', transport=httpx.MockTransport(provider))
    result = run_phase(directory, 'before', 1, allow_paid=True, api_key='synthetic', transport=httpx.MockTransport(provider))
    assert result['reserved_calls'] == 1 and result['remaining_calls'] == 0
    assert result['attempts'][0]['diagnostics']['finish_reason'] == 'stop'
    assert result['attempts'][0]['result']['label_counts'] == {'undetermined': 1}
    assert read_report(directory)['reserved_calls'] == 1
    run_phase(directory, 'before', 1, allow_paid=True, api_key='synthetic', transport=httpx.MockTransport(provider))
    assert len(requests) == 1


def test_process_exit_does_not_release_reserved_budget_or_automatically_replay(settings, sample, tmp_path):
    import subprocess
    import sys
    from locomo_memory.relation_replay import run_phase, read_report, ReplayError
    settings = settings.model_copy(update={'db_path': tmp_path / 'source' / 'memory.sqlite3'})
    build_id = stopped_source(settings, sample)
    directory = tmp_path / 'isolated'
    prepare_plan(settings.db_path, build_id, [1], directory)
    program = '''
import os, sys
from pathlib import Path
import httpx
from locomo_memory.relation_replay import run_phase
def provider(request):
    os._exit(23)
run_phase(Path(sys.argv[1]), 'before', 2, allow_paid=True, api_key='synthetic', transport=httpx.MockTransport(provider))
'''
    child = subprocess.run([sys.executable, '-c', program, str(directory)], capture_output=True, timeout=15)
    assert child.returncode == 23, child.stderr.decode()
    report = read_report(directory)
    assert report['status'] == 'outcome_unknown'
    assert report['reserved_calls'] == 1 and report['remaining_calls'] == 1
    assert report['usage']['reported_tokens']['total_tokens'] is None
    assert report['attempts'][0]['result'] is None
    with pytest.raises(ReplayError, match='uncommitted_attempt_requires_review'):
        run_phase(directory, 'before', 2, allow_paid=True, api_key='synthetic', transport=httpx.MockTransport(lambda _: pytest.fail('Must not replay')))


def test_budget_cannot_be_increased_by_repeating_command(settings, sample, tmp_path):
    from locomo_memory.relation_replay import run_phase, ReplayError
    settings = settings.model_copy(update={'db_path': tmp_path / 'source' / 'memory.sqlite3'})
    build_id = stopped_source(settings, sample)
    directory = tmp_path / 'isolated'
    prepare_plan(settings.db_path, build_id, [1], directory)
    run_phase(directory, 'before', 1, allow_paid=True, api_key='synthetic', transport=httpx.MockTransport(two_memory_provider))
    with pytest.raises(ReplayError, match='frozen_approval_mismatch'):
        run_phase(directory, 'before', 2, allow_paid=True, api_key='synthetic', transport=httpx.MockTransport(lambda _: pytest.fail('Must not increase budget')))


def test_no_after_calls_without_reproduced_failure(settings, sample, tmp_path):
    from locomo_memory.relation_replay import run_phase, ReplayError
    settings = settings.model_copy(update={'db_path': tmp_path / 'source' / 'memory.sqlite3'})
    build_id = stopped_source(settings, sample)
    directory = tmp_path / 'isolated'
    prepare_plan(settings.db_path, build_id, [1], directory)
    run_phase(directory, 'before', 2, allow_paid=True, api_key='synthetic', transport=httpx.MockTransport(two_memory_provider))
    with pytest.raises(ReplayError, match='failure_not_reproduced'):
        run_phase(directory, 'after', 2, allow_paid=True, api_key='synthetic', transport=httpx.MockTransport(lambda _: pytest.fail('Must not run after')))


def test_provider_failure_stops_future_calls_and_cannot_resume_implicitly(settings, sample, tmp_path):
    from locomo_memory.relation_replay import run_phase, ReplayError
    settings = settings.model_copy(update={'db_path': tmp_path / 'source' / 'memory.sqlite3'})
    build_id = stopped_source(settings, sample)
    directory = tmp_path / 'isolated'
    prepare_plan(settings.db_path, build_id, [1], directory)
    def failure(_):
        raise httpx.ReadTimeout('synthetic-private-marker')
    report = run_phase(directory, 'before', 2, allow_paid=True, api_key='synthetic', transport=httpx.MockTransport(failure))
    assert report['attempts'][0]['diagnostics']['failure_stage'] == 'transport'
    assert 'synthetic-private-marker' not in json.dumps(report)
    with pytest.raises(ReplayError, match='provider_failure_requires_review'):
        run_phase(directory, 'before', 2, allow_paid=True, api_key='synthetic', transport=httpx.MockTransport(lambda _: pytest.fail('Must stop')))


def test_hard_budget_stops_before_second_task(settings, sample, tmp_path):
    from locomo_memory.relation_replay import run_phase
    from test_builds import completion, draft
    settings = settings.model_copy(update={'db_path': tmp_path / 'source' / 'memory.sqlite3'})
    def extraction(request):
        payload = json.loads(json.loads(request.content)['messages'][1]['content'])
        return completion({'memories': [draft([source['source_id']]) for source in payload['sources']]})
    model = DeepSeekModel(settings, api_key='synthetic', transport=httpx.MockTransport(extraction))
    with TestClient(create_app(settings, model=model, embedder=ControlledEmbedder())) as client:
        build_id = build(client, sample)
        client.post(f'/builds/{build_id}/index')
        client.app.state.relations.start(build_id)
    directory = tmp_path / 'isolated'
    prepare_plan(settings.db_path, build_id, [1, 2], directory)
    requests = []
    def provider(request):
        requests.append(request)
        return two_memory_provider(request)
    report = run_phase(directory, 'before', 1, allow_paid=True, api_key='synthetic', transport=httpx.MockTransport(provider))
    assert report['status'] == 'budget_exhausted' and len(requests) == 1
    run_phase(directory, 'before', 1, allow_paid=True, api_key='synthetic', transport=httpx.MockTransport(provider))
    assert len(requests) == 1


def test_changed_source_is_rejected_before_provider_call(settings, sample, tmp_path):
    import sqlite3
    from locomo_memory.relation_replay import run_phase, ReplayError
    settings = settings.model_copy(update={'db_path': tmp_path / 'source' / 'memory.sqlite3'})
    build_id = stopped_source(settings, sample)
    directory = tmp_path / 'isolated'
    prepare_plan(settings.db_path, build_id, [1], directory)
    with sqlite3.connect(settings.db_path) as db:
        db.execute("UPDATE relation_tasks SET status='failed'")
    db.close()
    with pytest.raises(ReplayError, match='source_snapshot_mismatch'):
        run_phase(directory, 'before', 2, allow_paid=True, api_key='synthetic', transport=httpx.MockTransport(lambda _: pytest.fail('Changed inputs must stop')))


def test_missing_credential_does_not_charge_provider_budget(settings, sample, tmp_path, monkeypatch):
    from locomo_memory.relation_replay import run_phase, read_report, ReplayError
    monkeypatch.delenv('DEEPSEEK_API_KEY', raising=False)
    settings = settings.model_copy(update={'db_path': tmp_path / 'source' / 'memory.sqlite3'})
    build_id = stopped_source(settings, sample)
    directory = tmp_path / 'isolated'
    prepare_plan(settings.db_path, build_id, [1], directory)
    with pytest.raises(ReplayError, match='missing_credentials'):
        run_phase(directory, 'before', 2, allow_paid=True, transport=httpx.MockTransport(lambda _: pytest.fail('Must not call without credential')))
    assert read_report(directory)['reserved_calls'] == 0


def test_replay_ledger_excludes_invalid_output_and_private_exception_text(settings, sample, tmp_path):
    import sqlite3
    from locomo_memory.relation_replay import run_phase
    from test_builds import completion
    settings = settings.model_copy(update={'db_path': tmp_path / 'source' / 'memory.sqlite3'})
    build_id = stopped_source(settings, sample)
    directory = tmp_path / 'isolated'
    prepare_plan(settings.db_path, build_id, [1], directory)
    marker = 'synthetic-private-marker'
    report = run_phase(directory, 'before', 2, allow_paid=True, api_key='synthetic', transport=httpx.MockTransport(lambda _: completion({marker: marker})))
    assert {item['error_code'] for item in report['attempts'][0]['diagnostics']['validation_errors']} == {'missing_field', 'extra_field'}
    assert marker not in json.dumps(report)
    with sqlite3.connect(directory / 'calls.sqlite3') as db:
        stored = '\n'.join(db.iterdump())
        assert marker not in stored
        assert 'I live in Paris' not in stored
        assert 'Alex lives in Paris' not in stored


def test_source_backend_lock_and_nonempty_wal_block_preparation(settings, sample, tmp_path):
    import fcntl
    from locomo_memory.relation_replay import ReplayError
    settings = settings.model_copy(update={'db_path': tmp_path / 'source' / 'memory.sqlite3'})
    build_id = stopped_source(settings, sample)
    with settings.db_path.with_name(settings.db_path.name + '.runtime.lock').open('rb') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(ReplayError, match='source_backend_running'):
            prepare_plan(settings.db_path, build_id, [1], tmp_path / 'isolated')
    settings.db_path.with_name(settings.db_path.name + '-wal').write_bytes(b'synthetic-uncheckpointed-wal')
    with pytest.raises(ReplayError, match='source_has_nonempty_wal'):
        prepare_plan(settings.db_path, build_id, [1], tmp_path / 'isolated')


def test_source_directory_and_ledger_symlink_are_rejected(settings, sample, tmp_path):
    from locomo_memory.relation_replay import ReplayError, run_phase
    settings = settings.model_copy(update={'db_path': tmp_path / 'source' / 'memory.sqlite3'})
    build_id = stopped_source(settings, sample)
    with pytest.raises(ReplayError, match='output_must_be_separate_from_source'):
        prepare_plan(settings.db_path, build_id, [1], settings.db_path.parent / 'bad-output')
    directory = tmp_path / 'isolated'
    prepare_plan(settings.db_path, build_id, [1], directory)
    (directory / 'calls.sqlite3').symlink_to(settings.db_path)
    before = hashlib.sha256(settings.db_path.read_bytes()).hexdigest()
    with pytest.raises(ReplayError, match='replay_files_must_not_be_symlinks'):
        run_phase(directory, 'before', 2, allow_paid=True, api_key='synthetic', transport=httpx.MockTransport(lambda _: pytest.fail('Must not call')))
    assert hashlib.sha256(settings.db_path.read_bytes()).hexdigest() == before
