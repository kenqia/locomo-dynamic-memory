"""The opt-in reader hides invalid targets without expanding citation permission."""
from copy import deepcopy
import json

import httpx
import pytest

from locomo_memory.config import Settings
from locomo_memory.evidence_catalog import EvidenceCatalog
from locomo_memory.layered_evidence import ContractViolation
from locomo_memory.model import DeepSeekModel, ModelFailure
from locomo_memory.source_answer_reader import SourceAnswerReader, reading_payload


def inputs():
    source = dict(source_id='s', sample_id='c', dataset_id='d', session_id='session_1',
                  dia_id='D1:1', speaker='Lea', session_time='12:00 pm on 3 July, 2023',
                  position=0, text='I painted the moon with my kids yesterday.\nIt was fun!')
    memory = dict(memory_id='m', source_ids=['s'], content='Lea painted with a partner.', time={})
    payload = dict(question='What did Lea paint, and with whom?', time={}, status='sufficient',
                   memories=[memory], sources=[source])
    context = dict(status='sufficient', memories={'m': memory}, raw_sources={'s': source}, input_budget=12000)
    return payload, context


def test_reading_keeps_lossless_text_and_time_anchor_but_no_extraction_targets():
    payload, context = inputs()
    catalog = EvidenceCatalog(payload['sources'], payload['memories'], raw_source_ids=context['raw_sources'])
    before = deepcopy((catalog.turns, payload))
    wire = reading_payload(catalog, payload)
    assert ''.join(u['text'] for t in wire['turns'] for u in t['units']) == payload['sources'][0]['text']
    assert wire['turns'][0]['session_time'] == payload['sources'][0]['session_time']
    assert wire['evidence_refs'] == ['E0', 'E1']
    assert all('time_expressions' not in t for t in wire['turns'])
    assert 'unverified_memory_hints' not in wire
    assert (catalog.turns, payload) == before


@pytest.mark.parametrize('ref,success', [('E0', True), ('T0', False), ('R.E0', False), ('E99', False)])
def test_real_adapter_path_preserves_metering_and_strict_binding(ref, success):
    payload, context = inputs()
    original = deepcopy((payload, context))
    observed, requests = [], []
    def transport(request):
        body = json.loads(request.content)
        requests.append(body)
        content = json.dumps({'status': 'sufficient', 'claims': [
            {'text': 'Lea painted the moon with her kids.', 'evidence_refs': [ref]}]})
        return httpx.Response(200, json={'model': 'synthetic-model', 'choices': [
            {'finish_reason': 'stop', 'message': {'content': content}}],
            'usage': {'prompt_tokens': 40, 'completion_tokens': 20, 'total_tokens': 60}})
    model = DeepSeekModel(Settings(model_retries=0), api_key='synthetic-key', transport=httpx.MockTransport(transport))
    reader = SourceAnswerReader(model)
    if success:
        result = reader.generate(payload, context=context, on_call=observed.append)
        assert result.answer.citations[0].memory_id is None
        assert result.answer.citations[0].source_ids == ['s']
        assert result.evidence_audit[0]['supports'][0]['text'].endswith('\n')
        assert result.metadata['calls'][0]['usage']['total_tokens'] == 60
        assert result.metadata['source_reader']['semantic_support'] == 'not_established_by_binding'
    else:
        with pytest.raises(ModelFailure, match='source_answer_binding_invalid') as caught:
            reader.generate(payload, context=context, on_call=observed.append)
        assert caught.value.metadata['calls'][0]['usage']['total_tokens'] == 60
    assert len(requests) == 1 and observed[-1]['completed_at']
    assert 'time_expressions' not in requests[0]['messages'][-1]['content']
    assert (payload, context) == original


@pytest.mark.parametrize('mutation', ['missing', 'different_text', 'different_memories', 'different_status', 'missing_budget', 'boolean_budget'])
def test_scope_cannot_be_invented_before_model_call(mutation):
    payload, context = inputs()
    if mutation == 'missing':
        context.pop('raw_sources')
    elif mutation == 'different_text':
        context['raw_sources'] = {'s': {**context['raw_sources']['s'], 'text': 'Different text.'}}
    elif mutation == 'different_memories':
        context['memories'] = {}
    elif mutation == 'missing_budget':
        context.pop('input_budget')
    elif mutation == 'boolean_budget':
        context['input_budget'] = True
    else:
        context['status'] = 'insufficient'
    # No model object is required to demonstrate the pre-call rejection.
    with pytest.raises(ContractViolation):
        SourceAnswerReader(None).generate(payload, context=context)


def test_empty_permitted_scope_does_not_make_attached_memory_sources_citable():
    payload, context = inputs()
    context['raw_sources'] = {}
    catalog = EvidenceCatalog(payload['sources'], payload['memories'], raw_source_ids=[])
    wire = reading_payload(catalog, payload)
    assert wire['turns'] == wire['evidence_refs'] == []


def test_reader_full_input_over_budget_fails_before_http_with_zero_call_metadata():
    payload, context = inputs()
    context['input_budget'] = 1
    requests = []
    def transport(request):
        requests.append(request)
        raise AssertionError('over_budget_request_must_not_be_sent')
    model = DeepSeekModel(Settings(), api_key='synthetic-key', transport=httpx.MockTransport(transport))
    with pytest.raises(ModelFailure, match='input_budget_exceeded') as caught:
        SourceAnswerReader(model).generate(payload, context=context)
    assert requests == [] and caught.value.metadata['calls'] == []
