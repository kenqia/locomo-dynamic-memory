"""Run the authorized conv-26 experiment with a durable provider-call ceiling.

Only the local ASGI client is in-process. DeepSeek uses its normal real HTTP
transport, and MiniLM uses the real local adapter. No request is altered.
"""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import threading
import time

from fastapi.testclient import TestClient

from locomo_memory.api import create_app
from locomo_memory.config import Settings
from locomo_memory.experiment import Experiment, ExperimentError, write_json
from locomo_memory.implementation_identity import implementation_sha256
from locomo_memory.model import DeepSeekModel, RELATION_PROMPT_VERSION, utc_now
from locomo_memory.relation_replay import read_report
from locomo_memory.relation_schemas import RELATION_SCHEMA_VERSION
from locomo_memory.usage import provider_usage

TERMINAL_SMOKE = {'passed', 'failed', 'interrupted', 'completed_with_errors',
                  'controlled_validation_only'}


class CeilingReached(RuntimeError):
    pass


class CallBudget:
    def __init__(self, path, limit, previous_calls, identity):
        self.path = path
        self.lock = threading.Lock()
        self.header = dict(limit=limit, previous_calls=previous_calls,
                           implementation_sha256=identity)
        with sqlite3.connect(path) as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS header(value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS calls(
                    sequence INTEGER PRIMARY KEY, operation TEXT NOT NULL,
                    started_at TEXT NOT NULL, metadata TEXT NOT NULL);
            ''')
            row = db.execute('SELECT value FROM header').fetchone()
            if row:
                if json.loads(row[0]) != self.header:
                    raise ValueError('frozen_budget_mismatch')
            else:
                db.execute('INSERT INTO header VALUES (?)', (json.dumps(self.header),))

    def reserve(self, operation):
        with self.lock, sqlite3.connect(self.path) as db:
            db.execute('BEGIN IMMEDIATE')
            used = db.execute('SELECT COUNT(*) FROM calls').fetchone()[0]
            if used + self.header['previous_calls'] >= self.header['limit']:
                raise CeilingReached()
            sequence = used + 1
            db.execute('INSERT INTO calls VALUES (?,?,?,?)',
                       (sequence, operation, utc_now(), json.dumps({'status': 'started'})))
            return sequence

    def observe(self, sequence, call):
        fields = ('attempt', 'timestamp', 'completed_at', 'status', 'outcome',
                  'response_received', 'requested_model', 'returned_model', 'usage',
                  'elapsed_seconds', 'failure_stage', 'error_code', 'field_path',
                  'finish_reason', 'finish_reason_status', 'validation_errors',
                  'task_id', 'logical_attempt', 'provider_attempt', 'call_id')
        safe = {key: call[key] for key in fields if key in call}
        with self.lock, sqlite3.connect(self.path) as db:
            db.execute('UPDATE calls SET metadata=? WHERE sequence=?',
                       (json.dumps(safe), sequence))

    def summary(self):
        with sqlite3.connect(self.path) as db:
            rows = db.execute('SELECT operation,metadata FROM calls ORDER BY sequence').fetchall()
        calls = [json.loads(row[1]) for row in rows]
        return {'limit': self.header['limit'], 'previous_calls': self.header['previous_calls'],
                'reserved_new_calls': len(rows),
                'reserved_total_calls': len(rows) + self.header['previous_calls'],
                'operations': dict(Counter(row[0] for row in rows)),
                'outcomes': dict(Counter(call.get('outcome', 'unknown') for call in calls)),
                'errors': dict(Counter(call['error_code'] for call in calls if call.get('error_code'))),
                'usage': provider_usage(calls)}


def attach_budget(model, budget, identity):
    generate = model.generate
    halted = threading.Event()

    def bounded(operation, payload, schema, *, context=None, on_call=None):
        if halted.is_set() or implementation_sha256() != identity:
            raise RuntimeError('execution_stopped')
        slots = {}

        def observe(call):
            attempt = call['attempt']
            if call['status'] == 'started':
                if halted.is_set() or implementation_sha256() != identity:
                    raise RuntimeError('execution_stopped')
                slots[attempt] = budget.reserve(operation)
            slot = slots[attempt]
            budget.observe(slot, call)
            if on_call:
                on_call(call)
                budget.observe(slot, call)
            if call.get('completed_at'):
                print(json.dumps({'event': 'provider_call_finished', 'sequence': slot,
                                  'operation': operation, 'outcome': call.get('outcome'),
                                  'error_code': call.get('error_code')}), flush=True)
            if call.get('outcome') in {'model_http_error', 'model_timeout', 'context_length_exceeded'}:
                halted.set()
                raise RuntimeError('provider_failure_requires_review')

        return generate(operation, payload, schema, context=context, on_call=observe)

    model.generate = bounded


def self_check():
    import httpx
    from locomo_memory.model import DiagnosticPersistenceFailure
    from locomo_memory.relation_schemas import RelationBatch

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'budget.sqlite3'
        budget = CallBudget(path, 3, 1, 'synthetic')
        assert budget.reserve('answer') == 1
        budget.observe(1, {'status': 'succeeded', 'outcome': 'succeeded', 'private': 'discard'})
        assert budget.reserve('relate') == 2
        restarted = CallBudget(path, 3, 1, 'synthetic')
        try:
            restarted.reserve('extract')
        except CeilingReached:
            pass
        else:
            raise AssertionError('budget_not_enforced')
        summary = restarted.summary()
        assert summary['reserved_total_calls'] == 3
        assert summary['outcomes'] == {'succeeded': 1, 'unknown': 1}
        with sqlite3.connect(path) as db:
            assert 'discard' not in db.execute('SELECT metadata FROM calls WHERE sequence=1').fetchone()[0]
        requests = []
        def invalid_response(request):
            requests.append(True)
            return httpx.Response(200, json={'choices': [{'finish_reason': 'stop',
                'message': {'content': '{invalid'}}]})
        identity = implementation_sha256()
        one_call = CallBudget(Path(tmp) / 'one.sqlite3', 1, 0, identity)
        model = DeepSeekModel(Settings(model_retries=2), api_key='synthetic',
                              transport=httpx.MockTransport(invalid_response))
        attach_budget(model, one_call, identity)
        try:
            model.generate('relate', {}, RelationBatch)
        except DiagnosticPersistenceFailure:
            pass
        else:
            raise AssertionError('internal_retry_bypassed_budget')
        assert len(requests) == 1
        assert one_call.summary()['reserved_total_calls'] == 1
    print('PASS: ceiling, durable reservations, restart, unknown counts and metadata allowlist; zero model calls.')


def run(directory, replay_directories):
    identity = implementation_sha256()
    previous = [read_report(path) for path in replay_directories]
    if any(r['mode'] != 'live' or r['reserved_calls'] != 3 or
           any(a['result'] is None for a in r['attempts']) for r in previous):
        raise ValueError('verification_history_incomplete')
    if any(a['result']['status'] != 'succeeded' for a in previous[-1]['attempts']):
        raise ValueError('latest_verification_not_passed')
    if any(a['implementation_sha256'] != identity or
           a['prompt_version'] != RELATION_PROMPT_VERSION or
           a['schema_version'] != RELATION_SCHEMA_VERSION
           for a in previous[-1]['attempts']):
        raise ValueError('verification_execution_identity_changed')
    if directory.exists():
        raise ValueError('new_experiment_directory_required')
    directory.mkdir(parents=True)
    prior = sum(r['reserved_calls'] for r in previous)
    budget = CallBudget(directory / 'provider-budget.sqlite3', 1000, prior, identity)
    settings = Settings(db_path=directory / 'memory.sqlite3')
    model = DeepSeekModel(settings)
    attach_budget(model, budget, identity)
    manifest = {'started_at': utc_now(), 'implementation_sha256': identity,
                'runner_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                'provider_call_limit': 1000, 'earlier_verification_calls': prior,
                'scope': 'new conv-26 build and five-question smoke only',
                'public_api_client': 'in-process ASGI TestClient; real DeepSeek and MiniLM',
                'settings': settings.snapshot(), 'status': 'running'}
    write_json(directory / 'continuation.json', manifest)
    experiment = None
    try:
        app = create_app(settings, model=model)
        with TestClient(app, raise_server_exceptions=False) as client:
            experiment = Experiment(client, directory)
            experiment.prepare()
            experiment.require_live_prerequisites()
            experiment.contract(Path('/home/kenqia/my_folder/locomo-worktrees/real-baseline-issue15/model-contract.json'))
            verified = experiment.verify()
            experiment.probe(verified)
            for _ in range(8):
                experiment.evaluate('smoke', verified)
                print(json.dumps({'event': 'phase_observed', 'status': experiment.state['status'],
                                  'budget': budget.summary()}), flush=True)
                if experiment.state.get('live_smoke') in TERMINAL_SMOKE:
                    break
                run_id = experiment.state.get('smoke_run_id')
                if run_id:
                    deadline = time.monotonic() + 3600
                    last_progress = None
                    while time.monotonic() < deadline:
                        progress = experiment.request('GET', f'/evaluation-runs/{run_id}/progress')
                        if progress['progress'] != last_progress:
                            print(json.dumps({'event': 'smoke_progress', **progress}), flush=True)
                            last_progress = progress['progress']
                        if progress['status'] != 'running':
                            break
                        time.sleep(2)
                    else:
                        raise RuntimeError('smoke_observation_deadline')
            experiment.export('smoke')
            manifest['status'] = experiment.state['status']
            if experiment.state.get('live_smoke') not in TERMINAL_SMOKE:
                manifest['status'] = 'stopped'
                manifest['error_code'] = ('provider_budget_exhausted' if
                    budget.summary()['reserved_total_calls'] >= 1000 else 'continuation_incomplete')
    except Exception as error:
        manifest['status'] = 'stopped'
        manifest['error_code'] = error.code if isinstance(error, ExperimentError) else 'continuation_stopped_requires_review'
        if experiment:
            manifest['last_experiment_status'] = experiment.state.get('status')
    finally:
        manifest['finished_at'] = utc_now()
        manifest['budget'] = budget.summary()
        write_json(directory / 'continuation.json', manifest)
        print(json.dumps(manifest), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--self-check', action='store_true')
    parser.add_argument('--directory', type=Path)
    parser.add_argument('--verification', type=Path, nargs='+')
    args = parser.parse_args()
    if args.self_check:
        self_check()
    else:
        try:
            run(args.directory.resolve(), args.verification)
        except Exception:
            print(json.dumps({'status': 'stopped', 'error_code': 'continuation_prerequisite_failed'}), flush=True)
            raise SystemExit(2)
