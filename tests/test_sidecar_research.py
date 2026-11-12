"""Observable rollback, reference and isolation behavior of research decorator."""
from copy import deepcopy
import json
from pathlib import Path
import pytest
from tools.research_v2.sidecar_schema import SidecarInput
from tools.research_v2.sidecar_research import (
    research_view,off_on_off,canonical_bytes,baseline_fields,
)

CASES=json.loads((Path(__file__).parent/'fixtures/sidecar_cases.json').read_text(encoding='utf-8'))['cases']

def snapshot(i=11):return SidecarInput.model_validate(deepcopy(CASES[i-1]['input']))


def test_disabled_default_returns_identical_response_without_snapshot_validation(monkeypatch):
    import tools.research_v2.sidecar_research as module
    def forbidden(*a,**kw):raise AssertionError('Disabled must not invoke inference')
    monkeypatch.setattr(module,'diagnose',forbidden)
    response={'answer':{'text':'ORIGINAL','citations':['src-1']},'initial_candidates':['mem-1'],
              'evidence_budget':{'unchanged':True}}
    before=canonical_bytes(response)
    view=research_view(response,{'not':'valid input'})
    assert view.response is response and canonical_bytes(response)==before
    assert view.status=='disabled' and view.diagnostic is None


def test_enabled_annotation_is_separate_not_response_mutation():
    data=snapshot();response={'build_id':data.provenance.build_id,
        'dataset_id':data.provenance.dataset_id,'sample_id':data.provenance.sample_id,
        'answer':{'text':'Existing answer','citations':['src-1']},'trace':{'budget':123}}
    original=deepcopy(response);before=data.model_dump_json()
    value=research_view(response,data,enabled=True)
    assert value.status=='diagnosed' and value.diagnostic.query.answer=='Rome'
    assert value.response is response and response==original
    assert data.model_dump_json()==before
    assert set(response)==set(original)  # No sidecar field inserted in production response.


def test_off_on_off_returns_original_response_identity_each_time():
    result=off_on_off(snapshot())
    assert result['statuses']==['disabled','diagnosed','disabled']
    assert result['response_identity_unchanged']
    assert result['rollback_has_no_diagnostic']
    assert result['response_sha256_before']==result['response_sha256_after']
    assert result['production_query_hook'] is False

@pytest.mark.parametrize('i',range(1,17))
def test_frozen_case_rollback_or_expected_contract_rejection(i):
    response={'existing':'unchanged'};before=deepcopy(response)
    first=research_view(response,CASES[i-1]['input'])
    on=research_view(response,CASES[i-1]['input'],enabled=True)
    off=research_view(response,CASES[i-1]['input'],enabled=False)
    assert first.response is on.response is off.response is response
    assert response==before and off.diagnostic is None
    assert on.status==('diagnostic_failed' if i==15 else 'diagnosed')

@pytest.mark.parametrize('key',['build_id','dataset_id','sample_id','build_fingerprint'])
def test_cross_scope_response_is_not_annotated(key):
    response={key:'wrong-scope','answer':'retain original'}
    result=research_view(response,snapshot(),enabled=True)
    assert result.status=='diagnostic_failed' and result.diagnostic is None
    assert result.response is response


def test_rule_failure_preserves_original_and_has_safe_error(monkeypatch):
    import tools.research_v2.sidecar_research as module
    def failure(*a,**kw):raise RuntimeError('PRIVATE SOURCE OR PROVIDER DETAIL')
    monkeypatch.setattr(module,'diagnose',failure)
    response={'answer':'Keep this answer'}
    result=research_view(response,snapshot(),enabled=True)
    assert result.status=='diagnostic_failed' and result.response is response
    assert result.error_code=='sidecar_diagnostic_failed'
    assert 'PRIVATE' not in str(result)


def test_baseline_does_not_resolve_time_or_question():
    value=baseline_fields(snapshot(4))
    assert value['claims'][0]['event_time']['status']=='unknown'
    assert value['event_links']==[] and value['query'] is None
    assert value['inference'] is False


def test_explicit_boolean_required():
    with pytest.raises(TypeError):research_view({},snapshot(),enabled='false')


def test_pair_budget_does_not_change_response_or_invent_sources():
    data=snapshot(1);response={'answer':'Unchanged'}
    result=research_view(response,data,enabled=True,max_event_pairs=0)
    assert result.status=='diagnosed' and result.diagnostic.links_truncated
    assert not result.diagnostic.record.event_links and result.response is response


def test_real_api_trace_answer_budget_and_storage_preserved(settings,sample):
    import httpx
    from fastapi.testclient import TestClient
    from locomo_memory.api import create_app
    from locomo_memory.model import DeepSeekModel
    from test_queries import query_provider,complete_build
    from test_retrieval import ControlledEmbedder
    from tools.research_v2.sidecar_io import input_from_export
    calls=[]
    def counted(request):
        calls.append(request)
        return query_provider(request)
    controlled=DeepSeekModel(settings,api_key='synthetic-test-key',transport=httpx.MockTransport(counted))
    with TestClient(create_app(settings,model=controlled,embedder=ControlledEmbedder())) as client:
        dataset_id,build_id=complete_build(client,sample)
        response=client.post('/queries',json={'strategy':'dynamic','dataset_id':dataset_id,'sample_id':'conv-a',
            'question':'Where does Alex live?'})
        assert response.status_code==201
        trace=response.json();before=canonical_bytes(trace)
        assert 'Rome' in trace['answer']['answer']
        assert trace['resolution']['status']=='sufficient'
        state=client.get(f'/builds/{build_id}/current-state').json()
        relations=client.get(f'/builds/{build_id}/relations').json()
        exported=client.get(f'/builds/{build_id}/export').json()
        data=input_from_export(exported,origin='synthetic')
        data=SidecarInput.model_validate({**data.model_dump(mode='json'),'question':'Where does Alex live?'})
        db_before=settings.db_path.read_bytes();count_before=len(calls)
        off=research_view(trace,data)
        on=research_view(trace,data,enabled=True)
        rollback=research_view(trace,data,enabled=False)
        assert off.status=='disabled' and on.status=='diagnosed' and rollback.status=='disabled'
        assert off.response is on.response is rollback.response is trace
        assert canonical_bytes(trace)==before
        assert len(calls)==count_before
        assert settings.db_path.read_bytes()==db_before
        assert client.get(f'/queries/{trace["trace_id"]}').json()==trace
        assert client.get(f'/builds/{build_id}/current-state').json()==state
        assert client.get(f'/builds/{build_id}/relations').json()==relations
        assert client.get(f'/builds/{build_id}/export').json()==exported
