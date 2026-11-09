"""Prepare prediction-blind query applicability review from frozen dev traces."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sqlite3

from locomo_memory.export_schemas import MemoryExport
from locomo_memory.m5_query_review import score_query_applicability
from tools.m5.offline import DEV, ORIGIN, ROOT, RUN, sha, write

SEED = 'm5-query-applicability-v1'


def select(items, per_conversation=10):
    """Select by identity only, including failed items; no prediction/QA filters."""
    if len({x['question_id'] for x in items}) != len(items):
        raise ValueError('duplicate_question_identity')
    if set(x['sample_id'] for x in items) != set(DEV):
        raise ValueError('query_review_development_scope_required')
    chosen = []
    for conv in DEV:
        candidates = [x for x in items if x['sample_id'] == conv]
        if len(candidates) < per_conversation:
            raise ValueError('insufficient_query_review_candidates')
        chosen += sorted(candidates, key=lambda x: hashlib.sha256(
            (SEED+'|'+x['question_id']).encode()).hexdigest())[:per_conversation]
    return chosen


def prepare(label):
    if not label.replace('-', '').isalnum():
        raise ValueError('invalid_query_review_label')
    before = sha(ORIGIN)
    with sqlite3.connect(ORIGIN.resolve().as_uri()+'?mode=ro', uri=True) as db:
        items = [json.loads(row[0]) for row in db.execute(
            "SELECT item_json FROM evaluation_run_items WHERE run_id=? AND json_extract(item_json,'$.strategy')='dynamic' ORDER BY ordinal",
            (RUN,))]
    if len(items) != 757:
        raise ValueError('frozen_query_denominator_changed')
    selected = select(items)
    # Freeze identity-only selection before loading any reference or prediction.
    public = ROOT/'experiments/m5-development'/label
    private = ROOT/'var/m5-development'/label
    public.mkdir(parents=True, exist_ok=False)
    private.mkdir(parents=True, exist_ok=False)
    private.chmod(0o700)
    identities = [dict(question_id=x['question_id'], sample_id=x['sample_id']) for x in selected]
    write(public/'selection-freeze.json', dict(seed=SEED, per_conversation=10,
        planned=40, items=identities, source_run=RUN, source_database_sha256=before,
        selection_basis='question identity only; no category/status/answer/prediction filtering'))
    bundles = {conv: MemoryExport.model_validate_json(
        (ROOT/'var/m5-development/replay-v1/exports'/f'{conv}.json').read_text()) for conv in DEV}
    units, predictions = [], []
    for item in selected:
        conv = item['sample_id']
        bundle = bundles[conv]
        trace = item.get('result', {}).get('trace') or {}
        candidates = trace.get('expanded', {}).get('candidates', [])
        # The ordinary Dynamic controller preserves complete expanded input.
        memories = [c['memory'] for c in candidates]
        mids = [m['memory_id'] for m in memories]
        if len(set(mids)) != len(mids):
            raise ValueError('duplicate_query_review_memory')
        if trace.get('build_id') != bundle.build.build_id:
            raise ValueError('query_review_build_mismatch')
        known = {m.memory_id: m.model_dump(mode='json') for m in bundle.memories}
        if any(m != known.get(m['memory_id']) for m in memories):
            raise ValueError('query_review_memory_export_mismatch')
        source_ids = {sid for m in memories for sid in m['source_ids']}
        sources = {s.source_id:s.model_dump(mode='json') for s in bundle.sources if s.source_id in source_ids}
        if set(sources) != source_ids:
            raise ValueError('query_review_source_scope_missing')
        uid = hashlib.sha256((SEED+'|'+item['question_id']).encode()).hexdigest()
        units.append(dict(unit_id=uid, question_id=item['question_id'], sample_id=conv,
            build_id=bundle.build.build_id, question=item['question'], time=trace.get('time'),
            memories=memories, sources=sources, reference=None, reviewer=None,
            scope='Applicability among saved expanded candidates only; assess source contradictions and missing coverage explicitly. No global recall claim.'))
        resolution = trace.get('resolution')
        predictions.append(dict(unit_id=uid, trace_id=trace.get('trace_id'),
            effective_ids=resolution['effective_memory_ids'] if resolution else None,
            status=resolution['status'] if resolution else None,
            item_status=item['status'], trace_outcome=trace.get('outcome'),
            answer_delivery_ids=[m['memory_id'] for m in trace.get('effective_memories', [])]
                if 'effective_memories' in trace else None))
    write(private/'review-units.json', units)
    write(private/'historical-predictions.json', predictions)
    assert sha(ORIGIN) == before
    summary = dict(status='prepared_not_reviewed', planned=40, original_query_denominator=757,
        existing_resolution_predictions=sum(p['effective_ids'] is not None for p in predictions),
        missing_resolution_predictions=sum(p['effective_ids'] is None for p in predictions),
        historical_item_statuses=dict(Counter(p['item_status'] for p in predictions)),
        per_conversation={c:sum(u['sample_id']==c for u in units) for c in DEV},
        units_sha256=sha(private/'review-units.json'), predictions_sha256=sha(private/'historical-predictions.json'),
        provider_requests=0, source_database_unchanged=True, holdout_qa_read=False,
        metric='not_measured; independent references absent',
        reviewer_packet_excludes=['stored relations','resolver choices','generated answer','QA answer/evidence','item success/failure'],
        limitation='Historical Dynamic applicability audit, not new M5 QA or a temporal-stratified benchmark')
    write(public/'preparation-summary.json', summary)
    print(json.dumps(summary))


def score(label, paths):
    if not label.replace('-', '').isalnum():
        raise ValueError('invalid_query_review_label')
    private = ROOT/'var/m5-development'/label
    public = ROOT/'experiments/m5-development'/label
    summary = json.loads((public/'preparation-summary.json').read_text())
    unit_path = private/'review-units.json'
    pred_path = private/'historical-predictions.json'
    if sha(unit_path) != summary['units_sha256'] or sha(pred_path) != summary['predictions_sha256']:
        raise ValueError('query_review_prepared_artifacts_changed')
    units = json.loads(unit_path.read_text())
    refs = [r for path in paths for r in json.loads(path.read_text())]
    if len(refs) != len(units) or {r['unit_id'] for r in refs} != {u['unit_id'] for u in units}:
        raise ValueError('query_review_references_incomplete')
    # Validate independent reference evidence before opening frozen predictions.
    score_query_applicability(units, refs, [])
    write(public/'reference-freeze.json', dict(units_sha256=sha(unit_path),
        predictions_sha256=sha(pred_path), references={str(p):sha(p) for p in paths},
        protocol=SEED, scope='Independent AI references; not human or teacher truth'))
    predictions = json.loads(pred_path.read_text())
    result = score_query_applicability(units, refs, predictions)
    per_unit = result.pop('per_unit')
    result.update(source_run=RUN, new_provider_requests=0, new_qa_f1='not_measured',
        per_conversation={conv:{k:v for k,v in score_query_applicability(
            [u for u in units if u['sample_id']==conv],
            [r for r in refs if r['unit_id'] in {u['unit_id'] for u in units if u['sample_id']==conv}],
            [p for p in predictions if p['unit_id'] in {u['unit_id'] for u in units if u['sample_id']==conv}]).items()
            if k != 'per_unit'} for conv in DEV})
    write(public/'per-unit-results.json', per_unit)
    write(public/'metrics-summary.json', result)
    print(json.dumps(result))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label', required=True)
    parser.add_argument('--review', type=Path, action='append')
    args = parser.parse_args()
    score(args.label, args.review) if args.review else prepare(args.label)
