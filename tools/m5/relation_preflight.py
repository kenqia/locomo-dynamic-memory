"""Compute relation task identities and cost bounds without index/model/QA calls."""
import argparse
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import sqlite3

from locomo_memory.config import Settings
from locomo_memory.model import request_messages
from locomo_memory.query_payload import query_wire_payload
from locomo_memory.relation_schemas import RelationBatch, relation_label_error
from locomo_memory.relation_selection import select_history
from tools.m5.offline import sha, write


def run(stage, output):
    settings = Settings.model_validate_json((stage/'settings.json').read_text())
    results = []
    maximum_bytes = 160000
    attempts = settings.model_retries + 1
    output_tokens = settings.relation_max_tokens or settings.model_max_tokens
    per_request = (Decimal(maximum_bytes)*Decimal('.30') +
                   Decimal(output_tokens)*Decimal('1.20'))/Decimal(1000000)
    with sqlite3.connect((stage/'memory.sqlite3').resolve().as_uri()+'?mode=ro', uri=True) as db:
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA query_only=ON')
        db.execute('BEGIN')
        for build in db.execute('SELECT build_id,sample_id,status,fingerprint FROM build_versions ORDER BY sample_id'):
            bid = build['build_id']
            # Keep the exact producer ordering, including the insertion-order tie.
            rows = db.execute('SELECT m.memory_json,MIN(s.position) AS source_order FROM memories m '
                'JOIN memory_sources ms ON m.memory_id=ms.memory_id JOIN source_turns s ON s.source_id=ms.source_id '
                'WHERE m.build_id=? GROUP BY m.memory_id ORDER BY source_order,m.rowid', (bid,)).fetchall()
            previous, tasks, truncated = {}, [], 0
            for ordinal, row in enumerate(rows):
                new = json.loads(row['memory_json'])
                history = previous.setdefault(new['entity_id'], [])
                bounded, selection = select_history(new, history, settings)
                if bounded:
                    ids = {sid for m in [new, *bounded] for sid in m['source_ids']}
                    sources = {sid: dict(db.execute('SELECT * FROM source_turns WHERE source_id=?', (sid,)).fetchone()) for sid in sorted(ids)}
                    payload = dict(new_memory=new, history=bounded, sources=list(sources.values()),
                        allowed_labels_by_old_memory={m['memory_id']: [label for label in (
                            'RETAIN','UPDATE','SUPERSEDE','CONFLICT','undetermined')
                            if relation_label_error(label, m, new) is None] for m in bounded})
                    messages = request_messages('relate', query_wire_payload('relate', payload), RelationBatch)
                    size = len(json.dumps(messages, ensure_ascii=False).encode())
                    tasks.append(dict(ordinal=ordinal, new_memory_id=new['memory_id'],
                        history_ids=[m['memory_id'] for m in bounded], input_message_bytes=size,
                        fits_proposed_byte_cap=size <= maximum_bytes))
                    truncated += selection['omitted_count']
                history.append(new)
            results.append(dict(build_id=bid, sample_id=build['sample_id'], status=build['status'],
                build_fingerprint=build['fingerprint'], memory_count=len(rows), relation_tasks=len(tasks),
                comparisons=sum(len(t['history_ids']) for t in tasks), omitted_history_comparisons=truncated,
                max_first_attempt_message_bytes=max((t['input_message_bytes'] for t in tasks), default=0),
                over_cap_tasks=sum(not t['fits_proposed_byte_cap'] for t in tasks),
                request_bound=len(tasks)*attempts,
                worst_reserved_usd=str(per_request*len(tasks)*attempts),
                eligible_for_complete_build_proposal=build['status']=='extracted',
                task_identity_sha256=hashlib.sha256(json.dumps(tasks,sort_keys=True).encode()).hexdigest()))
    summary = dict(status='read_only_preflight_not_authorized', builds=results,
        output_tokens=output_tokens, max_input_message_bytes=maximum_bytes, attempts_per_task=attempts,
        per_physical_request_upper_usd=str(per_request),
        total_request_bound=sum(r['request_bound'] for r in results),
        total_worst_reserved_usd=str(sum((Decimal(r['worst_reserved_usd']) for r in results),Decimal(0))),
        relation_thinking_effort=settings.relation_thinking_effort,
        price_basis='2026-11-04 DeepSeek peak cache-miss input .30/output 1.20 USD per million',
        exact_scope='Existing accepted extraction snapshot only. Failed conv-44 is provisional and must be recomputed after recovery.',
        byte_cap_scope='Retry feedback may increase messages; proposed transport refuses over-cap requests, no silent evidence truncation.',
        excludes=['embedding/index runtime verification','relation provider calls','query/evaluation','holdout QA/evidence'],
        provider_requests=0, source_plan_sha256=sha(stage/'plan.json'),
        source_settings_sha256=sha(stage/'settings.json'))
    write(output, summary)
    print(json.dumps(summary))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    run(args.stage, args.output)
