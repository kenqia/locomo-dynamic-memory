"""Offline delivery replay over public LoCoMo experiment traces; no provider calls.

Read only the selected experiment SQLite and never modify its builds or traces.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3

from locomo_memory.config import Settings
from locomo_memory.builds import BuildError
from locomo_memory.raw_queries import pack_payload, retrieval_limitations
from locomo_memory.raw_retrieval import retrieve_sources
from locomo_memory.temporal import query_memory_times


def replay(path):
    reports = []
    with sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True) as db:
        db.row_factory = sqlite3.Row
        sources = {r['source_id']:dict(r) for r in db.execute('SELECT * FROM source_turns')}
        traces = [json.loads(r[0]) for r in db.execute('SELECT result_json FROM query_traces ORDER BY rowid')]
        # The latest historical trace per question is the fixed replay input.
        selected = {t['question']:t for t in traces if t.get('strategy') == 'dynamic_raw_fallback'}
        for question, trace in selected.items():
            settings = Settings.model_validate(trace['config'])
            memories = {c['memory']['memory_id']:c['memory'] for c in trace['expanded']['candidates']}
            memories, diagnostics = query_memory_times(memories, sources)
            base = dict(operation='resolve_raw', question=question, time=trace['time'],
                        analysis={k:trace['initial']['analysis'][k] for k in ('status','result')}, relations=trace['relations'],
                        evidence_profile=trace['evidence_selection']['profile'],
                        candidates_truncated=trace['expanded']['truncated'] or trace['initial']['initial_truncated'])
            first, first_audit = pack_payload(base, list(memories.values()), [], sources, settings)
            initial = trace['initial_resolution']
            gaps = [c['gap'] for c in initial['coverage'] if c['status'] == 'insufficient' and c['gap']]
            all_raw = sorted([s for s in sources.values() if s['dataset_id'] == trace['dataset_id']
                              and s['sample_id'] == trace['sample_id']], key=lambda s:s['position'])
            raw, raw_audit = retrieve_sources(all_raw, question, gaps, settings)
            recovery = None
            try:
                joint, joint_audit = pack_payload({**base, 'previous_coverage':initial['coverage'],
                    'raw_retrieval_limitations':retrieval_limitations(raw_audit)},
                    list(memories.values()), raw, sources, settings)
            except BuildError as error:
                if error.code != 'previous_evidence_budget_exceeded':
                    raise
                recovery = error.code
                joint, joint_audit = None, None
            delivered = {m['memory_id'] for m in first['memories']}
            joint_ids = {m['memory_id'] for m in joint['memories']} if joint else set()
            old_support = {m for c in initial['coverage'] for m in c['memory_ids']}
            original_ids = {m['memory_id'] for m in memories.values()}
            report = dict(question=question, trace_id=trace['trace_id'],
                original_candidates=len(memories), first_input_tokens=first_audit['input_token_count'],
                first_delivered=[dict(memory_id=m['memory_id'], content=m['content'],
                    source_ids=m['source_ids']) for m in first['memories']],
                first_omitted_memory_ids=sorted(original_ids - delivered),
                old_supported_memory_ids=sorted(old_support),
                joint_input_tokens=joint_audit['input_token_count'] if joint_audit else None,
                joint_retains_all_prior_support=old_support <= joint_ids if joint else None,
                required_recovery=recovery,
                joint_delivered_source_ids=[s['source_id'] for s in joint['raw_sources']] if joint else [],
                time_diagnostics=diagnostics)
            assert first_audit['input_token_count'] <= settings.resolution_input_budget
            if joint:
                assert joint_audit['input_token_count'] <= settings.resolution_input_budget
                assert old_support <= joint_ids
            reports.append(report)
    return dict(kind='offline_delivery_replay_not_live_answers', source_database=str(path.resolve()),
                provider_calls=0, reports=reports)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('database', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    result = replay(args.database)
    result['replay_script_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    for row in result['reports']:
        print(row['question'], row['first_input_tokens'], row['joint_input_tokens'], row['joint_retains_all_prior_support'])
