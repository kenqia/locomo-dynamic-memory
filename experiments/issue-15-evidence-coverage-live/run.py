"""Frozen targeted and question-held-out QA under the remaining approved budget."""
import argparse
import fcntl
import hashlib
import importlib.util
import json
from pathlib import Path
import sqlite3
import sys
import time

from fastapi.testclient import TestClient
from locomo_memory.api import create_app
from locomo_memory.config import Settings
from locomo_memory.implementation_identity import implementation_sha256
from locomo_memory.model import DeepSeekModel, utc_now

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT.parent / 'real-baseline-issue15-answer-output-conv26'
PRIOR = SOURCE / 'campaign.sqlite3'
ORIGINAL_LOCK = ROOT.parent / 'real-baseline-issue15-relations-v6/campaign.quality.lock'
spec = importlib.util.spec_from_file_location('previous_repeat', ROOT / 'experiments/issue-15-answer-output-live/run.py')
previous = importlib.util.module_from_spec(spec)
spec.loader.exec_module(previous)
sys.path.insert(0, str(ROOT / 'experiments/issue-15-v6-gates'))
import v6_campaign
save = previous.save
SELECTION = {
    'A': [(3, 'targeted_research'), (15, 'targeted_enumeration'), (153, 'targeted_refusal'),
          (0, 'time_nonregression'), (53, 'time_nonregression')],
    'B': [(18, 'cross_session'), (55, 'cross_session'), (36, 'time'), (74, 'time'),
          (65, 'dynamic_changes'), (136, 'dynamic_changes'), (32, 'enumeration'),
          (60, 'enumeration'), (178, 'refusal'), (191, 'refusal')]}
STRATEGIES = {'A': ['dynamic', 'dynamic_raw_fallback'],
              'B': ['dynamic_raw_fallback', 'hybrid_no_resolution']}


def prepare(directory, audit_path):
    directory.mkdir(parents=True, exist_ok=False)
    source_plan = json.loads((SOURCE / 'plan.json').read_text())
    source_outcome = json.loads((SOURCE / 'outcome.json').read_text())
    audit = json.loads(audit_path.read_text())
    assert not set(audit['used_qa_indices']) & {i for i, _ in SELECTION['B']}
    assert audit['selected_b_indices'] == [i for i, _ in SELECTION['B']]
    raw = (ROOT / 'data/raw/locomo/locomo10.json').read_bytes()
    assert hashlib.sha256(raw).hexdigest() == source_plan['official_artifact_sha256']
    qa = next(c for c in json.loads(raw) if c['sample_id'] == 'conv-26')['qa']
    with sqlite3.connect((SOURCE / 'memory.sqlite3').as_uri() + '?mode=ro', uri=True) as src:
        with sqlite3.connect(directory / 'memory.sqlite3') as dst:
            src.backup(dst)
    with sqlite3.connect(PRIOR.as_uri() + '?mode=ro', uri=True) as db:
        old_header = json.loads(db.execute('SELECT value FROM header').fetchone()[0])
        calls = [json.loads(r[0]) for r in db.execute('SELECT metadata FROM calls')]
    assert all(c.get('completed_at') for c in calls)
    used, ceiling = old_header['previous_calls'] + len(calls), old_header['limit']
    assert used == 1009 and ceiling == 1111
    campaign = v6_campaign.Campaign(directory / 'campaign.sqlite3', PRIOR, create=True, limit=ceiling)
    immutable = previous.artifact_digest(SOURCE / 'memory.sqlite3')
    assert previous.artifact_digest(directory / 'memory.sqlite3') == immutable
    settings = Settings.model_validate({**source_plan['settings'], 'db_path': str(directory / 'memory.sqlite3')})
    plan = {'created_at': utc_now(), 'sample_id': 'conv-26', 'source_directory': str(SOURCE),
            'source_build_id': source_outcome['build_id'], 'source_dataset_id': source_outcome['dataset_id'],
            'reference_run_id': source_outcome['run_id'], 'settings': settings.snapshot(),
            'implementation_sha256': implementation_sha256(), 'immutable_build_artifacts_sha256': immutable,
            'official_artifact_sha256': source_plan['official_artifact_sha256'],
            'budget_before': campaign.summary(), 'remaining_authorized_calls': ceiling - used,
            'evidence_profile': 'expanded', 'experiments': {
                label: {'strategies': STRATEGIES[label], 'questions': [
                    {'question_id': f'conv-26:qa:{i}', 'qa_index': i, 'purpose': purpose, 'official_qa': qa[i]}
                    for i, purpose in selection], 'logical_items': len(selection) * len(STRATEGIES[label])}
                for label, selection in SELECTION.items()},
            'selection_scope': audit['scope_limitation'],
            'budget_authority': 'Current user requested experiments A/B; reuse only the remaining 102 calls from the already approved 200-call extension. No increase in cumulative ceiling; all historical calls remain counted.',
            'selection_note': 'B chosen using questions, categories and evidence-session structure, without examining answers or model results. Two per purpose; no post-result reselection.'}
    save(directory / 'question-usage-audit.json', audit)
    save(directory / 'plan.json', plan)
    return plan


def run_group(client, app, directory, plan, label, outcome):
    group = plan['experiments'][label]
    samples = [{'sample_id': 'conv-26', **{k: q['official_qa'][k] for k in ['question', 'answer', 'category', 'evidence'] if k in q['official_qa']}}
               for q in group['questions']]
    created = client.post('/evaluation-inputs', json={'dataset_id': plan['source_dataset_id'],
        'kind': 'course', 'course_split': previous.original.COURSE_SPLIT, 'samples': samples})
    created.raise_for_status()
    save(directory / f'{label}-input.json', created.json())
    response = client.post('/evaluation-runs', json={'input_id': created.json()['input_id'],
        'strategies': group['strategies'], 'partition': 'dev', 'evidence_profile': plan['evidence_profile'],
        'build_ids': {'conv-26': plan['source_build_id']}, 'wait': False})
    response.raise_for_status()
    run_id = response.json()['run_id']
    outcome['runs'][label] = {'run_id': run_id, 'status': 'running'}
    save(directory / 'outcome.json', outcome)
    while app.state.evaluation.execution.progress(run_id)['status'] == 'running':
        time.sleep(1)
    result = app.state.evaluation.get('evaluation_runs', run_id)
    save(directory / f'{label}-run.json', result)
    outcome['runs'][label].update(status=result['status'], progress=result['progress'])
    save(directory / 'outcome.json', outcome)


def execute(directory, plan):
    assert implementation_sha256() == plan['implementation_sha256']
    assert not (directory / 'outcome.json').exists(), 'explicit_recovery_required'
    campaign = v6_campaign.Campaign(directory / 'campaign.sqlite3', PRIOR, limit=plan['budget_before']['limit'])
    assert campaign.summary()['reserved_total_calls'] == plan['budget_before']['reserved_total_calls']
    assert previous.artifact_digest(directory / 'memory.sqlite3') == plan['immutable_build_artifacts_sha256']
    v6_campaign.FIELDS += ('thinking', 'reasoning_effort', 'max_tokens')
    audit = previous.ValidationAudit(directory)
    model = DeepSeekModel(Settings.model_validate(plan['settings']), transport=audit)
    generate = model.generate
    def observed(operation, payload, schema, *, context=None, on_call=None):
        audit.operation, audit.schema, audit.context = operation, schema, context
        return generate(operation, payload, schema, context=context, on_call=on_call)
    model.generate = observed
    campaign.bind(model, 'evidence-coverage-A-B')
    outcome = {'started_at': utc_now(), 'status': 'running', 'runs': {}, 'directory': str(directory)}
    save(directory / 'outcome.json', outcome)
    try:
        app = create_app(Settings.model_validate(plan['settings']), model=model)
        with TestClient(app) as client:
            assert app.state.builds.get(plan['source_build_id'])['status'] == 'complete'
            for label in ['A', 'B']:
                run_group(client, app, directory, plan, label, outcome)
        outcome['status'] = 'completed' if all(r['status'] == 'completed' for r in outcome['runs'].values()) else 'completed_with_errors'
    except Exception as error:
        outcome.update(status='experiment_stopped', error_type=type(error).__name__)
    finally:
        outcome.update(completed_at=utc_now(), budget_after=campaign.summary(),
            original_build_unchanged=previous.artifact_digest(SOURCE / 'memory.sqlite3') == plan['immutable_build_artifacts_sha256'],
            snapshot_build_unchanged=previous.artifact_digest(directory / 'memory.sqlite3') == plan['immutable_build_artifacts_sha256'])
        save(directory / 'outcome.json', outcome)
        print(json.dumps({'status': outcome['status'], 'runs': outcome['runs']}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['prepare', 'execute'])
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--question-audit', type=Path)
    args = parser.parse_args()
    with ORIGINAL_LOCK.open('a+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        directory = args.directory.resolve()
        if args.action == 'prepare':
            plan = prepare(directory, args.question_audit)
            print(json.dumps({'status': 'prepared', 'items': 30, 'remaining_calls': plan['remaining_authorized_calls']}))
        else:
            execute(directory, json.loads((directory / 'plan.json').read_text()))
