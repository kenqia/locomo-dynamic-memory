"""Finite, isolated relation replays. Never start an app or write the source database."""
from collections import Counter
from contextlib import closing, contextmanager
import argparse
import fcntl
import hashlib
import json
from pathlib import Path
import sqlite3

import httpx

from .config import Settings
from .experiment import write_json
from .implementation_identity import implementation_sha256
from .imports import canonical_json
from .model import DeepSeekModel, ModelFailure, utc_now
from .usage import provider_usage
from . import model as model_contract, relation_schemas as relation_contract


class ReplayError(Exception):
    """Only fixed codes are exposed by the command-line entry point."""


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


@contextmanager
def source_snapshot(path: Path):
    wal = path.with_name(path.name + '-wal')
    with path.with_name(path.name + '.runtime.lock').open('rb') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_SH | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ReplayError('source_backend_running') from None
        if wal.exists() and wal.stat().st_size:
            raise ReplayError('source_has_nonempty_wal')
        before = digest(path.read_bytes())
        with closing(sqlite3.connect(path.as_uri() + '?mode=ro&immutable=1', uri=True)) as db:
            db.row_factory = sqlite3.Row
            db.execute('PRAGMA query_only=ON')
            yield db, before
        if digest(path.read_bytes()) != before or (wal.exists() and wal.stat().st_size):
            raise ReplayError('source_changed')


def comparison(db, build_id: str, ordinal: int):
    task = db.execute('SELECT * FROM relation_tasks WHERE build_id=? AND ordinal=?', (build_id, ordinal)).fetchone()
    if task is None:
        raise ReplayError('task_not_found')
    def memory(memory_id):
        row = db.execute('SELECT memory_json FROM memories WHERE build_id=? AND memory_id=?', (build_id, memory_id)).fetchone()
        if row is None:
            raise ReplayError('memory_not_found')
        return json.loads(row[0])
    new = memory(task['new_memory_id'])
    history = [memory(item) for item in json.loads(task['history_ids_json'])]
    source_ids = sorted({source_id for item in [new, *history] for source_id in item['source_ids']})
    sources = {source_id: dict(db.execute('SELECT * FROM source_turns WHERE source_id=?', (source_id,)).fetchone()) for source_id in source_ids}
    context = {'new_memory': new, 'history': history, 'sources': sources}
    payload = {**context, 'sources': list(sources.values())}
    identity = {'task_id': task['task_id'], 'ordinal': ordinal, 'original_status': task['status'],
                'new_memory_id': new['memory_id'], 'history_ids': [item['memory_id'] for item in history],
                'history_count': len(history), 'source_ids': source_ids,
                'payload_sha256': digest(canonical_json(payload).encode())}
    return identity, payload, context


def request_identity(settings, payload, context):
    captured = []
    def capture(request):
        captured.append(digest(request.content))
        return httpx.Response(200, json={})
    model = DeepSeekModel(settings, api_key='synthetic-offline', transport=httpx.MockTransport(capture))
    try:
        model.generate('relate', payload, relation_contract.RelationBatch, context=context)
    except ModelFailure as error:
        return {'request_sha256': captured[0], 'request_context_estimate': error.metadata['request_context_estimate']}
    raise ReplayError('offline_capture_failed')


def isolated_directory(directory: Path, source: Path):
    directory = directory.resolve()
    if directory.is_relative_to(source.parent) or source.is_relative_to(directory):
        raise ReplayError('output_must_be_separate_from_source')
    return directory


def prepare_plan(source: Path, build_id: str, ordinals: list[int], directory: Path) -> dict:
    source = source.resolve()
    directory = isolated_directory(directory, source)
    if not 1 <= len(ordinals) <= 3 or len(set(ordinals)) != len(ordinals):
        raise ReplayError('select_one_to_three_unique_tasks')
    if directory.exists():
        raise ReplayError('output_directory_already_exists')
    with source_snapshot(source) as (db, source_hash):
        build = db.execute('SELECT * FROM build_versions WHERE build_id=?', (build_id,)).fetchone()
        if build is None:
            raise ReplayError('build_not_found')
        saved_config = json.loads(build['config_json'])
        # Old builds predate per-stage thinking and always sent disabled.
        original = Settings.model_validate({**saved_config,
            'relation_thinking_effort': saved_config.get('relation_thinking_effort', 'disabled')})
        fields = ('model_name', 'model_base_url', 'model_timeout_seconds', 'model_temperature',
                  'model_max_tokens', 'relation_max_tokens', 'thinking_enabled', 'relation_thinking_effort')
        settings = Settings(**{key: getattr(original, key) for key in fields}, model_retries=0)
        tasks = []
        for ordinal in ordinals:
            identity, payload, context = comparison(db, build_id, ordinal)
            tasks.append({**identity, **request_identity(settings, payload, context)})
        plan = {'format_version': 1, 'created_at': utc_now(), 'status': 'awaiting_budget_approval',
                'source_database': str(source), 'source_database_sha256': source_hash,
                'source_build_id': build_id, 'source_build_fingerprint': build['fingerprint'],
                'implementation_sha256': implementation_sha256(),
                'prompt_version': model_contract.RELATION_PROMPT_VERSION,
                'schema_version': relation_contract.RELATION_SCHEMA_VERSION,
                'settings': {key: getattr(settings, key) for key in (*fields, 'model_retries')},
                'original_model_retries': original.model_retries,
                'proposed_call_limit': 2 * len(tasks), 'tasks': tasks}
    directory.mkdir(parents=True, exist_ok=False)
    write_json(directory / 'plan.json', plan)
    return plan


def read_report(directory: Path) -> dict:
    directory = directory.resolve()
    path = directory / 'calls.sqlite3'
    if not path.exists():
        return {'status': 'not_started', 'reserved_calls': 0, 'attempts': []}
    with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)) as db:
        db.row_factory = sqlite3.Row
        header = json.loads(db.execute('SELECT value FROM replay_header').fetchone()[0])
        attempts = []
        for row in db.execute('SELECT * FROM replay_calls ORDER BY sequence'):
            item = dict(row)
            item['diagnostics'] = json.loads(item.pop('metadata_json'))
            result = item.pop('result_json')
            item['result'] = json.loads(result) if result is not None else None
            attempts.append(item)
    status = 'outcome_unknown' if any(item['result'] is None for item in attempts) else 'budget_exhausted' if len(attempts) == header['approved_call_limit'] else 'observations_saved'
    return {**header, 'status': status, 'reserved_calls': len(attempts),
            'usage': provider_usage([item['diagnostics'] for item in attempts]),
            'remaining_calls': header['approved_call_limit'] - len(attempts), 'attempts': attempts}


def run_phase(directory: Path, phase: str, approved_call_limit: int, *, allow_paid: bool,
              api_key: str | None = None, transport: httpx.BaseTransport | None = None) -> dict:
    if not allow_paid:
        raise ReplayError('paid_approval_required')
    if phase not in {'before', 'after'}:
        raise ReplayError('invalid_phase')
    directory = directory.resolve()
    plan = json.loads((directory / 'plan.json').read_text())
    source = Path(plan['source_database']).resolve()
    isolated_directory(directory, source)
    if any((directory / name).is_symlink() for name in ('calls.sqlite3', 'calls.sqlite3-wal', 'calls.sqlite3-shm', 'run.lock')):
        raise ReplayError('replay_files_must_not_be_symlinks')
    if not 1 <= approved_call_limit <= min(6, plan['proposed_call_limit']):
        raise ReplayError('invalid_approved_call_limit')
    plan_hash = digest(canonical_json(plan).encode())
    identity = implementation_sha256()
    if phase == 'before' and identity != plan['implementation_sha256']:
        raise ReplayError('before_implementation_changed')
    settings = Settings(**plan['settings'])
    if settings.model_retries != 0:
        raise ReplayError('diagnostic_retries_must_be_zero')
    # Hold the source lock only while reconstructing and checking the frozen inputs.
    inputs = []
    with source_snapshot(source) as (db, source_hash):
        if source_hash != plan['source_database_sha256']:
            raise ReplayError('source_snapshot_mismatch')
        for task in plan['tasks']:
            current, payload, context = comparison(db, plan['source_build_id'], task['ordinal'])
            if current['payload_sha256'] != task['payload_sha256'] or current['history_ids'] != task['history_ids']:
                raise ReplayError('frozen_input_mismatch')
            request = request_identity(settings, payload, context)
            if phase == 'before' and request['request_sha256'] != task['request_sha256']:
                raise ReplayError('before_request_changed')
            inputs.append((task, payload, context, request))
    with (directory / 'run.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with closing(sqlite3.connect(directory / 'calls.sqlite3')) as db:
            db.execute('PRAGMA journal_mode=WAL')
            db.executescript('''
                CREATE TABLE IF NOT EXISTS replay_header (value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS replay_calls (
                    sequence INTEGER PRIMARY KEY, phase TEXT NOT NULL, source_task_id TEXT NOT NULL,
                    implementation_sha256 TEXT NOT NULL, prompt_version TEXT NOT NULL,
                    schema_version TEXT NOT NULL, request_sha256 TEXT NOT NULL,
                    metadata_json TEXT NOT NULL, result_json TEXT,
                    UNIQUE(phase,source_task_id)
                );
            ''')
            row = db.execute('SELECT value FROM replay_header').fetchone()
            mode = 'mock' if transport is not None else 'live'
            if row:
                header = json.loads(row[0])
                if (header['plan_sha256'], header['approved_call_limit'], header['mode']) != (plan_hash, approved_call_limit, mode):
                    raise ReplayError('frozen_approval_mismatch')
            else:
                import uuid
                header = {'replay_id': uuid.uuid4().hex, 'plan_sha256': plan_hash,
                          'approved_call_limit': approved_call_limit, 'mode': mode, 'status': 'observing'}
                db.execute('INSERT INTO replay_header VALUES (?)', (canonical_json(header),))
                db.commit()
            rows = db.execute('SELECT phase,metadata_json,result_json FROM replay_calls').fetchall()
            if any(result is None for _, _, result in rows):
                raise ReplayError('uncommitted_attempt_requires_review')
            if any(json.loads(result)['status'] not in {'succeeded', 'invalid_output'} for _, _, result in rows):
                raise ReplayError('provider_failure_requires_review')
            if phase == 'after':
                baseline = [json.loads(result) for saved_phase, _, result in rows if saved_phase == 'before']
                if len(baseline) != len(plan['tasks']):
                    raise ReplayError('before_phase_incomplete')
                if not any(result['status'] == 'invalid_output' for result in baseline):
                    raise ReplayError('failure_not_reproduced')
                if identity == plan['implementation_sha256']:
                    raise ReplayError('after_requires_evidence_based_change')
            for task, payload, context, request in inputs:
                if db.execute('SELECT 1 FROM replay_calls WHERE phase=? AND source_task_id=?', (phase, task['task_id'])).fetchone():
                    continue
                used = db.execute('SELECT COUNT(*) FROM replay_calls').fetchone()[0]
                if used >= approved_call_limit:
                    break
                def observe(call):
                    if call['attempt'] != 1:
                        raise ReplayError('unexpected_provider_retry')
                    call.update(task_id=f"{header['replay_id']}:{phase}:relation:{task['ordinal']}",
                                source_task_id=task['task_id'], logical_attempt=1, provider_attempt=1)
                    if call['status'] == 'started':
                        # A reservation survives crashes and is never silently reused.
                        db.execute('INSERT INTO replay_calls VALUES (?,?,?,?,?,?,?,?,NULL)',
                                   (used + 1, phase, task['task_id'], identity, model_contract.RELATION_PROMPT_VERSION,
                                    relation_contract.RELATION_SCHEMA_VERSION, request['request_sha256'], canonical_json(call)))
                    else:
                        db.execute('UPDATE replay_calls SET metadata_json=? WHERE phase=? AND source_task_id=?',
                                   (canonical_json(call), phase, task['task_id']))
                    db.commit()
                model = DeepSeekModel(settings, api_key=api_key, transport=transport)
                try:
                    generated = model.generate('relate', payload, relation_contract.RelationBatch, context=context, on_call=observe)
                    judgments = generated.value.judgments
                    result = {'status': 'succeeded', 'candidate_count': len(context['history']),
                              'covered_candidate_count': len(judgments),
                              'label_counts': dict(Counter(item.label for item in judgments)),
                              'judgments': [{key: getattr(item, key) for key in ('old_memory_id', 'new_memory_id', 'label', 'source_ids')} for item in judgments]}
                except ModelFailure as error:
                    if not error.metadata.get('calls'):
                        raise ReplayError(error.code) from None
                    result = {'status': error.code}
                db.execute('UPDATE replay_calls SET result_json=? WHERE phase=? AND source_task_id=?',
                           (canonical_json(result), phase, task['task_id']))
                db.commit()
                if result['status'] not in {'succeeded', 'invalid_output'}:
                    break
    return read_report(directory)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    prepare = commands.add_parser('prepare')
    prepare.add_argument('--source-database', type=Path, required=True)
    prepare.add_argument('--build-id', required=True)
    prepare.add_argument('--ordinals', type=int, nargs='+', default=[2, 44, 90])
    prepare.add_argument('--directory', type=Path, required=True)
    run = commands.add_parser('run')
    run.add_argument('--directory', type=Path, required=True)
    run.add_argument('--phase', choices=['before', 'after'], required=True)
    run.add_argument('--approved-call-limit', type=int, required=True)
    run.add_argument('--allow-paid', action='store_true')
    status = commands.add_parser('status')
    status.add_argument('--directory', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == 'prepare':
            result = prepare_plan(args.source_database, args.build_id, args.ordinals, args.directory)
        elif args.command == 'run':
            result = run_phase(args.directory, args.phase, args.approved_call_limit, allow_paid=args.allow_paid)
        else:
            result = read_report(args.directory.resolve())
    except ReplayError as error:
        print(json.dumps({'status': 'stopped', 'error_code': str(error)}))
        return 2
    except Exception:
        print(json.dumps({'status': 'stopped', 'error_code': 'replay_internal_error'}))
        return 2
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
