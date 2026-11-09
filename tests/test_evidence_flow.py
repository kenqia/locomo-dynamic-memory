"""Stage audits distinguish rejection from delivery limits without semantic labels."""
from locomo_memory.evidence_flow import evidence_flow


def test_flow_distinguishes_rejected_evidence_from_budget_and_unobserved_delivery():
    memories = [dict(memory_id=mid, source_ids=[sid]) for mid, sid in [('a', 's1'), ('b', 's2'), ('c', 's2')]]
    trace = dict(initial=dict(initial_candidates=[dict(memory=m) for m in memories]),
        expanded=dict(candidates=[dict(memory=m) for m in memories]),
        resolution_budgets=dict(resolve=dict(complete_memory_ids=['a', 'b', 'c'])),
        resolution=dict(effective_memory_ids=['b', 'c'], decisions=[
            dict(memory_id='a', selected=False, reason='Different person'),
            dict(memory_id='b', selected=True, reason='Supports the question'),
            dict(memory_id='c', selected=True, reason='Additional detail')]),
        effective_memories=[memories[1]], evidence_budget=dict(omitted_memory_ids=['c']))
    result = evidence_flow(trace)
    assert result['stages']['effective']['source_ids'] == ['s2']
    assert result['losses'] == [dict(memory_id='a', source_ids=['s1'], stage='resolution',
        reason='Different person', kind='resolver_rejected'), dict(memory_id='c', source_ids=['s2'],
        stage='answer', reason='evidence_token_budget', kind='answer_budget')]
    assert result['semantic_support'] == 'not_measured'
    assert evidence_flow({})['stages']['delivered'] is None
