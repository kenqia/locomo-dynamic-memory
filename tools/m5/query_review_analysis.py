"""Derive compact, text-free differences from frozen applicability review."""
import argparse
from collections import Counter
import json
import math
from pathlib import Path

from tools.m5.offline import ROOT, sha, write


def run(label, output):
    if not label.replace('-', '').isalnum():
        raise ValueError('invalid_query_review_label')
    base = ROOT/'experiments/m5-development'/label
    private = ROOT/'var/m5-development'/label
    frozen = json.loads((base/'reference-freeze.json').read_text())
    paths = [Path(p) for p in frozen['references']]
    if any(sha(p) != frozen['references'][str(p)] for p in paths):
        raise ValueError('query_review_reference_changed')
    units = json.loads((private/'review-units.json').read_text())
    refs = {r['unit_id']:r for p in paths for r in json.loads(p.read_text())}
    preds = {r['unit_id']:r for r in json.loads((private/'historical-predictions.json').read_text())}
    results = {r['unit_id']:r for r in json.loads((base/'per-unit-results.json').read_text())}
    rows = []
    for unit in units:
        uid = unit['unit_id']
        ref, pred, result = refs[uid], preds[uid], results.get(uid)
        expected, actual = set(ref['effective_ids']), set(pred.get('effective_ids') or [])
        rows.append(dict(unit_id=uid, question_id=unit['question_id'], sample_id=unit['sample_id'],
            scorable=result is not None, uncertain=ref['uncertain'], unresolvable=ref['unresolvable'],
            reference_status=ref['status'], predicted_status=pred['status'],
            prediction_present=pred['effective_ids'] is not None,
            reference_ids=sorted(expected), predicted_ids=sorted(actual) if pred['effective_ids'] is not None else None,
            reference_only_ids=sorted(expected-actual), prediction_only_ids=sorted(actual-expected),
            exact_match=result['exact_match'] if result else None,
            difference_kind=('not_scorable' if result is None else 'missing_prediction' if not result['prediction_present']
                else 'exact' if result['exact_match'] else 'subset' if actual < expected
                else 'superset' if expected < actual else 'mixed')))
    output.mkdir(parents=True, exist_ok=False)
    write(output/'case-differences.json', rows)
    k, n = sum(r['exact_match'] is True for r in rows), len(results)
    if not n:
        raise ValueError('no_scorable_query_review')
    z, p = 1.959963984540054, k/n
    center = (p+z*z/(2*n))/(1+z*z/n)
    half = z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/(1+z*z/n)
    write(output/'diagnostic-summary.json', dict(
        reference_status_counts=dict(Counter(r['status'] for r in refs.values())),
        reference_reviewed=len(refs), reference_scorable=n, reference_coverage=n/len(units),
        difference_counts=dict(Counter(r['difference_kind'] for r in rows)),
        strict_exact_successes=k, strict_exact_denominator=n,
        strict_exact_wilson95=[center-half,center+half],
        interval_limitation='Small candidate-conditional AI-reference diagnostic; interval ignores conversation clustering and reference ambiguity',
        historical_missing_predictions_total=sum(p['effective_ids'] is None for p in preds.values()),
        historical_missing_predictions_scorable=sum(not r['prediction_present'] for r in rows if r['scorable']),
        independent_review_files={p.name:sha(p) for p in paths}, provider_requests=0))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    run(args.label, args.output.resolve())
