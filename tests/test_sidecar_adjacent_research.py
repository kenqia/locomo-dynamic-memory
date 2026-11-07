"""Adjacent synthetic regression oracles; never count as real quality labels."""
from copy import deepcopy
import json
from pathlib import Path
import pytest
from tools.research_v2.sidecar_schema import SidecarInput
from tools.research_v2.sidecar_core import diagnose
from tools.research_v2.sidecar_research import research_view

CASES = json.loads((Path(__file__).parent / 'fixtures/sidecar_cases.json').read_text())['cases']

@pytest.mark.parametrize('reverse', [False, True])
def test_competing_birth_year_source_in_one_memory_survives(reverse):
    d = deepcopy(CASES[12]['input']); d['claims'] = d['claims'][:1]; d['sources'] = d['sources'][:1]
    other = dict(d['sources'][0], source_id='birth-other', turn_id='D1:99', text='My birth year is 1991.')
    d['sources'].append(other); d['claims'][0]['source_ids'].append(other['source_id'])
    if reverse: d['claims'][0]['source_ids'].reverse(); d['sources'].reverse()
    q = diagnose(SidecarInput.model_validate(d), enabled=True).query
    assert q.evidence_status == 'conflict' and q.answer is None
    assert set(q.source_ids) == set(d['claims'][0]['source_ids'])

@pytest.mark.parametrize('reverse', [False, True])
def test_attendance_contradiction_never_claims_supported(reverse):
    d = deepcopy(CASES[0]['input']); d['claims'] = d['claims'][:1]; d['sources'] = d['sources'][:1]
    other = dict(d['sources'][0], source_id='deny', turn_id='D1:99', text='I did not attend the Berlin conference on May 1.')
    d['sources'].append(other); d['claims'][0]['source_ids'].append('deny')
    if reverse: d['claims'][0]['source_ids'].reverse(); d['sources'].reverse()
    c = diagnose(SidecarInput.model_validate(d), enabled=True).claims[0]
    assert c.attended == 'unknown' and 'conflicting_attendance_evidence' in c.warnings
    assert set(c.attendance_support_source_ids) | set(c.attendance_denial_source_ids) == set(c.source_ids)

@pytest.mark.parametrize('expression', ['June 2026', 'last week'])
def test_claim_temporal_expression_does_not_borrow_different_source_time(expression):
    d = deepcopy(CASES[3]['input'])
    d['claims'][0]['content'] = f'I arrived in {expression}.'
    d['sources'][0]['text'] = 'I arrived on May 1, 2026.'
    assert diagnose(SidecarInput.model_validate(d), enabled=True).claims[0].event_time.status == 'unknown'


def test_omitted_year_past_event_not_promoted_to_future_day():
    d = deepcopy(CASES[3]['input']); d['sources'][0]['reported_at'] = '2026-01-02T10:00:00+00:00'
    d['sources'][0]['text'] = 'I arrived on December 31.'
    assert diagnose(SidecarInput.model_validate(d), enabled=True).claims[0].event_time.status == 'unknown'


def test_calendar_underflow_does_not_escape_diagnostic_decorator():
    d = deepcopy(CASES[3]['input']); d['sources'][0]['reported_at'] = '0001-01-01T00:00:00+00:00'
    original = {'answer': 'unchanged'}
    result = research_view(original, d, enabled=True)
    assert result.response is original and result.status == 'diagnosed'
    assert result.diagnostic.claims[0].event_time.status == 'unknown'


def test_unexpected_internal_exception_preserves_original(monkeypatch):
    import tools.research_v2.sidecar_research as wrapper
    def fail(*args, **kwargs): raise OverflowError('synthetic, no private text')
    monkeypatch.setattr(wrapper, 'diagnose', fail)
    original = object(); result = wrapper.research_view(original, CASES[0]['input'], enabled=True)
    assert result.response is original and result.status == 'diagnostic_failed'
    assert result.diagnostic is None and result.error_code == 'sidecar_diagnostic_failed'

@pytest.mark.parametrize('qualifier', ['before', 'after', 'around', 'by'])
def test_claim_qualifier_cannot_borrow_exact_source_day(qualifier):
    d = deepcopy(CASES[3]['input'])
    d['claims'][0]['content'] = f'I arrived {qualifier} May 1, 2026.'
    d['sources'][0]['text'] = 'I arrived on May 1, 2026.'
    assert diagnose(SidecarInput.model_validate(d), enabled=True).claims[0].event_time.status == 'unknown'

@pytest.mark.parametrize('kind', ['network', 'sqlite'])
def test_study_abort_is_not_swallowed_by_diagnostic_failure_isolation(monkeypatch, kind):
    import runpy
    import tools.research_v2.sidecar_research as wrapper
    study = runpy.run_path(str(Path(__file__).parents[1] / 'research/sidecar-20261107/run.py'))
    guard = study['forbidden_' + kind]
    monkeypatch.setattr(wrapper, 'diagnose', guard)
    with pytest.raises(study['StudyAbort']):
        wrapper.research_view(object(), CASES[0]['input'], enabled=True)
    assert study['ATTEMPTS'][kind] == 1
