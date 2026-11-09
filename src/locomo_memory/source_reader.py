"""Opt-in source-grounded statements; all prose follows one evidence contract.

This is a new declared raw-source interface, not repair of old R.E references.
Binding checks delivered provenance, never natural-language entailment.
"""
from typing import Literal

from .evidence_catalog import CatalogAnswer, CatalogClaim, EvidenceCatalog, ANSWER_PROMPT
from .layered_contracts import Contract
from .layered_evidence import ContractViolation

SOURCE_READER_VERSION = 'source-statements-v1'


class SupportedAnswer(Contract):
    status: Literal['sufficient', 'conflict', 'insufficient']
    claims: list[CatalogClaim]


def source_payload(catalog: EvidenceCatalog, payload, *, include_hints=True):
    wire = catalog.answer_payload(payload)
    wire['turns'] = [turn for turn, source in zip(catalog.turns, catalog.sources.values())
                     if source['source_id'] in catalog.raw_ids]
    wire['evidence_refs'] = [ref for ref, unit in catalog.units.items()
                             if unit['source_id'] in catalog.raw_ids]
    hints = [{k:v for k,v in memory.items() if k not in {'memory_ref','evidence_refs'}}
             for memory in wire.pop('memories')]
    wire.pop('raw_evidence_refs')
    if include_hints:
        wire['unverified_memory_hints'] = hints
    return wire


def bind_supported_answer(catalog, value, context, *, source_only=False):
    candidate = SupportedAnswer.model_validate(value)
    claims = []
    for claim in candidate.claims:
        refs = claim.evidence_refs
        if source_only:
            if any(ref not in catalog.units or
                   catalog.units[ref]['source_id'] not in catalog.raw_ids for ref in refs):
                raise ContractViolation('unknown_delivered_source_excerpt')
            refs = ['R.'+ref for ref in refs]
        claims.append({'text':claim.text,'evidence_refs':refs})
    # Qualifications and scope statements remain in claims. There is no free
    # explanation channel that can introduce unsupported factual assertions.
    return catalog.bind_answer(CatalogAnswer(status=candidate.status,claims=claims),context)


ALL_STATEMENTS = '''
Every factual sentence you output, including qualifications, uncertainty and explanatory
context needed to answer the question, MUST be an atomic claim with supporting evidence_refs.
There is no separate explanation field. Do not omit necessary qualifications or supported
facts to satisfy this format. Avoid unrelated background. Cite source excerpts that support
the entire assertion, including actor, event identity, time, completion and type.
If none of the requested facts is supported, return status insufficient and empty claims.
Evidence that a person likes a subject or plans an action cannot establish completion.
Treat supplied summaries as unverified hints; raw source text determines support.
'''

QUALIFIED_PROMPT = ANSWER_PROMPT.replace(
    'Explanation must also be supported and relevant.', '') + ALL_STATEMENTS
SOURCE_PROMPT = QUALIFIED_PROMPT.replace(
    'evidence_refs selects qualified M0.E0 etc\nfrom that memory\'s evidence_refs, or R.E0 from raw_evidence_refs. The backend binds IDs.',
    'evidence_refs selects plain E0, E1 etc from the supplied evidence_refs list. '
    'Each handle identifies an original text excerpt. The backend binds source IDs.')
SOURCE_PROMPT += '''
Only the original source excerpts are citation targets. unverified_memory_hints, if present,
help locate topics but do not establish facts, collaborators, types or event identity.
Use the exact plain E handles shown in evidence_refs; M and R prefixes are not this interface.
'''

PROMPTS = {'qualified_statements':QUALIFIED_PROMPT, 'source_statements':SOURCE_PROMPT}
