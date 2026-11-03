"""Ordinary Dynamic must reject oversized input without silently dropping facts."""
import json

import httpx
from fastapi.testclient import TestClient
import pytest
from pydantic import ValidationError

from locomo_memory.api import create_app
from locomo_memory.model import DeepSeekModel
from locomo_memory.query_schemas import EffectiveResolution
from locomo_memory.resolution_delivery import complete_resolution_input
from locomo_memory.config import Settings
from test_builds import completion
from test_queries import complete_build, query_provider
from test_retrieval import ControlledEmbedder


@pytest.mark.parametrize('budget', [100, 5000])
def test_dynamic_never_drops_facts_to_fit_budget_and_retains_failure_trace(settings,sample,budget):
    sample[0]['conversation']['session_1'][0]['text'] += ' Synthetic background.' * 5000
    observed=[]
    def provider(request):
        payload=json.loads(json.loads(request.content)['messages'][1]['content'])
        operation=payload.get('operation')
        if operation in {'resolve','answer','resolve_raw'}:
            observed.append((operation,payload))
        if operation=='resolve' and not payload['memories']:
            return completion(dict(status='insufficient',effective_memory_ids=[],decisions=[],
                                   explanation='Evidence could not fit the input budget'))
        if operation=='answer' and payload['status']=='insufficient':
            return completion(dict(status='insufficient',answer='No information available.',citations=[]))
        return query_provider(request)
    local=settings.model_copy(update={'resolution_input_budget':budget,'model_retries':0})
    model=DeepSeekModel(local,api_key='synthetic',transport=httpx.MockTransport(provider))
    with TestClient(create_app(local,model=model,embedder=ControlledEmbedder())) as client:
        dataset,bid=complete_build(client,sample)
        state=client.get(f'/builds/{bid}/current-state').json()
        response=client.post('/queries',json=dict(dataset_id=dataset,sample_id='conv-a',build_id=bid,
                                                 question='Where does Alex live?'))
        assert response.status_code==422,response.text
        trace=client.get('/queries/'+response.json()['error']['trace_id']).json()
        assert trace['error']['code']=='complete_resolution_input_budget_exceeded'
        assert observed==[] and 'answer' not in trace
        audit=trace['resolution_budgets']['resolve']
        assert audit['input_token_count']>budget and not audit['within_budget']
        assert not audit['truncated'] and audit['omitted_groups']==[]
        assert audit['complete_memory_ids']
        assert audit['source_delivery']['status']=='not_sent'
        assert client.get(f'/builds/{bid}/current-state').json()==state
        assert client.get('/queries/'+trace['trace_id']).json()==trace


def test_full_input_budget_boundary_preserves_whole_memory_values_and_source_text():
    from copy import deepcopy
    from locomo_memory.model import request_token_estimate
    payload=dict(operation='resolve', question='What changed?', memories=[{
        'memory_id':'m1','content':'Alex is researching adoption agencies.',
        'statement_type':'fact','source_ids':['s1'],'time':{'original_expression':None}}],
        sources=[{'source_id':'s1','text':'I am researching agencies.'}],relations=[])
    before=deepcopy(payload)
    cost=request_token_estimate('resolve',payload,EffectiveResolution)
    for budget,fits in [(cost,True),(cost-1,False)]:
        context,audit=complete_resolution_input(payload,Settings(resolution_input_budget=budget))
        assert audit['within_budget'] is fits
        assert context['memories']['m1']==payload['memories'][0]
        assert context['sources']['s1']['text']==payload['sources'][0]['text']
        assert audit['omitted_groups']==[] and not audit['truncated']
    assert payload==before


def test_resolution_cannot_assert_certain_applicability_with_missing_safety_endpoint():
    context=dict(memories={'m1':{}},sources={},incomplete_relations=[dict(
        old_memory_id='m0',new_memory_id='m1',label='SUPERSEDE')])
    value=dict(status='sufficient',effective_memory_ids=['m1'],decisions=[dict(
        memory_id='m1',selected=True,reason='Only delivered endpoint')],explanation='Current')
    with pytest.raises(ValidationError):
        EffectiveResolution.model_validate(value,context=context)
    value['status']='insufficient'
    assert EffectiveResolution.model_validate(value,context=context).effective_memory_ids==['m1']
