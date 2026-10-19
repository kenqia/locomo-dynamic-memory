import json

import httpx
from fastapi.testclient import TestClient

from locomo_memory.api import create_app
from locomo_memory.model import DeepSeekModel
from test_queries import complete_build, query_provider
from test_retrieval import ControlledEmbedder


def test_evaluation_is_separate_persisted_and_reports_mapping_denominators(settings, sample):
    model = DeepSeekModel(settings, api_key="synthetic-test-key", transport=httpx.MockTransport(query_provider))
    with TestClient(create_app(settings, model=model, embedder=ControlledEmbedder())) as client:
        dataset_id, build_id = complete_build(client, sample)
        payload = {"dataset_id": dataset_id, "kind": "synthetic", "samples": [
            {"sample_id": "conv-a", "question": "Where does Alex live?", "answer": "Rome", "category": 4, "evidence": ["D1:1, D2:1"]},
            {"sample_id": "conv-a", "question": "Where does Alex live?", "answer": "Rome", "category": 4, "evidence": ["D999:1"]},
            {"sample_id": "conv-a", "question": "Where does Alex live?", "category": 5, "evidence": []}]}
        response = client.post("/evaluation-inputs", json=payload)
        assert response.status_code == 201, response.text
        inputs = response.json()
        result = client.post("/evaluation-runs", json={"input_id": inputs["input_id"], "strategies": ["dynamic"], "build_ids": {"conv-a": build_id}})
        assert result.status_code == 201, result.text
        run = result.json()
        assert run["summary"]["dynamic"]["source_coverage"]["initial"]["scored"] == 1
        assert run["summary"]["dynamic"]["source_coverage"]["initial"]["unscored"] == 2
        assert run["summary"]["dynamic"]["qa"]["scored"] == 3
        assert run["results"][0]["mapping"]["original"] == ["D1:1, D2:1"]
        assert run["results"][1]["source_coverage"]["effective"] is None
        assert run["course_metrics"]["status"] == "unavailable"
        assert client.get(f"/evaluation-runs/{run['run_id']}").json() == run


def test_category_branches_unknown_missing_and_strict_reference_mapping(settings, sample):
    def scoring_provider(request):
        payload = json.loads(json.loads(request.content)["messages"][1]["content"])
        if payload.get('operation') == 'answer':
            texts = {'Number?': '3', 'Lists?': 'red, blue, extra', 'Stems?': 'Running!', 'Domain?': 'Paris', 'Refusal?': 'Not mentioned here.'}
            return __import__('test_builds').completion({'status': payload['status'], 'answer': texts.get(payload['question'], 'Paris'), 'citations': [{'memory_id': m['memory_id'], 'source_ids': m['source_ids']} for m in payload['memories']]})
        return query_provider(request)
    model = DeepSeekModel(settings, api_key='synthetic-test-key', transport=httpx.MockTransport(scoring_provider))
    with TestClient(create_app(settings, model=model, embedder=ControlledEmbedder())) as client:
        dataset_id, build_id = complete_build(client, sample)
        cases = [('Lists?', 'blue, red', 1, ['D1:1; D2:1']), ('Stems?', 'runs', 2, ['D1:1']), ('Domain?', 'Paris; non-gold explanation', 3, ['D1:1']), ('Refusal?', None, 5, []), ('Missing?', None, 4, ['D1:1']), ('Unknown?', 'Paris', 99, ['D1:1']), ('Malformed?', 'Paris', 4, ['D1:1, D9:9']), ('Malformed?', 'Paris', 4, ['D1:1 and D2:1']), ('Number?', 3, 4, ['D1:1'])]
        inputs = client.post('/evaluation-inputs', json={'dataset_id': dataset_id, 'samples': [{'sample_id': 'conv-a', 'question': question, 'answer': answer, 'category': category, 'evidence': refs} for question, answer, category, refs in cases]}).json()
        response = client.post('/evaluation-runs', json={'input_id': inputs['input_id'], 'strategies': ['hybrid_no_resolution'], 'build_ids': {'conv-a': build_id}})
        assert response.status_code == 201, response.text
        run = response.json()
        assert [r['qa']['value'] for r in run['results']] == [1, 1, 1, 1, None, None, 1, 1, 1]
        assert run['results'][3]['qa']['missing_gold']
        assert run['summary']['hybrid_no_resolution']['qa']['scored'] == 7
        assert run['results'][6]['source_coverage']['initial'] is None
        assert run['results'][7]['mapping']['errors'][0]['reason'] == 'malformed_reference'
        assert run['summary']['hybrid_no_resolution']['source_coverage']['effective']['scored'] == 0


def test_baselines_really_select_dense_raw_and_expanded_context_and_never_leak_gold(settings, sample):
    observed = []
    def provider(request):
        payload = json.loads(json.loads(request.content)['messages'][1]['content'])
        observed.append(payload)
        assert 'HIDDEN_GOLD' not in json.dumps(payload)
        if payload.get('operation') == 'answer' and not payload['memories']:
            sources = payload['sources']
            return __import__('test_builds').completion({'status': payload['status'], 'answer': 'Raw conversation answer', 'citations': [{'memory_id': None, 'source_ids': [sources[0]['source_id']]}]})
        return query_provider(request)
    settings = settings.model_copy(update={'initial_k': 1})
    model = DeepSeekModel(settings, api_key='synthetic-test-key', transport=httpx.MockTransport(provider))
    with TestClient(create_app(settings, model=model, embedder=ControlledEmbedder())) as client:
        dataset_id, build_id = complete_build(client, sample)
        observed.clear()
        inputs = client.post('/evaluation-inputs', json={'dataset_id': dataset_id, 'samples': [{'sample_id': 'conv-a', 'question': 'Where does Alex live?', 'answer': 'HIDDEN_GOLD', 'category': 4, 'evidence': ['D2:1']}]}).json()
        response = client.post('/evaluation-runs', json={'input_id': inputs['input_id'], 'strategies': ['full_text', 'vector', 'hybrid_no_resolution', 'dynamic'], 'build_ids': {'conv-a': build_id}})
        assert response.status_code == 201, response.text
        rows = {r['strategy']: r for r in response.json()['results']}
        assert len(rows['full_text']['trace']['raw_context']) == 3
        assert rows['full_text']['memory_rankings']['initial'] == []
        assert rows['full_text']['trace']['answer']['citations'][0]['memory_id'] is None
        assert len(rows['vector']['memory_rankings']['answer_context']) == 1
        assert len(rows['hybrid_no_resolution']['memory_rankings']['answer_context']) == 2
        assert len(rows['dynamic']['memory_rankings']['effective']) == 1
        assert rows['vector']['memory_rankings']['initial'] == [rows['vector']['trace']['retrieval']['channels']['dense'][0]['memory_id']]
        assert len([p for p in observed if p.get('operation') == 'resolve']) == 1
        for row in rows.values():
            if row['strategy'] == 'full_text':
                assert row['trace']['evidence_budget']['budget'] is None
            else:
                assert row['trace']['evidence_budget']['token_count'] <= settings.evidence_token_budget
            assert row['trace']['evidence_budget']['model_metadata']['calls']
            assert row['diagnosis']['certainty'] == 'possible_causes_only'


def test_evaluation_rejects_unknown_conversations_split_and_official_generation(client, sample):
    from conftest import import_sample
    dataset_id = import_sample(client, sample).json()['dataset_id']
    body = {'dataset_id': dataset_id, 'kind': 'official_structure_only', 'samples': [{'sample_id': 'conv-a', 'question': 'Where?'}]}
    assert client.post('/evaluation-inputs', json={**body, 'samples': [{'sample_id': 'unknown', 'question': 'Where?'}]}).status_code == 422
    assert client.post('/evaluation-inputs', json={**body, 'course_split': {'dev': ['a'] * 4, 'test': ['b'] * 2}}).status_code == 422
    inputs = client.post('/evaluation-inputs', json=body).json()
    result = client.post('/evaluation-runs', json={'input_id': inputs['input_id'], 'strategies': ['dynamic']})
    assert result.status_code == 422
    assert result.json()['error']['code'] == 'official_structure_only_no_generation'


def test_legal_whitespace_composites_and_failed_baseline_are_persisted(settings, sample):
    fail = {'enabled': False}
    def provider(request):
        payload = json.loads(json.loads(request.content)['messages'][1]['content'])
        if fail['enabled'] and payload.get('operation') == 'answer':
            return __import__('test_builds').completion({'status': 'sufficient', 'answer': 'Invalid citation', 'citations': [{'memory_id': None, 'source_ids': ['wrong/conversation/source']}]})
        return query_provider(request)
    settings = settings.model_copy(update={'model_retries': 0})
    model = DeepSeekModel(settings, api_key='synthetic-test-key', transport=httpx.MockTransport(provider))
    with TestClient(create_app(settings, model=model, embedder=ControlledEmbedder())) as client:
        dataset_id, build_id = complete_build(client, sample)
        inputs = client.post('/evaluation-inputs', json={'dataset_id': dataset_id, 'samples': [{'sample_id': 'conv-a', 'question': 'Where does Alex live?', 'answer': 'Rome', 'category': 4, 'evidence': ['D1:1 D2:1']}]}).json()
        assert inputs['mappings'][0]['scorable']
        assert len(inputs['mappings'][0]['source_ids']) == 2
        fail['enabled'] = True
        response = client.post('/evaluation-runs', json={'input_id': inputs['input_id'], 'strategies': ['full_text', 'vector'], 'build_ids': {'conv-a': build_id}})
        assert response.status_code == 201, response.text
        run = response.json()
        for item in run['results']:
            assert item['error']['code'] == 'invalid_output'
            assert item['qa']['value'] is None
            assert item['trace']['operations']['failed_operation']['calls']
            assert item['trace']['evidence_budget']['token_count'] > 0
            assert 'effective_memories' not in item['trace']
        assert client.get('/evaluation-runs/' + run['run_id']).json() == run


def test_course_partition_and_independent_truth_are_validated_without_fabricated_metrics(settings, sample):
    from copy import deepcopy
    for suffix in 'bcdef':
        extra = deepcopy(sample[0])
        extra['sample_id'] = 'conv-' + suffix
        sample.append(extra)
    model = DeepSeekModel(settings, api_key='synthetic-test-key', transport=httpx.MockTransport(query_provider))
    with TestClient(create_app(settings, model=model, embedder=ControlledEmbedder())) as client:
        dataset_id, build_id = complete_build(client, sample)
        memories = client.get(f'/builds/{build_id}/memories').json()['items']
        expected = [m['memory_id'] for m in memories if m['state_value'] == 'Rome']
        body = {'dataset_id': dataset_id, 'kind': 'course', 'course_split': {'dev': ['conv-a', 'conv-b', 'conv-c', 'conv-d'], 'test': ['conv-e', 'conv-f']}, 'samples': [{'sample_id': 'conv-a', 'question': 'Where does Alex live?', 'category': 4, 'answer': 'Rome', 'evidence': ['D2:1'], 'dynamic_truth': {'provenance': 'human-reviewed synthetic fixture, not actual course labels', 'effective_memory_ids': expected, 'relation_labels': [{'old_memory_id': next(m['memory_id'] for m in memories if m['state_value'] == 'Paris'), 'new_memory_id': expected[0], 'label': 'SUPERSEDE'}]}}]}
        inputs = client.post('/evaluation-inputs', json=body)
        assert inputs.status_code == 201, inputs.text
        request = {'input_id': inputs.json()['input_id'], 'strategies': ['dynamic'], 'build_ids': {'conv-a': build_id}}
        assert client.post('/evaluation-runs', json=request).status_code == 422
        result = client.post('/evaluation-runs', json={**request, 'partition': 'dev'})
        assert result.status_code == 201, result.text
        assert result.json()['results'][0]['dynamic_metric']['value'] == 1
        assert result.json()['summary']['dynamic']['relations']['scored'] == 1
        assert client.post('/evaluation-runs', json={**request, 'partition': 'test'}).status_code == 422
        body['samples'][0]['dynamic_truth']['effective_memory_ids'] = ['other-version']
        other = client.post('/evaluation-inputs', json=body).json()
        result = client.post('/evaluation-runs', json={**request, 'input_id': other['input_id'], 'partition': 'dev'}).json()
        assert result['results'][0]['dynamic_metric']['value'] is None
        assert result['results'][0]['dynamic_metric']['reason'] == 'truth_outside_pinned_build'


def test_failed_embedding_reports_unknown_call_count_and_preserves_run(settings, sample):
    from locomo_memory.embeddings import EmbeddingFailure
    class FailingEmbedder(ControlledEmbedder):
        fail = False
        def encode(self, texts):
            if self.fail:
                raise EmbeddingFailure('embedding_unavailable')
            return super().encode(texts)
    embedder = FailingEmbedder()
    model = DeepSeekModel(settings, api_key='synthetic-test-key', transport=httpx.MockTransport(query_provider))
    with TestClient(create_app(settings, model=model, embedder=embedder)) as client:
        dataset_id, build_id = complete_build(client, sample)
        inputs = client.post('/evaluation-inputs', json={'dataset_id': dataset_id, 'samples': [{'sample_id': 'conv-a', 'question': 'Where does Alex live?', 'answer': 'Rome', 'category': 4, 'evidence': ['D2:1']}]}).json()
        embedder.fail = True
        response = client.post('/evaluation-runs', json={'input_id': inputs['input_id'], 'strategies': ['vector', 'dynamic'], 'build_ids': {'conv-a': build_id}})
        assert response.status_code == 201, response.text
        run = response.json()
        assert all(r['error']['code'] == 'embedding_unavailable' for r in run['results'])
        assert run['usage_summary']['samples_with_unknown_embedding_call_count'] == 2
        assert run['usage_summary']['generation_calls'] == 0
        assert all(r['usage_summary']['embedding_calls'] is None for r in run['results'])
        assert client.get('/evaluation-runs/' + run['run_id']).json() == run
