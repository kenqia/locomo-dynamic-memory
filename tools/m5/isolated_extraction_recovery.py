"""Prepare a new, independently authorized retry on a copy of one failed fragment.

The original stage and its old ledgers stay read-only. This deliberately uses the
unchanged producer contract: it offers another finite attempt, not a proven fix
for stochastic model output. It never indexes, relates, publishes or reads QA.
"""
import argparse
from collections import Counter
from contextlib import contextmanager
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import sqlite3

import httpx

from locomo_memory.builds import BuildService
from locomo_memory.config import Settings
from locomo_memory.database import Database, backend_ownership
from locomo_memory.m5_budget import BudgetTransport
from locomo_memory.memory_schemas import Memory
from locomo_memory.model import DeepSeekModel
from tools.m5 import extraction_recovery as legacy
from tools.m5.holdout_relations import NoProvider, producer_hashes
from tools.m5.offline import sha, write

VERSION = 'm5-conv44-isolated-recovery-v2'
SCOPE = 'independent copy; retry conv-44 failed extraction fragment only; no index/relation/publish/QA'
POLICY = {**legacy.POLICY, 'max_requests': 3, 'max_usd': '0.2619648'}


@contextmanager
def readonly(path):
    db = sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA query_only=ON')
    db.execute('BEGIN')
    try:
        yield db
    finally:
        db.close()


def require_conversation_only(path):
    """Check absence of evaluation content in SQL before hashing any rows."""
    with readonly(path) as db:
        tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        allowed = {'datasets', 'import_artifacts', 'conversations', 'source_turns',
                   'build_versions', 'build_fragments', 'memories', 'memory_sources'}
        if tables != allowed:
            raise ValueError('isolated_conversation_only_tables_required')
        if db.execute("SELECT COUNT(*) FROM import_artifacts a,json_each(a.annotations_json) s,"
                      "json_each(s.value) f WHERE f.key!='sample_id' AND f.type!='null'").fetchone()[0]:
            raise ValueError('isolated_nonempty_annotations_forbidden')


def protected_snapshot(path, initial_calls):
    """Hash all original rows, allowing only the explicit fragment's changes."""
    digest = hashlib.sha256()
    with readonly(path) as db:
        schema = db.execute('SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY type,name').fetchall()
        digest.update(json.dumps([tuple(r) for r in schema]).encode())
        for name, in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
            quoted = '"' + name.replace('"', '""') + '"'
            rows = []
            for raw in db.execute('SELECT * FROM ' + quoted):
                row = dict(raw)
                if name == 'build_versions' and row['build_id'] == legacy.BUILD:
                    row.pop('status')
                    row.pop('updated_at')
                    metadata = json.loads(row['model_metadata_json'])
                    if len(metadata['calls']) < initial_calls:
                        raise ValueError('isolated_historical_calls_removed')
                    metadata['calls'] = metadata['calls'][:initial_calls]
                    metadata['returned_models'] = list(dict.fromkeys(
                        c['returned_model'] for c in metadata['calls'] if c.get('returned_model')))
                    row['model_metadata_json'] = json.dumps(metadata, sort_keys=True)
                if name == 'build_fragments' and row['fragment_id'] == f'{legacy.BUILD}:{legacy.ORDINAL}':
                    for key in ('status', 'attempts', 'error_code', 'error_message',
                                'model_metadata_json', 'no_facts_reason'):
                        row.pop(key)
                if name == 'memories' and row['fragment_id'] == f'{legacy.BUILD}:{legacy.ORDINAL}':
                    continue
                if name == 'memory_sources' and db.execute(
                        'SELECT 1 FROM memories WHERE memory_id=? AND fragment_id=?',
                        (row['memory_id'], f'{legacy.BUILD}:{legacy.ORDINAL}')).fetchone():
                    continue
                rows.append(json.dumps(row, sort_keys=True, ensure_ascii=False, default=str))
            digest.update(json.dumps([name, sorted(rows)], ensure_ascii=False).encode())
    return digest.hexdigest()


def source_identity(source):
    return dict(database=legacy.snapshot(source/'memory.sqlite3'),
                ledger=legacy.snapshot(source/'physical-requests.sqlite3'),
                plan=sha(source/'plan.json'), settings=sha(source/'settings.json'))


def prepare(source, output):
    source, output = source.resolve(), output.resolve()
    require_conversation_only(source/'memory.sqlite3')
    settings = legacy.check_stage(source)
    if settings.model_max_tokens != POLICY['max_output_tokens']:
        raise ValueError('isolated_output_policy_changed')
    before = source_identity(source)
    output.mkdir(parents=True, exist_ok=False)
    output.chmod(0o700)
    target = output/'memory.sqlite3'
    with readonly(source/'memory.sqlite3') as src, sqlite3.connect(target) as dst:
        src.backup(dst)
    target.chmod(0o600)
    # Keep every frozen config field, including db_path; route storage explicitly.
    write(output/'settings.json', settings.snapshot())
    builds = BuildService(Database(target), settings, NoProvider())
    build = builds.get(legacy.BUILD)
    builds.require_current_contract(build)
    with readonly(target) as db:
        metadata = json.loads(db.execute('SELECT model_metadata_json FROM build_versions WHERE build_id=?',
                                        (legacy.BUILD,)).fetchone()[0])
        initial_calls = len(metadata['calls'])
        fragment = db.execute('SELECT source_ids_json FROM build_fragments WHERE build_id=? AND ordinal=?',
                              (legacy.BUILD, legacy.ORDINAL)).fetchone()
    BudgetTransport(output/'physical-requests.sqlite3', None, **POLICY)
    if source_identity(source) != before:
        raise ValueError('isolated_source_changed_during_prepare')
    plan = dict(version=VERSION, status='prepared_not_authorized', scope=SCOPE,
        source_stage=str(source), source_identity=before, build_id=legacy.BUILD,
        fragment_ordinal=legacy.ORDINAL, fragment_turns=len(json.loads(fragment[0])),
        policy=POLICY, initial_build_calls=initial_calls,
        prepared_database_snapshot=legacy.snapshot(target),
        protected_snapshot=protected_snapshot(target, initial_calls),
        ledger_snapshot=legacy.snapshot(output/'physical-requests.sqlite3'),
        settings_sha256=sha(output/'settings.json'), implementation_sha256=producer_hashes(),
        script_sha256=sha(Path(__file__)), provider_requests=0, holdout_qa_read=False,
        automatic_recovery=False, old_budget_transferred=False,
        limitation='same producer and full fragment; another bounded attempt, not a demonstrated model repair')
    write(output/'plan.json', plan)
    write(output/'authorization-template.json', {**authorization(output), 'approved': False})
    return plan


def authorization(output):
    return dict(approved=True, version=VERSION, scope=SCOPE, build_id=legacy.BUILD,
                fragment_ordinal=legacy.ORDINAL, policy=POLICY,
                plan_sha256=sha(output/'plan.json'))


def execute(output, delegate=None):
    output = output.resolve()
    if (output/'execution-started.json').exists():
        raise FileExistsError('isolated_recovery_already_started')
    if json.loads((output/'authorization.json').read_text()) != authorization(output):
        raise ValueError('isolated_authorization_mismatch')
    plan = json.loads((output/'plan.json').read_text())
    if (plan['version'] != VERSION or plan['status'] != 'prepared_not_authorized'
            or plan['scope'] != SCOPE or plan['build_id'] != legacy.BUILD
            or plan['fragment_ordinal'] != legacy.ORDINAL or plan['policy'] != POLICY
            or plan['implementation_sha256'] != producer_hashes()
            or plan['script_sha256'] != sha(Path(__file__))
            or plan['settings_sha256'] != sha(output/'settings.json')):
        raise ValueError('isolated_plan_changed')
    source = Path(plan['source_stage'])
    require_conversation_only(source/'memory.sqlite3')
    require_conversation_only(output/'memory.sqlite3')
    legacy.check_stage(source)
    if source_identity(source) != plan['source_identity']:
        raise ValueError('isolated_original_source_changed')
    settings = Settings.model_validate_json((output/'settings.json').read_text())
    if (settings.extraction_thinking_effort != 'disabled' or settings.model_retries != 2
            or settings.model_name != POLICY['model'] or settings.model_max_tokens != POLICY['max_output_tokens']):
        raise ValueError('isolated_settings_changed')
    target = output/'memory.sqlite3'
    with backend_ownership(target):
        if (legacy.snapshot(target) != plan['prepared_database_snapshot']
                or legacy.snapshot(output/'physical-requests.sqlite3') != plan['ledger_snapshot']):
            raise ValueError('isolated_prepared_snapshot_changed')
        builds = BuildService(Database(target), settings, NoProvider())
        builds.require_current_contract(builds.get(legacy.BUILD))
        write(output/'execution-started.json', dict(scope=SCOPE, plan_sha256=sha(output/'plan.json')))
        owns_delegate = delegate is None
        delegate = httpx.HTTPTransport(retries=0) if owns_delegate else delegate
        try:
            guard = BudgetTransport(output/'physical-requests.sqlite3', delegate, **POLICY)
            builds.model = DeepSeekModel(settings, transport=guard)
            builds.retry(legacy.BUILD)
            builds.run(legacy.BUILD)
        finally:
            if owns_delegate:
                delegate.close()
        if protected_snapshot(target, plan['initial_build_calls']) != plan['protected_snapshot']:
            raise ValueError('isolated_protected_rows_changed')
        if source_identity(source) != plan['source_identity']:
            raise ValueError('isolated_original_source_changed')
        with readonly(target) as db:
            fragment = db.execute('SELECT source_ids_json,model_metadata_json FROM build_fragments '
                                  'WHERE build_id=? AND ordinal=?', (legacy.BUILD, legacy.ORDINAL)).fetchone()
            source_ids = json.loads(fragment[0])
            sources = {sid: dict(db.execute('SELECT * FROM source_turns WHERE source_id=?', (sid,)).fetchone())
                       for sid in source_ids}
            added = db.execute('SELECT memory_json FROM memories WHERE fragment_id=?',
                               (f'{legacy.BUILD}:{legacy.ORDINAL}',)).fetchall()
            for row in added:
                Memory.model_validate_json(row[0], context={'sources': sources})
            if db.execute('PRAGMA foreign_key_check').fetchone():
                raise ValueError('isolated_foreign_keys_changed')
            calls = json.loads(fragment[1]).get('calls', [])
        with readonly(output/'physical-requests.sqlite3') as db:
            requests = db.execute('SELECT reserved_usd,status,usage_json FROM physical_requests ORDER BY rowid').fetchall()
        if len(calls) != len(requests) or any(
                c.get('thinking') != {'type': 'disabled'} or c.get('reasoning_effort') is not None for c in calls):
            raise ValueError('isolated_attempt_ledger_mismatch')
        reserved = sum((Decimal(r[0]) for r in requests), Decimal(0))
        tokens, unknown, unknown_reserved = Counter(), 0, Decimal(0)
        for row in requests:
            usage = json.loads(row[2])
            if not isinstance(usage, dict) or not all(type(usage.get(k)) is int for k in
                                                     ('prompt_tokens', 'completion_tokens')):
                unknown += 1
                unknown_reserved += Decimal(row[0])
            if isinstance(usage, dict):
                tokens.update(usage)
        if len(requests) > POLICY['max_requests'] or reserved > Decimal(POLICY['max_usd']):
            raise ValueError('isolated_ledger_limit_exceeded')
        result = builds.get(legacy.BUILD)
        outcome = dict(scope=SCOPE, status=result['status'], phase=result['phase'],
            progress=result['progress'], new_memories=len(added), physical_requests=len(requests),
            protected_rows_unchanged=True, original_stage_and_ledger_unchanged=True,
            original_build_fingerprint_preserved=True, thinking='disabled',
            holdout_qa_read=False, complete_build=False, automatic_recovery=False,
            ledger=dict(reserved_usd=str(reserved), request_statuses=dict(Counter(r[1] for r in requests)),
                reported_tokens=dict(tokens), unknown_usage_requests=unknown,
                unknown_usage_reserved_usd=str(unknown_reserved),
                reported_fields_peak_upper_usd=str((Decimal(tokens['prompt_tokens'])*Decimal('.30') +
                                                   Decimal(tokens['completion_tokens'])*Decimal('1.20'))/1000000),
                actual_invoice='not_accessed', remaining_capacity_authorizes_extra_attempts=False))
        write(output/'outcome.json', outcome)
    if result['status'] != 'extracted':
        raise RuntimeError('isolated_recovery_incomplete_no_automatic_retry')
    return outcome


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--execute-authorized', action='store_true')
    args = parser.parse_args()
    if args.execute_authorized:
        result = execute(args.output)
    elif args.source is not None:
        plan = prepare(args.source, args.output)
        result = {k: plan[k] for k in ('status', 'scope', 'policy', 'provider_requests')}
    else:
        parser.error('--source required for preparation')
    print(json.dumps(result, ensure_ascii=False))
