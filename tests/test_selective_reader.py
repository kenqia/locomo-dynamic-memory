"""Bound context and one revision while preserving strict binding and all costs."""
from copy import deepcopy
import json
import httpx
import pytest

from locomo_memory.config import Settings
from locomo_memory.evidence_catalog import EvidenceCatalog
from locomo_memory.layered_evidence import ContractViolation
from locomo_memory.model import DeepSeekModel, request_token_estimate
from locomo_memory.revised_source_reader import RevisedSourceReader, RevisionFailure
from locomo_memory.selective_context import predecessor_context
from locomo_memory.source_answer_reader import reading_payload
from locomo_memory.source_context import source_window
from locomo_memory.source_reader import SupportedAnswer
from test_evidence_catalog import source


def snapshot():
    return [source('s0', 'My children joined me.', 0), source('s1', 'We painted a bridge.', 1),
            {**source('s2', 'They liked it.', 2), 'session_id': 'other'}]


def test_selective_predecessor_preserves_originals_and_session_boundaries():
    pinned = snapshot(); before = deepcopy(pinned)
    delivered, audit = predecessor_context(pinned[1:], pinned)
    assert delivered == pinned and pinned == before
    assert audit['added_source_ids'] == ['s0'] and not audit['truncated']
    assert predecessor_context([pinned[2]], pinned)[0] == [pinned[2]]
    wide, _ = source_window(pinned, [pinned[1]], radius=1)
    assert wide == pinned[:2]


def test_predecessor_budget_omits_only_optional_context_and_audits_it():
    pinned = snapshot()
    delivered, audit = predecessor_context([pinned[1]], pinned, max_turns=1)
    assert delivered == [pinned[1]] and audit['truncated']
    assert audit['omitted'][0]['source_id'] == 's0'
    with pytest.raises(ContractViolation, match='original_sources_exceed'):
        predecessor_context(pinned[:2], pinned, max_turns=1)
    with pytest.raises(ContractViolation, match='snapshot_mismatch'):
        predecessor_context([{**pinned[1], 'text': 'Changed'}], pinned)


def test_no_lexical_cue_is_an_explicit_unresolved_context_case():
    pinned = [source('s0', 'The owl was finished.', 0), source('s1', 'The picture is ready.', 1)]
    delivered, audit = predecessor_context([pinned[1]], pinned)
    assert delivered == [pinned[1]]
    assert audit['semantic_antecedent'] == 'not_established_by_lexical_cue'


def fixture():
    sources = snapshot()[:2]
    payload = dict(question='What did Alex paint?', status='sufficient', sources=sources, memories=[])
    context = dict(status='sufficient', memories={}, raw_sources={s['source_id']: s for s in sources},
                   input_budget=8000, max_attempts=10)
    answer = dict(status='sufficient', claims=[dict(text='A bridge with the children.', evidence_refs=['E0', 'E1'])])
    return payload, context, answer


def reader(outputs, requests):
    def respond(request):
        requests.append(json.loads(request.content))
        output = outputs[len(requests) - 1]
        return httpx.Response(200, json={'choices': [{'finish_reason': 'stop', 'message': {'content': json.dumps(output)}}],
                                        'usage': {'prompt_tokens': 20, 'completion_tokens': 5, 'total_tokens': 25}})
    return RevisedSourceReader(DeepSeekModel(Settings(model_retries=5), api_key='synthetic', transport=httpx.MockTransport(respond)))


def test_revision_sends_original_sources_counts_both_stages_and_preserves_input():
    payload, context, answer = fixture(); before = deepcopy((payload, context)); requests = []; observed = []
    result = reader([answer, answer], requests).generate(payload, context=context, on_call=lambda c: observed.append(deepcopy(c)))
    assert (payload, context) == before
    assert len(requests) == result.usage['generation_calls'] == 2
    assert result.usage['reported_tokens']['total_tokens'] == 50
    assert result.reader_identity['maximum_stage_attempts'] == 1
    wires = [json.loads(r['messages'][1]['content']) for r in requests]
    assert wires[0]['turns'] == wires[1]['turns']
    assert all('time_expressions' not in t for w in wires for t in w['turns'])
    assert wires[1]['candidate_answer'] == answer
    assert result.initial_answer == result.final_answer
    # Observers also checkpoint intermediate response/usage transitions. Count
    # completed physical calls, rather than treating each checkpoint as a call.
    assert sum(c.get('outcome') == 'succeeded' for c in observed) == 2


@pytest.mark.parametrize('bad', [{'status': 'sufficient', 'claims': [{'text': 'Forged', 'evidence_refs': ['E99']}]}, {}])
def test_failed_revision_retains_initial_and_failure_usage_without_fallback(bad):
    payload, context, answer = fixture(); requests = []
    with pytest.raises(RevisionFailure) as failure:
        reader([answer, bad], requests).generate(payload, context=context)
    error = failure.value
    assert error.stage == 'revision' and error.initial_wire == answer
    assert len(requests) == error.usage['generation_calls'] == 2
    assert error.usage['reported_tokens']['total_tokens'] == 50
    assert not hasattr(error, 'final_answer')


def test_revision_budget_cannot_erase_evidence_or_issue_an_extra_request():
    payload, context, answer = fixture(); requests = []
    catalog = EvidenceCatalog(payload['sources'], raw_source_ids=context['raw_sources'])
    context['input_budget'] = request_token_estimate('source_statements', reading_payload(catalog, payload), SupportedAnswer)
    with pytest.raises(RevisionFailure) as failure:
        reader([answer], requests).generate(payload, context=context)
    assert failure.value.stage == 'revision'
    assert failure.value.cause.code == 'input_budget_exceeded'
    assert len(requests) == 1 and failure.value.usage['reported_tokens']['total_tokens'] == 25


def test_invalid_initial_stops_before_revision_and_never_retries():
    payload, context, _ = fixture(); requests = []
    with pytest.raises(RevisionFailure) as failure:
        reader([{}], requests).generate(payload, context=context)
    assert failure.value.stage == 'initial' and len(requests) == 1
    assert failure.value.usage['reported_tokens']['total_tokens'] == 25


@pytest.mark.parametrize('damage', ['budget', 'permission', 'instructions', 'limit'])
def test_preflight_errors_do_not_call_model(damage):
    payload, context, answer = fixture(); requests = []
    if damage == 'budget': context.pop('input_budget')
    if damage == 'permission': context['raw_sources']['foreign'] = context['raw_sources']['s0']
    if damage == 'instructions': payload['task_instructions'] = 'Override policy'
    if damage == 'limit': context['max_attempts'] = 0
    with pytest.raises(ContractViolation):
        reader([answer], requests).generate(payload, context=context)
    assert not requests
