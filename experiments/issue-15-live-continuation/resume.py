"""One explicit same-contract phase retry, sharing the unchanged call budget."""

import argparse
import hashlib
import json
from pathlib import Path
import sqlite3
import time

from fastapi.testclient import TestClient

from locomo_memory.api import create_app
from locomo_memory.config import Settings
from locomo_memory.experiment import Experiment, ExperimentError, write_json
from locomo_memory.implementation_identity import implementation_sha256
from locomo_memory.model import DeepSeekModel, utc_now
from run import CallBudget, attach_budget


def resume(directory, build_id):
    initial = json.loads((directory / 'continuation.json').read_text())
    target = directory / 'explicit-phase-retry.json'
    if target.exists() or initial['status'] != 'stopped':
        raise ValueError('explicit_retry_not_available')
    identity = implementation_sha256()
    if identity != initial['implementation_sha256']:
        raise ValueError('implementation_changed')
    settings = Settings(db_path=directory / 'memory.sqlite3')
    if settings.snapshot() != initial['settings']:
        raise ValueError('configuration_changed')
    ledger = directory / 'provider-budget.sqlite3'
    if not ledger.is_file():
        raise ValueError('existing_budget_required')
    with sqlite3.connect(ledger.as_uri() + '?mode=ro', uri=True) as db:
        header = json.loads(db.execute('SELECT value FROM header').fetchone()[0])
        expected = {'limit': 1000, 'previous_calls': initial['earlier_verification_calls'],
                    'implementation_sha256': identity}
        if header != expected:
            raise ValueError('existing_budget_identity_mismatch')
    budget = CallBudget(ledger, 1000,
                        initial['earlier_verification_calls'], identity)
    before = budget.summary()
    if before['reserved_total_calls'] < initial['budget']['reserved_total_calls']:
        raise ValueError('budget_history_rolled_back')
    if (before['outcomes'].get('unknown', 0) or before['reserved_total_calls'] >= 1000 or
            any(code in before['errors'] for code in ('model_http_error', 'model_timeout', 'context_length_exceeded'))):
        raise ValueError('budget_or_provider_requires_review')
    model = DeepSeekModel(settings)
    attach_budget(model, budget, identity)
    outcome = {'status': 'running', 'started_at': utc_now(), 'build_id': build_id,
               'implementation_sha256': identity, 'budget_before': before,
               'runner_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               'budget_support_sha256': hashlib.sha256(Path(__file__).with_name('run.py').read_bytes()).hexdigest()}
    write_json(target, outcome)
    try:
        with TestClient(create_app(settings, model=model), raise_server_exceptions=False) as client:
            experiment = Experiment(client, directory)
            if experiment.state['builds'].get('conv-26') != build_id:
                raise ValueError('experiment_build_not_owned')
            build = experiment.snapshot_build(build_id)
            if build['phase'] != 'extraction' or build['status'] != 'failed':
                raise ValueError('only_failed_extraction_retry_selected')
            experiment.require_live_prerequisites()
            experiment.contract()
            verified = experiment.verify()
            experiment.resume('smoke', build_id=build_id)
            experiment.evaluate('smoke', verified)
            run_id = experiment.state.get('smoke_run_id')
            if run_id:
                deadline, last = time.monotonic() + 3600, None
                while time.monotonic() < deadline:
                    progress = experiment.request('GET', f'/evaluation-runs/{run_id}/progress')
                    if progress['progress'] != last:
                        print(json.dumps({'event': 'smoke_progress', **progress}), flush=True)
                        last = progress['progress']
                    if progress['status'] != 'running':
                        break
                    time.sleep(2)
                else:
                    raise RuntimeError('smoke_observation_deadline')
                experiment.evaluate('smoke', verified)
            experiment.export('smoke')
            outcome['status'] = experiment.state['status']
            if experiment.state.get('live_smoke') not in {'passed', 'completed_with_errors', 'failed', 'interrupted', 'controlled_validation_only'}:
                outcome.update(status='stopped', error_code='continuation_incomplete')
    except Exception as error:
        outcome.update(status='stopped', error_code=error.code if isinstance(error, ExperimentError) else 'explicit_retry_stopped_requires_review')
    finally:
        outcome.update(finished_at=utc_now(), budget_after=budget.summary())
        write_json(target, outcome)
        print(json.dumps(outcome), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--build-id', required=True)
    args = parser.parse_args()
    try:
        resume(args.directory.resolve(), args.build_id)
    except Exception:
        print(json.dumps({'status': 'stopped', 'error_code': 'explicit_retry_prerequisite_failed'}), flush=True)
        raise SystemExit(2)
