"""Read-only allowlisted relation-phase audit; never emit source/model text."""
import argparse
from collections import Counter
from contextlib import contextmanager
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import sqlite3

import numpy as np

from locomo_memory.projection import create_projection
from locomo_memory.relation_schemas import MemoryRelation
from tools.m5.extraction_recovery import snapshot
from tools.m5.offline import sha, write

PROTECTED = ('datasets', 'import_artifacts', 'conversations', 'source_turns',
             'memories', 'memory_sources', 'build_fragments', 'build_indexes', 'index_entries')


@contextmanager
def connect(path):
    db = sqlite3.connect(path.resolve().as_uri()+'?mode=ro', uri=True)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA query_only=ON')
    db.execute('BEGIN')
    try:
        yield db
    finally:
        db.close()


def table_digest(db, names):
    digest = hashlib.sha256()
    for name in names:
        # Names are a fixed local allowlist.
        rows = sorted(json.dumps(tuple(row), ensure_ascii=False, default=str)
                      for row in db.execute('SELECT * FROM '+name))
        digest.update(json.dumps([name, rows], ensure_ascii=False).encode())
    return digest.hexdigest()


def audit(stage):
    plan = json.loads((stage/'plan.json').read_text())
    bid = plan['build_id']
    source = Path(plan['source_index_stage'])/'memory.sqlite3'
    assert snapshot(source) == plan['source_index_snapshot'], 'frozen_source_index_changed'
    with connect(stage/'physical-requests.sqlite3') as ledger:
        rows = ledger.execute('SELECT reserved_usd,status,usage_json FROM physical_requests').fetchall()
        policy = json.loads(ledger.execute('SELECT json FROM policy').fetchone()[0])
    proposed = plan['policy']
    expected = dict(max_requests=proposed['max_requests'], max_usd=str(Decimal(proposed['max_usd'])),
        model=proposed['model'], input_rate=str(Decimal(proposed['input_usd_per_million'])),
        output_rate=str(Decimal(proposed['output_usd_per_million'])),
        max_input_bytes=proposed['max_input_bytes'], max_output_tokens=proposed['max_output_tokens'])
    assert policy == expected, 'ledger_policy_differs_from_frozen_plan'
    reserved = sum((Decimal(r[0]) for r in rows), Decimal(0))
    usage, known_peak, unknown = Counter(), Decimal(0), 0
    for row in rows:
        item = json.loads(row['usage_json'])
        if not isinstance(item, dict) or not all(k in item for k in ('prompt_tokens','completion_tokens')):
            unknown += 1
            continue
        usage.update(item)
        known_peak += (Decimal(item['prompt_tokens'])*Decimal(policy['input_rate']) +
                       Decimal(item['completion_tokens'])*Decimal(policy['output_rate']))/Decimal(1000000)
    assert len(rows) <= policy['max_requests'] and reserved <= Decimal(policy['max_usd'])
    with connect(stage/'memory.sqlite3') as db, connect(source) as original:
        protected = table_digest(db, PROTECTED)
        assert protected == table_digest(original, PROTECTED)
        other_builds = [tuple(r) for r in db.execute('SELECT * FROM build_versions WHERE build_id!=? ORDER BY build_id', (bid,))]
        assert other_builds == [tuple(r) for r in original.execute('SELECT * FROM build_versions WHERE build_id!=? ORDER BY build_id', (bid,))]
        assert db.execute('SELECT COUNT(*) FROM relation_tasks WHERE build_id!=?', (bid,)).fetchone()[0] == 0
        build = dict(db.execute('SELECT * FROM build_versions WHERE build_id=?', (bid,)).fetchone())
        states = dict(db.execute('SELECT status,COUNT(*) FROM relation_tasks WHERE build_id=? GROUP BY status', (bid,)))
        errors = dict(db.execute('SELECT error_code,COUNT(*) FROM relation_tasks WHERE build_id=? AND error_code IS NOT NULL GROUP BY error_code', (bid,)))
        calls = [json.loads(r[0]) for r in db.execute(
            'SELECT c.metadata_json FROM relation_provider_calls c JOIN relation_tasks t USING(task_id) WHERE t.build_id=?', (bid,))]
        memories = {r[0]: json.loads(r[1]) for r in db.execute('SELECT memory_id,memory_json FROM memories WHERE build_id=?', (bid,))}
        labels = Counter()
        for row in db.execute('SELECT relation_json FROM memory_relations WHERE build_id=?', (bid,)):
            value = json.loads(row[0])
            old, new = memories[value['old_memory_id']], memories[value['new_memory_id']]
            ids = set(old['source_ids']+new['source_ids'])
            sources = {sid: dict(db.execute('SELECT * FROM source_turns WHERE source_id=?', (sid,)).fetchone()) for sid in ids}
            validated = MemoryRelation.model_validate(value, context=dict(
                new_memory=new, history=[old], sources=sources))
            assert validated.build_id == bid and old['sample_id'] == new['sample_id'] == 'conv-43'
            labels[validated.label] += 1
        names = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        for name in ('active_versions','candidate_queries','query_traces','evaluation_runs','evaluation_run_items'):
            if name in names:
                assert db.execute('SELECT COUNT(*) FROM '+name).fetchone()[0] == 0
        projection_verified = False
        if build['status'] == 'related':
            build['config'] = json.loads(build['config_json'])
            expected = create_projection(db, build)
            stored = db.execute('SELECT projection_json FROM current_state_projections WHERE build_id=?', (bid,)).fetchone()
            assert stored is not None and json.loads(stored[0]) == expected
            projection_verified = True
        terminal = build['status'] in ('related','relations_failed')
        if terminal:
            assert len(calls) == len(rows)
            assert sum(states.values()) == plan['relation_tasks']
            assert not states.get('pending') and not states.get('running')
    elapsed = [c['elapsed_seconds'] for c in calls if isinstance(c.get('elapsed_seconds'), (int,float))]
    return dict(status=build['status'], scope=plan['scope'], relation_tasks=states,
        task_error_codes=errors, stored_relations=dict(labels), projection_contract_verified=projection_verified,
        source_memory_fragments_indexes_unchanged=True, protected_tables_sha256=protected,
        other_builds_unchanged=True, published=False, query_or_evaluation_run=False,
        physical_requests=len(rows), request_statuses=dict(Counter(r['status'] for r in rows)),
        conservative_reserved_usd=str(reserved), reported_usage=dict(usage),
        reported_usage_peak_cache_miss_upper_usd=str(known_peak), unknown_usage_requests=unknown,
        remaining_requests=policy['max_requests']-len(rows),
        remaining_reserved_capacity_usd=str(Decimal(policy['max_usd'])-reserved),
        call_outcomes=dict(Counter(c.get('outcome','in_flight') for c in calls)),
        call_error_codes=dict(Counter(c['error_code'] for c in calls if c.get('error_code'))),
        attempt_elapsed_seconds_p50_p95=np.quantile(elapsed,[.5,.95]).tolist() if elapsed else None,
        elapsed_scope='completed model-adapter physical attempts; excludes entire Build and query latency',
        actual_bill_usd='not_measured', holdout_qa_read=False,
        relation_semantic_accuracy='not_measured; source/schema validation is not independent truth',
        policy=policy, plan_sha256=sha(stage/'plan.json'), terminal=terminal)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.stage.resolve())
    write(args.output, result)
    print(json.dumps(result))
