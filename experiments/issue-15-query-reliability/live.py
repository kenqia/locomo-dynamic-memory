"""Freeze and execute a bounded query-only replay using existing evaluation APIs."""
import argparse
import fcntl
import hashlib
import importlib.util
import json
from pathlib import Path
import sqlite3
import sys

from fastapi.testclient import TestClient
from locomo_memory.api import create_app
from locomo_memory.config import Settings
from locomo_memory.implementation_identity import implementation_sha256
from locomo_memory.model import DeepSeekModel, utc_now

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT.parent / 'real-baseline-issue15-evidence-coverage-ab'
PRIOR = SOURCE / 'campaign.sqlite3'
spec = importlib.util.spec_from_file_location('coverage_live', ROOT / 'experiments/issue-15-evidence-coverage-live/run.py')
previous = importlib.util.module_from_spec(spec)
spec.loader.exec_module(previous)
sys.path.insert(0, str(ROOT / 'experiments/issue-15-v6-gates'))
import v6_campaign

save = previous.save
CALL_LIMIT = 64
GROUPS = {'primary': ('dynamic_raw_fallback', [0, 3, 15, 18, 32, 36, 53, 60, 74, 136, 153]),
          'dynamic_nonregression': ('dynamic', [3, 15, 53])}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(directory):
    directory.mkdir(parents=True, exist_ok=False)
    source_plan = json.loads((SOURCE / 'plan.json').read_text())
    with sqlite3.connect(PRIOR.as_uri() + '?mode=ro', uri=True) as db:
        header = json.loads(db.execute('SELECT value FROM header').fetchone()[0])
        calls = [json.loads(r[0]) for r in db.execute('SELECT metadata FROM calls')]
    assert all(c.get('completed_at') for c in calls), 'unresolved_prior_call'
    used = header['previous_calls'] + len(calls)
    raw = ROOT / 'data/raw/locomo/locomo10.json'
    assert digest(raw) == source_plan['official_artifact_sha256']
    qa = next(c for c in json.loads(raw.read_text()) if c['sample_id'] == 'conv-26')['qa']
    with sqlite3.connect((SOURCE / 'memory.sqlite3').as_uri() + '?mode=ro', uri=True) as src:
        with sqlite3.connect(directory / 'memory.sqlite3') as dst:
            src.backup(dst)
    build_digest = previous.previous.artifact_digest(SOURCE / 'memory.sqlite3')
    assert previous.previous.artifact_digest(directory / 'memory.sqlite3') == build_digest
    settings = Settings.model_validate({**source_plan['settings'], 'db_path': str(directory / 'memory.sqlite3')})
    plan = dict(created_at=utc_now(), sample_id='conv-26',
        source_directory=str(SOURCE), prior_ledger_sha256=digest(PRIOR),
        source_build_id=source_plan['source_build_id'], source_dataset_id=source_plan['source_dataset_id'],
        immutable_build_artifacts_sha256=build_digest, official_artifact_sha256=digest(raw),
        implementation_sha256=implementation_sha256(), settings=settings.snapshot(), evidence_profile='expanded',
        previous_calls=used, previous_ceiling=header['limit'], call_limit=CALL_LIMIT,
        campaign_phase=f'query-reliability-frozen-{sum(len(indices) for _, indices in GROUPS.values())}',
        cumulative_ceiling=used + CALL_LIMIT,
        authorization='Pending explicit confirmation of this frozen plan and call ceiling; prepare makes no model calls.',
        policy='One pass, no question reselection, no answer-driven tuning, no rebuild, no automatic run recovery. Retries count toward the same hard ceiling.',
        experiments={label: {'strategies': [strategy], 'logical_items': len(indices), 'questions': [
            {'question_id': f'conv-26:qa:{i}', 'qa_index': i, 'official_qa': qa[i]}
            for i in indices]} for label, (strategy, indices) in GROUPS.items()})
    save(directory / 'plan.json', plan)
    (directory / 'plan.sha256').write_text(digest(directory / 'plan.json') + '\n')
    return plan


def execute(directory, authorized_call_limit):
    assert authorized_call_limit == CALL_LIMIT, 'explicit_frozen_call_limit_required'
    assert digest(directory / 'plan.json') == (directory / 'plan.sha256').read_text().strip()
    plan = json.loads((directory / 'plan.json').read_text())
    assert implementation_sha256() == plan['implementation_sha256']
    assert digest(PRIOR) == plan['prior_ledger_sha256']
    assert digest(ROOT / 'data/raw/locomo/locomo10.json') == plan['official_artifact_sha256']
    assert not (directory / 'outcome.json').exists(), 'explicit_recovery_required'
    artifact_digest = previous.previous.artifact_digest
    assert artifact_digest(directory / 'memory.sqlite3') == plan['immutable_build_artifacts_sha256']
    campaign = v6_campaign.Campaign(directory / 'campaign.sqlite3', PRIOR, create=True, limit=plan['cumulative_ceiling'])
    assert campaign.header['previous_calls'] == plan['previous_calls']
    v6_campaign.FIELDS += ('thinking', 'reasoning_effort', 'max_tokens')
    settings = Settings.model_validate(plan['settings'])
    audit = previous.previous.ValidationAudit(directory)
    model = DeepSeekModel(settings, transport=audit)
    generate = model.generate
    def observed(operation, payload, schema, *, context=None, on_call=None):
        audit.operation, audit.schema, audit.context = operation, schema, context
        return generate(operation, payload, schema, context=context, on_call=on_call)
    model.generate = observed
    campaign.bind(model, plan.get('campaign_phase', 'query-reliability-frozen-14'))
    outcome = dict(started_at=utc_now(), status='running', runs={}, authorized_call_limit=authorized_call_limit)
    save(directory / 'outcome.json', outcome)
    try:
        app = create_app(settings, model=model)
        with TestClient(app) as client:
            assert client.get(f"/builds/{plan['source_build_id']}").json()['status'] == 'complete'
            for label in plan['experiments']:
                previous.run_group(client, app, directory, plan, label, outcome)
        outcome['status'] = 'completed' if all(r['status'] == 'completed' for r in outcome['runs'].values()) else 'completed_with_errors'
    except Exception as error:
        outcome.update(status='experiment_stopped', error_type=type(error).__name__)
    finally:
        outcome.update(completed_at=utc_now(), budget_after=campaign.summary(),
            source_build_unchanged=artifact_digest(SOURCE / 'memory.sqlite3') == plan['immutable_build_artifacts_sha256'],
            snapshot_build_unchanged=artifact_digest(directory / 'memory.sqlite3') == plan['immutable_build_artifacts_sha256'])
        save(directory / 'outcome.json', outcome)
    print(json.dumps(outcome), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare', 'execute'])
    parser.add_argument('--directory', required=True, type=Path)
    parser.add_argument('--authorized-call-limit', type=int)
    args = parser.parse_args()
    with previous.ORIGINAL_LOCK.open('a+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if args.action == 'prepare':
            plan = prepare(args.directory.resolve())
            print(json.dumps({'status': 'frozen_pending_authorization', 'call_limit': plan['call_limit'],
                              'previous_calls': plan['previous_calls'], 'cumulative_ceiling': plan['cumulative_ceiling']}))
        else:
            execute(args.directory.resolve(), args.authorized_call_limit)
