"""Frozen expectations are an independent oracle; engine sees only input.

These tests assert diagnostic semantics, not real QA quality or course accuracy.
"""
import json
from copy import deepcopy
from pathlib import Path
import pytest
from pydantic import ValidationError
from tools.research_v2.sidecar_core import diagnose
from tools.research_v2.sidecar_schema import SidecarInput

CASES=json.loads((Path(__file__).parent/'fixtures/sidecar_cases.json').read_text(encoding='utf-8'))['cases']

def case(i):return deepcopy(CASES[i-1]['input'])

def run(data,**kwargs):return diagnose(SidecarInput.model_validate(data),enabled=True,**kwargs)

@pytest.mark.parametrize('frozen',CASES,ids=lambda c:c['case_id'])
def test_frozen_behavior(frozen):
    before=deepcopy(frozen['input'])
    if not frozen['expected_contract_valid']:
        with pytest.raises(ValidationError):run(before)
        return
    result=run(before)
    expect=frozen['expected_behavior']
    # No expected behavior or case identity is supplied to diagnose().
    assert before==frozen['input']
    if 'event_link' in expect:
        assert len(result.record.event_links)==1
        assert result.record.event_links[0].decision==expect['event_link']
        assert result.record.event_links[0].reason_code
    if 'time_status' in expect:assert result.claims[0].event_time.status==expect['time_status']
    if 'event_start' in expect:assert result.claims[0].event_time.start.isoformat()==expect['event_start']
    if 'event_end' in expect:assert result.claims[0].event_time.end.isoformat()==expect['event_end']
    if 'reported_day' in expect:assert result.claims[0].reported_at[0][:10]==expect['reported_day']
    if 'completed' in expect:assert result.claims[0].completed==expect['completed']
    if 'attended' in expect:assert result.claims[0].attended==expect['attended']
    if 'answer' in expect:assert result.query.answer==expect['answer']
    if 'evidence_status' in expect:assert result.query.evidence_status==expect['evidence_status']
    if 'source_ids' in expect:assert set(result.query.source_ids)==set(expect['source_ids'])
    if 'retain_memory_ids' in expect:assert result.retained_memory_ids==tuple(expect['retain_memory_ids'])
    if 'global_mutation' in expect:assert result.global_mutation==expect['global_mutation']
    if 'event_links' in expect:assert list(result.record.event_links)==expect['event_links']

@pytest.mark.parametrize('text,day,status',[
    ('I arrived on 2024-02-29.','2024-02-29','known'),
    ('I arrived on 2023-02-29.',None,'unknown'),
    ('I arrived in February 2024.','2024-02-01','range'),
    ('I arrived this week.','2026-05-04','range'),
    ('I arrived last week.','2026-04-27','range'),
    ('I arrived last Sunday.','2026-05-03','known'),
    ('I arrived on May 1 and May 8.',None,'unknown'),
    ('I arrived next month.',None,'unknown'),
    ('I might arrive on May 1.',None,'unknown'),
    ('I arrived on May 1 if invited.',None,'unknown'),
])
def test_time_boundaries(text,day,status):
    data=case(4);data['sources'][0]['text']=text
    result=run(data).claims[0].event_time
    assert result.status==status
    assert (result.start.isoformat() if result.start else None)==day


def test_bad_derived_date_does_not_override_source():
    data=case(4)
    data['claims'][0]['event_time']={'status':'known','start':'2030-01-01','end':'2030-01-01',
        'original_expression':'yesterday','anchor_source_id':'src-1','basis':'Extracted guess'}
    assert run(data).claims[0].event_time.start.isoformat()=='2026-05-09'


def test_no_source_expression_does_not_trust_derived_dates():
    data=case(5)
    data['claims'][0]['event_time']={'status':'known','start':'2026-05-01','end':'2026-05-01',
        'original_expression':'recently','anchor_source_id':'src-1','basis':'Extracted guess'}
    assert run(data).claims[0].event_time.status=='unknown'


def test_default_disabled_and_deterministic():
    data=SidecarInput.model_validate(case(1));before=data.model_dump_json()
    disabled=diagnose(data)
    assert disabled.record.enabled is False and disabled.claims==() and disabled.query is None
    first=diagnose(data,enabled=True).model_dump_json()
    assert first==diagnose(data,enabled=True).model_dump_json()
    assert before==data.model_dump_json()


def test_engine_rejects_whole_case_expected_labels():
    with pytest.raises(TypeError):diagnose(CASES[0],enabled=True)
    data=case(1);data['expected_behavior']={'event_link':'same_event'}
    with pytest.raises(ValidationError):SidecarInput.model_validate(data)


def test_event_dates_alone_do_not_split():
    data=case(1)
    data['sources'][1]['text']='That same Berlin conference on May 2 had a keynote.'
    assert run(data).record.event_links[0].decision=='unknown'


def test_shared_event_different_people_is_not_automatically_distinct():
    data=case(1);data['sources'][1]['speaker']='Sam';data['claims'][1]['entity_id']='Sam'
    assert run(data).record.event_links[0].decision=='unknown'


def test_same_person_generic_facts_do_not_merge():
    data=case(16)
    for c in data['claims']:c['statement_type']='fact'
    assert run(data).record.event_links[0].decision=='unknown'


def test_state_similarity_does_not_create_event_identity():
    data=case(1)
    for c in data['claims']:c['memory_type']='state'
    assert run(data).record.event_links[0].decision=='unknown'


def test_quoted_utterance_not_speaker_fact():
    data=case(4);data['sources'][0]['text']='I heard Sam say "I arrived yesterday."'
    assert run(data).claims[0].event_time.status=='unknown'


def test_plan_does_not_override_residence():
    data=case(11);data['claims'][1]['statement_type']='plan'
    data['sources'][1]['text']='I plan to move from Paris to Rome on March 1, 2026.'
    assert run(data).query.answer=='Paris'
    assert run(data).claims[1].completed=='unknown'


def test_future_query_is_not_known_reality():
    data=case(11);data['as_of']='2027-01-01'
    assert run(data).query.evidence_status=='insufficient'
    assert run(data).query.answer is None


def test_explicit_question_date_and_request_precedence():
    data=case(12);data['as_of']=None
    assert run(data).query.answer=='Paris'
    data['as_of']='2026-04-01'
    assert run(data).query.answer=='Rome'


def test_later_report_of_past_event_is_valid_historical_evidence():
    data=case(12);data['as_of']='2026-03-15'
    # Move was reported Apr 1, happened Mar 1. Do not filter by report time.
    assert run(data).query.answer=='Rome'


def test_conflict_does_not_select_newer_value():
    data=case(13);data['sources'][1]['reported_at']='2026-06-01T10:00:00+00:00'
    assert run(data).query.evidence_status=='conflict'
    assert run(data).query.answer is None


def test_query_order_no_mutation():
    data=case(11);before=deepcopy(data)
    current=run(data)
    history=deepcopy(data);history['as_of']='2026-02-01'
    assert run(history).query.answer=='Paris'
    assert run(data)==current
    assert data==before


def test_reordered_claims_keep_residence_answer():
    data=case(11);data['claims'].reverse();data['sources'].reverse()
    assert run(data).query.answer=='Rome'


def test_renamed_memory_and_source_ids_not_hardcoded():
    data=case(11)
    for i,c in enumerate(data['claims']):c['memory_id']=f'changed-{i}';c['source_ids']=[f'x-{i}']
    for i,s in enumerate(data['sources']):s['source_id']=f'x-{i}'
    result=run(data)
    assert result.query.answer=='Rome' and result.query.memory_ids==('changed-1',)


def test_pair_budget_visible():
    result=run(case(1),max_event_pairs=0)
    assert result.links_truncated and not result.record.event_links
    with pytest.raises(ValueError):run(case(1),max_event_pairs=-1)


def test_no_report_does_not_prove_retention_or_completion():
    result=run(case(10))
    assert result.claims[0].completed=='unknown'
    assert result.record.event_links==()


def test_wrong_entity_question_unknown():
    data=case(11);data['question']='Where does Sam live?'
    assert run(data).query.evidence_status=='unknown'


def test_residence_negation_not_silently_discarded():
    data=case(11);data['claims'][1]['polarity']='negative'
    assert run(data).query.evidence_status=='unknown'


def test_empty_input_bounded_diagnostic():
    result=run(case(14))
    assert not result.claims and not result.record.event_links
    assert result.query.evidence_status=='insufficient'

@pytest.mark.parametrize('i',[1,2])
def test_event_comparison_input_order_not_semantics(i):
    data=case(i);expected=run(data).record.event_links[0].decision
    data['claims'].reverse()
    assert run(data).record.event_links[0].decision==expected


def test_other_fact_date_not_transferred_to_claim():
    data=case(4);data['sources'][0]['text']='I graduated yesterday.'
    assert run(data).claims[0].event_time.status=='unknown'


def test_last_year_qualifier_not_dropped():
    data=case(4);data['sources'][0]['text']='I arrived on May 1 last year.'
    assert run(data).claims[0].event_time.status=='unknown'


def test_unknown_dated_residence_not_silently_ignored():
    data=case(11);data['sources'][1]['text']='I moved from Paris to Rome recently.'
    assert run(data).query.evidence_status=='unknown'


def test_extract_value_disagreement_not_silently_ignored():
    data=case(11);data['claims'][1]['state_value']='London'
    assert run(data).query.evidence_status=='unknown'


def test_two_repeat_phrases_do_not_recurse_or_prove_identity():
    data=case(2)
    data['sources'][0]['text']='I visited Rome again on May 1, a second trip.'
    assert run(data).record.event_links[0].decision=='unknown'
