"""Safe diagnostics at the provider adapter boundary; no network access."""
import json

import httpx
import pytest

from locomo_memory.model import DeepSeekModel, ModelFailure
from locomo_memory.relation_schemas import RelationBatch


@pytest.mark.parametrize('content,stage,code,path', [
    ('{private-marker', 'json_parsing', 'invalid_json', None),
    ('{}', 'schema_validation', 'missing_field', 'judgments'),
    ('{"judgments": [], "private-marker": "private-marker"}', 'schema_validation', 'extra_field', None),
])
def test_invalid_output_has_safe_stage_code_and_schema_path(settings, content, stage, code, path):
    settings = settings.model_copy(update={'model_retries': 0})
    response = {'choices': [{'finish_reason': 'stop', 'message': {'content': content}}]}
    model = DeepSeekModel(settings, api_key='synthetic', transport=httpx.MockTransport(lambda _: httpx.Response(200, json=response)))
    with pytest.raises(ModelFailure) as failure:
        model.generate('relate', {}, RelationBatch)
    assert failure.value.code == 'invalid_output'
    call = failure.value.metadata['calls'][0]
    assert (call['failure_stage'], call['error_code'], call['field_path']) == (stage, code, path)
    assert call['finish_reason'] == 'stop'
    assert 'private-marker' not in json.dumps(failure.value.metadata)


def document(content='{"judgments": []}', **choice_changes):
    return {'choices': [{'finish_reason': 'stop', 'message': {'content': content}, **choice_changes}],
            'usage': {'prompt_tokens': 3, 'completion_tokens': 1, 'total_tokens': 4}}


@pytest.mark.parametrize('response,stage,code,finish,finish_status', [
    ([], 'provider_response', 'invalid_provider_document', None, 'not_observed'),
    ({'choices': []}, 'provider_response', 'invalid_provider_document', None, 'not_observed'),
    ({'choices': ['private-marker']}, 'provider_response', 'invalid_provider_document', None, 'not_observed'),
    (document(message={}), 'provider_response', 'invalid_provider_message', 'stop', 'reported'),
    (document(message={'content': 7}), 'provider_response', 'invalid_provider_message', 'stop', 'reported'),
    (document(content='  '), 'content', 'empty_content', 'stop', 'reported'),
    (document(finish_reason='length'), 'completion', 'non_stop_finish_reason', 'length', 'reported'),
    (document(finish_reason='content_filter'), 'completion', 'non_stop_finish_reason', 'content_filter', 'reported'),
    (document(finish_reason=None), 'completion', 'non_stop_finish_reason', None, 'missing'),
    (document(finish_reason={'private-marker': True}), 'completion', 'non_stop_finish_reason', None, 'unrecognized'),
    (document(finish_reason='private-marker'), 'completion', 'non_stop_finish_reason', None, 'unrecognized'),
])
def test_provider_structure_content_and_actual_finish_reason(settings, response, stage, code, finish, finish_status):
    settings = settings.model_copy(update={'model_retries': 0})
    model = DeepSeekModel(settings, api_key='synthetic', transport=httpx.MockTransport(lambda _: httpx.Response(200, json=response)))
    observed = []
    with pytest.raises(ModelFailure) as failure:
        model.generate('relate', {}, RelationBatch, on_call=lambda call: observed.append(dict(call)))
    call = failure.value.metadata['calls'][0]
    assert (call['failure_stage'], call['error_code']) == (stage, code)
    assert (call['finish_reason'], call['finish_reason_status']) == (finish, finish_status)
    assert observed[0]['status'] == 'started'
    assert observed[-1] == call
    assert 'private-marker' not in json.dumps(observed)


def test_missing_finish_reason_is_not_inferred_from_tokens(settings):
    response = document()
    del response['choices'][0]['finish_reason']
    model = DeepSeekModel(settings.model_copy(update={'model_retries': 0}), api_key='synthetic', transport=httpx.MockTransport(lambda _: httpx.Response(200, json=response)))
    with pytest.raises(ModelFailure) as failure:
        model.generate('relate', {}, RelationBatch)
    assert failure.value.metadata['calls'][0]['finish_reason_status'] == 'missing'


@pytest.mark.parametrize('changes,code,path', [
    ({'label': 'private-marker'}, 'invalid_enum', 'judgments[0].label'),
    ({'private-marker': 'private-marker'}, 'extra_field', 'judgments[0]'),
    ({'applicability': {'private-marker': True}}, 'extra_field', 'judgments[0].applicability'),
    ({'applicability': {'from_date': '2024-01-02', 'to_date': '2024-01-01'}}, 'applicability_range_reversed', 'judgments[0].applicability'),
    ({'reason': ' '}, 'reason_and_unique_evidence_required', 'judgments[0]'),
])
def test_schema_and_domain_diagnostics_never_echo_values_or_unknown_keys(settings, changes, code, path):
    judgment = {'old_memory_id': 'a', 'new_memory_id': 'b', 'label': 'undetermined',
                'reason': 'Unknown', 'source_ids': ['s1'], **changes}
    response = document(json.dumps({'judgments': [judgment]}))
    model = DeepSeekModel(settings.model_copy(update={'model_retries': 0}), api_key='synthetic', transport=httpx.MockTransport(lambda _: httpx.Response(200, json=response)))
    with pytest.raises(ModelFailure) as failure:
        model.generate('relate', {}, RelationBatch)
    call = failure.value.metadata['calls'][0]
    assert (call['error_code'], call['field_path']) == (code, path)
    assert call['failure_stage'] == ('domain_validation' if code in {'applicability_range_reversed', 'reason_and_unique_evidence_required'} else 'schema_validation')
    assert 'private-marker' not in json.dumps(call)


def test_successful_internal_retry_preserves_failed_call_and_usage(settings):
    responses = iter([document('{private-marker'), document()])
    requests = []
    def provider(request):
        requests.append(json.loads(request.content))
        return httpx.Response(200, json=next(responses))
    model = DeepSeekModel(settings.model_copy(update={'model_retries': 2}), api_key='synthetic', transport=httpx.MockTransport(provider))
    result = model.generate('relate', {}, RelationBatch)
    assert [c['status'] for c in result.metadata['calls']] == ['invalid_output', 'succeeded']
    assert result.metadata['calls'][0]['error_code'] == 'invalid_json'
    assert result.metadata['calls'][1]['failure_stage'] is None
    assert result.metadata['calls'][1]['finish_reason'] == 'stop'
    assert result.metadata['calls'][1]['usage']['completion_tokens'] == 1
    assert len(requests) == 2 and requests[0] == requests[1]


@pytest.mark.parametrize('error,code,stage', [
    (httpx.ReadTimeout('private-marker'), 'model_timeout', 'transport'),
    (httpx.ConnectError('private-marker'), 'model_http_error', 'transport'),
])
def test_transport_exceptions_are_safe_and_saved_before_propagation(settings, error, code, stage):
    def provider(_):
        raise error
    observed = []
    model = DeepSeekModel(settings.model_copy(update={'model_retries': 0}), api_key='synthetic', transport=httpx.MockTransport(provider))
    with pytest.raises(ModelFailure) as failure:
        model.generate('relate', {}, RelationBatch, on_call=lambda call: observed.append(dict(call)))
    assert observed[-1] == failure.value.metadata['calls'][0]
    assert observed[-1]['error_code'] == code
    assert observed[-1]['failure_stage'] == stage
    assert observed[-1]['usage'] == {} and observed[-1]['finish_reason'] is None
    assert 'private-marker' not in json.dumps(failure.value.metadata)


def test_relation_request_matches_frozen_pre_diagnostics_contract(settings):
    import hashlib
    requests = []
    def provider(request):
        requests.append(request.content)
        return httpx.Response(200, json=document())
    model = DeepSeekModel(settings, api_key='synthetic', transport=httpx.MockTransport(provider))
    model.generate('relate', {'diagnostic_fixture': 'synthetic'}, RelationBatch)
    # Independently captured from d65e380 before introducing diagnostics.
    assert hashlib.sha256(requests[0]).hexdigest() == '0b048493bd7e67c7abd18b392d33c9563cb1c269d1897033774c3b0394b80846'


def test_failed_checkpoint_does_not_trigger_another_provider_call(settings):
    from locomo_memory.model import DiagnosticPersistenceFailure
    requests = []
    def provider(request):
        requests.append(request)
        return httpx.Response(200, json=document('{}'))
    def observe(call):
        if call['status'] == 'invalid_output':
            raise ValueError('synthetic-private-marker')
    model = DeepSeekModel(settings, api_key='synthetic', transport=httpx.MockTransport(provider))
    with pytest.raises(DiagnosticPersistenceFailure, match='diagnostic_persistence_failed'):
        model.generate('relate', {}, RelationBatch, on_call=observe)
    assert len(requests) == 1
