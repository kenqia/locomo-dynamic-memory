from copy import deepcopy

import pytest

from locomo_memory.m5_query_review import score_query_applicability


@pytest.fixture
def reviewed():
    units = [dict(unit_id=uid, memories=[dict(memory_id=m, source_ids=[m]) for m in ['a','b']],
                  sources={'a':{'text':'I planned a trip.'}, 'b':{'text':'I cancelled the trip.'}})
             for uid in ['one','two']]
    refs = [dict(unit_id=u['unit_id'], status='sufficient', effective_ids=['a','b'],
        reviewer='Independent synthetic reviewer', review_kind='ai_assisted_independent',
        independent_of_implementation=True, provenance='Synthetic test, no system choices',
        rationale='Question needs original plan and cancellation', uncertain=False,
        support_quotes=[dict(source_id='a',quote='I planned a trip.'),
                        dict(source_id='b',quote='I cancelled the trip.')]) for u in units]
    return units, refs


def test_query_specific_scoring_keeps_missing_predictions_and_set_errors(reviewed):
    units, refs = reviewed
    result = score_query_applicability(units, refs,
        [dict(unit_id='one', status='sufficient', effective_ids=['a','b'])])
    assert result['scorable'] == 2
    assert result['effective_selection_exact_accuracy'] == .5
    assert result['effective_selection_macro_set_f1'] == .5
    assert result['missing_predictions'] == 1
    partial = score_query_applicability(units, refs,
        [dict(unit_id='one', status='sufficient', effective_ids=['a'])])
    assert partial['effective_selection_exact_accuracy'] == 0
    assert partial['effective_selection_macro_set_f1'] == pytest.approx(1/3)
    assert score_query_applicability(units, refs, [])['effective_selection_exact_accuracy'] == 'not_measured'


def test_empty_effective_set_is_measured_and_uncertain_is_separate(reviewed):
    units, refs = reviewed
    refs[0].update(status='insufficient', effective_ids=[])
    refs[1]['uncertain'] = True
    result = score_query_applicability(units, refs,
        [dict(unit_id='one', status='insufficient', effective_ids=[])])
    assert result['effective_selection_exact_accuracy'] == 1
    assert result['effective_selection_macro_set_f1'] == 1
    assert result['uncertain_or_unresolvable'] == 1
    assert result['scorable'] == 1


@pytest.mark.parametrize('change', ['self_label','invented_quote','missing_endpoint','duplicate','out_of_scope', 'string_uncertainty'])
def test_query_review_rejects_unverifiable_reference(reviewed, change):
    units, refs = deepcopy(reviewed)
    if change == 'self_label': refs[0]['independent_of_implementation'] = False
    if change == 'invented_quote': refs[0]['support_quotes'][0]['quote'] = 'Invented'
    if change == 'missing_endpoint': refs[0]['support_quotes'] = refs[0]['support_quotes'][:1]
    if change == 'duplicate': refs.append(refs[0])
    if change == 'out_of_scope': refs[0]['effective_ids'] = ['unknown']
    if change == 'string_uncertainty': refs[0]['uncertain'] = 'false'
    with pytest.raises(ValueError):
        score_query_applicability(units, refs, [])


def test_query_review_prediction_scope_is_validated(reviewed):
    units, refs = reviewed
    with pytest.raises(ValueError, match='prediction_selection'):
        score_query_applicability(units, refs,
            [dict(unit_id='one', status='sufficient', effective_ids=['foreign'])])


def test_selection_ignores_prediction_status_and_order():
    from pathlib import Path
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from tools.m5.query_review import select
    items = [dict(question_id=f'{conv}:{i}', sample_id=conv, status='failed')
             for conv in ['conv-26','conv-30','conv-41','conv-42'] for i in range(12)]
    chosen = select(items)
    modified = [dict(x, status='succeeded', resolution={'effective_memory_ids':['fake']}) for x in reversed(items)]
    assert [x['question_id'] for x in chosen] == [x['question_id'] for x in select(modified)]
    assert len(chosen) == 40
