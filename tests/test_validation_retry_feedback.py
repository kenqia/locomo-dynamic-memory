"""Finite retries use safe diagnostics, retain usage and recheck input budgets."""
from copy import deepcopy
import json

import httpx
import pytest
from pydantic import ValidationError

from locomo_memory.diagnostics import validation_diagnostics
from locomo_memory.memory_schemas import ExtractionBatch
from locomo_memory.model import DeepSeekModel, ModelFailure, request_token_estimate
from locomo_memory.query_schemas import EffectiveResolution, EvidenceAnswer
from locomo_memory.raw_schemas import MixedResolution


def extraction():
    value = dict(memories=[dict(content='Alex painted yesterday.', memory_type='event',
        statement_type='fact', polarity='positive', entity_id='Alex', state_dimension='painting',
        source_ids=['s1'], time=dict(original_expression='yesterday', anchor_source_id='s1',
        event_start='2023-05-01', event_end='2023-05-01', basis='Relative to May 2.'))])
    return value, dict(sources={'s1': {'text': 'I painted yesterday.'}, 's2': {'text': 'I like painting.'}})


@pytest.mark.parametrize('case,code', [
    ('uncited', 'extraction_time_anchor_cited'),
    ('expression', 'extraction_time_expression_required'),
])
def test_extraction_constraints_are_distinguished_and_still_strict(case, code):
    value, context = extraction()
    if case == 'uncited':
        value['memories'][0]['source_ids'] = ['s2']
    else:
        value['memories'][0]['time']['original_expression'] = 'private-invalid-expression'
    with pytest.raises(ValidationError) as failure:
        ExtractionBatch.model_validate(value, context=context)
    assert validation_diagnostics(failure.value, ExtractionBatch) == [dict(
        failure_stage='domain_validation', error_code=code, field_path='memories[0]')]


def query_case(operation):
    if operation == 'resolve':
        value = dict(status='sufficient', effective_memory_ids=['m1'], decisions=[
            dict(memory_id='m1', selected=True, reason='Supported')], explanation='Supported')
        bad = {**value, 'decisions': [], 'explanation': 'private-invalid-answer'}
        return EffectiveResolution, dict(memories={'m1': {}}, sources={}), value, bad, 'resolution_every_candidate_required'
    value = dict(status='sufficient', answer='Supported fact.',
                 citations=[dict(memory_id='m1', source_ids=['s1'])])
    bad = {**value, 'citations': [], 'answer': 'private-invalid-answer'}
    return EvidenceAnswer, dict(status='sufficient', memories={'m1': dict(source_ids=['s1'])}), value, bad, 'answer_citations_required'


@pytest.mark.parametrize('operation', ['resolve', 'answer'])
def test_retry_contains_only_safe_diagnostic_and_revalidates_full_output(settings, operation):
    schema, context, good, bad, code = query_case(operation)
    requests, outputs = [], iter([bad, good])
    def provider(request):
        requests.append(json.loads(request.content))
        return httpx.Response(200, json=dict(choices=[dict(finish_reason='stop', message=dict(
            content=json.dumps(next(outputs)), reasoning_content='private-hidden-output'))],
            usage=dict(prompt_tokens=100, completion_tokens=10, total_tokens=110)))
    model = DeepSeekModel(settings.model_copy(update={'model_retries': 1}), api_key='synthetic',
                          transport=httpx.MockTransport(provider))
    result = model.generate(operation, {'operation': operation}, schema, context=context)
    feedback = json.loads(requests[1]['messages'][1]['content'])['retry_feedback']
    assert feedback['error_code'] == code
    assert 'private-' not in json.dumps([feedback, result.metadata])
    assert requests[0]['messages'][0] == requests[1]['messages'][0]
    assert result.metadata['calls'][1]['retry_feedback_mode'] == 'full'
    assert [c['outcome'] for c in result.metadata['calls']] == ['invalid_output', 'succeeded']
    assert sum(c['usage']['total_tokens'] for c in result.metadata['calls']) == 220


@pytest.mark.parametrize('operation', ['resolve', 'answer'])
def test_invalid_retries_do_not_repair_state_or_citations_in_controller(settings, operation):
    schema, context, _, bad, code = query_case(operation)
    requests = []
    def provider(request):
        requests.append(request)
        return httpx.Response(200, json=dict(choices=[dict(finish_reason='stop', message=dict(content=json.dumps(bad)))]))
    model = DeepSeekModel(settings.model_copy(update={'model_retries': 1}), api_key='synthetic',
                          transport=httpx.MockTransport(provider))
    with pytest.raises(ModelFailure) as failure:
        model.generate(operation, {}, schema, context=context)
    assert len(requests) == len(failure.value.metadata['calls']) == 2
    assert all(c['error_code'] == code for c in failure.value.metadata['calls'])


@pytest.mark.parametrize('operation', ['resolve', 'answer'])
def test_feedback_cannot_bypass_input_budget_or_lose_prior_usage(settings, operation):
    schema, context, _, bad, _ = query_case(operation)
    payload = {'operation': operation}
    context = {**context, 'input_budget': request_token_estimate(operation, payload, schema)}
    calls = []
    def provider(request):
        calls.append(request)
        return httpx.Response(200, json=dict(choices=[dict(finish_reason='stop', message=dict(content=json.dumps(bad)))],
            usage=dict(prompt_tokens=100, completion_tokens=10, total_tokens=110)))
    model = DeepSeekModel(settings.model_copy(update={'model_retries': 2}), api_key='synthetic',
                          transport=httpx.MockTransport(provider))
    with pytest.raises(ModelFailure) as failure:
        model.generate(operation, payload, schema, context=context)
    assert failure.value.code == 'input_budget_exceeded'
    assert len(calls) == len(failure.value.metadata['calls']) == 1
    assert failure.value.metadata['calls'][0]['usage']['total_tokens'] == 110


@pytest.mark.parametrize('case', ['uncited', 'expression'])
def test_extraction_feedback_rechecks_anchor_and_expression_without_clearing_date(settings, case):
    good, context = extraction()
    bad = deepcopy(good)
    if case == 'uncited':
        bad['memories'][0]['source_ids'] = ['s2']
    else:
        bad['memories'][0]['time']['original_expression'] = 'private-invalid-expression'
    requests, outputs = [], iter([bad, good])
    def provider(request):
        requests.append(json.loads(request.content))
        return httpx.Response(200, json=dict(choices=[dict(finish_reason='stop', message=dict(content=json.dumps(next(outputs))))]))
    model = DeepSeekModel(settings.model_copy(update={'model_retries': 1}), api_key='synthetic',
                          transport=httpx.MockTransport(provider))
    result = model.generate('extract', {}, ExtractionBatch, context=context)
    feedback = json.loads(requests[1]['messages'][1]['content'])['retry_feedback']
    assert 'Do not' in feedback['instruction']
    assert 'private-' not in json.dumps(feedback)
    assert result.value.memories[0].time.event_start.isoformat() == '2023-05-01'


@pytest.mark.parametrize('operation', ['resolve', 'resolve_raw', 'answer', 'answer_raw'])
@pytest.mark.parametrize('repaired', [True, False])
def test_small_safe_diagnostic_keeps_evidence_and_strict_validation(settings, operation, repaired):
    base_operation = operation.removesuffix('_raw')
    schema, context, good, bad, code = query_case(base_operation)
    if operation == 'resolve_raw':
        schema = MixedResolution
        coverage = [dict(question='Which fact?', status='sufficient', memory_ids=['m1'])]
        good = {**good, 'coverage': coverage}
        bad = {**bad, 'coverage': coverage}
        context = {**context, 'raw_sources': {}}
    payload = dict(operation=operation, question='Which fact?',
        memories=[dict(memory_id='m1', content='Supported fact.', source_ids=['s1'])],
        sources=[dict(source_id='s1', text='Supported fact.')])
    initial = request_token_estimate(operation, payload, schema)
    context = {**context, 'input_budget': initial + 40}
    requests, outputs = [], iter([bad, good if repaired else bad])
    def provider(request):
        body = json.loads(request.content)
        requests.append(body)
        wire = json.loads(body['messages'][1]['content'])
        assert request_token_estimate(operation, wire, schema) <= context['input_budget']
        return httpx.Response(200, json=dict(choices=[dict(finish_reason='stop', message=dict(
            content=json.dumps(next(outputs)), reasoning_content='private-hidden-output'))],
            usage=dict(prompt_tokens=100, completion_tokens=10, total_tokens=110)))
    model = DeepSeekModel(settings.model_copy(update={'model_retries': 1}), api_key='synthetic',
        transport=httpx.MockTransport(provider))
    if repaired:
        result = model.generate(operation, payload, schema, context=context)
        metadata = result.metadata
    else:
        with pytest.raises(ModelFailure) as failure:
            model.generate(operation, payload, schema, context=context)
        assert failure.value.code == 'invalid_output'
        metadata = failure.value.metadata
        assert all(call['error_code'] == code for call in metadata['calls'])
    assert len(requests) == len(metadata['calls']) == 2
    second = json.loads(requests[1]['messages'][1]['content'])
    assert second['retry_feedback'] == {'error_code': code, 'field_path': None}
    assert {k: v for k, v in second.items() if k != 'retry_feedback'} == json.loads(requests[0]['messages'][1]['content'])
    assert requests[0]['messages'][0] == requests[1]['messages'][0]
    assert metadata['calls'][1]['retry_feedback_mode'] == 'diagnostic_only'
    assert [call['outcome'] for call in metadata['calls']] == ['invalid_output', 'succeeded' if repaired else 'invalid_output']
    assert sum(call['usage']['total_tokens'] for call in metadata['calls']) == 220
    assert 'private-' not in json.dumps([second, metadata])
