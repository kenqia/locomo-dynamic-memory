"""Repeat the fixed paired QA on a snapshot; preserve the original build and ledger."""
import argparse
import ast
import fcntl
import hashlib
import importlib.util
import json
from pathlib import Path
import sqlite3
import sys

import httpx
from fastapi.testclient import TestClient
from pydantic import ValidationError

from locomo_memory.api import create_app
from locomo_memory.config import Settings
from locomo_memory.diagnostics import schema_path
from locomo_memory.export_schemas import MemoryExport
from locomo_memory.implementation_identity import implementation_sha256
from locomo_memory.model import DeepSeekModel, utc_now

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT.parent / 'real-baseline-issue15-thinking-conv26-v3'
PRIOR = ROOT.parent / 'real-baseline-issue15-relations-v6/campaign.sqlite3'
sys.path.insert(0, str(ROOT / 'experiments/issue-15-v6-gates'))
import v6_campaign
spec = importlib.util.spec_from_file_location('original_experiment', ROOT / 'experiments/issue-15-thinking-qa/run.py')
original = importlib.util.module_from_spec(spec)
spec.loader.exec_module(original)
save = original.save
IMMUTABLE = ['datasets', 'conversations', 'source_turns', 'build_versions', 'build_fragments',
             'memories', 'memory_sources', 'build_indexes', 'index_entries', 'relation_phases',
             'relation_tasks', 'memory_relations', 'current_state_projections', 'active_versions']


def artifact_digest(path):
    with sqlite3.connect(path.as_uri() + '?mode=ro', uri=True) as db:
        rows = {table: [[v.hex() if isinstance(v, bytes) else v for v in row]
                        for row in db.execute(f'SELECT * FROM {table} ORDER BY rowid')]
                for table in IMMUTABLE}
    return hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest()


class ValidationAudit(httpx.BaseTransport):
    """Validate responses in memory; retain only fixed code/schema diagnostics."""
    def __init__(self, directory):
        self.directory, self.schema, self.context, self.operation = directory, None, None, None
        self.allowed = set()
        for path in (ROOT / 'src/locomo_memory').glob('*.py'):
            for node in ast.walk(ast.parse(path.read_text())):
                if isinstance(node, ast.Raise) and isinstance(node.exc, ast.Call) and isinstance(node.exc.func, ast.Name) and node.exc.func.id == 'ValueError':
                    if node.exc.args and isinstance(node.exc.args[0], ast.Constant) and isinstance(node.exc.args[0].value, str):
                        self.allowed.add(node.exc.args[0].value)

    def handle_request(self, request):
        with httpx.HTTPTransport() as transport:
            response = transport.handle_request(request)
            response.read()
        if response.status_code == 200:
            try:
                content = response.json()['choices'][0]['message']['content']
                self.schema.model_validate_json(content, context=self.context)
            except ValidationError as error:
                errors = []
                for item in error.errors():
                    cause = str(item.get('ctx', {}).get('error', ''))
                    errors.append({'type': item['type'], 'field_path': schema_path(self.schema, item['loc']),
                                   'cause': cause if cause in self.allowed else 'other_validation_error'})
                path = self.directory / 'validation-causes.json'
                previous = json.loads(path.read_text()) if path.exists() else []
                save(path, [*previous, {'at': utc_now(), 'operation': self.operation, 'errors': errors}])
            except (ValueError, KeyError, IndexError, TypeError):
                pass
        return response


def prepare(directory):
    directory.mkdir(parents=True, exist_ok=False)
    old = json.loads((SOURCE / 'plan.json').read_text())
    old_outcome = json.loads((SOURCE / 'outcome.json').read_text())
    MemoryExport.model_validate_json((SOURCE / 'memory-export.json').read_bytes())
    with sqlite3.connect((SOURCE / 'memory.sqlite3').as_uri() + '?mode=ro', uri=True) as src:
        with sqlite3.connect(directory / 'memory.sqlite3') as dst:
            src.backup(dst)
    settings = Settings.model_validate({**old['settings'], 'db_path': str(directory / 'memory.sqlite3')})
    # The new authorization adds at most 200 calls, not a reset of the old 911.
    with sqlite3.connect(PRIOR.as_uri() + '?mode=ro', uri=True) as db:
        used = json.loads(db.execute('SELECT value FROM header').fetchone()[0])['previous_calls'] + db.execute('SELECT COUNT(*) FROM calls').fetchone()[0]
        assert not any(not json.loads(r[0]).get('completed_at') for r in db.execute('SELECT metadata FROM calls'))
    assert used == 911
    campaign = v6_campaign.Campaign(directory / 'campaign.sqlite3', PRIOR, create=True, limit=used + 200)
    source_digest = artifact_digest(SOURCE / 'memory.sqlite3')
    assert artifact_digest(directory / 'memory.sqlite3') == source_digest
    plan = {**old, 'created_at': utc_now(), 'settings': settings.snapshot(),
            'implementation_sha256': implementation_sha256(),
            'source_plan': str(SOURCE / 'plan.json'), 'source_directory': str(SOURCE),
            'source_build_id': old_outcome['build_id'], 'source_dataset_id': old_outcome['dataset_id'],
            'source_build_implementation_sha256': old['implementation_sha256'],
            'immutable_build_artifacts_sha256': source_digest,
            'budget_before': campaign.summary(), 'additional_call_limit': 200,
            'authorization': '2026-10-21 user approved up to 200 additional calls and complete four-strategy paired comparison; cumulative ceiling 1200, enforced tighter at 911+200=1111.',
            'build_reuse_note': 'Query-only experiment on an SQLite snapshot of the existing complete build; no extraction, relation or index rebuild. Only query implementation changes.',
            'reference_run_id': old_outcome['run_id']}
    assert hashlib.sha256((ROOT / 'data/raw/locomo/locomo10.json').read_bytes()).hexdigest() == plan['official_artifact_sha256']
    save(directory / 'plan.json', plan)
    return plan


def execute(directory, plan):
    assert implementation_sha256() == plan['implementation_sha256']
    assert not (directory / 'outcome.json').exists(), 'explicit_recovery_required'
    assert artifact_digest(directory / 'memory.sqlite3') == plan['immutable_build_artifacts_sha256']
    campaign = v6_campaign.Campaign(directory / 'campaign.sqlite3', PRIOR, limit=plan['budget_before']['limit'])
    assert campaign.summary()['reserved_total_calls'] == plan['budget_before']['reserved_total_calls']
    v6_campaign.FIELDS += ('thinking', 'reasoning_effort', 'max_tokens')
    settings = Settings.model_validate(plan['settings'])
    audit = ValidationAudit(directory)
    model = DeepSeekModel(settings, transport=audit)
    generate = model.generate
    def observed(operation, payload, schema, *, context=None, on_call=None):
        audit.operation, audit.schema, audit.context = operation, schema, context
        return generate(operation, payload, schema, context=context, on_call=on_call)
    model.generate = observed
    campaign.bind(model, 'answer-output-repeat-qa')
    outcome = {'started_at': utc_now(), 'status': 'running', 'directory': str(directory),
               'build_id': plan['source_build_id'], 'dataset_id': plan['source_dataset_id']}
    save(directory / 'outcome.json', outcome)
    try:
        app = create_app(settings, model=model)
        with TestClient(app) as client:
            assert app.state.builds.get(outcome['build_id'])['status'] == 'complete'
            original.run_evaluation(client, app, directory, plan, outcome)
    except Exception as error:
        outcome.update(status='experiment_stopped', error_type=type(error).__name__)
    finally:
        unchanged = artifact_digest(directory / 'memory.sqlite3') == plan['immutable_build_artifacts_sha256']
        original_unchanged = artifact_digest(SOURCE / 'memory.sqlite3') == plan['immutable_build_artifacts_sha256']
        outcome.update(completed_at=utc_now(), budget_after=campaign.summary(),
                       snapshot_build_unchanged=unchanged, original_build_unchanged=original_unchanged)
        save(directory / 'outcome.json', outcome)
        print(json.dumps({k: outcome[k] for k in ['status', 'build_id', 'run_id'] if k in outcome}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['prepare', 'execute'])
    parser.add_argument('--directory', required=True, type=Path)
    args = parser.parse_args()
    directory = args.directory.resolve()
    with PRIOR.with_suffix('.quality.lock').open('a+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if args.action == 'prepare':
            plan = prepare(directory)
            print(json.dumps({'status': 'prepared', 'items': plan['logical_items'], 'budget': plan['budget_before']['limit']}))
        else:
            execute(directory, json.loads((directory / 'plan.json').read_text()))
