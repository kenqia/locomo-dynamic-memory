from datetime import date

from locomo_memory.m5_adaptive import route, query_interval, prioritize


def test_routes_explain_actual_channels_without_gold():
    assert route('What is her status now?')['graph_depth'] == 1
    assert route('What did both friends do together?')['graph_depth'] == 2
    assert route('When did she move?')['kind'] == 'temporal'
    assert route('What does Alex do?', {'entities': ['Alex']})['kind'] == 'entity'
    assert route('Favorite food?')['channels'] == ['bm25', 'dense', 'rrf']


def test_intervals_anchor_to_conversation_and_keep_unknown():
    cutoff = date(2023, 10, 22)
    assert query_interval('What happened yesterday?', cutoff)['start'] == '2023-10-21'
    interval = query_interval('What happened last week?', cutoff)
    assert (interval['start'], interval['end']) == ('2023-10-09', '2023-10-15')
    assert query_interval('In the old days?', cutoff)['start'] is None
    assert query_interval('Between 2023-01-01 and 2023-02-01?', cutoff)['start'] is None


def test_priority_preserves_other_people_plans_and_unknown_dates():
    memories = {'a': dict(entity_id='Alex', time={}, statement_type='plan'),
                'b': dict(entity_id='Ben', time={}, statement_type='fact'),
                'c': dict(entity_id='Alex', time={'valid_from': '2023-01-01'})}
    ids = ['b', 'a', 'c']
    assert prioritize(ids, memories, route('Alex now?', {'entities': ['Alex']}),
                      query_interval('now', date(2023, 2, 1))) == ['c', 'a', 'b']
    assert ids == ['b', 'a', 'c']
