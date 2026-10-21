#!/usr/bin/env python3
"""Audit persisted relation failures offline; never import or call model code."""

import argparse
from collections import Counter
import csv
import fcntl
import hashlib
import json
from pathlib import Path
import sqlite3


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_csv(path, rows):
    with path.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def audit(directory, build_id):
    database = directory / 'memory.sqlite3'
    task_export = directory / 'builds' / build_id / 'relation-tasks.json'
    replay_path = directory / 'observations' / 'relation-diagnostic-replay.json'
    sources = [database, task_export, replay_path]
    sources += [p for p in (database.with_name(database.name + '-wal'),
                           directory / 'builds' / build_id / 'build.json') if p.exists()]
    before = {str(p): digest(p) for p in sources}
    # Immutable reads are safe here only for a stopped backend with no WAL data.
    wal = database.with_name(database.name + '-wal')
    if wal.exists() and wal.stat().st_size:
        raise ValueError('Nonempty WAL: use a consistent offline snapshot first')
    with database.with_name(database.name + '.runtime.lock').open('rb') as lock:
        fcntl.flock(lock, fcntl.LOCK_SH | fcntl.LOCK_NB)
        with sqlite3.connect(database.as_uri() + '?mode=ro&immutable=1', uri=True) as db:
            db.execute('PRAGMA query_only=ON')
            db.row_factory = sqlite3.Row
            tasks = [dict(r) for r in db.execute(
                'SELECT * FROM relation_tasks WHERE build_id=? ORDER BY ordinal', (build_id,))]
            memories = {}
            for row in db.execute('SELECT memory_id,fragment_id,memory_json FROM memories WHERE build_id=?', (build_id,)):
                memories[row['memory_id']] = {**json.loads(row['memory_json']), 'fragment_id': row['fragment_id']}
            fragments = {r['fragment_id']: r['ordinal'] for r in db.execute(
                'SELECT fragment_id,ordinal FROM build_fragments WHERE build_id=?', (build_id,))}
            build = dict(db.execute('SELECT * FROM build_versions WHERE build_id=?', (build_id,)).fetchone())
            positions = {r['source_id']: r['position'] for r in db.execute(
                'SELECT source_id,position FROM source_turns WHERE dataset_id=? AND sample_id=?',
                (build['dataset_id'], build['sample_id']))}
    exported = {t['task_id']: t for t in json.loads(task_export.read_text())}
    if len(tasks) != len(exported):
        raise ValueError('Database/export task count mismatch')
    for task in tasks:
        normalized = {k: v for k, v in task.items() if k not in {'history_ids_json', 'metadata_json'}}
        normalized.update(history_ids=json.loads(task['history_ids_json']), model_metadata=json.loads(task['metadata_json']))
        if normalized != exported[task['task_id']]:
            raise ValueError('Database/export mismatch: ' + task['task_id'])

    def memory_descriptor(memory_id):
        memory = memories[memory_id]
        return {**{k: memory[k] for k in ('memory_id', 'state_key', 'state_dimension', 'entity_id',
                                         'memory_type', 'statement_type', 'polarity', 'fragment_id', 'source_ids')},
                'fragment_ordinal_zero_based': fragments[memory['fragment_id']],
                'source_positions_zero_based': [positions[s] for s in memory['source_ids']]}

    global_calls = Counter(json.dumps(c, sort_keys=True) for c in json.loads(build['model_metadata_json'])['calls'])
    details, task_rows, attempt_rows, candidate_rows = [], [], [], []
    for task in (t for t in tasks if t['status'] == 'failed'):
        calls = json.loads(task['metadata_json']).get('calls', [])
        if task['attempts'] != 1:
            raise ValueError('Multiple logical attempts require additional historical snapshots')
        if any(set(call) - {'attempt', 'timestamp', 'outcome', 'response_received', 'requested_model',
                            'returned_model', 'elapsed_seconds', 'usage'} for call in calls):
            raise ValueError('Richer call diagnostics found: review before assigning unknown categories')
        new = memory_descriptor(task['new_memory_id'])
        candidates = []
        for index, memory_id in enumerate(json.loads(task['history_ids_json'])):
            old = memory_descriptor(memory_id)
            comparison = {'history_candidate_index_zero_based': index, 'old_memory': old,
                          'same_state_key': old['state_key'] == new['state_key'],
                          'same_entity': old['entity_id'] == new['entity_id'],
                          'original_output_judgment_index': None}
            candidates.append(comparison)
            candidate_rows.append({
                'task_id': task['task_id'], 'task_ordinal_zero_based': task['ordinal'],
                'history_candidate_index_zero_based': index, 'original_output_judgment_index': 'unknown',
                **{'new_' + k: new[k] for k in ('memory_id', 'entity_id', 'state_key', 'memory_type', 'statement_type', 'fragment_id', 'fragment_ordinal_zero_based')},
                **{'old_' + k: old[k] for k in ('memory_id', 'entity_id', 'state_key', 'memory_type', 'statement_type', 'fragment_id', 'fragment_ordinal_zero_based')},
                'same_state_key': comparison['same_state_key'], 'same_entity': comparison['same_entity'],
                'input_attribute_is_output_violation_evidence': False})
        attempts = []
        for index, call in enumerate(calls):
            if not global_calls[json.dumps(call, sort_keys=True)]:
                raise ValueError('Task call absent from Build metadata')
            # Deliberately project known metadata; do not copy response text or logs.
            record = {k: call.get(k) for k in ('attempt', 'timestamp', 'outcome', 'response_received',
                                              'requested_model', 'returned_model', 'elapsed_seconds', 'usage')}
            record.update(field_path=None, specific_error_category=None, validation_rule=None,
                          finish_reason=None, at_configured_output_cap=call.get('usage', {}).get('completion_tokens') == json.loads(build['config_json'])['model_max_tokens'])
            attempts.append(record)
            attempt_rows.append({
                'task_id': task['task_id'], 'task_ordinal_zero_based': task['ordinal'],
                'logical_task_attempt': task['attempts'], 'provider_attempt': call['attempt'],
                'is_last_recorded_provider_attempt': index == len(calls) - 1,
                'timestamp': call.get('timestamp'), 'recorded_error_category': call.get('outcome'),
                'specific_error_category': 'unknown', 'field_path': 'unknown', 'finish_reason': 'not_persisted',
                'completion_tokens': call.get('usage', {}).get('completion_tokens'),
                'at_configured_output_cap': record['at_configured_output_cap']})
        unknowns = {k: None for k in ('json_syntax_or_structure_error', 'schema_field_error', 'enum_or_value_error',
                                    'domain_constraint_error', 'incomplete_output_or_truncation')}
        detail = {'task_id': task['task_id'], 'task_ordinal_zero_based': task['ordinal'],
                  'logical_task_attempt_count': task['attempts'], 'recorded_error_category': task['error_code'],
                  'new_memory': new, 'history_candidates': candidates, 'provider_attempt_history': attempts,
                  'last_recorded_provider_attempt': attempts[-1] if attempts else None,
                  'specific_error_determinable_from_original_persisted_diagnostics': False,
                  'original_output_classification': unknowns,
                  'replay_evidence_ref': 'independent_replay' if task['task_id'] == json.loads(replay_path.read_text())['task_id'] else None}
        details.append(detail)
        task_rows.append({'task_id': task['task_id'], 'task_ordinal_zero_based': task['ordinal'],
                          'new_state_key': new['state_key'], 'new_entity_id': new['entity_id'],
                          'new_memory_type': new['memory_type'], 'new_statement_type': new['statement_type'],
                          'new_fragment_ordinal_zero_based': new['fragment_ordinal_zero_based'],
                          'history_candidate_count': len(candidates), 'logical_task_attempt_count': task['attempts'],
                          'provider_attempts': len(attempts), 'last_error_category': attempts[-1]['outcome'] if attempts else task['error_code'],
                          'historical_error_categories': ','.join(a['outcome'] for a in attempts),
                          'specific_category_and_field_path': 'unknown',
                          'provider_attempts_at_output_cap': ','.join(str(a['attempt']) for a in attempts if a['at_configured_output_cap'])})

    replay = json.loads(replay_path.read_text())
    replay['evidence_scope'] = 'independent_replay_only; no attribution to original provider attempts'
    failed_calls = [a for d in details for a in d['provider_attempt_history']]
    result = {
        'schema_version': 'offline-relation-audit-v1', 'new_model_calls': 0,
        'database_open_mode': 'mode=ro&immutable=1; query_only; stopped backend lock; empty WAL',
        'build_id': build_id, 'task_states': dict(Counter(t['status'] for t in tasks)),
        'original_failed_tasks': len(details), 'original_failed_task_provider_attempts': len(failed_calls),
        'original_specific_error_category_determinable_tasks': 0,
        'original_specific_error_category_unknown_tasks': len(details),
        'original_attempt_error_categories': dict(Counter(a['outcome'] for a in failed_calls)),
        'original_field_paths_present': sum(a['field_path'] is not None for a in failed_calls),
        'original_finish_reasons_present': sum(a['finish_reason'] is not None for a in failed_calls),
        'output_cap_clue_provider_attempts': sum(a['at_configured_output_cap'] for a in failed_calls),
        'output_cap_clue_task_ids': [d['task_id'] for d in details if any(a['at_configured_output_cap'] for a in d['provider_attempt_history'])],
        'candidate_input_attributes': {
            'failed_task_candidate_pairs': len(candidate_rows),
            'failed_task_cross_state_key_pairs': sum(not row['same_state_key'] for row in candidate_rows),
            'failed_tasks_with_cross_state_key_candidates': sum(any(not p['same_state_key'] for p in d['history_candidates']) for d in details),
            'succeeded_tasks_with_cross_state_key_candidates': sum(
                any(memories[old]['state_key'] != memories[t['new_memory_id']]['state_key']
                    for old in json.loads(t['history_ids_json'])) for t in tasks if t['status'] == 'succeeded'),
            'not_a_root_cause_classification': True},
        'original_failure_class_counts': {k: None for k in details[0]['original_output_classification']},
        'independent_replay': replay, 'failed_tasks': details,
        'input_memory_attributes_are_not_generated_output_violations': True,
        'positions': 'All input positions are zero-based. Candidate input order is not original output judgment order.',
        'history_limit': 'Provider history is the persisted metadata for the current logical attempt. All failed tasks have one logical attempt; no prior logical retries are inferred.',
    }
    after = {str(p): digest(p) for p in sources}
    if before != after:
        raise ValueError('Input changed during offline audit')
    result['verification'] = {'all_database_tasks_equal_export': True, 'all_original_failed_calls_found_in_build_metadata': True,
                              'input_hashes_unchanged': True, 'input_sha256': before}
    return result, task_rows, attempt_rows, candidate_rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, required=True, help='Stopped experiment directory')
    parser.add_argument('--build-id', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result, tasks, attempts, candidates = audit(args.directory.resolve(), args.build_id)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / 'diagnosis.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    for name, rows in [('failed-tasks', tasks), ('provider-attempts', attempts), ('candidate-memories', candidates)]:
        write_csv(args.output / (name + '.csv'), rows)
    print(json.dumps({k: result[k] for k in ('new_model_calls', 'task_states', 'original_failed_tasks',
                                            'original_failed_task_provider_attempts', 'output_cap_clue_provider_attempts',
                                            'original_specific_error_category_determinable_tasks', 'verification')}, ensure_ascii=False))


if __name__ == '__main__':
    main()
