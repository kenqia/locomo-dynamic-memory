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


def test_relation_prompt_changes_preserve_request_envelope(settings):
    requests = []
    def provider(request):
        requests.append(json.loads(request.content))
        return httpx.Response(200, json=document())
    model = DeepSeekModel(settings, api_key='synthetic', transport=httpx.MockTransport(provider))
    payload = {'diagnostic_fixture': 'synthetic'}
    model.generate('relate', payload, RelationBatch)
    body = requests[0]
    # Prompt wording is evaluated by the fixed live semantic probes. Here the
    # stable contract is the schema, user data and provider parameters.
    messages = body.pop('messages')
    assert len(messages) == 2 and messages[0]['role'] == 'system'
    assert json.loads(messages[0]['content'].split('\nJSON schema:\n', 1)[1]) == RelationBatch.model_json_schema()
    assert messages[1]['role'] == 'user' and json.loads(messages[1]['content']) == payload
    assert body == {'model': settings.model_name, 'thinking': {'type': 'disabled'},
                    'response_format': {'type': 'json_object'},
                    'temperature': settings.model_temperature, 'max_tokens': settings.model_max_tokens}


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


@pytest.mark.parametrize('label', ['RETAIN', 'UPDATE', 'CONFLICT', 'SUPERSEDE', 'undetermined'])
@pytest.mark.parametrize('statement_type', ['plan', 'intention', 'uncertain'])
def test_nonfactual_new_claim_cannot_resolve_old_fact(settings, label, statement_type):
    common = dict(build_id='b', dataset_id='d', sample_id='s', entity_id='Alex',
                  memory_type='state', state_key='s:Alex:residence')
    old = dict(common, memory_id='old', statement_type='fact', source_ids=['s1'])
    new = dict(common, memory_id='new', statement_type=statement_type, source_ids=['s2'])
    context = dict(new_memory=new, history=[old], sources={
        's1': {'text': 'I live in Paris.'},
        's2': {'text': 'I may live in Rome next year.'},
    })
    judgment = dict(old_memory_id='old', new_memory_id='new', label=label,
                    reason='A future possibility does not establish a factual transition',
                    source_ids=['s1', 's2'], support_quote='I may live in Rome next year.')
    model = DeepSeekModel(settings.model_copy(update={'model_retries': 0}), api_key='synthetic',
                          transport=httpx.MockTransport(lambda _: httpx.Response(200, json=document(json.dumps({'judgments': [judgment]})))))
    if label == 'undetermined':
        result = model.generate('relate', context, RelationBatch, context=context)
        assert result.value.judgments[0].label == 'undetermined'
    else:
        with pytest.raises(ModelFailure) as failure:
            model.generate('relate', context, RelationBatch, context=context)
        call = failure.value.metadata['calls'][0]
        assert call['failure_stage'] == 'domain_validation'
        assert call['field_path'] == 'judgments[0]'
        assert call['error_code'] == ('factual_states_required' if label == 'SUPERSEDE' else 'factual_resolution_required')


@pytest.mark.parametrize('label', ['RETAIN', 'UPDATE', 'SUPERSEDE', 'CONFLICT', 'undetermined'])
@pytest.mark.parametrize('new_changes,allowed,error_codes', [
    ({'statement_type': 'intention'}, ['undetermined'],
     {'RETAIN': 'factual_resolution_required', 'UPDATE': 'factual_resolution_required',
      'SUPERSEDE': 'factual_states_required', 'CONFLICT': 'factual_resolution_required'}),
    ({'state_key': 's:Alex:travel'}, ['UPDATE', 'undetermined'],
     {'RETAIN': 'same_state_dimension_required', 'SUPERSEDE': 'same_state_dimension_required',
      'CONFLICT': 'same_state_dimension_required'}),
    ({}, ['RETAIN', 'UPDATE', 'SUPERSEDE', 'CONFLICT', 'undetermined'], {}),
    ({'memory_type': 'event'}, ['RETAIN', 'UPDATE', 'CONFLICT', 'undetermined'],
     {'SUPERSEDE': 'factual_states_required'}),
    ({'state_key': 's:Alex:travel', 'statement_type': 'intention'}, ['undetermined'],
     {'RETAIN': 'same_state_dimension_required', 'SUPERSEDE': 'same_state_dimension_required',
      'CONFLICT': 'same_state_dimension_required', 'UPDATE': 'factual_resolution_required'}),
])
def test_candidate_label_prerequisites_match_validation_without_mutating_input(settings, label, new_changes, allowed, error_codes):
    from copy import deepcopy
    common = dict(build_id='b', dataset_id='d', sample_id='s', entity_id='Alex',
                  memory_type='state', statement_type='fact', state_key='s:Alex:residence',
                  source_ids=['s1'])
    history = [dict(common, memory_id=memory_id) for memory_id in ['z-old', 'a-old']]
    new = {**common, 'memory_id': 'new', **new_changes}
    source = {'text': 'I live in Paris and may move to Rome.'}
    context = dict(new_memory=new, history=history, sources={'s1': source})
    payload = dict(new_memory=new, history=history, sources=[source])
    original_payload, original_context = deepcopy(payload), deepcopy(context)
    judgments = [dict(old_memory_id=old['memory_id'], new_memory_id='new', label=label,
                      reason='Compare the supplied residence claims', source_ids=['s1'],
                      support_quote=source['text']) for old in history]
    requests = []
    def provider(request):
        requests.append(json.loads(request.content))
        return httpx.Response(200, json=document(json.dumps({'judgments': judgments})))
    model = DeepSeekModel(settings.model_copy(update={'model_retries': 0}), api_key='synthetic',
                          transport=httpx.MockTransport(provider))
    if label in allowed:
        assert model.generate('relate', payload, RelationBatch, context=context).value.judgments[0].label == label
    else:
        with pytest.raises(ModelFailure) as failure:
            model.generate('relate', payload, RelationBatch, context=context)
        assert failure.value.metadata['calls'][0]['error_code'] == error_codes[label]
    sent = json.loads(requests[0]['messages'][1]['content'])
    assert sent['allowed_labels_by_old_memory'] == {'z-old': allowed, 'a-old': allowed}
    assert list(sent['allowed_labels_by_old_memory']) == ['z-old', 'a-old']
    assert sent['history'] == history
    assert payload == original_payload and context == original_context


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
