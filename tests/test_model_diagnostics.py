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
    ({'reason': ' '}, 'nonblank_reason_required', 'judgments[0]'),
    ({'source_ids': ['s1', 's1']}, 'unique_evidence_required', 'judgments[0]'),
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
    assert call['failure_stage'] == ('domain_validation' if code in {'applicability_range_reversed', 'nonblank_reason_required', 'unique_evidence_required'} else 'schema_validation')
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


def test_relation_request_adds_label_and_unique_source_guidance_only(settings):
    import hashlib
    requests = []
    def provider(request):
        requests.append(request.content)
        return httpx.Response(200, json=document())
    model = DeepSeekModel(settings, api_key='synthetic', transport=httpx.MockTransport(provider))
    model.generate('relate', {'diagnostic_fixture': 'synthetic'}, RelationBatch)
    body = json.loads(requests[0])
    gate = ('First compare the supplied state_key values exactly. RETAIN, SUPERSEDE and\n'
            'CONFLICT are allowed only when old.state_key equals new.state_key. Do not\n'
            'reinterpret different keys as the same dimension. For different keys, still\n'
            'assess UPDATE under its same-process evidence rule; otherwise use undetermined.\n')
    assert gate in body['messages'][0]['content']
    unique_sources = ("Each judgment's source_ids must be a set-like list with no repeated IDs, including\n"
                      'when both endpoint memories cite the same source. A shared source_id covers both\n'
                      'endpoints when it supports both; list it once. Preserve evidence for each endpoint.\n')
    assert unique_sources in body['messages'][0]['content']
    # Removing the added instructions must reproduce the independently captured
    # pre-diagnostics request: same schema, payload, parameters and other guidance.
    body['messages'][0]['content'] = body['messages'][0]['content'].replace(gate, '', 1)
    body['messages'][0]['content'] = body['messages'][0]['content'].replace(unique_sources, '', 1)
    with httpx.Client() as client:
        previous = client.build_request('POST', 'https://api.deepseek.com/chat/completions', json=body)
    assert hashlib.sha256(previous.content).hexdigest() == '0b048493bd7e67c7abd18b392d33c9563cb1c269d1897033774c3b0394b80846'


@pytest.mark.parametrize('label', ['UPDATE', 'undetermined'])
@pytest.mark.parametrize('source_ids', [['s1'], ['s1', 's1']])
def test_one_shared_source_can_support_both_endpoints_but_duplicate_ids_fail(settings, label, source_ids):
    common = dict(build_id='b', dataset_id='d', sample_id='s', entity_id='Alex',
                  memory_type='state', statement_type='fact', source_ids=['s1'])
    old = dict(common, memory_id='old', state_key='s:Alex:research')
    new = dict(common, memory_id='new', state_key='s:Alex:application')
    context = dict(new_memory=new, history=[old],
                   sources={'s1': {'text': 'I researched agencies and submitted an application.'}})
    judgment = dict(old_memory_id='old', new_memory_id='new', label=label,
                    reason='The same source describes two stages', source_ids=source_ids,
                    support_quote='I researched agencies and submitted an application.')
    model = DeepSeekModel(settings.model_copy(update={'model_retries': 0}), api_key='synthetic',
                          transport=httpx.MockTransport(lambda _: httpx.Response(200, json=document(json.dumps({'judgments': [judgment]})))))
    if len(source_ids) == 1:
        assert model.generate('relate', context, RelationBatch, context=context).value.judgments[0].source_ids == ['s1']
    else:
        with pytest.raises(ModelFailure) as failure:
            model.generate('relate', context, RelationBatch, context=context)
        assert failure.value.metadata['calls'][0]['error_code'] == 'unique_evidence_required'


@pytest.mark.parametrize('label', ['RETAIN', 'SUPERSEDE', 'CONFLICT', 'UPDATE', 'undetermined'])
def test_state_key_gate_preserves_cross_dimension_update_and_undetermined(settings, label):
    common = dict(build_id='b', dataset_id='d', sample_id='s', entity_id='Alex',
                  memory_type='state', statement_type='fact')
    old = dict(common, memory_id='old', state_key='s:Alex:research', source_ids=['s1'])
    new = dict(common, memory_id='new', state_key='s:Alex:application', source_ids=['s2'])
    sources = {'s1': {'text': 'I researched agencies.'}, 's2': {'text': 'I submitted the application.'}}
    context = dict(new_memory=new, history=[old], sources=sources)
    judgment = dict(old_memory_id='old', new_memory_id='new', label=label,
                    reason='Evidence for stages of the same process', source_ids=['s1', 's2'],
                    support_quote='I submitted the application.')
    model = DeepSeekModel(settings.model_copy(update={'model_retries': 0}), api_key='synthetic',
                          transport=httpx.MockTransport(lambda _: httpx.Response(200, json=document(json.dumps({'judgments': [judgment]})))))
    if label in {'UPDATE', 'undetermined'}:
        result = model.generate('relate', context, RelationBatch, context=context)
        assert result.value.judgments[0].label == label
    else:
        with pytest.raises(ModelFailure) as failure:
            model.generate('relate', context, RelationBatch, context=context)
        assert failure.value.metadata['calls'][0]['error_code'] == 'same_state_dimension_required'


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
