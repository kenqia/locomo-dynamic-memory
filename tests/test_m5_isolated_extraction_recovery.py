"""Independent retry keeps old paid stages immutable; all data are synthetic."""
import json
from pathlib import Path
import sqlite3
import sys

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.m5 import isolated_extraction_recovery as recovery
from tools.m5.offline import write
from test_m5_extraction_recovery import prepared
from test_builds import completion, draft


@pytest.fixture
def isolated(prepared, monkeypatch, tmp_path):
    source, _ = prepared
    # The shared generic fixture includes known synthetic QA sentinels. This
    # phase's input must be conversation-only before any all-row snapshot.
    with sqlite3.connect(source/'memory.sqlite3') as db:
        db.execute("UPDATE import_artifacts SET annotations_json='[]'")
    # The shared fixture's output cap is 8192; actual prepared stage uses 32768.
    monkeypatch.setattr(recovery, 'POLICY', {**recovery.POLICY, 'max_output_tokens': 8192})
    output = tmp_path/'isolated'
    recovery.prepare(source, output)
    return source, output


def test_nonempty_annotations_are_rejected_before_copy_or_snapshot(prepared, monkeypatch, tmp_path):
    source, _ = prepared
    monkeypatch.setattr(recovery, 'source_identity', lambda _: pytest.fail('must not hash annotations'))
    output = tmp_path/'rejected'
    with pytest.raises(ValueError, match='nonempty_annotations_forbidden'):
        recovery.prepare(source, output)
    assert not output.exists()


def authorize(output):
    write(output/'authorization.json', recovery.authorization(output))


def requests(output):
    with sqlite3.connect(output/'physical-requests.sqlite3') as db:
        return db.execute('SELECT COUNT(*) FROM physical_requests').fetchone()[0]


def test_prepare_and_authorization_denial_do_not_touch_old_stage(isolated):
    source, output = isolated
    before = recovery.source_identity(source)
    assert requests(output) == 0
    assert not (output/'authorization.json').exists()
    assert not json.loads((output/'authorization-template.json').read_text())['approved']
    with pytest.raises(FileNotFoundError):
        recovery.execute(output)
    assert recovery.source_identity(source) == before
    assert not (output/'execution-started.json').exists()


@pytest.mark.parametrize('valid', [True, False])
def test_new_finite_stage_preserves_old_database_ledger_and_good_fragments(isolated, valid):
    source, output = isolated
    before = recovery.source_identity(source)
    authorize(output)
    seen = []
    def provider(request):
        body = json.loads(request.content)
        assert body['thinking'] == {'type': 'disabled'} and 'reasoning_effort' not in body
        wire = json.loads(body['messages'][1]['content'])
        seen.append(wire)
        assert wire['sample_id'] == 'conv-44' and len(wire['sources']) == 1
        value = {'memories': [draft([wire['sources'][0]['source_id']])]} if valid else {'memories': []}
        return completion(value)
    if valid:
        result = recovery.execute(output, httpx.MockTransport(provider))
        assert result['status'] == 'extracted' and result['new_memories'] == 1
    else:
        with pytest.raises(RuntimeError, match='incomplete_no_automatic_retry'):
            recovery.execute(output, httpx.MockTransport(provider))
        result = json.loads((output/'outcome.json').read_text())
        assert result['status'] == 'failed' and result['new_memories'] == 0
    expected = 1 if valid else 3
    assert requests(output) == len(seen) == result['physical_requests'] == expected
    assert result['protected_rows_unchanged'] and result['original_build_fingerprint_preserved']
    assert recovery.source_identity(source) == before
    with pytest.raises(FileExistsError, match='already_started'):
        recovery.execute(output, httpx.MockTransport(provider))
    assert len(seen) == expected


@pytest.mark.parametrize('target', ['source', 'copy', 'ledger', 'settings', 'plan', 'approval'])
def test_changed_identity_rejected_before_send_or_marker(isolated, target):
    source, output = isolated
    authorize(output)
    if target in {'source', 'copy'}:
        directory = source if target == 'source' else output
        with sqlite3.connect(directory/'memory.sqlite3') as db:
            db.execute("UPDATE source_turns SET text=text || ' synthetic mutation'")
    elif target == 'ledger':
        with sqlite3.connect(output/'physical-requests.sqlite3') as db:
            db.execute("INSERT INTO physical_requests VALUES('test','.01','transport_unknown','null')")
    else:
        name = {'settings': 'settings.json', 'plan': 'plan.json', 'approval': 'authorization.json'}[target]
        path = output/name
        data = json.loads(path.read_text())
        if target == 'settings': data['extraction_thinking_effort'] = 'high'
        elif target == 'plan': data['scope'] = 'wrong scope'
        else: data['approved'] = False
        path.write_text(json.dumps(data))
    sent = []
    with pytest.raises(ValueError):
        recovery.execute(output, httpx.MockTransport(lambda request: sent.append(request)))
    assert not sent and not (output/'execution-started.json').exists()


def test_invalid_time_stays_rejected_on_all_three_attempts(isolated):
    source, output = isolated
    authorize(output)
    def provider(request):
        wire = json.loads(json.loads(request.content)['messages'][1]['content'])
        memory = draft([wire['sources'][0]['source_id']])
        memory['time'] = dict(original_expression='synthetic missing expression',
                              anchor_source_id=wire['sources'][0]['source_id'])
        return completion({'memories': [memory]})
    with pytest.raises(RuntimeError, match='incomplete_no_automatic_retry'):
        recovery.execute(output, httpx.MockTransport(provider))
    assert requests(output) == 3
    with sqlite3.connect(output/'memory.sqlite3') as db:
        metadata = json.loads(db.execute('SELECT model_metadata_json FROM build_fragments '
            'WHERE build_id=? AND ordinal=?', (recovery.legacy.BUILD, recovery.legacy.ORDINAL)).fetchone()[0])
    assert {c['error_code'] for c in metadata['calls']} == {'extraction_time_expression_required'}


def test_protected_snapshot_detects_historical_metadata_mutation(isolated):
    _, output = isolated
    plan = json.loads((output/'plan.json').read_text())
    with sqlite3.connect(output/'memory.sqlite3') as db:
        raw = db.execute('SELECT model_metadata_json FROM build_versions WHERE build_id=?',
                         (recovery.legacy.BUILD,)).fetchone()[0]
        metadata = json.loads(raw)
        metadata['calls'][0]['outcome'] = 'synthetic mutation'
        db.execute('UPDATE build_versions SET model_metadata_json=? WHERE build_id=?',
                   (json.dumps(metadata), recovery.legacy.BUILD))
    assert recovery.protected_snapshot(output/'memory.sqlite3', plan['initial_build_calls']) != plan['protected_snapshot']


def test_transport_unknown_keeps_full_reservations_and_stops_after_three(isolated):
    _, output = isolated
    authorize(output)
    def timeout(request):
        raise httpx.ReadTimeout('synthetic timeout', request=request)
    with pytest.raises(RuntimeError, match='incomplete_no_automatic_retry'):
        recovery.execute(output, httpx.MockTransport(timeout))
    outcome = json.loads((output/'outcome.json').read_text())
    assert outcome['physical_requests'] == 3
    assert outcome['ledger']['request_statuses'] == {'transport_unknown': 3}
    assert outcome['ledger']['unknown_usage_requests'] == 3
    assert outcome['ledger']['unknown_usage_reserved_usd'] == outcome['ledger']['reserved_usd']
