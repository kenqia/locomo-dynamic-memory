from copy import deepcopy
import json

import httpx
import pytest
from fastapi.testclient import TestClient

from locomo_memory.api import create_app
from locomo_memory.model import DeepSeekModel
from locomo_memory.query_schemas import QueryRequest
from tools.research_v2.router import QueryComplexityRouter, observe, query_opt_in
from tools.research_v2.phase3_simulate import select_threshold
from test_builds import completion, draft
from test_retrieval import ControlledEmbedder, build


def observation():
    memory=dict(draft(['s1']),memory_id='m1',build_id='b1',sample_id='conv-a')
    return dict(analysis=dict(status='succeeded',result=dict(entities=['Alex'],time=None)),
                initial_candidates=[dict(memory=memory)]),{'s1':dict(source_id='s1',sample_id='conv-a',speaker='Alex',text='I live in Paris.')}


def route(question='Where does Alex live?',**kwargs):
    initial,sources=observation()
    return QueryComplexityRouter().route(question=question,initial=initial,sources=sources,**kwargs)


def test_source_supported_simple_fact_can_skip_resolution_with_auditable_features():
    decision=route()
    assert decision.path=='hybrid'
    assert decision.observed_features['eligible_claims'][0]['support'][0]['source_id']=='s1'
    assert decision.estimated_extra_cost['provider_calls']==0
    assert decision.uncertainty!='high_confidence'


@pytest.mark.parametrize('question',[
    'Where did Alex live before 2023?', 'Where does Alex live as of May 2023?',
    'Where does Alex live now?', 'Why did Alex move?', 'What does Alex plan to do?',
    'What are all the places Alex lived?', 'How many pets does Alex have?'])
def test_temporal_multi_event_and_unsupported_slot_take_dynamic(question):
    assert route(question).path=='dynamic'


@pytest.mark.parametrize('text',[
    'Do I live in Paris?', 'I do not live in Paris.', 'Sam lives in Paris.',
    'I hope to live in Paris.', 'I work in Paris. I live in Rome.',
    "I don't live in Paris.", 'If I live in Paris, I will work there.',
    'I live in Parisian district.', 'I work in Paris but live in Rome.'])
def test_source_existence_alone_is_not_sufficiency(text):
    initial,sources=observation();sources['s1']['text']=text
    assert QueryComplexityRouter().route(question='Where does Alex live?',initial=initial,sources=sources).path=='dynamic'


def test_ambiguity_relation_signals_missing_analysis_and_scope_are_conservative():
    initial,sources=observation()
    second=deepcopy(initial['initial_candidates'][0]);second['memory'].update(memory_id='m2',state_value='Rome')
    initial['initial_candidates'].append(second)
    assert QueryComplexityRouter().route(question='Where does Alex live?',initial=initial,sources=sources).path=='dynamic'
    initial,sources=observation()
    relation=dict(relation_id='r1',old_memory_id='m1',new_memory_id='m2',label='SUPERSEDE')
    assert QueryComplexityRouter().route(question='Where does Alex live?',initial=initial,sources=sources,relations=[relation]).path=='dynamic'
    initial['analysis']['status']='fallback'
    assert QueryComplexityRouter().route(question='Where does Alex live?',initial=initial,sources=sources).path=='dynamic'
    assert QueryComplexityRouter().route(question='Where does Alex live?',initial=None,sources={}).path=='dynamic'


def test_outcome_fields_and_llm_confidence_do_not_affect_features():
    initial,sources=observation();expected=observe('Where does Alex live?',initial,sources)
    initial.update(qa=1,gold_evidence=['hidden'],answer='Rome',resolution=dict(status='conflict'),failed=True,confidence=.999)
    actual=observe('Where does Alex live?',initial,sources)
    assert actual==expected
    assert QueryComplexityRouter().route(question='Where does Alex live?',initial=initial,sources=sources).path=='hybrid'


def test_budget_risk_is_visible_without_silently_deleting_evidence():
    budget=dict(input_token_count=100001,input_budget=96000,within_budget=False)
    result=route('Where did Alex live before 2023?',complete_budget=budget)
    assert result.path=='dynamic'
    assert 'dynamic_complete_input_budget_risk' in result.reason_codes
    assert result.observed_features['dynamic_complete_input_budget']==budget


def test_threshold_selection_does_not_accept_an_empty_or_unregistered_grid():
    with pytest.raises(ValueError):QueryComplexityRouter(.9)


def test_training_threshold_selection_rejects_quality_loss_despite_low_cost():
    def arm(qa,cost):return dict(status='succeeded',qa=qa,cost_by_stage={'all':{'known_peak_estimate_cny':cost,'unknown_reservation_cny':0}})
    rows=[dict(question_id='train-1',pair_state='both_succeeded',hybrid=arm(.3,1),dynamic=arm(.9,10)),
          dict(question_id='train-2',pair_state='both_succeeded',hybrid=arm(.4,1),dynamic=arm(.4,10))]
    predictions={.5:{'train-1':dict(path='hybrid'),'train-2':dict(path='hybrid')},
                 .75:{'train-1':dict(path='dynamic'),'train-2':dict(path='hybrid')},
                 1.:{'train-1':dict(path='dynamic'),'train-2':dict(path='dynamic')}}
    threshold,search=select_threshold(rows,predictions)
    assert threshold==.75
    assert not search[0]['feasible'] and search[1]['feasible']


def test_actual_opt_in_hybrid_off_dynamic_and_no_extra_router_provider_calls(settings,sample):
    operations=[]
    def provider(request):
        payload=json.loads(json.loads(request.content)['messages'][1]['content']);operation=payload.get('operation')
        operations.append(operation or 'build_or_analysis')
        if operation=='resolve':
            memories=payload['memories']
            return completion(dict(status='sufficient',effective_memory_ids=[m['memory_id'] for m in memories],
                decisions=[dict(memory_id=m['memory_id'],selected=True,reason='Source applies') for m in memories],supplemental_relations=[],explanation='Applicable'))
        if operation=='answer':
            m=payload['memories'][0]
            return completion(dict(status=payload['status'],answer='Paris',citations=[dict(memory_id=m['memory_id'],source_ids=m['source_ids'])]))
        if 'new_memory' in payload:return completion(dict(judgments=[]))
        if 'sources' in payload:return completion(dict(memories=[draft([payload['sources'][0]['source_id']])]))
        return completion(dict(entities=['Alex'],topic='residence',time=None,keywords=[]))
    model=DeepSeekModel(settings,api_key='synthetic-test-key',transport=httpx.MockTransport(provider))
    with TestClient(create_app(settings,model=model,embedder=ControlledEmbedder())) as client:
        bid=build(client,sample)
        assert client.post(f'/builds/{bid}/index').status_code==201
        assert client.post(f'/builds/{bid}/relations').status_code==202
        assert client.post(f'/builds/{bid}/publish').status_code==200
        q=client.app.state.queries;req=QueryRequest(dataset_id=q.versions.builds.get(bid)['dataset_id'],sample_id='conv-a',build_id=bid,question='Where does Alex live?')
        operations.clear();routed=query_opt_in(q,req,enabled=True)
        assert routed['research_routing']['path']=='hybrid'
        assert 'resolve' not in operations
        assert operations.count('answer')==1
        operations.clear();ordinary=query_opt_in(q,req,enabled=False)
        assert 'research_routing' not in ordinary
        assert operations.count('resolve')==1
        assert routed['answer']==ordinary['answer']
        assert routed['query_fingerprint']!=ordinary['query_fingerprint']
        assert client.post('/queries',json={**req.model_dump(mode='json'),'router':True}).status_code==422
        from locomo_memory.queries import QueryFailure
        q.settings=q.settings.model_copy(update={'resolution_input_budget':1})
        operations.clear()
        with pytest.raises(QueryFailure) as error:
            query_opt_in(q,req.model_copy(update={'question':'Where did Alex live before 2023?'}),enabled=True)
        trace=q.get(error.value.trace_id)
        assert error.value.code=='complete_resolution_input_budget_exceeded'
        assert 'dynamic_complete_input_budget_risk' in trace['research_routing']['reason_codes']
        assert 'resolve' not in operations and 'answer' not in operations
