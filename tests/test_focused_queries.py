"""Focused/expanded comparison at the public query boundary."""
import json

import httpx
import pytest
from fastapi.testclient import TestClient

from locomo_memory.api import create_app
from locomo_memory.model import DeepSeekModel
from test_builds import completion, draft
from test_raw_queries import published
from test_relations import relation
from test_retrieval import ControlledEmbedder


@pytest.mark.parametrize('question,label,applicability', [
    ('Where did Alex work on 1 May 2023?', 'undetermined', {}),
    ('Where does Alex work?', 'RETAIN', {}),
    ('Where does Alex work?', 'CONFLICT', {}),
    ('Where does Alex work?', 'SUPERSEDE', {'condition':'if the contract is approved'}),
    ('Where does Alex work?', 'SUPERSEDE', {}),
])
def test_focus_removes_unrelated_group_but_keeps_employment_history_and_uncertainty(settings, sample, question, label, applicability):
    sample[0]['conversation']['session_1'][0]['text'] = 'I work for Cedar part time.'
    sample[0]['conversation']['session_1'][1]['text'] = 'I collect violet marbles.'
    sample[0]['conversation']['session_2'][0]['text'] = 'I work for Larch. I do not work for Pine. Cedar may continue; the contract approval date is unknown.'
    observed = []
    def provider(request):
        payload = json.loads(json.loads(request.content)['messages'][1]['content'])
        op = payload.get('operation')
        if 'new_memory' in payload:
            new = payload['new_memory']
            judgments = []
            for old in payload['history']:
                use_label = label if new['state_value']=='Larch' else 'undetermined'
                judgments.append(relation(old,new,label=use_label,applicability=applicability if use_label=='SUPERSEDE' else {},
                    support_quote=payload['sources'][-1]['text'] if use_label!='undetermined' else None))
            return completion({'judgments':judgments})
        if op == 'resolve_raw':
            observed.append(payload)
            ms = [m for m in payload['memories'] if m['entity_id']=='Alex']
            status = 'conflict' if label=='CONFLICT' else 'sufficient'
            return completion({'status':status,'effective_memory_ids':[m['memory_id'] for m in ms],
                'effective_source_ids':[], 'decisions':[{'memory_id':m['memory_id'],'selected':m in ms,'reason':'Necessary history or compatible/uncertain employment'} for m in payload['memories']],
                'supplemental_relations':[], 'coverage':[{'question':question,'status':status,'memory_ids':[m['memory_id'] for m in ms],'source_ids':[],'gap':None}], 'explanation':'Keep both jobs, negative claim and unknown applicability.'})
        if op == 'answer_raw':
            return completion({'status':payload['status'],'answer':'Last known employment includes Cedar and Larch; Pine is denied. Current continuation is uncertain.',
                'citations':[{'memory_id':m['memory_id'],'source_ids':m['source_ids']} for m in payload['memories']]})
        if op is None and 'sources' in payload:
            s = payload['sources']
            return completion({'memories':[
                draft([s[0]['source_id']],content='Alex works for Cedar part time.',state_dimension='employment',state_value='Cedar'),
                draft([s[1]['source_id']],content='Sam collects violet marbles.',entity_id='Sam',state_dimension='hobby',state_value='marbles'),
                draft([s[2]['source_id']],content='Alex works for Larch.',state_dimension='employment',state_value='Larch'),
                draft([s[2]['source_id']],content='Alex does not work for Pine.',state_dimension='employment',state_value='Pine',polarity='negative'),
            ]})
        return completion({'entities':['Alex'],'topic':'employment','time':None,'keywords':[]})
    model = DeepSeekModel(settings,api_key='synthetic-test-key',transport=httpx.MockTransport(provider))
    with TestClient(create_app(settings,model=model,embedder=ControlledEmbedder())) as client:
        query = {**published(client,sample),'question':question}
        responses = [client.post('/queries',json={**query,'evidence_profile':profile}) for profile in ('expanded','focused')]
        for response in responses:
            assert response.status_code == 201, response.text
        expanded,focused = [r.json() for r in responses]
        assert len(observed[0]['memories']) == 4
        assert len(observed[1]['memories']) == 3
        assert {m['state_value'] for m in observed[1]['memories']} == {'Cedar','Larch','Pine'}
        assert focused['resolution_budgets']['resolve']['input_token_count'] < expanded['resolution_budgets']['resolve']['input_token_count']
        assert focused['answer'] == expanded['answer']
        assert focused['query_fingerprint'] != expanded['query_fingerprint']
        assert focused['evidence_selection']['omitted'][0]['reason'] == 'no_original_question_match_or_connected_history'
        assert any(m['polarity']=='negative' for m in observed[1]['memories'])
        assert observed[1]['relations'] == observed[0]['relations']


def test_focus_without_original_question_anchor_preserves_expanded_candidates(settings, sample):
    from test_raw_queries import raw_provider
    observed = []
    model = DeepSeekModel(settings,api_key='synthetic-test-key',transport=httpx.MockTransport(raw_provider(observed,enough=True)))
    with TestClient(create_app(settings,model=model,embedder=ControlledEmbedder())) as client:
        query = {**published(client,sample),'question':'Explain the situation?','evidence_profile':'focused'}
        response = client.post('/queries',json=query)
        assert response.status_code == 201, response.text
        trace = response.json()
        assert trace['evidence_selection']['fallback_to_expanded']
        assert trace['evidence_selection']['omitted'] == []
        assert len(trace['evidence_selection']['retained']) == len(trace['expanded']['candidates'])


def test_focused_profile_is_explicitly_scoped_to_the_new_strategy(client):
    response = client.post('/queries',json={'dataset_id':'synthetic','sample_id':'conv-a','question':'Where?','strategy':'dynamic','evidence_profile':'focused'})
    assert response.status_code == 422


@pytest.mark.parametrize('question', ["What is Alex's occupation and favorite color?", 'Where does Alex work?'])
def test_partial_lexical_match_never_hides_synonymous_fact_or_named_person(settings,sample,question):
    sample[0]['conversation']['session_1'][0]['text'] = 'I am employed as a nurse. My favorite color is violet.'
    sample[0]['conversation']['session_1'][1]['text'] = 'I work as a teacher.'
    observed = []
    def provider(request):
        p = json.loads(json.loads(request.content)['messages'][1]['content'])
        op = p.get('operation')
        if 'new_memory' in p:
            return completion({'judgments':[relation(old,p['new_memory']) for old in p['history']]})
        if op == 'resolve_raw':
            observed.append(p)
            mids = [m['memory_id'] for m in p['memories']]
            return completion({'status':'sufficient','effective_memory_ids':mids,'effective_source_ids':[],
                'decisions':[{'memory_id':mid,'selected':True,'reason':'Preserve supplied facts'} for mid in mids],
                'coverage':[{'question':question,'status':'sufficient','memory_ids':mids,'source_ids':[]}], 'explanation':'Source facts retained'})
        if op == 'answer_raw':
            return completion({'status':p['status'],'answer':'Alex is a nurse and likes violet.', 'citations':[{'memory_id':m['memory_id'],'source_ids':m['source_ids']} for m in p['memories']]})
        if 'sources' in p:
            return completion({'memories':[
                draft([p['sources'][0]['source_id']],content='Alex is employed as a nurse.',state_dimension='employment',state_value='nurse'),
                draft([p['sources'][0]['source_id']],content="Alex's favorite color is violet.",state_dimension='favorite_color',state_value='violet'),
                draft([p['sources'][1]['source_id']],content='Sam works as a teacher.',entity_id='Sam',state_dimension='employment',state_value='teacher')]})
        return completion({'entities':['Alex'],'topic':None,'time':None,'keywords':[]})
    model = DeepSeekModel(settings,api_key='synthetic-test-key',transport=httpx.MockTransport(provider))
    with TestClient(create_app(settings,model=model,embedder=ControlledEmbedder())) as client:
        response = client.post('/queries',json={**published(client,sample),'question':question,'evidence_profile':'focused'})
        assert response.status_code == 201, response.text
        assert {m['state_value'] for m in observed[0]['memories']} == {'nurse','violet','teacher'}
        assert response.json()['evidence_selection']['fallback_to_expanded']
