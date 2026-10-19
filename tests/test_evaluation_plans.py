"""Development planning through the public API, without generation or builds."""
import httpx
from fastapi.testclient import TestClient

from locomo_memory.api import create_app
from locomo_memory.model import DeepSeekModel
from test_retrieval import ControlledEmbedder


def test_official_development_plan_is_complete_stable_and_offline(settings):
    calls = []

    def unexpected_provider(request):
        calls.append(request)
        raise AssertionError('Planning must not call a generation provider')

    model = DeepSeekModel(settings, api_key='synthetic-test-key', transport=httpx.MockTransport(unexpected_provider))
    with TestClient(create_app(settings, model=model, embedder=ControlledEmbedder())) as client:
        imported = client.post('/imports/official').json()
        request = {'dataset_id': imported['dataset_id'], 'artifact_sha256': imported['artifact_sha256'], 'scope': 'development'}
        response = client.post('/evaluation-plans', json=request)
        assert response.status_code == 201, response.text
        plan = response.json()
        assert plan['course_split'] == {'dev': ['conv-26', 'conv-30', 'conv-41', 'conv-42'], 'test': ['conv-43', 'conv-44']}
        assert plan['question_count'] == 757
        assert plan['combination_count'] == 3028
        assert plan['strategies'] == ['full_text', 'vector', 'hybrid_no_resolution', 'dynamic']
        assert plan['status'] == 'preview'
        assert plan['grading_set'] == 'hidden_not_available'
        assert plan['source_sha256'] == imported['source_sha256']
        assert plan['artifact_sha256'] == '79fa87e90f04081343b8c8debecb80a9a6842b76a7aa537dc9fdf651ea698ff4'
        assert plan['version'] == '3eb6f2c585f5e1699204e3c3bdf7adc5c28cb376'
        assert {q['sample_id'] for q in plan['questions']} == {'conv-26', 'conv-30', 'conv-41', 'conv-42'}
        assert plan['questions'][0]['question_id'] == 'conv-26:qa:0'
        assert plan['questions'][1]['question_id'] == 'conv-26:qa:1'
        assert client.get('/evaluation-plans/' + plan['plan_id']).json() == plan
        assert client.post('/evaluation-plans', json=request).json() == plan
        inputs = client.get('/evaluation-inputs/' + plan['input_id']).json()
        assert inputs['kind'] == 'course'
        assert len(inputs['samples']) == 757
        assert {s['sample_id'] for s in inputs['samples']} == {'conv-26', 'conv-30', 'conv-41', 'conv-42'}
        turns = client.get(f"/datasets/{imported['dataset_id']}/conversations/conv-26/turns").json()
        assert all(set(t) == {'source_id', 'dataset_id', 'sample_id', 'session_id', 'dia_id', 'speaker', 'session_time', 'text', 'position'} for t in turns['items'])
        assert calls == []


def test_smoke_plan_uses_first_original_question_per_category(client):
    imported = client.post('/imports/official').json()
    response = client.post('/evaluation-plans', json={'dataset_id': imported['dataset_id'], 'artifact_sha256': imported['artifact_sha256'], 'scope': 'smoke'})
    assert response.status_code == 201, response.text
    plan = response.json()
    assert plan['question_count'] == 5
    assert plan['combination_count'] == 20
    assert [q['qa_index'] for q in plan['questions']] == [0, 2, 3, 82, 152]
    assert [q['category'] for q in plan['questions']] == [2, 3, 1, 4, 5]
    assert {q['sample_id'] for q in plan['questions']} == {'conv-26'}
    inputs = client.get('/evaluation-inputs/' + plan['input_id']).json()
    assert inputs['question_identities'] == [{'sample_id': 'conv-26', 'qa_index': index, 'question_id': f'conv-26:qa:{index}'} for index in [0, 2, 3, 82, 152]]


def test_smoke_rejects_missing_categories_and_keeps_duplicate_questions(client, sample):
    from copy import deepcopy
    from conftest import import_sample

    data = []
    for sample_id in ['conv-26', 'conv-30', 'conv-41', 'conv-42', 'conv-43', 'conv-44']:
        item = deepcopy(sample[0])
        item['sample_id'] = sample_id
        item['qa'] = [{'question': 'Identical?', 'category': category, 'answer': 'ANNOTATION ONLY', 'evidence': ['D1:1']} for category in [2, 2, 3, 1, 4]]
        data.append(item)
    imported = import_sample(client, data).json()
    request = {'dataset_id': imported['dataset_id'], 'artifact_sha256': imported['artifact_sha256'], 'scope': 'smoke'}
    rejected = client.post('/evaluation-plans', json=request)
    assert rejected.status_code == 422
    assert rejected.json()['error']['code'] == 'smoke_categories_missing'
    full = client.post('/evaluation-plans', json={**request, 'scope': 'development'}).json()
    assert full['question_count'] == 20
    assert full['combination_count'] == 80
    assert [q['qa_index'] for q in full['questions'][:5]] == [0, 1, 2, 3, 4]
    assert len({q['question_id'] for q in full['questions']}) == 20
    original_id = full['plan_id']
    for item in data:
        item['qa'].append({'question': 'Last category?', 'category': 5})
    new_artifact = import_sample(client, data).json()
    assert new_artifact['dataset_id'] == imported['dataset_id']
    smoke = client.post('/evaluation-plans', json={**request, 'artifact_sha256': new_artifact['artifact_sha256']})
    assert smoke.status_code == 201, smoke.text
    assert [q['qa_index'] for q in smoke.json()['questions']] == [0, 2, 3, 4, 5]
    assert client.get('/evaluation-plans/' + original_id).json() == full
    turns = client.get(f"/datasets/{imported['dataset_id']}/conversations/conv-26/turns").json()
    assert 'ANNOTATION ONLY' not in str(turns)


def test_plan_requires_explicit_artifact_and_survives_restart(settings):
    with TestClient(create_app(settings, embedder=ControlledEmbedder())) as client:
        imported = client.post('/imports/official').json()
        request = {'dataset_id': imported['dataset_id'], 'artifact_sha256': imported['artifact_sha256'], 'scope': 'smoke'}
        missing = client.post('/evaluation-plans', json={**request, 'artifact_sha256': '0' * 64})
        assert missing.status_code == 404
        assert missing.json()['error']['code'] == 'evaluation_artifact_not_found'
        assert client.post('/evaluation-plans', json={**request, 'scope': 'test'}).status_code == 422
        plan = client.post('/evaluation-plans', json=request).json()
    with TestClient(create_app(settings, embedder=ControlledEmbedder())) as restarted:
        assert restarted.get('/evaluation-plans/' + plan['plan_id']).json() == plan
        inputs = restarted.get('/evaluation-inputs/' + plan['input_id']).json()
        assert inputs['source_identity']['artifact_sha256'] == imported['artifact_sha256']
        assert inputs['source_identity']['source_sha256'] == imported['source_sha256']
        assert inputs['plan_id'] == plan['plan_id']
