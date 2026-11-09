"""Score independently reviewed query-specific candidate applicability."""

STATUSES = ('sufficient', 'insufficient', 'conflict')


def score_query_applicability(units, references, predictions):
    by_id = {u['unit_id']:u for u in units}
    if len(by_id) != len(units):
        raise ValueError('duplicate_query_review_unit')
    refs, preds = {}, {}
    for reference in references:
        uid = reference['unit_id']
        if uid not in by_id or uid in refs:
            raise ValueError('invalid_query_reference_identity')
        if (reference.get('review_kind') not in ('human_independent', 'ai_assisted_independent')
                or reference.get('independent_of_implementation') is not True
                or not reference.get('reviewer') or not reference.get('provenance')
                or not reference.get('rationale') or type(reference.get('uncertain')) is not bool
                or type(reference.get('unresolvable', False)) is not bool):
            raise ValueError('independent_query_reference_required')
        unit = by_id[uid]
        memories = {m['memory_id']:m for m in unit['memories']}
        selected = reference.get('effective_ids')
        if (not isinstance(selected, list) or len(set(selected)) != len(selected)
                or not set(selected) <= memories.keys() or reference.get('status') not in STATUSES):
            raise ValueError('invalid_query_reference_selection')
        if reference['status'] in ('sufficient', 'conflict') and not selected:
            raise ValueError('nonempty_query_reference_required')
        evidence = reference.get('support_quotes')
        if not evidence:
            raise ValueError('query_reference_quotes_required')
        cited = set()
        for quote in evidence:
            source = unit['sources'].get(quote.get('source_id'))
            if not source or not quote.get('quote') or quote['quote'] not in source['text']:
                raise ValueError('query_reference_verbatim_support_required')
            cited.add(quote['source_id'])
        if any(not cited.intersection(memories[mid]['source_ids']) for mid in selected):
            raise ValueError('selected_query_reference_support_required')
        refs[uid] = reference
    for prediction in predictions:
        uid = prediction['unit_id']
        if uid not in by_id or uid in preds:
            raise ValueError('invalid_query_prediction_identity')
        selected = prediction.get('effective_ids')
        ids = {m['memory_id'] for m in by_id[uid]['memories']}
        if selected is not None and (not isinstance(selected, list)
                or len(set(selected)) != len(selected) or not set(selected) <= ids
                or prediction.get('status') not in STATUSES):
            raise ValueError('invalid_query_prediction_selection')
        preds[uid] = prediction
    judged = {uid:r for uid,r in refs.items() if not r['uncertain'] and not r.get('unresolvable', False)}
    measured = any(p.get('effective_ids') is not None for p in preds.values())
    rows = []
    for uid, ref in judged.items():
        p = preds.get(uid, {})
        present = p.get('effective_ids') is not None
        expected, actual = set(ref['effective_ids']), set(p.get('effective_ids') or [])
        rows.append(dict(unit_id=uid, prediction_present=present,
            exact_match=present and expected==actual,
            set_f1=(2*len(expected & actual)/(len(expected)+len(actual))
                    if expected or actual else 1.0) if present else 0.0,
            status_correct=present and p.get('status')==ref['status']))
    n = len(rows)
    return dict(planned=len(units), reviewed=len(refs), scorable=n,
        uncertain_or_unresolvable=len(refs)-n, unreviewed=len(units)-len(refs),
        effective_selection_exact_accuracy=sum(r['exact_match'] for r in rows)/n if measured and n else 'not_measured',
        effective_selection_macro_set_f1=sum(r['set_f1'] for r in rows)/n if measured and n else 'not_measured',
        status_accuracy=sum(r['status_correct'] for r in rows)/n if measured and n else 'not_measured',
        missing_predictions=sum(not r['prediction_present'] for r in rows),
        per_unit=rows, reference_kinds=sorted({r['review_kind'] for r in refs.values()}),
        scope='Query-specific applicability among supplied candidates; no global recall or QA quality claim')
