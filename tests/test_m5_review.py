import pytest

from locomo_memory.m5_review import score_relations


def test_dynamic_truth_requires_independent_verbatim_review_and_keeps_failures():
    units = [dict(unit_id='one', old_memory={'memory_id': 'a', 'source_ids': ['s']}, new_memory={'memory_id': 'b', 'source_ids': ['s']},
                  sources={'s': {'text': 'I changed jobs.'}}),
             dict(unit_id='two', old_memory={'memory_id': 'c', 'source_ids': ['s']}, new_memory={'memory_id': 'd', 'source_ids': ['s']},
                  sources={'s': {'text': 'I still work here.'}})]
    assert score_relations(units, [], [])['relation_accuracy'] == 'not_measured'
    base = dict(reviewer='independent AI reviewer', provenance='frozen review packet',
                review_kind='ai_assisted_independent', independent_of_implementation=True,
                support_quotes=[{'source_id': 's', 'quote': 'I changed jobs.'}])
    refs = [{**base, 'unit_id': 'one', 'label': 'SUPERSEDE', 'effective_ids': ['b']},
            {**base, 'unit_id': 'two', 'label': 'RETAIN', 'effective_ids': ['c', 'd'],
             'support_quotes': [{'source_id': 's', 'quote': 'I still work here.'}]}]
    score = score_relations(units, refs, [{'unit_id': 'one', 'label': 'SUPERSEDE', 'effective_ids': ['b']}])
    assert score['relation_accuracy'] == score['effective_selection_accuracy'] == 0.5
    assert score['missing_predictions'] == 1
    relation_only = score_relations(units, refs, [{'unit_id': 'one', 'label': 'SUPERSEDE', 'effective_ids': None}])
    assert relation_only['effective_selection_accuracy'] == 'not_measured'
    assert relation_only['effective_denominator'] == 0
    with pytest.raises(ValueError):
        score_relations(units, [{**refs[0], 'independent_of_implementation': False}], [])
    with pytest.raises(ValueError):
        score_relations(units, [{**refs[0], 'support_quotes': [{'source_id': 's', 'quote': 'invented'}]}], [])
