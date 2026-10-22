"""Failure-aware experimental denominators through the public evaluation API."""
from copy import deepcopy
import json

import httpx
import pytest
from fastapi.testclient import TestClient

from locomo_memory.api import create_app
from locomo_memory.model import DeepSeekModel
from test_builds import completion
from test_queries import complete_build, query_provider
from test_retrieval import ControlledEmbedder


def test_reports_separate_applicable_failures_missing_labels_and_weighted_groups(settings, sample):
    other = deepcopy(sample[0])
    other['sample_id'] = 'conv-b'
    other['conversation']['session_2'][0]['text'] = 'I moved from Paris to Rome on 2 May 2023.'
    sample.append(other)
    settings = settings.model_copy(update={'model_retries': 0})

    def provider(request):
        payload = json.loads(json.loads(request.content)['messages'][1]['content'])
        if payload.get('operation') == 'answer':
            if payload['question'] == 'Fail?':
                return httpx.Response(503, json={'error': 'controlled failure'})
            return completion({'status': payload['status'],
                'answer': 'Not mentioned.' if payload['question'] == 'Refusal?' else 'Rome',
                'citations': [{'memory_id': None, 'source_ids': [payload['sources'][-1]['source_id']]}]})
        return query_provider(request)

    model = DeepSeekModel(settings, api_key='synthetic-test-key', transport=httpx.MockTransport(provider))
    with TestClient(create_app(settings, model=model, embedder=ControlledEmbedder())) as client:
        dataset_id, build_id = complete_build(client, sample)
        second = client.post('/builds', json={'dataset_id': dataset_id, 'sample_id': 'conv-b'}).json()['build_id']
        assert client.post(f'/builds/{second}/index').status_code == 201
        assert client.post(f'/builds/{second}/relations').status_code == 202
        assert client.post(f'/builds/{second}/publish').status_code == 200
        cases = [
            {'question': 'Success?', 'answer': 'Rome', 'category': 4, 'evidence': ['D2:1']},
            {'question': 'Fail?', 'answer': 'Rome', 'category': 4, 'evidence': ['D2:1']},
            {'question': 'Missing?', 'category': 4, 'evidence': []},
            {'question': 'Unknown?', 'answer': 'Rome', 'category': 99, 'evidence': ['D1:1']},
            {'question': 'Bad evidence?', 'answer': 'Rome', 'category': 4, 'evidence': ['D999:1']},
            {'question': 'Refusal?', 'category': 5, 'evidence': ['D2:1']},
        ]
        inputs = client.post('/evaluation-inputs', json={'dataset_id': dataset_id, 'samples': [
            {'sample_id': 'conv-a', **case} for case in cases
        ] + [{'sample_id': 'conv-b', 'question': 'Other?', 'answer': 'Rome', 'category': 4, 'evidence': ['D2:1']}]}).json()
        response = client.post('/evaluation-runs', json={'input_id': inputs['input_id'],
            'strategies': ['full_text'], 'build_ids': {'conv-a': build_id, 'conv-b': second}, 'wait': True})
        assert response.status_code == 201, response.text
        run = response.json()
        report = run['summary']['full_text']
        assert report['qa']['mean'] == 1
        assert report['qa']['scored'] == 4
        assert report['qa']['unscored'] == 3
        assert report['execution']['planned'] == 7
        assert report['execution']['succeeded'] == 6
        assert report['execution']['failed'] == 1
        assert report['execution']['success_rate'] == pytest.approx(6 / 7)
        assert report['baseline_run_score'] == {
            'value': .8, 'numerator': 4, 'denominator': 5, 'excluded': 2,
            'status': 'complete', 'failure_zero_count': 1,
        }
        assert report['missing_gold'] == 2
        assert report['unknown_category'] == 1
        assert report['invalid_evidence'] == 2
        assert run['results'][4]['qa']['value'] == 1
        assert run['results'][4]['source_coverage']['answer_context'] is None
        assert run['results'][5]['qa']['value'] == 1
        groups = run['grouped_summary']
        assert groups['conversation']['conv-a']['full_text']['baseline_run_score']['value'] == .75
        assert groups['conversation']['conv-b']['full_text']['baseline_run_score']['value'] == 1
        assert groups['category']['5']['full_text']['baseline_run_score']['denominator'] == 1
        assert groups['conversation_means']['full_text']['baseline_run_score']['mean'] == .875
        assert run['overall_summary']['baseline_run_score']['value'] == .8
        assert run['course_metrics']['status'] == 'unavailable'
        assert client.get('/evaluation-runs/' + run['run_id']).json() == run


def test_unknown_and_pending_items_keep_final_score_incomplete_until_explicit_recovery(settings, sample):
    fail = {'enabled': True}

    def provider(request):
        payload = json.loads(json.loads(request.content)['messages'][1]['content'])
        if payload.get('operation') == 'answer':
            if payload['question'] == 'Unknown outcome?' and fail['enabled']:
                raise RuntimeError('controlled external outcome unknown')
            return completion({'status': payload['status'], 'answer': 'Rome',
                'citations': [{'memory_id': None, 'source_ids': [payload['sources'][-1]['source_id']]}]})
        return query_provider(request)

    model = DeepSeekModel(settings, api_key='synthetic-test-key', transport=httpx.MockTransport(provider))
    with TestClient(create_app(settings, model=model, embedder=ControlledEmbedder())) as client:
        dataset_id, _ = complete_build(client, sample)
        inputs = client.post('/evaluation-inputs', json={'dataset_id': dataset_id, 'samples': [
            {'sample_id': 'conv-a', 'question': 'Success?', 'answer': 'Rome', 'category': 4},
            {'sample_id': 'conv-a', 'question': 'Unknown outcome?', 'answer': 'Rome', 'category': 4},
            {'sample_id': 'conv-a', 'question': 'Pending without gold?', 'category': 4},
        ]}).json()
        run = client.post('/evaluation-runs', json={'input_id': inputs['input_id'], 'strategies': ['full_text'], 'wait': True}).json()
        report = run['summary']['full_text']
        assert report['qa']['mean'] == 1
        assert report['qa']['scored'] == 1
        assert report['execution']['success_rate'] == pytest.approx(1 / 3)
        assert report['execution']['pending'] == 1
        assert report['execution']['unknown'] == 1
        assert report['baseline_run_score']['value'] is None
        assert report['baseline_run_score']['status'] == 'incomplete'
        assert report['baseline_run_score']['denominator'] == 2
        assert report['baseline_run_score']['failure_zero_count'] == 0
        assert run['usage_summary']['unknown_attempts'] == 1
        partial = client.post('/evaluation-runs/' + run['run_id'] + '/resume', json={'wait': True}).json()
        assert partial['summary']['full_text']['baseline_run_score']['value'] is None
        assert partial['summary']['full_text']['execution']['succeeded'] == 2
        fail['enabled'] = False
        completed = client.post('/evaluation-runs/' + run['run_id'] + '/resume', json={'retry_unknown': True, 'wait': True}).json()
        assert completed['summary']['full_text']['baseline_run_score']['value'] == 1
        assert completed['summary']['full_text']['baseline_run_score']['denominator'] == 2
        assert completed['usage_summary']['unknown_attempts'] == 1
        assert completed['usage_summary']['logical_retries'] == 1
        assert completed['usage_summary']['generation_calls'] == 3
        assert completed['usage_summary']['provider_usage_complete'] is False


def test_retry_keeps_prior_provider_usage_and_distinguishes_partial_fields_from_zero(settings, sample):
    fail = {'enabled': True}
    answers = []
    settings = settings.model_copy(update={'model_retries': 0})

    def provider(request):
        payload = json.loads(json.loads(request.content)['messages'][1]['content'])
        if payload.get('operation') == 'answer':
            answers.append(payload['question'])
            output = {'status': payload['status'], 'answer': 'Rome',
                'citations': [{'memory_id': None, 'source_ids': ['wrong/source'] if fail['enabled'] else [payload['sources'][-1]['source_id']]}]}
            response = completion(output)
            if fail['enabled']:
                body = response.json()
                body['usage'] = {'prompt_tokens': 7}
                return httpx.Response(200, json=body)
            return response
        return query_provider(request)

    model = DeepSeekModel(settings, api_key='synthetic-test-key', transport=httpx.MockTransport(provider))
    with TestClient(create_app(settings, model=model, embedder=ControlledEmbedder())) as client:
        dataset_id, build_id = complete_build(client, sample)
        inputs = client.post('/evaluation-inputs', json={'dataset_id': dataset_id, 'samples': [
            {'sample_id': 'conv-a', 'question': 'Retry?', 'answer': 'Rome', 'category': 4},
        ]}).json()
        run = client.post('/evaluation-runs', json={'input_id': inputs['input_id'], 'strategies': ['full_text'], 'wait': True}).json()
        assert run['summary']['full_text']['baseline_run_score']['value'] == 0
        assert run['summary']['full_text']['qa']['mean'] is None
        assert run['summary']['full_text']['execution']['succeeded'] == 0
        assert run['usage_summary']['reported_tokens'] == {'prompt_tokens': 7, 'completion_tokens': None, 'total_tokens': None}
        assert run['results'][0]['usage_summary']['reported_tokens']['completion_tokens'] is None
        fail['enabled'] = False
        done = client.post('/evaluation-runs/' + run['run_id'] + '/resume', json={'retry_failed': True, 'wait': True}).json()
        assert done['summary']['full_text']['baseline_run_score']['value'] == 1
        assert done['summary']['full_text']['baseline_run_score']['denominator'] == 1
        assert done['usage_summary']['generation_calls'] == 2
        assert done['usage_summary']['reported_tokens'] == {'prompt_tokens': 17, 'completion_tokens': 5, 'total_tokens': 15}
        assert done['usage_summary']['usage_fields']['prompt_tokens']['complete'] is True
        assert done['usage_summary']['usage_fields']['completion_tokens']['calls_missing_usage'] == 1
        assert done['usage_summary']['usage_fields']['total_tokens']['complete'] is False
        assert done['usage_summary']['calls_with_partial_usage'] == 1
        assert done['usage_summary']['first_attempt_failures'] == 1
        assert done['usage_summary']['failed_attempts'] == 1
        assert done['usage_summary']['logical_retries'] == 1
        assert len(done['items'][0]['attempts']) == 2
        assert done['build_usage_summary']['generation_calls'] == 2
        assert done['build_usage_summary']['reported_tokens']['total_tokens'] == 30
        assert done['build_usage_summary']['by_build'][build_id]['embedding_calls'] is None
        assert done['usage_summary']['reported_embedding_calls'] == 0
        assert done['usage_summary']['samples_with_unknown_embedding_call_count'] == 0
        assert done['usage_summary']['reported_attempt_seconds'] > 0
        assert client.get('/evaluation-runs/' + run['run_id']).json() == done
        assert answers == ['Retry?', 'Retry?']


def test_query_trace_does_not_turn_unreported_usage_fields_into_zero(settings, sample):
    def provider(request):
        response = query_provider(request)
        payload = json.loads(json.loads(request.content)['messages'][1]['content'])
        if payload.get('operation') == 'answer':
            body = response.json()
            body['usage'] = {'prompt_tokens': 7}
            return httpx.Response(200, json=body)
        return response

    model = DeepSeekModel(settings, api_key='synthetic-test-key', transport=httpx.MockTransport(provider))
    with TestClient(create_app(settings, model=model, embedder=ControlledEmbedder())) as client:
        dataset_id, _ = complete_build(client, sample)
        trace = client.post('/queries', json={'dataset_id': dataset_id, 'sample_id': 'conv-a', 'question': 'Where does Alex live?'}).json()
        usage = trace['usage_summary']
        assert usage['reported_tokens'] == {'prompt_tokens': 27, 'completion_tokens': 10, 'total_tokens': 30}
        assert usage['calls_with_partial_usage'] == 1
        assert usage['usage_fields']['completion_tokens']['complete'] is False
        assert usage['usage_fields']['completion_tokens']['calls_missing_usage'] == 1
        assert client.get('/queries/' + trace['trace_id']).json() == trace
