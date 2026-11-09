"""Shared sources do not consume the final evidence budget more than once."""
from types import SimpleNamespace

import pytest

from locomo_memory.imports import canonical_json
from locomo_memory.model import Generation, ModelFailure
from locomo_memory.queries import QueryService
from locomo_memory.query_schemas import EvidenceAnswer
from locomo_memory.retrieval import budget_tokens


class DeliveredAnswer:
    def __init__(self):
        self.payloads = []

    def generate(self, operation, payload, schema, *, context):
        self.payloads.append(payload)
        value = dict(status=payload['status'], answer='Supported facts.', citations=[
            dict(memory_id=m['memory_id'], source_ids=m['source_ids']) for m in payload['memories']])
        return Generation(EvidenceAnswer.model_validate(value, context=context), {'calls': []})


def evidence():
    sources = {'shared': dict(source_id='shared', text='Synthetic background. ' * 160)}
    memories = [dict(memory_id='m1', source_ids=['shared'], content='Alex paints.'),
                dict(memory_id='m2', source_ids=['shared'], content='Alex plays the violin.')]
    return memories, sources


def cost(memories, sources):
    selected = {sid: sources[sid] for m in memories for sid in m['source_ids']}
    return budget_tokens(canonical_json(dict(memories=memories, sources=list(selected.values()))))


def service(settings, budget):
    return SimpleNamespace(settings=settings.model_copy(update={'evidence_token_budget': budget}),
                           model=DeliveredAnswer())


def test_shared_turn_delivers_both_atomic_facts_when_exact_payload_fits(settings):
    memories, sources = evidence()
    q = service(settings, cost(memories, sources))
    answer, delivered, budget = QueryService.generate_answer(q, 'Activities?', {}, memories, sources, 'sufficient')
    assert delivered == memories
    assert len(q.model.payloads[0]['sources']) == 1
    assert budget['token_count'] == q.settings.evidence_token_budget
    assert budget['omitted_memory_ids'] == []


def test_one_token_below_full_payload_preserves_order_and_reports_omission(settings):
    memories, sources = evidence()
    q = service(settings, cost(memories, sources) - 1)
    _, delivered, budget = QueryService.generate_answer(q, 'Activities?', {}, memories, sources, 'sufficient')
    assert delivered == memories[:1]
    assert budget['omitted_memory_ids'] == ['m2']
    assert budget['token_count'] == cost(delivered, sources)
    assert budget['token_count'] <= q.settings.evidence_token_budget


def test_conflict_evidence_is_not_partially_sent_when_budget_is_too_small(settings):
    memories, sources = evidence()
    q = service(settings, cost(memories[:1], sources))
    audit = {}
    with pytest.raises(ModelFailure) as failure:
        QueryService.generate_answer(q, 'Which is true?', {}, memories, sources, 'conflict', audit=audit)
    assert failure.value.code == 'conflict_evidence_budget_exceeded'
    assert failure.value.metadata['calls'] == []
    assert q.model.payloads == []
    assert audit['effective_memories'] == []
    assert audit['evidence_budget']['omitted_memory_ids'] == ['m1', 'm2']


def test_full_text_keeps_complete_raw_sources_under_tiny_rag_budget(settings):
    _, sources = evidence()
    q = service(settings, 1)
    # The production Full Text answer validator permits raw-only citations.
    class RawAnswer:
        def generate(self, operation, payload, schema, *, context):
            assert payload['sources'] == list(sources.values())
            value = dict(status='sufficient', answer='Supported raw fact.',
                         citations=[dict(memory_id=None, source_ids=['shared'])])
            return Generation(EvidenceAnswer.model_validate(value, context=context), {'calls': []})
    q.model = RawAnswer()
    _, delivered, budget = QueryService.generate_answer(q, 'Activities?', {}, [], sources, 'sufficient',
                                                       raw_sources=list(sources.values()))
    assert delivered == list(sources.values())
    assert budget['budget'] is None and not budget['truncated']
