"""Collect safe persisted diagnostics from the stopped v5 experiment, offline."""

import argparse
from collections import Counter
import csv
import fcntl
import hashlib
import json
from pathlib import Path
import sqlite3

from locomo_memory.implementation_identity import implementation_sha256
from locomo_memory.model import utc_now
from locomo_memory.usage import provider_usage


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def collect(directory, output):
    build_id = '23f0459c5b3b47269dc1497cfc066810'
    baseline = directory.parent / 'real-baseline-issue15' / 'memory.sqlite3'
    task_path = directory / 'builds' / build_id / 'relation-tasks.json'
    sources = [directory / name for name in ('memory.sqlite3', 'provider-budget.sqlite3')]
    sources += [baseline, task_path]
    for path in sources[:2]:
        wal = path.with_name(path.name + '-wal')
        if wal.exists() and wal.stat().st_size:
            raise ValueError('nonempty_wal_requires_consistent_snapshot')
    before = {str(path): digest(path) for path in sources}
    with (directory / 'memory.sqlite3.runtime.lock').open('rb') as lock:
        fcntl.flock(lock, fcntl.LOCK_SH | fcntl.LOCK_NB)
        with sqlite3.connect(sources[0].as_uri() + '?mode=ro&immutable=1', uri=True) as db:
            db.row_factory = sqlite3.Row
            build = dict(db.execute('SELECT * FROM build_versions WHERE build_id=?', (build_id,)).fetchone())
            assert build['status'] == 'interrupted'
            tasks = [dict(row) for row in db.execute('SELECT * FROM relation_tasks WHERE build_id=? ORDER BY ordinal', (build_id,))]
            memories = {row['memory_id']: {**json.loads(row['memory_json']), 'fragment_id': row['fragment_id']}
                        for row in db.execute('SELECT memory_id,fragment_id,memory_json FROM memories WHERE build_id=?', (build_id,))}
            fragments = dict(db.execute('SELECT fragment_id,ordinal FROM build_fragments WHERE build_id=?', (build_id,)))
            fragments_status = dict(db.execute('SELECT status,COUNT(*) FROM build_fragments WHERE build_id=? GROUP BY status', (build_id,)))
            call_rows = db.execute('SELECT c.metadata_json FROM relation_provider_calls c JOIN relation_tasks t USING(task_id) WHERE t.build_id=? ORDER BY t.ordinal,c.logical_attempt,c.provider_attempt', (build_id,)).fetchall()
            persisted_calls = [json.loads(row[0]) for row in call_rows]
            labels = dict(db.execute('SELECT label,COUNT(*) FROM memory_relations WHERE build_id=? GROUP BY label', (build_id,)))
    with sqlite3.connect(sources[1].as_uri() + '?mode=ro&immutable=1', uri=True) as db:
        header = json.loads(db.execute('SELECT value FROM header').fetchone()[0])
        ledger = [(row[0], row[1], json.loads(row[2])) for row in db.execute('SELECT sequence,operation,metadata FROM calls ORDER BY sequence')]
    assert header['implementation_sha256'] == implementation_sha256()
    assert before[str(baseline)] == '13497e43f418275585532d7d8a3a2bb326035662ed6eef67f41a05b6e8f46116'
    exported = json.loads(task_path.read_text())
    assert len(tasks) == len(exported) == 311
    by_id = {task['task_id']: task for task in exported}
    for task in tasks:
        observed = by_id[task['task_id']]
        for key, value in task.items():
            if key == 'metadata_json':
                assert observed['model_metadata'] == json.loads(value)
            elif key == 'history_ids_json':
                assert observed['history_ids'] == json.loads(value)
            else:
                assert observed[key] == value
    relation_ledger = [call for _, operation, call in ledger if operation == 'relate']
    assert len(relation_ledger) == len(persisted_calls) == 277
    persisted_by_id = {call['call_id']: call for call in persisted_calls}
    for call in relation_ledger:
        persisted = persisted_by_id[call['call_id']]
        assert all(persisted.get(key) == value for key, value in call.items())

    def descriptor(memory_id):
        memory = memories[memory_id]
        keys = ('memory_id', 'entity_id', 'state_key', 'state_dimension', 'memory_type', 'statement_type', 'polarity', 'fragment_id')
        return {**{key: memory[key] for key in keys}, 'fragment_ordinal_zero_based': fragments[memory['fragment_id']]}

    details, attempts, candidates, task_rows = [], [], [], []
    for task in exported:
        if task['status'] not in {'failed', 'interrupted'}:
            continue
        new = descriptor(task['new_memory_id'])
        history = []
        for logical in task['diagnostic_history']:
            for call in logical['calls']:
                keys = ('attempt', 'status', 'outcome', 'failure_stage', 'error_code', 'field_path', 'finish_reason', 'finish_reason_status', 'usage', 'call_id')
                record = {key: call.get(key) for key in keys}
                record['logical_attempt'] = logical['logical_attempt']
                history.append(record)
                attempts.append({'task_id': task['task_id'], 'task_status': task['status'], **{
                    key: record[key] for key in ('logical_attempt', 'attempt', 'outcome', 'failure_stage', 'error_code', 'field_path', 'finish_reason')},
                    'completion_tokens': call.get('usage', {}).get('completion_tokens')})
        old_memories = []
        for index, memory_id in enumerate(task['history_ids']):
            old = descriptor(memory_id)
            old_memories.append({'candidate_index_zero_based': index, **old})
            candidates.append({'task_id': task['task_id'], 'candidate_index_zero_based': index,
                               **{'new_' + key: value for key, value in new.items()},
                               **{'old_' + key: value for key, value in old.items()}})
        codes = sorted({call['error_code'] for call in history if call['error_code']})
        details.append({'task_id': task['task_id'], 'task_ordinal_zero_based': task['ordinal'],
                        'status': task['status'], 'new_memory': new, 'candidate_memories': old_memories,
                        'diagnostic_history_status': task['diagnostic_history_status'],
                        'provider_attempt_history': history, 'last_provider_attempt': history[-1] if history else None,
                        'observed_error_codes': codes})
        task_rows.append({'task_id': task['task_id'], 'status': task['status'], **new,
                          'candidate_count': len(old_memories), 'provider_attempts': len(history),
                          'observed_error_codes': ','.join(codes),
                          'last_error_code': history[-1]['error_code'] if history else None})
    all_calls = [call for _, _, call in ledger]
    previous_calls = []
    for round_number in (2, 3, 4):
        report = json.loads((Path(__file__).resolve().parents[1] / 'issue-15-relation-evidence-followup' / f'round-{round_number}' / 'results.json').read_text())
        for attempt in report['attempts']:
            previous_calls.append(attempt['diagnostics'])
    assert len(previous_calls) == header['previous_calls'] == 9
    assert len(all_calls) == 304
    failed_attempts = [a for a in attempts if a['task_status'] == 'failed']
    result = {'observed_at': utc_now(), 'new_model_calls_for_collection': 0,
              'build_id': build_id, 'build_status': build['status'], 'query_ready': False,
              'implementation_sha256': implementation_sha256(),
              'fragments': fragments_status, 'memory_count': len(memories),
              'relation_task_statuses': dict(Counter(task['status'] for task in exported)),
              'persisted_relation_label_counts': labels,
              'failed_task_observed_code_sets': dict(Counter(','.join(d['observed_error_codes']) for d in details if d['status'] == 'failed')),
              'failed_task_provider_attempt_errors': dict(Counter(a['error_code'] for a in failed_attempts)),
              'all_relation_provider_attempt_errors': dict(Counter(c['error_code'] for c in persisted_calls if c.get('error_code'))),
              'failed_and_interrupted_tasks': details,
              'budget': {**header, 'reserved_new_calls': len(ledger), 'reserved_total_calls': len(ledger) + header['previous_calls'],
                         'operations': dict(Counter(operation for _, operation, _ in ledger)),
                         'outcomes': dict(Counter(c.get('outcome', 'unknown') for c in all_calls))},
              'new_experiment_usage': provider_usage(all_calls),
              'whole_round_usage': provider_usage(previous_calls + all_calls),
              'last_provider_call': {key: all_calls[-1].get(key) for key in ('call_id', 'outcome', 'failure_stage', 'error_code', 'finish_reason', 'usage')},
              'limitations': ['Observed errors are validator stopping points, not an exhaustive classification of unseen output.',
                             'Output field indices do not identify input candidate positions.',
                             'memory_type event/state is persisted; no separate event_type field exists.',
                             'HTTP status and response body were not persisted; cause and missing usage remain unknown.',
                             'Original 29 legacy task failures retain their unknown root causes.',
                             'New extraction differs from baseline; full builds are not a paired causal comparison.',
                             'No publication or QA smoke ran.'],
              'verification': {'database_export_tasks_equal': True, 'relation_ledger_calls_equal_database': True,
                               'baseline_database_unchanged': True, 'source_sha256': before}}
    assert before == {str(path): digest(path) for path in sources}
    output.mkdir(parents=True, exist_ok=True)
    (output / 'final-summary.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    for name, rows in [('failed-and-interrupted-tasks', task_rows), ('provider-attempts', attempts), ('candidate-memories', candidates)]:
        with (output / (name + '.csv')).open('w', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator='\n')
            writer.writeheader()
            writer.writerows(rows)
    print(json.dumps({key: result[key] for key in ('relation_task_statuses', 'failed_task_observed_code_sets', 'failed_task_provider_attempt_errors', 'budget', 'whole_round_usage', 'last_provider_call')}, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    collect(args.directory.resolve(), args.output.resolve())
