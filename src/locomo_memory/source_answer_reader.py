"""Explicit, opt-in source reader; extraction-only time handles never reach QA.

Callers own retrieval and must declare the independently citable raw-source scope.
This reader cannot recover missing evidence or establish semantic entailment.
"""
from copy import deepcopy
from dataclasses import dataclass

from pydantic import ValidationError

from .evidence_catalog import EvidenceCatalog
from .layered_evidence import ContractViolation
from .model import ModelFailure
from .query_schemas import EvidenceAnswer
from .source_reader import SupportedAnswer, source_payload, bind_supported_answer

SOURCE_ANSWER_READER_VERSION = 'source-statements-v2-no-time-handles-integration-budget-v1'


def reading_payload(catalog, payload):
    """Preserve text, speaker and session anchor without exposing T addresses."""
    wire = source_payload(catalog, payload, include_hints=False)
    wire['turns'] = [{k: v for k, v in turn.items() if k != 'time_expressions'}
                     for turn in wire['turns']]
    return wire


@dataclass
class SourceReading:
    answer: EvidenceAnswer
    metadata: dict
    evidence_audit: list


class SourceAnswerReader:
    """Reuse a model's metering and finite-call policy, with strict raw binding.

    No default application path is changed. Sources in ``context.raw_sources``
    must already be delivered and independently permitted as citation targets.
    Memory-to-source attachment alone never creates that permission.
    """

    def __init__(self, model):
        self.model = model

    def generate(self, payload, *, context, on_call=None):
        if type(context.get('input_budget')) is not int or context['input_budget'] < 1:
            raise ContractViolation('explicit_reader_input_budget_required')
        sources = payload.get('sources', [])
        source_map = {s['source_id']: s for s in sources}
        raw = context.get('raw_sources')
        if not isinstance(raw, dict) or any(
                sid not in source_map or source_map[sid] != source
                for sid, source in raw.items()):
            raise ContractViolation('explicit_delivered_raw_scope_required')
        catalog = EvidenceCatalog(sources, payload.get('memories', []), raw_source_ids=raw)
        # No accepted citations can depend on unseen context-only Memory IDs.
        expected_memories = {m['memory_id']: m for m in payload.get('memories', [])}
        if context.get('memories') != expected_memories or context.get('status') != payload.get('status'):
            raise ContractViolation('reader_context_payload_mismatch')
        wire = reading_payload(catalog, payload)
        generated = self.model.generate('source_statements', wire, SupportedAnswer,
                                        context=deepcopy(context), on_call=on_call)
        try:
            answer, audit = bind_supported_answer(catalog, generated.value, context, source_only=True)
        except (ValidationError, ContractViolation) as error:
            raise ModelFailure('source_answer_binding_invalid', generated.metadata) from error
        metadata = {**generated.metadata, 'source_reader': {
            'version': SOURCE_ANSWER_READER_VERSION,
            'independently_citable_source_ids': sorted(raw),
            'semantic_support': 'not_established_by_binding'}}
        return SourceReading(answer=answer, metadata=metadata, evidence_audit=audit)
