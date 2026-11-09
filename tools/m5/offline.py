"""Frozen development replay. Outputs private evidence under var/, aggregates separately.

No generation, embeddings, credentials, test answers or historical writes.
"""
import argparse
from collections import Counter
from datetime import date
import hashlib
import json
from pathlib import Path
import resource
import sqlite3
import subprocess
import time

import numpy as np

from locomo_memory.evaluation_metrics import coverage
from locomo_memory.exports import read_bundle
from locomo_memory.imports import canonical_json
from locomo_memory.m5_adaptive import route, query_interval, prioritize
from locomo_memory.m5_compression import pack, expand
from locomo_memory.m5_graph import expand_relations, graph_view
from locomo_memory.m5_review import review_candidates
from locomo_memory.retrieval import budget_tokens

ROOT = Path(__file__).resolve().parents[2]
RESEARCH = ROOT.parent / 'research-next-20261101'
ORIGIN = RESEARCH / 'var/research-v2-full-baseline-20261101/memory.sqlite3'
RUN = 'a2abe1fb49be45ccba291728e1f6b3c9'
DEV = ('conv-26', 'conv-30', 'conv-41', 'conv-42')
HOLDOUT = ('conv-43', 'conv-44')


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as handle:
        json.dump(value, handle, indent=2, ensure_ascii=False)
        handle.write('\n')
    path.chmod(0o600)


def complete_memory_budget(ids, memories, budget=24000, limit=60):
    chosen, used, omitted = [], 2, []
    # Count the actual full array after every append; no estimated short labels.
    for mid in ids:
        count = budget_tokens(canonical_json([memories[x] for x in chosen + [mid]]))
        if count > budget or len(chosen) == limit:
            omitted.append(mid)
        else:
            chosen.append(mid)
            used = count
    return chosen, dict(token_count=used, token_budget=budget, omitted_ids=omitted)


def paired(values, seed=51104):
    array = np.asarray(values, dtype=float)
    if not len(array):
        return dict(mean=None, bootstrap95=None)
    rng = np.random.default_rng(seed)
    means = np.mean(array[rng.integers(0, len(array), (2000, len(array)))], axis=1)
    return dict(mean=float(np.mean(array)), bootstrap95=np.quantile(means, [.025, .975]).tolist(),
                improved=int(sum(array > 0)), regressed=int(sum(array < 0)), unchanged=int(sum(array == 0)),
                denominator=len(array), scope='exploratory paired question bootstrap; four exposed conversations')


def run(label):
    if not label.replace('-', '').replace('_', '').isalnum():
        raise ValueError('invalid_run_label')
    target = ROOT / 'experiments/m5-development' / label
    private = ROOT / 'var/m5-development' / label
    target.mkdir(parents=True, exist_ok=False)
    private.mkdir(parents=True, exist_ok=False)
    private.chmod(0o700)
    start, cpu = time.perf_counter(), time.process_time()
    original_sha = sha(ORIGIN)
    origin = sqlite3.connect(ORIGIN.resolve().as_uri() + '?mode=ro', uri=True)
    origin.row_factory = sqlite3.Row
    origin.execute('PRAGMA query_only=ON')
    origin.execute('BEGIN')
    meta = json.loads(origin.execute('SELECT result_json FROM evaluation_runs WHERE run_id=?', (RUN,)).fetchone()[0])
    if len(meta['input']['samples']) != 757 or set(meta['pins']) != set(DEV):
        raise ValueError('frozen_run_identity_changed')
    protocol = dict(version='m5-offline-v1', original_run=RUN, denominator=757,
        development=DEV, holdout=HOLDOUT, provider_calls=0, new_answers=False,
        arms=['H:frozen_hybrid_initial', 'D:frozen_dynamic_expanded', 'B1:graph_depth2',
              'B2:lossless_grouping', 'B3:adaptive', 'B4:temporal'],
        controls='D frozen pre-resolution candidates; same seeds and complete-Memory JSON budget per arm',
        graph=dict(depth=2, max_candidates=60, token_budget=24000, semantic_edges='stored relations only'),
        compression='exact roundtrip every field; no summary, no decoder prompt or provider claim',
        route='question + frozen analysis only; no answer or annotated evidence input',
        truth='adjacent same-state-key reports, SHA order, 15/conversation, no predicted labels',
        metrics='Source proxy Recall@K over Memory ranks, not fact recall or QA; failed arm recall zero when scorable',
        promotion='No paid/production promotion without independent positive fact review and zero severe errors',
        combinations='B5/B6 withheld until independent single-arm evidence', bootstrap=dict(seed=51104, repeats=2000))
    write(target / 'protocol.json', protocol)
    bundles, builds, truths = {}, [], []
    for conv in DEV:
        raw = dict(origin.execute('SELECT * FROM build_versions WHERE build_id=?', (meta['pins'][conv],)).fetchone())
        raw['config'] = json.loads(raw.pop('config_json'))
        bundle = read_bundle(origin, raw)
        if bundle.schema_version != 'memory-export-v2':
            raise ValueError('export_contract_changed')
        bundles[conv] = bundle
        export_file = private / 'exports' / (conv + '.json')
        write(export_file, bundle.model_dump(mode='json'))
        compression = pack([m.model_dump(mode='json') for m in bundle.memories])
        assert expand(compression['package']) == [m.model_dump(mode='json') for m in bundle.memories]
        write(private / 'compression' / (conv + '.json'), compression)
        graph = graph_view(bundle)
        write(private / 'graphs' / (conv + '.json'), graph)
        truths += review_candidates(bundle, limit=15)
        builds.append(dict(sample_id=conv, build_id=bundle.build.build_id,
            fingerprint=bundle.build.fingerprint, index=bundle.index.model_dump(mode='json'),
            projection_fingerprint=bundle.projection.fingerprint, export_sha256=sha(export_file),
            memories=len(bundle.memories), sources=len(bundle.sources), relations=len(bundle.relations),
            relation_labels=dict(Counter(r.label for r in bundle.relations)),
            compression=compression['metrics'], graph_nodes=len(graph['nodes']), graph_edges=len(graph['edges'])))
    write(private / 'dynamic-review-units.json', truths)
    write(target / 'build-identities.json', builds)
    # The holdout export below touches conversation fields only; no QA or summaries.
    source_rows = []
    for conv in (*DEV, *HOLDOUT):
        turns = [dict(row) for row in origin.execute('SELECT * FROM source_turns WHERE sample_id=? ORDER BY position', (conv,))]
        if not turns:
            raise ValueError('missing_conversation_source')
        write(private / 'conversation-only' / (conv + '.json'), turns)
        source_rows.append(dict(sample_id=conv, split='development' if conv in DEV else 'holdout',
            turns=len(turns), sessions=len({s['session_id'] for s in turns}),
            source_sha256=sha(private / 'conversation-only' / (conv + '.json')),
            complete_build=meta['pins'].get(conv), qa_read=conv in DEV))
    write(target / 'dataset-split.json', source_rows)
    # Freeze predetermined ordinary/diagnostic identities before running any arm.
    samples = meta['input']['samples']
    identities = meta['input']['question_identities']
    sample_by_id = {identity['question_id']: sample for identity, sample in zip(identities, samples)}
    def qhash(qid):
        return hashlib.sha256(('m5-fixed-live-v1|' + qid).encode()).hexdigest()
    ordinary, diagnostic = [], []
    for conv in DEV:
        ids = [qid for qid, s in sample_by_id.items() if s['sample_id'] == conv and s['category'] != 5]
        chosen = sorted(ids, key=qhash)[:20]
        ordinary += chosen
        diagnostic += sorted([qid for qid in ids if qid not in chosen and sample_by_id[qid]['category'] in (1, 2)], key=qhash)[:5]
    write(target / 'fixed-live-sample.json', dict(ordinary=ordinary, diagnostic=diagnostic,
        selection='SHA256 m5-fixed-live-v1 per conversation; 20 ordinary + 5 category1/2 diagnostic; excludes overlap',
        prior_protocol='Phase7/8 samples do not define requested 80+20 design; this M5 sample is new and exploratory',
        paid_authorization=False))
    rows = origin.execute("SELECT item_json FROM evaluation_run_items WHERE run_id=? AND json_extract(item_json,'$.strategy')='hybrid_no_resolution' ORDER BY ordinal", (RUN,)).fetchall()
    dynamics = {json.loads(row[0])['question_id']: json.loads(row[0]) for row in origin.execute(
        "SELECT item_json FROM evaluation_run_items WHERE run_id=? AND json_extract(item_json,'$.strategy')='dynamic'", (RUN,))}
    results = []
    for row in rows:
        item = json.loads(row[0])
        conv, qid = item['sample_id'], item['question_id']
        bundle = bundles[conv]
        memories = {m.memory_id: m.model_dump(mode='json') for m in bundle.memories}
        trace = item['result']['trace']
        initial = trace['retrieval']
        dyn_trace = dynamics[qid].get('result', {}).get('trace', {})
        # A Dynamic failure still retains its retrieval/expansion in the denominator.
        dyn_expanded = dyn_trace.get('expanded') or dyn_trace.get('expansion')
        if dyn_expanded is None:
            dyn_expanded = trace['expansion']
            seed_origin = 'hybrid_expansion_fallback_for_missing_dynamic_artifact'
        else:
            seed_origin = 'frozen_dynamic_expansion'
        seeds = [x['memory']['memory_id'] for x in dyn_expanded['candidates']]
        question = initial['question']
        if initial['build_id'] != bundle.build.build_id or question != item['question']:
            raise ValueError('query_identity_mismatch')
        decision = route(question, initial['analysis'].get('result') or {})
        interval = query_interval(question, date.fromisoformat(bundle.projection.cutoff[:10]))
        arm_outputs = {}
        d_ids, d_budget = complete_memory_budget(seeds, memories)
        h_ids, h_budget = complete_memory_budget([x['memory']['memory_id'] for x in initial['initial_candidates']], memories)
        for name in ('H', 'D', 'B1', 'B2', 'B3', 'B4'):
            tick = time.perf_counter()
            try:
                extra = {}
                ids = h_ids if name == 'H' else d_ids
                if name == 'B1':
                    graph = expand_relations(bundle, d_ids, depth=2, token_budget=24000)
                    ids = graph['memory_ids']
                    extra['paths'] = graph['paths']
                    extra['graph_omitted_ids'] = graph['omitted_ids']
                elif name == 'B2':
                    compressed = pack([memories[mid] for mid in d_ids])
                    assert expand(compressed['package']) == [memories[mid] for mid in d_ids]
                    extra['compression'] = compressed['metrics']
                elif name == 'B3':
                    ids = prioritize(d_ids, memories, decision, interval)
                    if decision['graph_depth']:
                        graph = expand_relations(bundle, ids, depth=decision['graph_depth'], token_budget=24000)
                        ids = graph['memory_ids']
                        extra['paths'] = graph['paths']
                    extra['route'] = decision
                elif name == 'B4':
                    ids = prioritize(d_ids, memories, {'entities': []}, interval)
                    extra['interval'] = interval
                if not set(ids) <= memories.keys():
                    raise ValueError('out_of_scope_memory')
                arm_outputs[name] = dict(status='succeeded', memory_ids=ids,
                    sources={str(k): sorted({sid for mid in ids[:k] for sid in memories[mid]['source_ids']}) for k in (5, 10, 20)},
                    token_count=budget_tokens(canonical_json([memories[mid] for mid in ids])),
                    **extra)
            except Exception as error:
                arm_outputs[name] = dict(status='failed', error_code=getattr(error, 'code', type(error).__name__), memory_ids=[])
            arm_outputs[name]['wall_seconds'] = time.perf_counter() - tick
        # Gold enters only after all arm decisions are frozen in memory.
        mapping = item['result']['mapping']
        for arm in arm_outputs.values():
            arm['source_recall'] = {str(k): coverage(arm.get('sources', {}).get(str(k), []), mapping) for k in (5, 10, 20)}
        results.append(dict(question_id=qid, sample_id=conv, category=item['category'],
            historical_status=item['status'], dynamic_historical_status=dynamics[qid]['status'],
            seed_origin=seed_origin, scorable=mapping['scorable'], arms=arm_outputs,
            original_dynamic_seed_ids=seeds, shared_budget_omitted=d_budget['omitted_ids']))
        if len(results) % 100 == 0:
            print(dict(processed=len(results)), flush=True)
    if len(results) != 757 or len({r['question_id'] for r in results}) != 757:
        raise ValueError('denominator_changed')
    write(private / 'raw-results.json', results)
    summary = dict(denominator=757, source_proxy_applicable=sum(r['scorable'] for r in results),
                   arms={}, new_qa_f1='not_measured', fact_recall='not_measured', answer_support='not_measured',
                   dynamic_accuracy='not_measured', provider_requests=0, provider_cost_cny=0,
                   historical_baseline=dict(full_text=.464869, vector=.519714, hybrid=.521886, dynamic=.515133))
    for name in ('H', 'D', 'B1', 'B2', 'B3', 'B4'):
        applicable = [r for r in results if r['scorable']]
        latency = [r['arms'][name]['wall_seconds'] for r in results]
        metrics = dict(successes=sum(r['arms'][name]['status'] == 'succeeded' for r in results),
            failures=dict(Counter(r['arms'][name]['error_code'] for r in results if r['arms'][name]['status'] != 'succeeded')),
            recall={str(k): float(np.mean([r['arms'][name]['source_recall'][str(k)] for r in applicable])) for k in (5, 10, 20)},
            p50_seconds=float(np.quantile(latency, .5)), p95_seconds=float(np.quantile(latency, .95)),
            paired_vs_D={str(k): paired([r['arms'][name]['source_recall'][str(k)] - r['arms']['D']['source_recall'][str(k)] for r in applicable]) for k in (5, 10, 20)},
            per_conversation={c: {str(k): paired([r['arms'][name]['source_recall'][str(k)] - r['arms']['D']['source_recall'][str(k)] for r in applicable if r['sample_id'] == c]) for k in (5, 10, 20)} for c in DEV},
            per_category={str(c): {str(k): paired([r['arms'][name]['source_recall'][str(k)] - r['arms']['D']['source_recall'][str(k)] for r in applicable if r['category'] == c]) for k in (5, 10, 20)} for c in range(1, 6)})
        summary['arms'][name] = metrics
    compression_metrics = [r['arms']['B2']['compression'] for r in results if r['arms']['B2']['status'] == 'succeeded']
    summary['compression'] = dict(roundtrips=len(compression_metrics),
        original_tokens=sum(m['original_tokens'] for m in compression_metrics),
        packed_tokens=sum(m['packed_tokens'] for m in compression_metrics),
        token_reduction=1 - sum(m['packed_tokens'] for m in compression_metrics) / sum(m['original_tokens'] for m in compression_metrics),
        decoded_memory_coverage=1, atomic_fact_retention='not_measured')
    summary['dynamic_review'] = dict(units=len(truths), independent_reviews=0, accuracy='not_measured',
        per_conversation=dict(Counter(t['sample_id'] for t in truths)), predicted_labels_hidden=True)
    summary['resources'] = dict(wall_seconds=time.perf_counter() - start, cpu_seconds=time.process_time() - cpu,
        peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss, gpu_used=False,
        latency_scope='local candidate transformation only, excludes provider and full pipeline')
    write(target / 'metrics-summary.json', summary)
    # IDs, ranks and metrics only; raw source text stays in the private directory.
    write(target / 'per-question-metrics.json', results)
    origin.rollback()
    origin.close()
    if sha(ORIGIN) != original_sha:
        raise ValueError('original_database_changed')
    write(target / 'source-manifest.json', dict(database=str(ORIGIN), sha256=original_sha,
        original_unchanged=True, implementation_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        dirty_files=subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True).splitlines(),
        implementation_sha256={str(p.relative_to(ROOT)): sha(p) for p in sorted((ROOT/'src/locomo_memory').glob('m5_*.py'))},
        runtime_private=str(private), complete_exports=4, holdout_qa_read=False))
    write(target / 'cost-ledger.json', dict(authorized_paid_budget_cny=0, physical_provider_requests=0,
        known_provider_cost_cny=0, unknown_provider_cost_cny=0, scope='offline only; local resource prices not_measured'))
    write(target / 'sha256-manifest.json', {str(p.relative_to(target)): sha(p) for p in sorted(target.rglob('*')) if p.is_file()})
    print(json.dumps(dict(output=str(target), private=str(private), denominator=757, provider_requests=0)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--label', required=True)
    run(parser.parse_args().label)
