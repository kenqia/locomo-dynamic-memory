"""Frozen paired diagnostics, failure reporting and timing without quality claims."""
import hashlib
import json
from pathlib import Path
import pytest
from tools.research_v2.sidecar_compare import compare_manifest,write_report

FROZEN=Path(__file__).parent/'fixtures/sidecar_cases.json'

def test_paired_report_preserves_case_scope_sources_and_input():
    before=FROZEN.read_bytes()
    result=compare_manifest(FROZEN,repeats=2)
    assert result['summary']['cases']==16
    assert result['summary']['compared']==15
    assert result['summary']['contract_rejected']==1
    assert result['summary']['measured_samples_per_variant']==30
    assert result['summary']['response_unchanged_all'] and result['summary']['references_valid_all']
    assert result['provider_calls']==0 and not result['production_query_hook']
    assert result['input_sha256_before']==result['input_sha256_after']==hashlib.sha256(before).hexdigest()
    assert FROZEN.read_bytes()==before
    for row in result['cases']:
        if row['status']!='compared':continue
        assert row['rollback']['statuses']==['disabled','diagnosed','disabled']
        for variant in ('control','sidecar'):
            for metric in ('cpu','wall'):
                values=row['timing'][variant][metric]
                assert values['samples']==2
                assert 0<=values['min_ns']<=values['median_ns']<=values['max_ns']
        # No imported expected answers or case category can leak into inference inputs.
        assert 'expected_behavior' not in json.dumps(row)
        assert row['sidecar']['record']['snapshot']==row['input']


def test_report_contains_both_rule_outputs_not_fake_scores(tmp_path):
    report=write_report(FROZEN,tmp_path/'new',repeats=1)
    body=(tmp_path/'new'/'comparison.md').read_text(encoding='utf-8')
    assert 'unknown' in body and 'contract_rejected' not in body
    assert '不是生产QA基线' in body and '不评模型质量' in body
    data=json.loads((tmp_path/'new'/'comparison.json').read_text(encoding='utf-8'))
    assert data==report
    assert data['cases'][0]['control']['event_links']==[]
    assert data['cases'][0]['sidecar']['record']['event_links'][0]['decision']=='same_event'
    with pytest.raises(ValueError):write_report(FROZEN,tmp_path/'new',repeats=1)

@pytest.mark.parametrize('repeats',[0,-1,201,True,1.5])
def test_bounded_repeat_budget(repeats):
    with pytest.raises(ValueError):compare_manifest(FROZEN,repeats=repeats)


def test_bad_digest_aborts_without_outputs(tmp_path):
    path=tmp_path/'bad.json';path.write_bytes(FROZEN.read_bytes()+b' ')
    path.with_suffix('.sha256').write_text('0'*64)
    with pytest.raises(ValueError):write_report(path,tmp_path/'out',repeats=1)
    assert not (tmp_path/'out').exists()


def test_expected_labels_cannot_affect_either_variant(tmp_path):
    original=compare_manifest(FROZEN,repeats=1)
    data=json.loads(FROZEN.read_text(encoding='utf-8'))
    for case in data['cases']:
        case['expected_behavior']={'attack':'DO_NOT_USE'}
        case['expected_contract_valid']=False
        case['name']='DO_NOT_USE'
    p=tmp_path/'changed.json';p.write_text(json.dumps(data),encoding='utf-8')
    p.with_suffix('.sha256').write_text(hashlib.sha256(p.read_bytes()).hexdigest())
    altered=compare_manifest(p,repeats=1)
    for before,after in zip(original['cases'],altered['cases']):
        assert before['case_id']==after['case_id'] and before['status']==after['status']
        if before['status']=='compared':
            assert before['control']==after['control'] and before['sidecar']==after['sidecar']
    assert 'DO_NOT_USE' not in json.dumps(altered['cases'])
