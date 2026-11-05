"""Replay actual production expansion and Answer packing, stopping before generation."""
from contextlib import contextmanager
from collections import Counter
import argparse
import json
from pathlib import Path
import resource
import sqlite3
import subprocess
import time
from types import SimpleNamespace
import uuid

import numpy as np

from locomo_memory.config import Settings
from locomo_memory.evaluation_metrics import coverage
from locomo_memory.export_schemas import MemoryExport
from locomo_memory.expansion import ExpansionService
from locomo_memory.imports import canonical_json
from locomo_memory.m5_queries import BonusExpansion, BonusRetrieval
from locomo_memory.m5_wire_compression import encode_request
from locomo_memory.model import ModelFailure, request_messages
from locomo_memory.queries import QueryService
from locomo_memory.query_schemas import EvidenceAnswer
from tools.m5.offline import ROOT, ORIGIN, RUN, DEV, sha, write, paired


class Scratch:
    def __init__(self, path, origin, pins):
        if path.exists():
            raise ValueError('scratch_already_exists')
        self.path = path
        with sqlite3.connect(path) as db:
            for table in ('source_turns', 'memories', 'memory_sources', 'memory_relations', 'relation_phases'):
                db.execute(origin.execute('SELECT sql FROM sqlite_master WHERE name=?', (table,)).fetchone()[0])
                if table == 'source_turns':
                    rows = origin.execute('SELECT * FROM source_turns WHERE sample_id IN (?,?,?,?)', DEV).fetchall()
                elif table == 'memory_sources':
                    rows = origin.execute('SELECT ms.* FROM memory_sources ms JOIN memories m ON m.memory_id=ms.memory_id WHERE m.build_id IN (?,?,?,?)', tuple(pins.values())).fetchall()
                else:
                    rows = origin.execute(f'SELECT * FROM {table} WHERE build_id IN (?,?,?,?)', tuple(pins.values())).fetchall()
                if rows:
                    db.executemany(f'INSERT INTO {table} VALUES ({",".join("?" for _ in rows[0])})', rows)
            db.execute('CREATE TABLE candidate_queries(query_id TEXT PRIMARY KEY,build_id TEXT,result_json TEXT)')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()


class Capture:
    def generate(self, *args, **kwargs):
        raise ModelFailure('m5_capture_no_provider', {'calls': []})


def answer_packet(settings, question, memories, sources, condition):
    service = QueryService.__new__(QueryService)
    service.settings, service.model = settings, Capture()
    audit = {}
    try:
        service.generate_answer(question, condition, memories, sources, 'sufficient', audit=audit, record_input=True)
    except ModelFailure as error:
        if error.code != 'm5_capture_no_provider':
            raise
    return audit


def source_ids(ids, memories):
    return list(dict.fromkeys(sid for mid in ids for sid in memories[mid]['source_ids']))


def run(label):
    if not label.replace('-', '').isalnum():
        raise ValueError('invalid_label')
    out = ROOT / 'experiments/m5-development' / label
    private = ROOT / 'var/m5-development' / label
    out.mkdir(parents=True, exist_ok=False)
    private.mkdir(parents=True, exist_ok=False)
    private.chmod(0o700)
    original_sha = sha(ORIGIN)
    start, cpu = time.perf_counter(), time.process_time()
    origin = sqlite3.connect(ORIGIN.resolve().as_uri() + '?mode=ro', uri=True)
    origin.row_factory = sqlite3.Row
    origin.execute('PRAGMA query_only=ON')
    origin.execute('BEGIN')
    meta = json.loads(origin.execute('SELECT result_json FROM evaluation_runs WHERE run_id=?', (RUN,)).fetchone()[0])
    settings = Settings.model_validate(meta['config'])
    scratch = Scratch(private/'scratch.sqlite3', origin, meta['pins'])
    expansion = ExpansionService(SimpleNamespace(database=scratch, settings=settings))
    bundles = {conv: MemoryExport.model_validate_json((ROOT/'var/m5-development/replay-v1/exports'/f'{conv}.json').read_text()) for conv in DEV}
    memories = {conv: {m.memory_id: m.model_dump(mode='json') for m in b.memories} for conv, b in bundles.items()}
    sources = {conv: {r['source_id']: dict(r) for r in origin.execute('SELECT * FROM source_turns WHERE sample_id=?', (conv,))} for conv in DEV}
    rows = [json.loads(r[0]) for r in origin.execute("SELECT item_json FROM evaluation_run_items WHERE run_id=? AND json_extract(item_json,'$.strategy')='hybrid_no_resolution' ORDER BY ordinal", (RUN,))]
    dynamic = {item['question_id']: item for item in (json.loads(r[0]) for r in origin.execute("SELECT item_json FROM evaluation_run_items WHERE run_id=? AND json_extract(item_json,'$.strategy')='dynamic'", (RUN,)))}
    arms = ('H', 'D', 'B1', 'B2', 'B3', 'B4')
    write(out/'protocol.json', dict(version='m5-delivery-replay-v1', denominator=757, original_run=RUN,
        arms=dict(H='frozen Hybrid query -> original expansion -> Answer packing',
                  D='frozen Dynamic query -> original expansion -> Answer packing',
                  B1='D + actual depth2 BonusExpansion', B2='D + optional actual wire compression including decoder',
                  B3='D + actual BonusRetrieval adaptive priority + routed BonusExpansion',
                  B4='D + actual temporal priority'),
        shared_settings=settings.model_dump(mode='json'),
        resolution='not executed for any arm; would-be Answer packet proxy only, not Dynamic effective selection',
        missing_frozen_query='failed arm remains denominator; no Hybrid fallback for missing Dynamic input',
        gold='mapping read after every arm; never provided to route, expansion or packing',
        token_scope='original QueryService unique-source evidence packing; compression over actual complete messages',
        gates='No new QA F1; no semantic or cost promotion without independent evidence',
        preregistration='registered before this run; exploratory correction after replay-v1'))
    results = []
    for row in rows:
        conv, qid = row['sample_id'], row['question_id']
        bundle, mm, ss = bundles[conv], memories[conv], sources[conv]
        htrace = row['result']['trace']
        dtrace = dynamic[qid].get('result', {}).get('trace', {})
        hquery, dquery = htrace.get('retrieval'), dtrace.get('initial')
        output = dict(question_id=qid, sample_id=conv, category=row['category'], arms={})
        for arm in arms:
            tick = time.perf_counter()
            try:
                initial = hquery if arm == 'H' else dquery
                if not isinstance(initial, dict):
                    raise ValueError('frozen_query_missing')
                if initial['build_id'] != bundle.build.build_id or initial['question'] != row['question']:
                    raise ValueError('frozen_query_scope_mismatch')
                with scratch.connect() as db:
                    initial = {**initial, 'query_id': uuid.uuid4().hex}
                    db.execute('INSERT INTO candidate_queries VALUES (?,?,?)', (initial['query_id'], initial['build_id'], canonical_json(initial)))
                base = SimpleNamespace(settings=settings, database=scratch, query=lambda build_id, question: initial)
                retrieval = BonusRetrieval(base, bundle, adaptive=arm == 'B3', temporal=arm == 'B4')
                selected = retrieval.query(bundle.build.build_id, row['question'])
                expanded = BonusExpansion(expansion, bundle, retrieval, graph_depth=2 if arm == 'B1' else 0,
                                          adaptive=arm == 'B3').expand(selected['query_id'])
                ids = [i['memory']['memory_id'] for i in expanded['candidates']]
                initial_ids = [i['memory']['memory_id'] for i in selected['initial_candidates']]
                audit = answer_packet(settings, row['question'], [mm[mid] for mid in ids], ss,
                                      (htrace if arm == 'H' else dtrace).get('time', {}))
                delivered = [m['memory_id'] for m in audit['effective_memories']]
                stages = dict(initial=initial_ids, expanded=ids, delivered=delivered)
                body = dict(messages=request_messages('answer', audit['answer_input'], EvidenceAnswer))
                _, compression = encode_request(body)
                output['arms'][arm] = dict(status='succeeded', memory_ids=stages,
                    source_ids={stage: source_ids(mids, mm) for stage, mids in stages.items()},
                    sources_at_k={str(k): source_ids(ids[:k], mm) for k in (5, 10, 20)},
                    evidence_budget=audit['evidence_budget'], graph=expanded.get('m5_graph'),
                    route=selected.get('m5_route'), interval=selected.get('m5_interval'),
                    wire_compression=compression if arm == 'B2' else None,
                    parity=dict(initial=selected['initial_candidates'] == initial['initial_candidates'],
                                expansion=expanded['candidates'] == (htrace.get('expansion', {}) if arm == 'H' else dtrace.get('expanded', {})).get('candidates'),
                                delivered=delivered == [m['memory_id'] for m in htrace.get('delivered_memories', [])]) if arm == 'H' else None)
            except Exception as error:
                output['arms'][arm] = dict(status='failed', error_code=getattr(error, 'code', str(error) if isinstance(error, ValueError) else type(error).__name__),
                                           memory_ids={}, source_ids={}, sources_at_k={})
            output['arms'][arm]['wall_seconds'] = time.perf_counter() - tick
        mapping = row['result']['mapping']
        output['scorable'] = mapping['scorable']
        for arm in output['arms'].values():
            arm['recall'] = {str(k): coverage(arm['sources_at_k'].get(str(k), []), mapping) for k in (5, 10, 20)}
            arm['stage_recall'] = {stage: coverage(arm['source_ids'].get(stage, []), mapping) for stage in ('initial', 'expanded', 'delivered')}
        results.append(output)
        if len(results) % 100 == 0:
            print(dict(processed=len(results)), flush=True)
    if len(results) != 757:
        raise ValueError('denominator_changed')
    write(private/'raw-results.json', results)
    applicable = [r for r in results if r['scorable']]
    summary = dict(denominator=757, source_proxy_applicable=len(applicable), arms={}, new_answers=0,
                   new_qa_f1='not_measured', semantic_fact_recall='not_measured', provider_requests=0)
    for arm in arms:
        successful = [r['arms'][arm] for r in results if r['arms'][arm]['status'] == 'succeeded']
        summary['arms'][arm] = dict(succeeded=len(successful), failed=757-len(successful),
            failure_codes=dict(Counter(r['arms'][arm]['error_code'] for r in results if r['arms'][arm]['status'] != 'succeeded')),
            recall={str(k): float(np.mean([r['arms'][arm]['recall'][str(k)] for r in applicable])) for k in (5, 10, 20)},
            stages={stage: float(np.mean([r['arms'][arm]['stage_recall'][stage] for r in applicable])) for stage in ('initial', 'expanded', 'delivered')},
            delivered_delta_vs_D=paired([r['arms'][arm]['stage_recall']['delivered']-r['arms']['D']['stage_recall']['delivered'] for r in applicable]),
            per_conversation={c: paired([r['arms'][arm]['stage_recall']['delivered']-r['arms']['D']['stage_recall']['delivered'] for r in applicable if r['sample_id']==c]) for c in DEV},
            per_category={str(c): paired([r['arms'][arm]['stage_recall']['delivered']-r['arms']['D']['stage_recall']['delivered'] for r in applicable if r['category']==c]) for c in range(1,6)},
            graph_added=sum(len(set(a['memory_ids']['expanded'])-set(results[i]['arms']['D']['memory_ids'].get('expanded', []))) for i, a in enumerate([r['arms'][arm] for r in results]) if a['status']=='succeeded'),
            p50_seconds=float(np.quantile([r['arms'][arm]['wall_seconds'] for r in results], .5)),
            p95_seconds=float(np.quantile([r['arms'][arm]['wall_seconds'] for r in results], .95)))
    compression = [r['arms']['B2']['wire_compression'] for r in results if r['arms']['B2']['status']=='succeeded']
    summary['compression'] = dict(requests=len(compression), applied=sum(a['applied'] for a in compression),
        original_message_tokens=sum(a['original_message_tokens'] for a in compression),
        sent_message_tokens=sum(a['sent_message_tokens'] for a in compression),
        token_reduction=1-sum(a['sent_message_tokens'] for a in compression)/sum(a['original_message_tokens'] for a in compression),
        billing_savings='not_measured', answer_quality='not_measured')
    summary['hybrid_parity_errors'] = sum(not all(r['arms']['H'].get('parity', {}).values()) for r in results if r['arms']['H']['status']=='succeeded')
    summary['resources'] = dict(wall_seconds=time.perf_counter()-start, cpu_seconds=time.process_time()-cpu,
        peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        scope='offline expansion, packing, SQLite and complete-message counting; no embeddings/resolve/provider')
    write(out/'metrics-summary.json', summary)
    write(out/'per-question-metrics.json', results)
    origin.rollback()
    origin.close()
    if sha(ORIGIN) != original_sha:
        raise ValueError('original_database_changed')
    write(out/'run-manifest.json', dict(original_database_sha256=original_sha, original_unchanged=True,
        private_output=str(private), holdout_answers_read=False, provider_requests=0,
        implementation_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True, cwd=ROOT).strip(),
        implementation_sha256={str(p.relative_to(ROOT)):sha(p) for p in sorted((ROOT/'src/locomo_memory').glob('m5_*.py'))},
        script_sha256=sha(Path(__file__))))
    write(out/'sha256-manifest.json', {str(p.relative_to(out)):sha(p) for p in sorted(out.rglob('*')) if p.is_file()})
    print(json.dumps(summary['compression']))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--label', required=True)
    run(parser.parse_args().label)
