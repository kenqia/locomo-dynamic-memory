"""Opt-in extraction with one generated proposition, not two semantic summaries.

The durable state_value retains the entire content verbatim, including modality
and negation. This is not a scalar state projection or an entailment guarantee.
No existing Memory or Build is migrated.
"""
from pydantic import Field

from .evidence_catalog import LabeledFact, labeled_fact


class PropositionFact(LabeledFact):
    model_config = {**LabeledFact.model_config, 'title': 'LabeledFact'}
    state_value: None = Field(default=None, description=(
        'Do not generate a second summary. Omit or return null. The backend stores '
        'the complete content verbatim as state_value, including negation, modality '
        'and uncertainty. All supported facts must remain in content.'))


def bind_proposition(catalog, record):
    """Validate before derivation; never silently erase a generated state value."""
    candidate = PropositionFact.model_validate(record)
    value = candidate.model_dump()
    value['state_value'] = value['content']
    converted, label = labeled_fact(value)
    memory, audit = catalog.bind_fact(converted)
    audit.update(entity_label=label, state_value_origin='verbatim_content',
                 semantic_support='not_established_by_binding')
    return memory, audit
