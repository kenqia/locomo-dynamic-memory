"""Prepare one failed extraction fragment for an explicitly authorized recovery."""
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3

import httpx

from locomo_memory.builds import BuildService
from locomo_memory.config import Settings
from locomo_memory.database import Database, backend_ownership
from locomo_memory.m5_budget import BudgetTransport
from locomo_memory.model import DeepSeekModel
from tools.m5.holdout_extraction import POLICY
from tools.m5.offline import ROOT, sha, write

BUILD = 'bef9f685957843698b3083ff4cbc79a4'
ORDINAL = 18
LIMIT_USD = '0.2619648'
SCOPE = 'retry one conv-44 extraction fragment; no index/relation/publish/QA'


def snapshot(path):
    """Hash logical committed rows, including WAL; never emit their contents."""
    digest = hashlib.sha256()
    with sqlite3.connect(path.resolve().as_uri()+'?mode=ro', uri=True) as db:
        db.execute('PRAGMA query_only=ON')
        db.execute('BEGIN')
        names = [r[0] for r in db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        for name in names:
            quoted = '"'+name.replace('"', '""')+'"'
            rows = sorted(json.dumps(r, ensure_ascii=False, default=str)
                          for r in db.execute('SELECT * FROM '+quoted))
            digest.update(json.dumps([name, rows], ensure_ascii=False).encode())
    return digest.hexdigest()


def check_stage(stage):
    original = json.loads((stage/'plan.json').read_text())
    if original['policy'] != POLICY or sha(stage/'settings.json') != original['settings_sha256']:
        raise ValueError('recovery_original_plan_changed')
    if any(sha(ROOT/name) != digest for name, digest in original['implementation_sha256'].items()):
        raise ValueError('recovery_producer_changed')
    settings = Settings.model_validate_json((stage/'settings.json').read_text())
    if (settings.db_path.resolve() != stage/'memory.sqlite3' or settings.model_retries != 2
            or settings.extraction_thinking_effort != 'disabled'):
        raise ValueError('recovery_settings_changed')
    with sqlite3.connect((stage/'memory.sqlite3').as_uri()+'?mode=ro', uri=True) as db:
        states = db.execute('SELECT build_id,sample_id,status,phase FROM build_versions ORDER BY sample_id').fetchall()
        failed = db.execute(
            "SELECT build_id,ordinal,status FROM build_fragments WHERE status!='succeeded'").fetchall()
        if (len(states) != 2 or states[0][1:] != ('conv-43', 'extracted', 'extraction')
                or states[1] != (BUILD, 'conv-44', 'failed', 'extraction')
                or failed != [(BUILD, ORDINAL, 'failed')]):
            raise ValueError('recovery_fragment_scope_changed')
        if db.execute('SELECT COUNT(*) FROM memories WHERE fragment_id=?', (f'{BUILD}:{ORDINAL}',)).fetchone()[0]:
            raise ValueError('recovery_fragment_has_memories')
    if not (stage/'extraction-outcomes.json').is_file():
        raise ValueError('recovery_original_execution_incomplete')
    return settings


def prepare(stage, output):
    check_stage(stage)
    output.mkdir(parents=True, exist_ok=False)
    output.chmod(0o700)
    plan = dict(status='prepared_not_authorized', scope=SCOPE, stage=str(stage),
        build_id=BUILD, fragment_ordinal=ORDINAL, max_additional_requests=3,
        max_additional_reserved_usd=LIMIT_USD, original_global_policy=POLICY,
        original_plan_sha256=sha(stage/'plan.json'), settings_sha256=sha(stage/'settings.json'),
        original_database_snapshot=snapshot(stage/'memory.sqlite3'),
        original_ledger_snapshot=snapshot(stage/'physical-requests.sqlite3'),
        script_sha256=sha(Path(__file__)))
    write(output/'plan.json', plan)
    print(json.dumps(dict(status=plan['status'], scope=SCOPE, provider_requests=0)))


def execute(output, delegate=None):
    """Caller must have explicit user approval; delegate injection is for offline tests."""
    if (output/'execution-started.json').exists():
        raise FileExistsError('recovery_already_started')
    plan = json.loads((output/'plan.json').read_text())
    expected = dict(approved=True, scope=SCOPE, build_id=BUILD, fragment_ordinal=ORDINAL,
        max_additional_requests=3, max_additional_reserved_usd=LIMIT_USD,
        plan_sha256=sha(output/'plan.json'))
    if json.loads((output/'authorization.json').read_text()) != expected:
        raise ValueError('recovery_authorization_mismatch')
    if (plan['status'] != 'prepared_not_authorized' or plan['scope'] != SCOPE
            or plan['build_id'] != BUILD or plan['fragment_ordinal'] != ORDINAL
            or plan['max_additional_requests'] != 3
            or plan['max_additional_reserved_usd'] != LIMIT_USD
            or plan['original_global_policy'] != POLICY
            or plan['script_sha256'] != sha(Path(__file__))):
        raise ValueError('recovery_plan_changed')
    stage = Path(plan['stage']).resolve()
    settings = check_stage(stage)
    if (sha(stage/'plan.json') != plan['original_plan_sha256']
            or sha(stage/'settings.json') != plan['settings_sha256']):
        raise ValueError('recovery_original_identity_changed')
    # Share the backend's exclusive owner lock. Never infer death from a file.
    with backend_ownership(settings.db_path):
        if (snapshot(settings.db_path) != plan['original_database_snapshot']
                or snapshot(stage/'physical-requests.sqlite3') != plan['original_ledger_snapshot']):
            raise ValueError('recovery_snapshot_changed')
        # Atomic exclusive marker prevents repeat execution, including after a crash.
        write(output/'execution-started.json', dict(scope=SCOPE, plan_sha256=sha(output/'plan.json')))
        owns_delegate = delegate is None
        delegate = httpx.HTTPTransport(retries=0) if owns_delegate else delegate
        try:
            global_guard = BudgetTransport(stage/'physical-requests.sqlite3', delegate, **POLICY)
            local_guard = BudgetTransport(output/'recovery-reservations.sqlite3', global_guard,
                **{**POLICY, 'max_requests': 3, 'max_usd': LIMIT_USD})
            builds = BuildService(Database(settings.db_path), settings, DeepSeekModel(
                settings, transport=local_guard))
            builds.retry(BUILD)
            builds.run(BUILD)
            result = builds.get(BUILD)
            outcome = {key: result[key] for key in ('build_id', 'status', 'phase', 'progress')}
            write(output/'outcome.json', dict(scope=SCOPE, outcome=outcome, complete_build=False,
                physical_request_authority='original global physical-requests.sqlite3; local reservations may include a global rejection'))
        finally:
            if owns_delegate:
                delegate.close()
    print(json.dumps(outcome))
    if outcome['status'] != 'extracted':
        raise RuntimeError('recovery_incomplete_no_automatic_retry')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--execute-authorized', action='store_true')
    args = parser.parse_args()
    if args.execute_authorized:
        execute(args.output.resolve())
    elif args.stage is not None:
        prepare(args.stage.resolve(), args.output.resolve())
    else:
        parser.error('--stage is required for preparation')
