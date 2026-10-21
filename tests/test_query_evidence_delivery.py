"""Budget-bound delivery behavior, independent of model-generated answers."""
import pytest

from locomo_memory.raw_queries import pack_payload


def evidence(count=8):
    memories, sources = [], {}
    for i in range(count):
        sid = f's{i}'
        sources[sid] = dict(source_id=sid, text='Unrelated historical detail. ' * 450,
                            session_time='2023-08-23T15:31:00', speaker='Alex')
        memories.append(dict(memory_id=f'm{i}', source_ids=[sid], entity_id='Alex',
                             state_key='Alex:adoption', state_dimension='adoption',
                             content='Alex completed an administrative step.', time={}))
    memories[-1]['content'] = 'Alex is researching adoption agencies.'
    sources[f's{count-1}']['text'] = 'I am researching adoption agencies.'
    return memories, sources


def test_core_fact_survives_large_same_state_history_at_fixed_budget(settings):
    memories, sources = evidence()
    base = dict(question='What did Alex research?', relations=[], coverage=[])
    payload, audit = pack_payload(base, memories, [], sources, settings)
    assert 'm7' in {m['memory_id'] for m in payload['memories']}
    assert 's7' in {s['source_id'] for s in payload['sources']}
    assert audit['input_token_count'] <= 12000
    assert audit['truncated']


@pytest.mark.parametrize('question,dimension,values', [
    ('What activities does Alex partake in?', 'hobby', ['walking', 'knitting']),
    ('What community events has Alex participated in?', 'attendance', ['community meeting', 'community festival']),
])
def test_multi_item_budget_prefers_distinct_facts_over_repeated_details(settings, question, dimension, values):
    memories, sources = evidence(5)
    for i, m in enumerate(memories):
        value = values[0] if i < 4 else values[1]
        m.update(content=f'Alex participated in {value} activities.', state_dimension=dimension, state_value=value)
        sources[f's{i}']['text'] = f'I enjoyed {value}. ' + 'Background detail. ' * 450
    payload, audit = pack_payload(dict(question=question, relations=[]), memories, [], sources,
                                  settings.model_copy(update={'resolution_input_budget': 7000}))
    assert {m['state_value'] for m in payload['memories']} == set(values)
    assert audit['truncated']


@pytest.mark.parametrize('label', ['CONFLICT', 'SUPERSEDE'])
def test_required_relation_sides_are_kept_together(settings, label):
    memories, sources = evidence(3)
    base = dict(question='What did Alex research?', coverage=[], relations=[
        dict(old_memory_id='m0', new_memory_id='m2', label=label)])
    payload, audit = pack_payload(base, memories, [], sources,
                                  settings.model_copy(update={'resolution_input_budget': 5000}))
    ids = {m['memory_id'] for m in payload['memories']}
    assert ('m0' in ids) == ('m2' in ids)
    assert audit['input_token_count'] <= 5000


def test_joint_packing_reserves_partial_prior_support_before_new_windows(settings):
    memories, sources = evidence(3)
    for s in sources.values():
        s['text'] = 'Prior supporting fact. ' * 80
    # The highest relevance new source is optional; prior support must survive.
    raw = [dict(source_id='new', text='research ' * 1800, session_time='2023-08-24')]
    sources.update({s['source_id']: s for s in raw})
    previous = [dict(question='Activities?', status='insufficient', memory_ids=['m0', 'm1'],
                     source_ids=[], gap='Other activities unknown')]
    base = dict(question='What did Alex research?', relations=[], previous_coverage=previous)
    payload, audit = pack_payload(base, memories, raw, sources,
                                  settings.model_copy(update={'resolution_input_budget': 5000}))
    assert {'m0', 'm1'} <= {m['memory_id'] for m in payload['memories']}
    assert not payload['raw_sources']
    assert audit['truncated']


def test_update_history_does_not_make_atomic_fact_an_indivisible_component(settings):
    memories, sources = evidence(8)
    relations = [dict(old_memory_id=f'm{i}', new_memory_id=f'm{i+1}', label='UPDATE') for i in range(7)]
    payload, audit = pack_payload(dict(question='What did Alex research?', relations=relations),
                                  memories, [], sources, settings)
    assert 'm7' in {m['memory_id'] for m in payload['memories']}
    assert audit['truncated']
    assert audit['incomplete_relations']


def test_missing_conflict_endpoint_cannot_be_accepted_as_certain(settings):
    from pydantic import ValidationError
    from locomo_memory.raw_schemas import MixedResolution
    memories, sources = evidence(1)
    payload, audit = pack_payload(dict(question='What did Alex research?', relations=[
        dict(old_memory_id='missing', new_memory_id='m0', label='CONFLICT')]), memories, [], sources, settings)
    response = dict(status='sufficient', effective_memory_ids=['m0'], effective_source_ids=[],
                    decisions=[dict(memory_id='m0', selected=True, reason='Candidate')], explanation='Certain',
                    coverage=[dict(question='Research?', status='sufficient', memory_ids=['m0'], source_ids=[])])
    with pytest.raises(ValidationError, match='Missing relation endpoints'):
        MixedResolution.model_validate(response, context=dict(memories={'m0':memories[0]}, sources=sources,
                                                              incomplete_relations=payload['incomplete_relations']))
    response['status'] = response['coverage'][0]['status'] = 'insufficient'
    response['coverage'][0]['gap'] = 'The other conflicting source is unavailable'
    assert MixedResolution.model_validate(response, context=dict(memories={'m0':memories[0]}, sources=sources,
        incomplete_relations=payload['incomplete_relations'])).effective_memory_ids == ['m0']


def test_answer_budget_keeps_prior_support_before_new_optional_raw(settings):
    memories, sources = evidence(1)
    raw = [dict(source_id='new', text='New supplementary fact. ' * 30)]
    base = dict(question='What did Alex research?', relations=[], retained_memory_ids=['m0'], coverage=[
        dict(question='Research?', status='insufficient', memory_ids=['m0'], source_ids=['new'], gap='Other details unknown')])
    payload, audit = pack_payload(base, memories, raw, sources,
        settings.model_copy(update={'evidence_token_budget': 150}), final=True)
    assert [m['memory_id'] for m in payload['memories']] == ['m0']
    assert not payload['raw_sources']
    assert audit['truncated']


def test_final_budget_never_splits_memory_raw_conflict(settings):
    memories, sources = evidence(1)
    raw = [dict(source_id='new', text='A contrary source. ' * 20)]
    base = dict(question='What did Alex research?', relations=[], coverage=[
        dict(question='Research?', status='conflict', memory_ids=['m0'], source_ids=['new'])])
    payload, audit = pack_payload(base, memories, raw, sources,
        settings.model_copy(update={'evidence_token_budget': 150}), final=True)
    assert bool(payload['memories']) == bool(payload['raw_sources'])
    assert audit['truncated']
