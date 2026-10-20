"""Targeted recovery at the relation adapter boundary, with synthetic HTTP only."""

from copy import deepcopy
import json

import httpx
import pytest

from locomo_memory.model import DeepSeekModel, ModelFailure
from locomo_memory.relation_schemas import RelationBatch
from test_model_diagnostics import update_stages


@pytest.mark.parametrize('failure_kind', ['length', 'quote'])
@pytest.mark.parametrize('retry_count', [0, 1, 2])
def test_relation_retry_delivers_safe_feedback_and_keeps_complete_validation(settings, failure_kind, retry_count):
    common = dict(build_id='b', dataset_id='d', sample_id='s', entity_id='Alex',
                  memory_type='state', statement_type='fact', state_key='s:Alex:application', source_ids=['s1'])
    history = [dict(common, memory_id=f'old-{index}') for index in range(20)]
    new = dict(common, memory_id='new')
    source = {'source_id': 's1', 'text': 'I researched agencies and submitted an application.'}
    context = dict(new_memory=new, history=history, sources={'s1': source})
    payload = dict(new_memory=new, history=history, sources=[source])
    original = deepcopy(payload)
    judgments = [dict(old_memory_id=old['memory_id'], new_memory_id='new', label='UPDATE',
                      reason='The application follows research', source_ids=['s1'],
                      support_quote='I researched agencies and submitted an application.') for old in history]
    for judgment,old in zip(judgments,history):
        judgment['update_evidence'] = update_stages(old,new,context['sources'])
    invalid = deepcopy(judgments)
    invalid[19]['support_quote'] = 'private-response-marker'
    requests = []

    def provider(request):
        body = json.loads(request.content)
        requests.append(body)
        # Two failed responses ensure feedback is replaced instead of accumulating.
        valid = len(requests) == 3
        return httpx.Response(200, json={'choices': [{
            'finish_reason': 'length' if failure_kind == 'length' and not valid else 'stop',
            'message': {'content': json.dumps({'judgments': judgments if valid else invalid})},
        }]})

    model = DeepSeekModel(settings.model_copy(update={'model_retries': retry_count}),
                          api_key='synthetic', transport=httpx.MockTransport(provider))
    if retry_count < 2:
        with pytest.raises(ModelFailure) as failure:
            model.generate('relate', payload, RelationBatch, context=context)
        assert len(failure.value.metadata['calls']) == retry_count + 1
        assert all(c['outcome'] == 'invalid_output' for c in failure.value.metadata['calls'])
    else:
        result = model.generate('relate', payload, RelationBatch, context=context)
        assert len(result.value.judgments) == 20
        assert all(j.label == 'UPDATE' for j in result.value.judgments)
        assert [c['outcome'] for c in result.metadata['calls']] == ['invalid_output', 'invalid_output', 'succeeded']
        assert requests[1] == requests[2]
    assert len(requests) == retry_count + 1
    assert payload == original
    assert 'retry_feedback' not in json.loads(requests[0]['messages'][1]['content'])
    for body in requests[1:]:
        sent = json.loads(body['messages'][1]['content'])
        feedback = sent['retry_feedback']
        expected_code = 'non_stop_finish_reason' if failure_kind == 'length' else 'verbatim_support_required'
        assert feedback['error_code'] == expected_code
        assert feedback['field_path'] == (None if failure_kind == 'length' else 'judgments[19]')
        assert 'private-response-marker' not in json.dumps(feedback)
        assert sent['history'] == history and sent['sources'] == [source]
        assert body['max_tokens'] == settings.model_max_tokens


def test_relation_prompt_guides_compact_output_and_single_source_quotes(settings):
    requests = []
    def provider(request):
        requests.append(json.loads(request.content))
        return httpx.Response(200, json={'choices': [{'finish_reason': 'stop', 'message': {'content': '{"judgments": []}'}}]})
    model = DeepSeekModel(settings, api_key='synthetic', transport=httpx.MockTransport(provider))
    model.generate('relate', {}, RelationBatch)
    prompt = requests[0]['messages'][0]['content']
    assert 'Omit optional fields when they have no evidence' in prompt
    assert 'one continuous substring of ONE cited source' in prompt
    assert 'never omit a history endpoint' in prompt


def test_retry_feedback_is_latest_only_and_context_estimate_includes_it(settings):
    from locomo_memory.retrieval import budget_tokens
    requests = []
    responses = iter([('length', 'private-response-marker'), ('stop', '{private-response-marker'),
                      ('stop', '{"judgments": []}')])
    def provider(request):
        requests.append(json.loads(request.content))
        finish, content = next(responses)
        return httpx.Response(200, json={'choices': [{'finish_reason': finish, 'message': {'content': content}}]})
    model = DeepSeekModel(settings.model_copy(update={'model_retries': 2}), api_key='synthetic',
                          transport=httpx.MockTransport(provider))
    result = model.generate('relate', {}, RelationBatch)
    assert 'retry_feedback' in json.loads(requests[1]['messages'][1]['content'])
    assert requests[0] == requests[2]
    assert 'private-response-marker' not in json.dumps(requests)
    assert result.metadata['request_context_estimate']['token_count'] == max(
        budget_tokens(json.dumps(request['messages'], ensure_ascii=False)) for request in requests)


def test_query_analysis_truncation_keeps_existing_retry_request(settings):
    requests = []
    def provider(request):
        requests.append(json.loads(request.content))
        return httpx.Response(200, json={'choices': [{
            'finish_reason': 'length' if len(requests) == 1 else 'stop',
            'message': {'content': '{"judgments": []}'},
        }]})
    model = DeepSeekModel(settings.model_copy(update={'model_retries': 1}), api_key='synthetic',
                          transport=httpx.MockTransport(provider))
    model.generate('query_analysis', {}, RelationBatch)
    assert len(requests) == 2 and requests[0] == requests[1]
