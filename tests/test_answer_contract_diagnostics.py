"""Synthetic answer contract failures remain strict and become distinguishable."""
from copy import deepcopy
import json

import httpx
import pytest
from pydantic import ValidationError

from locomo_memory.diagnostics import validation_diagnostics
from locomo_memory.model import DeepSeekModel, ModelFailure
from locomo_memory.query_schemas import EvidenceAnswer


def scope():
    return dict(status='sufficient', memories={
        'm1': dict(source_ids=['s1']), 'm2': dict(source_ids=['s2'])})


def valid():
    return dict(status='sufficient', answer='Supported synthetic answer.',
                citations=[dict(memory_id='m1', source_ids=['s1'])])


@pytest.mark.parametrize('case,code', [
    ('blank', 'answer_nonblank_required'),
    ('status', 'answer_evidence_status_required'),
    ('missing_citations', 'answer_citations_required'),
    ('foreign_memory', 'answer_memory_citation_scope_required'),
    ('null_memory', 'answer_memory_citation_scope_required'),
    ('foreign_memory_source', 'answer_memory_citation_scope_required'),
    ('duplicate_memory_source', 'answer_memory_citation_scope_required'),
    ('foreign_raw_source', 'answer_raw_citation_scope_required'),
    ('duplicate_raw_source', 'answer_raw_citation_scope_required'),
    ('conflict_memory_one_side', 'answer_conflict_sides_required'),
    ('conflict_raw_one_side', 'answer_conflict_sides_required'),
])
def test_existing_answer_rejections_have_specific_safe_codes(case, code):
    value, context = valid(), scope()
    if case == 'blank':
        value['answer'] = ' \t\n'
    if case == 'status':
        context['status'] = 'insufficient'
    if case == 'missing_citations':
        value['citations'] = []
    if case == 'foreign_memory':
        value['citations'][0]['memory_id'] = 'private-marker'
    if case == 'null_memory':
        value['citations'][0]['memory_id'] = None
    if case == 'foreign_memory_source':
        value['citations'][0]['source_ids'] = ['s2']
    if case == 'duplicate_memory_source':
        value['citations'][0]['source_ids'] = ['s1', 's1']
    if case in {'foreign_raw_source', 'duplicate_raw_source', 'conflict_raw_one_side'}:
        context['raw_sources'] = {'s1': dict(text='private-context-marker')}
        value['citations'][0]['memory_id'] = None
        value['citations'][0]['source_ids'] = ['private-marker'] if case == 'foreign_raw_source' else ['s1', 's1'] if case == 'duplicate_raw_source' else ['s1']
    if case.startswith('conflict_'):
        context['status'] = value['status'] = 'conflict'
        # Repeating a citation cannot substitute for a second endpoint.
        value['citations'] *= 2
    with pytest.raises(ValidationError) as failure:
        EvidenceAnswer.model_validate(value, context=context)
    diagnostic = validation_diagnostics(failure.value, EvidenceAnswer)
    assert diagnostic == [dict(failure_stage='domain_validation', error_code=code, field_path=None)]
    assert 'private-' not in json.dumps(diagnostic)


@pytest.mark.parametrize('case', ['memory', 'raw', 'conflict_memory', 'conflict_raw', 'downgrade', 'insufficient', 'no_context'])
def test_existing_valid_answer_boundaries_still_pass(case):
    value, context = valid(), scope()
    if case in {'raw', 'conflict_raw'}:
        context['raw_sources'] = {'s1': {}, 's2': {}}
        value['citations'][0]['memory_id'] = None
    if case.startswith('conflict_'):
        context['status'] = value['status'] = 'conflict'
        value['citations'].append(dict(memory_id=None if case == 'conflict_raw' else 'm2', source_ids=['s2']))
    if case in {'downgrade', 'insufficient'}:
        value.update(status='insufficient', citations=[])
        if case == 'insufficient':
            context['status'] = 'insufficient'
    if case == 'no_context':
        context = None
    assert EvidenceAnswer.model_validate(value, context=context).model_dump() == {**value, 'explanation': None}


@pytest.mark.parametrize('operation', ['answer', 'answer_raw'])
def test_adapter_preserves_answer_diagnostic_and_usage_without_retry_or_text(settings, operation):
    requests, observations = [], []
    value, context = valid(), scope()
    value['answer'] = 'private-answer-marker'
    value['explanation'] = 'private-explanation-marker'
    value['citations'][0]['source_ids'] = ['private-source-marker']
    code = 'answer_memory_citation_scope_required'
    if operation == 'answer_raw':
        value['citations'][0]['memory_id'] = None
        context['raw_sources'] = {'s1': {}}
        code = 'answer_raw_citation_scope_required'

    def provider(request):
        requests.append(request)
        return httpx.Response(200, json=dict(choices=[dict(finish_reason='stop', message=dict(
            content=json.dumps(value), reasoning_content='private-reasoning-marker'))],
            usage=dict(prompt_tokens=100, completion_tokens=10, total_tokens=110)))

    model = DeepSeekModel(settings.model_copy(update=dict(model_retries=0)), api_key='synthetic',
                          transport=httpx.MockTransport(provider))
    with pytest.raises(ModelFailure) as failure:
        model.generate(operation, {}, EvidenceAnswer, context=context,
                       on_call=lambda c: observations.append(deepcopy(c)))
    assert failure.value.code == 'invalid_output'
    call = failure.value.metadata['calls'][0]
    assert (call['http_status'], call['finish_reason'], call['failure_stage'], call['error_code'], call['field_path']) == (200, 'stop', 'domain_validation', code, None)
    assert call['usage']['total_tokens'] == 110
    assert len(requests) == len(failure.value.metadata['calls']) == 1
    assert observations[-1] == call
    assert 'private-' not in json.dumps([failure.value.metadata, observations])


@pytest.mark.parametrize('arm', ['A', 'D'])
def test_answer_diagnostic_survives_persisted_ablation_trace(settings, sample, arm):
    from fastapi.testclient import TestClient
    from locomo_memory.ablation import AblationService
    from locomo_memory.api import create_app
    from locomo_memory.query_schemas import QueryRequest
    from test_builds import completion
    from test_queries import complete_build, query_provider
    from test_retrieval import ControlledEmbedder

    answers = []

    def provider(request):
        payload = json.loads(json.loads(request.content)['messages'][1]['content'])
        if payload.get('operation') == 'answer':
            answers.append(payload)
            return completion(dict(status='sufficient', answer='private-answer-marker', citations=[]))
        return query_provider(request)

    local = settings.model_copy(update=dict(model_retries=0))
    model = DeepSeekModel(local, api_key='synthetic', transport=httpx.MockTransport(provider))
    with TestClient(create_app(local, model=model, embedder=ControlledEmbedder())) as client:
        did, bid = complete_build(client, sample)
        service = AblationService(client.app.state.queries)
        prepared = service.prepare(QueryRequest(dataset_id=did, sample_id='conv-a', build_id=bid,
                                                question='Where does Alex live?'))
        trace = service.execute(prepared, arm, 1)
        assert trace['outcome'] == 'failed'
        assert trace['error'] == dict(stage='answer', code='invalid_output')
        calls = trace['operations']['answer']['calls']
        assert len(answers) == len(calls) == 1
        assert calls[0]['error_code'] == 'answer_citations_required'
        assert client.app.state.queries.get(trace['trace_id']) == trace
        assert 'private-answer-marker' not in json.dumps(trace)
