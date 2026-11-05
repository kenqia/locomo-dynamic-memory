"""Retain exact proposition semantics; reject an independent generated summary."""
from copy import deepcopy
import pytest
from pydantic import ValidationError
from locomo_memory.evidence_catalog import EvidenceCatalog
from locomo_memory.proposition_extraction import bind_proposition
from test_evidence_catalog import source


def record(**fields):
    return dict(content='Alex did not plan a move yesterday.', memory_type='event',
                statement_type='fact', polarity='negative', entity_label='Alex',
                state_dimension='moving_plan', state_value=None, evidence_refs=['E0'], time_refs=['T0'], **fields)


def test_verbatim_proposition_keeps_negation_modality_time_and_input():
    catalog = EvidenceCatalog([source(text='I did not plan a move yesterday.')])
    value = record(); before = deepcopy(value)
    memory, audit = bind_proposition(catalog, value)
    assert value == before
    assert memory.content == memory.state_value == value['content']
    assert memory.polarity == 'negative' and memory.statement_type == 'fact'
    assert str(memory.time.event_start) == '2023-07-02'
    assert audit['state_value_origin'] == 'verbatim_content'
    assert audit['semantic_support'] == 'not_established_by_binding'


def test_independent_state_summary_is_rejected_not_erased():
    catalog = EvidenceCatalog([source(text='I did not plan a move yesterday.')])
    value = record(); value['state_value'] = 'moving'
    with pytest.raises(ValidationError):
        bind_proposition(catalog, value)
    assert value['state_value'] == 'moving'
