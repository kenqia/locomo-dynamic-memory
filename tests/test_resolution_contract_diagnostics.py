"""Resolver constraints remain strict while their failures become distinguishable."""
from copy import deepcopy
import json

import httpx
import pytest
from pydantic import ValidationError

from locomo_memory.diagnostics import validation_diagnostics
from locomo_memory.model import DeepSeekModel, ModelFailure, request_messages
from locomo_memory.query_schemas import EffectiveResolution


def scope():
    return dict(memories={mid: dict(memory_id=mid) for mid in ('m1', 'm2')}, sources={})


def valid():
    return dict(status='sufficient', effective_memory_ids=['m1'],
        decisions=[dict(memory_id=mid, selected=mid == 'm1', reason='Source-backed scope') for mid in ('m1','m2')],
        explanation='Supplied evidence', supplemental_relations=[])


@pytest.mark.parametrize('case,code', [
    ('blank_explanation', 'resolution_explanation_required'),
    ('foreign_selected', 'resolution_unique_supplied_ids_required'),
    ('duplicate_selected', 'resolution_unique_supplied_ids_required'),
    ('missing_decision', 'resolution_every_candidate_required'),
    ('duplicate_decision', 'resolution_every_candidate_required'),
    ('selection_mismatch', 'resolution_selection_agreement_required'),
    ('sufficient_empty', 'resolution_sufficient_evidence_required'),
    ('conflict_one_side', 'resolution_conflict_sides_required'),
    ('unknown_endpoints', 'resolution_supplemental_endpoints_required'),
])
def test_existing_rejections_have_specific_safe_codes(case, code):
    value = valid()
    if case == 'blank_explanation': value['explanation'] = ' '
    if case == 'foreign_selected': value['effective_memory_ids'] = ['private-marker']
    if case == 'duplicate_selected': value['effective_memory_ids'] *= 2
    if case == 'missing_decision': value['decisions'].pop()
    if case == 'duplicate_decision': value['decisions'][1] = deepcopy(value['decisions'][0])
    if case == 'selection_mismatch': value['decisions'][1]['selected'] = True
    if case == 'sufficient_empty':
        value['effective_memory_ids'] = []
        for item in value['decisions']: item['selected'] = False
    if case == 'conflict_one_side': value['status'] = 'conflict'
    if case == 'unknown_endpoints':
        value['supplemental_relations'] = [dict(old_memory_id='private-marker',new_memory_id='m2',
            label='undetermined',reason='Unsupported endpoint',source_ids=['s1'])]
    with pytest.raises(ValidationError) as failure:
        EffectiveResolution.model_validate(value, context=scope())
    diagnostics = validation_diagnostics(failure.value, EffectiveResolution)
    assert diagnostics == [dict(failure_stage='domain_validation', error_code=code, field_path=None)]
    assert 'private-marker' not in json.dumps(diagnostics)


@pytest.mark.parametrize('omitted', ['time_anchor_source_id','original_time_expression','time_basis'])
def test_dates_without_each_provenance_field_still_fail(omitted):
    value = valid()
    applicability = dict(from_date='2023-05-27', time_anchor_source_id='s1',
        original_time_expression='May 27',time_basis='Explicit literal date')
    del applicability[omitted]
    value['supplemental_relations'] = [dict(old_memory_id='m1',new_memory_id='m2',label='undetermined',
        reason='Uncertain',source_ids=['s1','s2'],applicability=applicability)]
    with pytest.raises(ValidationError) as failure:
        EffectiveResolution.model_validate(value, context=scope())
    assert validation_diagnostics(failure.value, EffectiveResolution) == [dict(failure_stage='domain_validation',
        error_code='applicability_time_evidence_required', field_path='supplemental_relations[0].applicability')]


def test_prompt_explains_date_provenance_without_silently_dropping_supported_dates():
    prompt = request_messages('resolve', {}, EffectiveResolution)[0]['content'].split('\nJSON schema:',1)[0]
    for name in ('from_date','to_date','time_anchor_source_id','original_time_expression','time_basis',
                 'effective_memory_ids','decisions','condition_source_ids'):
        assert name in prompt
    assert 'Do not clear a supported date' in prompt


def test_provider_failure_keeps_code_and_usage_without_retry(settings):
    value = valid(); value['decisions'].pop()
    requests = []
    def provider(request):
        requests.append(request)
        return httpx.Response(200,json=dict(choices=[dict(finish_reason='stop',message=dict(content=json.dumps(value)))],
            usage=dict(prompt_tokens=100,completion_tokens=10,total_tokens=110)))
    model = DeepSeekModel(settings.model_copy(update=dict(model_retries=0)), api_key='synthetic',
        transport=httpx.MockTransport(provider))
    with pytest.raises(ModelFailure) as failure:
        model.generate('resolve', {}, EffectiveResolution, context=scope())
    call = failure.value.metadata['calls'][0]
    assert call['error_code'] == 'resolution_every_candidate_required'
    assert call['usage']['total_tokens'] == 110 and len(requests) == 1


def test_valid_output_still_passes():
    assert EffectiveResolution.model_validate(valid(),context=scope()).effective_memory_ids == ['m1']
