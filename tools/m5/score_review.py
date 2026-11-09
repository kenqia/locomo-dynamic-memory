"""Score independently frozen relation references against frozen Build predictions."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

from locomo_memory.export_schemas import MemoryExport
from locomo_memory.m5_review import score_relations
from tools.m5.offline import ROOT, write, sha


def run(paths, label):
    units_path = ROOT/'var/m5-development/replay-v1/dynamic-review-units.json'
    units = json.loads(units_path.read_text())
    references = [ref for path in paths for ref in json.loads(path.read_text())]
    if len(references) != len(units) or {r['unit_id'] for r in references} != {u['unit_id'] for u in units}:
        raise ValueError('review_denominator_not_complete')
    # Freeze review identities before consulting stored model predictions.
    freeze = dict(units_sha256=sha(units_path), reviews={str(p):sha(p) for p in paths},
                  protocol='m5-dynamic-review-v1', independent_ai=True)
    out = ROOT/'experiments/m5-development'/label
    private = ROOT/'var/m5-development'/label
    out.mkdir(parents=True,exist_ok=False)
    private.mkdir(parents=True,exist_ok=False)
    write(out/'reference-freeze.json', freeze)
    by_build = {}
    for path in (ROOT/'var/m5-development/replay-v1/exports').glob('*.json'):
        bundle = MemoryExport.model_validate_json(path.read_text())
        by_build[bundle.build.build_id] = {(r.old_memory_id,r.new_memory_id):r for r in bundle.relations}
    predictions = []
    for unit in units:
        pair = (unit['old_memory']['memory_id'],unit['new_memory']['memory_id'])
        relation = by_build[unit['build_id']].get(pair)
        predictions.append(dict(unit_id=unit['unit_id'],label=relation.label if relation else None,
                                effective_ids=None,relation_id=relation.relation_id if relation else None))
    metrics = score_relations(units,references,predictions)
    metrics.update(query_specific_effective_accuracy='not_measured',
        pair_local_effective_accuracy='not_measured',
        effective_limitation='Frozen global projection is not a pair-local or query-specific prediction; no invented comparison',
        scope='60 prediction-blind state pairs; independent AI reference, not human or course truth',
        per_conversation={conv:score_relations([u for u in units if u['sample_id']==conv],
            [r for r in references if r['unit_id'] in {u['unit_id'] for u in units if u['sample_id']==conv}],
            [p for p in predictions if p['unit_id'] in {u['unit_id'] for u in units if u['sample_id']==conv}])
            for conv in sorted({u['sample_id'] for u in units})})
    write(private/'references.json',references)
    write(private/'predictions.json',predictions)
    write(out/'metrics-summary.json',metrics)
    by_ref = {r['unit_id']:r for r in references}
    write(out/'per-unit-results.json',[dict(unit_id=p['unit_id'], predicted=p['label'],
          reference=by_ref[p['unit_id']]['label'],correct=p['label']==by_ref[p['unit_id']]['label'],
          uncertain=by_ref[p['unit_id']].get('uncertain',False)) for p in predictions])
    print(json.dumps(metrics))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--review',type=Path,action='append',required=True)
    parser.add_argument('--label',required=True)
    args=parser.parse_args()
    run(args.review,args.label)
