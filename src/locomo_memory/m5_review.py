"""Prediction-blind review selection and explicit independent-reference scoring."""
from collections import defaultdict
import hashlib

LABELS = ('RETAIN', 'UPDATE', 'SUPERSEDE', 'CONFLICT', 'undetermined')


def review_candidates(bundle, *, limit=60, seed='m5-dynamic-review-v1'):
    """Sample adjacent state reports without consulting relation predictions or QA."""
    sources = {s.source_id: s.model_dump(mode='json') for s in bundle.sources}
    groups = defaultdict(list)
    for memory in bundle.memories:
        if memory.memory_type == 'state':
            groups[memory.state_key].append(memory)
    pairs = []
    for key, memories in sorted(groups.items()):
        ordered = sorted(memories, key=lambda m: (min(sources[s]['position'] for s in m.source_ids), m.memory_id))
        for old, new in zip(ordered, ordered[1:]):
            identity = '|'.join((seed, bundle.build.build_id, old.memory_id, new.memory_id))
            pairs.append(dict(unit_id=hashlib.sha256(identity.encode()).hexdigest(),
                build_id=bundle.build.build_id, sample_id=bundle.build.sample_id,
                entity_id=old.entity_id, state_dimension=old.state_dimension,
                old_memory=old.model_dump(mode='json'), new_memory=new.model_dump(mode='json'),
                sources={sid: sources[sid] for sid in sorted(set(old.source_ids + new.source_ids))},
                reference=None, reviewer=None, provenance=None, review_status='unreviewed'))
    return sorted(pairs, key=lambda p: p['unit_id'])[:limit]


def score_relations(units, references, predictions):
    """Missing predictions remain in the denominator. Reject self-labelled gold."""
    by_id = {unit['unit_id']: unit for unit in units}
    if len(by_id) != len(units):
        raise ValueError('duplicate_review_unit')
    refs = {}
    for ref in references:
        uid = ref['unit_id']
        if uid not in by_id or uid in refs or ref.get('label') not in LABELS:
            raise ValueError('invalid_reference_identity_or_label')
        if (not ref.get('reviewer') or not ref.get('provenance') or
                ref.get('review_kind') not in ('human_independent', 'ai_assisted_independent') or
                not ref.get('independent_of_implementation') or not ref.get('support_quotes')):
            raise ValueError('independent_reference_provenance_required')
        unit = by_id[uid]
        for evidence in ref['support_quotes']:
            source = unit['sources'].get(evidence.get('source_id'))
            if not source or not evidence.get('quote') or evidence['quote'] not in source['text']:
                raise ValueError('verbatim_reference_support_required')
        cited = {e['source_id'] for e in ref['support_quotes']}
        if any(not cited.intersection(unit[endpoint]['source_ids']) for endpoint in ('old_memory', 'new_memory')):
            raise ValueError('both_reference_endpoints_required')
        endpoint_ids = {unit['old_memory']['memory_id'], unit['new_memory']['memory_id']}
        if ref.get('effective_ids') is not None and not set(ref['effective_ids']) <= endpoint_ids:
            raise ValueError('effective_reference_out_of_scope')
        refs[uid] = ref
    if not refs:
        return dict(relation_accuracy='not_measured', macro_f1='not_measured',
                    effective_selection_accuracy='not_measured', reviewed=0, planned=len(units))
    predictions_by_id = {}
    for prediction in predictions:
        uid = prediction['unit_id']
        if uid not in by_id or uid in predictions_by_id:
            raise ValueError('invalid_prediction_identity')
        if prediction.get('label') not in (*LABELS, None):
            raise ValueError('invalid_prediction_label')
        effective_ids = prediction.get('effective_ids')
        endpoint_ids = {by_id[uid]['old_memory']['memory_id'], by_id[uid]['new_memory']['memory_id']}
        if effective_ids is not None and (len(set(effective_ids)) != len(effective_ids)
                                          or not set(effective_ids) <= endpoint_ids):
            raise ValueError('effective_prediction_out_of_scope')
        predictions_by_id[uid] = prediction
    judged = {uid: ref for uid, ref in refs.items() if not ref.get('uncertain') and not ref.get('unresolvable')}
    # Unresolvable contradictions may still have the determinate relation CONFLICT;
    # reviewers should reserve unresolvable=True for unscoreable reference labels.
    if not judged:
        return dict(relation_accuracy='not_measured', macro_f1='not_measured',
                    effective_selection_accuracy='not_measured', reviewed=len(refs), planned=len(units))
    correct = sum(predictions_by_id.get(uid, {}).get('label') == ref['label'] for uid, ref in judged.items())
    class_scores = {}
    for label in LABELS:
        tp = sum(ref['label'] == label and predictions_by_id.get(uid, {}).get('label') == label for uid, ref in judged.items())
        fp = sum(ref['label'] != label and predictions_by_id.get(uid, {}).get('label') == label for uid, ref in judged.items())
        fn = sum(ref['label'] == label and predictions_by_id.get(uid, {}).get('label') != label for uid, ref in judged.items())
        class_scores[label] = 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else None
    # An absent prediction counts as failure when this task is being measured.
    # When every prediction explicitly omits effective_ids, the task was not run.
    effective_measured = any(p.get('effective_ids') is not None for p in predictions_by_id.values())
    effective = [(uid in predictions_by_id and predictions_by_id[uid].get('effective_ids') is not None
                  and set(predictions_by_id[uid]['effective_ids']) == set(ref['effective_ids']))
                 for uid, ref in judged.items() if effective_measured and ref.get('effective_ids') is not None]
    return dict(relation_accuracy=correct / len(judged),
        macro_f1=sum(v for v in class_scores.values() if v is not None) / sum(v is not None for v in class_scores.values()),
        per_class_f1=class_scores, label_coverage={l: sum(r['label'] == l for r in judged.values()) for l in LABELS},
        effective_selection_accuracy=sum(effective) / len(effective) if effective else 'not_measured',
        effective_denominator=len(effective), reviewed=len(refs), scorable=len(judged), planned=len(units),
        missing_predictions=sum(uid not in predictions_by_id for uid in judged),
        undetermined_rate=sum(predictions_by_id.get(uid, {}).get('label') in (None, 'undetermined') for uid in judged) / len(judged),
        reference_kinds=sorted({r['review_kind'] for r in refs.values()}))
