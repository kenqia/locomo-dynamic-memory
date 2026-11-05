"""Audit only allowlisted extraction identities, contracts and usage; never print text."""
import argparse
from collections import Counter
from decimal import Decimal
import json
from pathlib import Path
import sqlite3

from locomo_memory.memory_schemas import Memory
from tools.m5.offline import write, sha


def audit(stage, output):
    with sqlite3.connect(stage/'physical-requests.sqlite3') as db:
        requests = db.execute('SELECT reserved_usd,status,usage_json FROM physical_requests').fetchall()
        policy = json.loads(db.execute('SELECT json FROM policy').fetchone()[0])
    reserved = sum((Decimal(r[0]) for r in requests), Decimal(0))
    usage, known_peak = Counter(), Decimal(0)
    unknown = 0
    for _, status, raw in requests:
        item = json.loads(raw)
        if not isinstance(item, dict) or not all(k in item for k in ('prompt_tokens', 'completion_tokens')):
            unknown += 1
            continue
        usage.update(item)
        known_peak += (Decimal(item['prompt_tokens'])*Decimal(policy['input_rate'])+
                       Decimal(item['completion_tokens'])*Decimal(policy['output_rate']))/Decimal(1000000)
    with sqlite3.connect((stage/'memory.sqlite3').resolve().as_uri()+'?mode=ro', uri=True) as db:
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA query_only=ON')
        builds = [dict(r) for r in db.execute(
            'SELECT build_id,sample_id,status,phase,fingerprint,source_sha256 FROM build_versions ORDER BY sample_id')]
        model_calls = []
        for build in builds:
            bid = build['build_id']
            metadata = json.loads(db.execute('SELECT model_metadata_json FROM build_versions WHERE build_id=?', (bid,)).fetchone()[0])
            build['returned_models'] = metadata.get('returned_models', [])
            model_calls.extend(metadata.get('calls', []))
            build['fragments'] = dict(db.execute('SELECT status,COUNT(*) FROM build_fragments WHERE build_id=? GROUP BY status', (bid,)))
            build['fragment_error_codes'] = dict(db.execute(
                'SELECT error_code,COUNT(*) FROM build_fragments WHERE build_id=? AND error_code IS NOT NULL GROUP BY error_code', (bid,)))
            memories = [Memory.model_validate_json(r[0]) for r in db.execute('SELECT memory_json FROM memories WHERE build_id=?', (bid,))]
            build['memories'] = len(memories)
            referenced = set()
            for memory in memories:
                assert memory.build_id == bid and memory.sample_id == build['sample_id']
                for sid in memory.source_ids:
                    source = db.execute('SELECT dataset_id,sample_id,session_time FROM source_turns WHERE source_id=?', (sid,)).fetchone()
                    assert source is not None and source['sample_id'] == memory.sample_id
                    assert source['dataset_id'] == memory.dataset_id and source['session_time'] in memory.session_times
                    referenced.add(sid)
            build['referenced_source_turns'] = len(referenced)
        table_names = {r[0] for r in db.execute('SELECT name FROM sqlite_master WHERE type="table"')}
        forbidden_present = table_names.intersection({'memory_relations', 'build_indexes', 'evaluation_run_items'})
        assert not forbidden_present
    assert len(requests) <= policy['max_requests'] and reserved <= Decimal(policy['max_usd'])
    summary = dict(status='extraction_stage_finished' if all(b['status'] in ('extracted', 'failed') for b in builds) else 'running',
        scope='conversation-only extraction, not complete Build or independent evaluation',
        builds=builds, physical_requests=len(requests), request_statuses=dict(Counter(r[1] for r in requests)),
        conservative_reserved_usd=str(reserved), reported_usage=dict(usage), unknown_usage_requests=unknown,
        approved_requests_remaining=policy['max_requests']-len(requests),
        approved_reservation_usd_remaining=str(Decimal(policy['max_usd'])-reserved),
        model_attempt_outcomes=dict(Counter(c.get('outcome', 'unknown') for c in model_calls)),
        reported_usage_peak_cache_miss_upper_usd=str(known_peak),
        actual_bill_usd='not_measured; cache/time-of-day discounts and account bill not accessed',
        policy=policy, holdout_answers_read=False, relation_index_qa_not_run=True,
        memory_and_source_contract='validated; no claim of semantic factual correctness',
        plan_sha256=sha(stage/'plan.json'), authorization_sha256=sha(stage/'user-authorization.json'))
    write(output, summary)
    print(json.dumps(summary))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    audit(args.stage, args.output)
