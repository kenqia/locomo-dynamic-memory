"""ARCH-01 structural checks, NOT proof the future inference rules work."""
import hashlib
import json
from copy import deepcopy
from pathlib import Path
import pytest
from pydantic import ValidationError
from tools.research_v2.sidecar_schema import (
    EventLink, SidecarInput, SidecarRecord, TimeInterval,
)

FIXTURES = Path(__file__).parent / 'fixtures'
MANIFEST_PATH = FIXTURES / 'sidecar_cases.json'
MANIFEST = json.loads(MANIFEST_PATH.read_text(encoding='utf-8'))
CASES = MANIFEST['cases']

def snapshot():
    return deepcopy(CASES[0]['input'])

def link(**changes):
    result = dict(left_memory_id='mem-1', right_memory_id='mem-2',
                  decision='unknown', reason_code='insufficient_identity',
                  reason='Contract example only; identity not established.',
                  source_ids=['src-1','src-2'])
    result.update(changes)
    return result

def test_frozen_manifest_identity():
    expected = (FIXTURES / 'sidecar_cases.sha256').read_text().split()[0]
    assert hashlib.sha256(MANIFEST_PATH.read_bytes()).hexdigest() == expected
    assert MANIFEST['case_count'] == 16 == len(CASES)
    assert len({c['case_id'] for c in CASES}) == 16
    assert all(c['expectation_basis'] for c in CASES)
    assert {'event_identity','time','modality','negation','as_of','uncertainty','input_integrity'} <= {c['category'] for c in CASES}

@pytest.mark.parametrize('case', CASES, ids=lambda c: c['case_id'])
def test_frozen_input_contract(case):
    # expected_behavior is deliberately NOT passed to any model or rule engine.
    if not case['expected_contract_valid']:
        with pytest.raises(ValidationError):
            SidecarInput.model_validate(case['input'])
    else:
        value = SidecarInput.model_validate(case['input'])
        assert value.provenance.origin == 'synthetic'
        assert SidecarInput.model_validate_json(value.model_dump_json()) == value

def test_output_default_is_disabled_diagnostic():
    value = SidecarRecord(snapshot=SidecarInput.model_validate(snapshot()))
    assert value.enabled is False
    assert value.mode == 'diagnostic_only'
    assert value.event_links == ()

def test_enabled_output_roundtrip_and_input_unchanged():
    payload = snapshot(); before = deepcopy(payload)
    result = SidecarRecord(snapshot=SidecarInput.model_validate(payload), enabled=True,
                           event_links=[EventLink(**link())])
    assert payload == before
    assert result.snapshot.provenance.build_fingerprint == payload['provenance']['build_fingerprint']
    assert SidecarRecord.model_validate_json(result.model_dump_json()) == result

@pytest.mark.parametrize('update', [
    {'status':'unknown','start':'2026-05-01'},
    {'status':'known','start':'2026-05-01','end':'2026-05-01'},
    {'status':'range','start':'2026-05-10','end':'2026-05-01'},
    {'status':'known','start':'2026-05-01','end':'2026-05-02'},
])
def test_invalid_time_contract(update):
    with pytest.raises(ValidationError): TimeInterval(**update)

@pytest.mark.parametrize('status,start,end', [
    ('known','2026-05-01','2026-05-01'),
    ('range','2026-04-01','2026-04-30'),
])
def test_supported_time_contract(status,start,end):
    value = TimeInterval(status=status,start=start,end=end,
        original_expression='May 1' if status=='known' else 'April',
        anchor_source_id='src-1',basis='Explicit source expression; contract check only.')
    assert value.start.isoformat() == start

def test_unknown_time_can_retain_original_expression():
    assert TimeInterval(original_expression='recently').start is None

@pytest.mark.parametrize('mutation', ['missing_source','duplicate_memory','bad_fingerprint',
    'outside_anchor','invented_expression','empty_claim','extra_field','empty_identity'])
def test_invalid_snapshot(mutation):
    data=snapshot()
    if mutation=='missing_source':data['claims'][0]['source_ids']=['missing']
    elif mutation=='duplicate_memory':data['claims'].append(deepcopy(data['claims'][0]))
    elif mutation=='bad_fingerprint':data['provenance']['build_fingerprint']='not-a-digest'
    elif mutation=='outside_anchor':data['claims'][0]['event_time']={'anchor_source_id':'src-2'}
    elif mutation=='invented_expression':data['claims'][0]['event_time']={'original_expression':'tomorrow','anchor_source_id':'src-1'}
    elif mutation=='empty_claim':data['claims'][0]['content']='   '
    elif mutation=='extra_field':data['expected_behavior']={'answer':'leaked'}
    elif mutation=='empty_identity':data['provenance']['build_id']=' '
    with pytest.raises(ValidationError):SidecarInput.model_validate(data)

@pytest.mark.parametrize('mutation', ['disabled_links','outside_endpoint','self_link',
    'outside_source','duplicate_pair','unsupported_decision','missing_reason'])
def test_invalid_output(mutation):
    data=dict(snapshot=snapshot(),enabled=True,event_links=[link()])
    if mutation=='disabled_links':data['enabled']=False
    elif mutation=='outside_endpoint':data['event_links'][0]['right_memory_id']='outside'
    elif mutation=='self_link':data['event_links'][0]['right_memory_id']='mem-1'
    elif mutation=='outside_source':data['event_links'][0]['source_ids']=['outside']
    elif mutation=='duplicate_pair':data['event_links'].append(link(left_memory_id='mem-2',right_memory_id='mem-1'))
    elif mutation=='unsupported_decision':data['event_links'][0]['decision']='same_person_so_same_event'
    elif mutation=='missing_reason':data['event_links'][0]['reason']=' '
    with pytest.raises(ValidationError):SidecarRecord.model_validate(data)

def test_unrelated_valid_source_cannot_support_link():
    data=snapshot()
    data['sources'].append(dict(source_id='src-3',session_id='s',turn_id='D1:3',
        speaker='Sam',reported_at='2026-05-10T09:00:00+00:00',text='Unrelated statement.'))
    with pytest.raises(ValidationError):
        SidecarRecord(snapshot=SidecarInput.model_validate(data),enabled=True,
                      event_links=[EventLink(**link(source_ids=['src-3']))])
