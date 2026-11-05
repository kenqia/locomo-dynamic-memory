"""Synthetic course boundaries: verify evidence plumbing, not model accuracy."""
import json

import httpx
import pytest
from fastapi.testclient import TestClient

from locomo_memory.api import create_app
from locomo_memory.m5_queries import query
from locomo_memory.model import DeepSeekModel
from locomo_memory.query_schemas import QueryRequest
from test_builds import completion, draft
from test_relations import relation
from test_retrieval import ControlledEmbedder, build


@pytest.mark.parametrize('options', [{}, {'temporal': True}, {'adaptive': True, 'graph_depth': 2}])
@pytest.mark.parametrize('scenario', ['cancelled_plan', 'joint_participants'])
def test_synthetic_cancellation_and_joint_participants_keep_all_endpoint_sources(
        settings, sample, scenario, options):
    conversation = sample[0]['conversation']
    if scenario == 'cancelled_plan':
        conversation['session_1'][0]['text'] = 'I plan to visit Paris.'
        conversation['session_2'][0]['text'] = 'I cancelled my Paris visit.'
        question = "What happened to Alex's Paris visit plan?"
    else:
        conversation['session_1'][0]['text'] = 'Sam and I visited Paris together.'
        question = 'Who visited Paris together?'
    observed = {}

    def provider(request):
        payload = json.loads(json.loads(request.content)['messages'][1]['content'])
        if 'new_memory' in payload:
            # A cancellation of a plan is not an assertion that a completed visit
            # was superseded. Cross-person facts must never become one relation.
            assert all(old['entity_id'] == payload['new_memory']['entity_id']
                       for old in payload['history'])
            return completion({'judgments': [relation(old, payload['new_memory'])
                                             for old in payload['history']]})
        if payload.get('operation') == 'resolve':
            observed['resolve'] = payload
            return completion(dict(status='sufficient',
                effective_memory_ids=[m['memory_id'] for m in payload['memories']],
                decisions=[dict(memory_id=m['memory_id'], selected=True,
                    reason='Both source-backed facts are needed for this synthetic question')
                    for m in payload['memories']], supplemental_relations=[],
                explanation='Preserve the separate assertions and their provenance'))
        if payload.get('operation') == 'answer':
            observed['answer'] = payload
            return completion(dict(status=payload['status'],
                answer=('Alex planned a Paris visit and later cancelled it.'
                        if scenario == 'cancelled_plan' else 'Alex and Sam visited Paris together.'),
                citations=[dict(memory_id=m['memory_id'], source_ids=m['source_ids'])
                           for m in payload['memories']]))
        if 'sources' in payload:
            sources = payload['sources']
            if scenario == 'cancelled_plan':
                memories = [
                    draft([sources[0]['source_id']], content='Alex plans to visit Paris.',
                          memory_type='event', statement_type='plan', state_dimension='visit'),
                    draft([sources[2]['source_id']], content='Alex cancelled the Paris visit.',
                          memory_type='event', polarity='negative', state_dimension='visit')]
            else:
                memories = [draft([sources[0]['source_id']],
                    content=f'{person} visited Paris with {other}.', entity_id=person,
                    memory_type='event', state_dimension='visit')
                    for person, other in [('Alex', 'Sam'), ('Sam', 'Alex')]]
            return completion({'memories': memories})
        # An incomplete entity analysis must not hard-filter a joint participant.
        return completion(dict(entities=['Alex'], topic='visit', time=None, keywords=['Paris']))

    settings = settings.model_copy(update={'initial_k': 10})
    model = DeepSeekModel(settings, api_key='synthetic-test-key',
                          transport=httpx.MockTransport(provider))
    app = create_app(settings, model=model, embedder=ControlledEmbedder())
    with TestClient(app) as client:
        bid = build(client, sample)
        assert client.post(f'/builds/{bid}/index').status_code == 201
        assert client.post(f'/builds/{bid}/relations').status_code == 202
        published = client.post(f'/builds/{bid}/publish')
        assert published.status_code == 200, published.text
        original = client.get(f'/builds/{bid}/export').json()
        result = query(app.state.queries, QueryRequest(
            dataset_id=published.json()['dataset_id'], sample_id='conv-a',
            build_id=bid, question=question), **options)
        assert result['outcome'] == 'succeeded'
        delivered = result['effective_memories']
        assert len(delivered) == len(observed['resolve']['memories']) == 2
        assert {m['memory_id'] for m in observed['answer']['memories']} == {
            m['memory_id'] for m in delivered}
        assert result['answer']['citations'] == [
            dict(memory_id=m['memory_id'], source_ids=m['source_ids']) for m in delivered]
        if scenario == 'cancelled_plan':
            assert {(m['statement_type'], m['polarity']) for m in delivered} == {
                ('plan', 'positive'), ('fact', 'negative')}
            assert len({sid for m in delivered for sid in m['source_ids']}) == 2
            stored = client.get(f'/builds/{bid}/relations').json()['items']
            assert [item['label'] for item in stored] == ['undetermined']
        else:
            assert {m['entity_id'] for m in delivered} == {'Alex', 'Sam'}
            assert delivered[0]['source_ids'] == delivered[1]['source_ids']
            assert client.get(f'/builds/{bid}/relations').json()['total'] == 0
        assert client.get(f'/queries/{result["trace_id"]}').json() == result
        assert client.get(f'/builds/{bid}/export').json() == original
