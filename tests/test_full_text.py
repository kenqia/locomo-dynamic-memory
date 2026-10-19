"""Full-context comparison behavior observed through HTTP and the provider boundary."""

import json

import httpx
from fastapi.testclient import TestClient

from locomo_memory.api import create_app
from locomo_memory.model import DeepSeekModel
from test_builds import completion
from test_queries import complete_build, query_provider
from test_retrieval import ControlledEmbedder


def test_full_text_delivers_complete_ordered_conversation_beyond_rag_budget(settings, sample):
    observed = []
    settings = settings.model_copy(update={'fragment_turns': 200})
    sample[0]['conversation']['session_3_date_time'] = '1:00 pm on 3 May, 2023'
    sample[0]['conversation']['session_3'] = [
        {'dia_id': f'D3:{index}', 'speaker': 'Sam', 'text': 'Background detail. ' * 30}
        for index in range(1, 61)
    ] + [{'dia_id': 'D3:61', 'speaker': 'Alex', 'text': 'The final access word is TAIL_FACT.'}]
    sample[0]['conversation']['session_4_date_time'] = '1:00 pm on 4 May, 2023'

    def provider(request):
        body = json.loads(request.content)
        payload = json.loads(body['messages'][1]['content'])
        assert 'HIDDEN_GOLD' not in request.content.decode()
        assert 'ANNOTATION ONLY' not in request.content.decode()
        if payload.get('operation') == 'answer':
            observed.append((body, payload))
            if not payload['memories']:
                assert [s['dia_id'] for s in payload['sources']] == ['D1:1', 'D1:2', 'D2:1'] + [f'D3:{index}' for index in range(1, 62)]
                assert payload['sources'][-1]['text'] == 'The final access word is TAIL_FACT.'
                return completion({'status': payload['status'], 'answer': 'TAIL_FACT',
                    'citations': [{'memory_id': None, 'source_ids': [payload['sources'][-1]['source_id']]}]})
        return query_provider(request)

    model = DeepSeekModel(settings, api_key='synthetic-test-key', transport=httpx.MockTransport(provider))
    with TestClient(create_app(settings, model=model, embedder=ControlledEmbedder())) as client:
        dataset_id, build_id = complete_build(client, sample)
        inputs = client.post('/evaluation-inputs', json={'dataset_id': dataset_id, 'samples': [
            {'sample_id': 'conv-a', 'question': 'What is the final access word?',
             'answer': 'HIDDEN_GOLD', 'category': 4, 'evidence': ['D3:61']},
        ]}).json()
        response = client.post('/evaluation-runs', json={'input_id': inputs['input_id'],
            'strategies': ['full_text', 'vector'], 'build_ids': {'conv-a': build_id}})
        assert response.status_code == 201, response.text
        rows = {r['strategy']: r for r in response.json()['results']}
        full = rows['full_text']['trace']
        assert full['answer']['citations'][0]['memory_id'] is None
        assert full['evidence_budget']['token_count'] > settings.evidence_token_budget
        assert full['evidence_budget']['budget'] is None
        assert full['evidence_budget']['truncated'] is False
        estimate = full['evidence_budget']['model_metadata']['request_context_estimate']
        assert estimate['token_count'] > full['evidence_budget']['token_count']
        assert estimate['method'] == 'regex-word-punctuation-v1'
        assert estimate['is_provider_token_count'] is False
        assert estimate['reserved_output_tokens'] == settings.model_max_tokens
        assert full['source_delivery']['expected_source_ids'] == full['source_delivery']['delivered_source_ids']
        assert len(full['source_delivery']['delivered_source_ids']) == 64
        assert rows['full_text']['source_coverage']['answer_context'] == 1
        assert rows['vector']['trace']['evidence_budget']['token_count'] <= settings.evidence_token_budget
        vector = rows['vector']['trace']
        assert vector['retrieval']['executed_components']['bm25'] is True
        assert vector['retrieval']['executed_components']['query_analysis'] is True
        assert vector['selection']['unused_components'] == ['query_analysis', 'bm25', 'rrf']
        assert len(vector['operations']['query_analysis_unused_by_vector_selection']['calls']) == 1
        full_body, _ = observed[0]
        vector_body, _ = observed[1]
        for field in ('model', 'temperature', 'max_tokens', 'response_format', 'thinking'):
            assert full_body[field] == vector_body[field]
        assert full_body['messages'][0] == vector_body['messages'][0]
        assert client.get('/evaluation-runs/' + response.json()['run_id']).json() == response.json()


def test_full_text_context_rejection_preserves_complete_attempt_and_safe_failure(settings, sample):
    answer_requests = []
    settings = settings.model_copy(update={'model_retries': 2})

    def provider(request):
        payload = json.loads(json.loads(request.content)['messages'][1]['content'])
        if payload.get('operation') == 'answer':
            answer_requests.append(payload)
            return httpx.Response(400, json={'error': {'code': 'context_length_exceeded',
                'message': 'Maximum context exceeded. synthetic-private-provider-detail'}})
        return query_provider(request)

    model = DeepSeekModel(settings, api_key='synthetic-test-key', transport=httpx.MockTransport(provider))
    with TestClient(create_app(settings, model=model, embedder=ControlledEmbedder())) as client:
        dataset_id, build_id = complete_build(client, sample)
        inputs = client.post('/evaluation-inputs', json={'dataset_id': dataset_id, 'samples': [
            {'sample_id': 'conv-a', 'question': 'Where does Alex live?', 'answer': 'Rome',
             'category': 4, 'evidence': ['D2:1']},
        ]}).json()
        response = client.post('/evaluation-runs', json={'input_id': inputs['input_id'],
            'strategies': ['full_text'], 'build_ids': {'conv-a': build_id}})
        assert response.status_code == 201, response.text
        row = response.json()['results'][0]
        assert row['error']['code'] == 'context_length_exceeded'
        assert row['qa']['value'] is None
        trace = row['trace']
        assert trace['outcome'] == 'failed'
        assert trace['initial_source_ids'] == [s['source_id'] for s in answer_requests[0]['sources']]
        assert trace['source_delivery']['expected_source_ids'] == trace['source_delivery']['delivered_source_ids']
        assert trace['source_delivery']['provider_accepted'] is False
        assert trace['evidence_budget']['context_limit_exceeded'] is True
        assert trace['evidence_budget']['truncated'] is False
        assert len(answer_requests) == 1
        assert 'synthetic-private-provider-detail' not in response.text
        assert 'synthetic-test-key' not in response.text
        assert client.get('/evaluation-runs/' + response.json()['run_id']).json() == response.json()
