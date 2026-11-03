"""HTTP failures remain distinct from model output validation failures."""
import json

import httpx
import pytest

from locomo_memory.model import DeepSeekModel, ModelFailure
from locomo_memory.relation_schemas import RelationBatch


@pytest.mark.parametrize('status,category,retryable', [
    (400, 'invalid_request', False), (401, 'authentication', False),
    (402, 'insufficient_balance', False), (403, 'permission', False),
    (408, 'temporary_service', True), (429, 'rate_limit', True),
    (500, 'temporary_service', True), (502, 'temporary_service', True),
    (503, 'temporary_service', True), (504, 'temporary_service', True),
    (422, 'invalid_request', False), (418, 'other_http', False),
])
def test_http_status_is_safe_classified_and_bounded(settings, status, category, retryable):
    requests = []
    def provider(request):
        requests.append(True)
        return httpx.Response(status, text='synthetic-private-marker', headers={'Retry-After': 'private-marker'})
    model = DeepSeekModel(settings.model_copy(update={'model_retries': 2}), api_key='synthetic',
                          transport=httpx.MockTransport(provider))
    observed = []
    with pytest.raises(ModelFailure) as failure:
        model.generate('relate', {}, RelationBatch, on_call=lambda c: observed.append(dict(c)))
    assert failure.value.code == 'model_http_error'
    calls = failure.value.metadata['calls']
    assert len(requests) == len(calls) == (3 if retryable else 1)
    assert observed[-1] == calls[-1]
    for call in calls:
        assert call['failure_stage'] == 'provider_http'
        assert call['http_status'] == status
        assert call['http_error_category'] == category
        assert call['http_retryable'] is retryable
        assert call['usage'] == {} and call['field_path'] is None
    assert 'private-marker' not in json.dumps(failure.value.metadata)


def test_temporary_http_then_domain_error_have_separate_diagnostics(settings):
    responses = iter([httpx.Response(503, text='private-marker'),
                      httpx.Response(200, json={'choices': [{'finish_reason': 'stop', 'message': {'content': '{"judgments": [{"old_memory_id": "a", "new_memory_id": "b", "label": "undetermined", "reason": " ", "source_ids": ["s"]}]}'}}]})])
    model = DeepSeekModel(settings.model_copy(update={'model_retries': 1}), api_key='synthetic',
                          transport=httpx.MockTransport(lambda _: next(responses)))
    with pytest.raises(ModelFailure) as failure:
        model.generate('relate', {}, RelationBatch)
    a, b = failure.value.metadata['calls']
    assert (a['failure_stage'], a['http_status'], a['http_error_category']) == ('provider_http', 503, 'temporary_service')
    assert (b['failure_stage'], b['error_code'], b['http_status']) == ('domain_validation', 'nonblank_reason_required', 200)
    assert b['http_error_category'] is None and b['http_retryable'] is None


def test_context_rejection_keeps_specific_code_and_does_not_retry(settings):
    model = DeepSeekModel(settings, api_key='synthetic', transport=httpx.MockTransport(
        lambda _: httpx.Response(400, json={'error': {'code': 'context_length_exceeded', 'message': 'private-marker'}})))
    with pytest.raises(ModelFailure) as failure:
        model.generate('relate', {}, RelationBatch)
    assert failure.value.code == 'context_length_exceeded'
    assert len(failure.value.metadata['calls']) == 1
    assert failure.value.metadata['calls'][0]['http_error_category'] == 'context_limit'
