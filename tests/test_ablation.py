"""Verify the experimental controls against real SQLite and existing services."""
import httpx
import json
import pytest
from fastapi.testclient import TestClient

from locomo_memory.api import create_app
from locomo_memory.model import DeepSeekModel
from locomo_memory.ablation import AblationService, ARMS
from locomo_memory.query_schemas import QueryRequest
from test_queries import complete_build, query_provider
from test_retrieval import ControlledEmbedder


def test_expansion_controls_disable_both_paths_without_changing_default(settings, sample):
    local = settings.model_copy(update={"initial_k": 1})
    model = DeepSeekModel(local, api_key="synthetic-test-key", transport=httpx.MockTransport(query_provider))
    with TestClient(create_app(local, model=model, embedder=ControlledEmbedder())) as client:
        _, build_id = complete_build(client, sample)
        service = client.app.state
        initial = service.retrieval.query(build_id, "Where does Alex live?")
        query_id = initial["query_id"]
        plain = service.expansion.expand(query_id, include_relations=False, include_state_history=False)
        same_key = service.expansion.expand(query_id, include_relations=False)
        full = service.expansion.expand(query_id)
        assert len(plain["candidates"]) == 1
        assert not plain["added_candidates"]
        assert plain["state_history_enabled"] is False
        assert len(same_key["candidates"]) == len(full["candidates"]) == 2
        assert {o["kind"] for c in same_key["added_candidates"] for o in c["origins"]} == {"state_key"}
        assert any(o["kind"] == "relation" for c in full["added_candidates"] for o in c["origins"])


def test_five_arms_share_analysis_and_expose_selection_before_answer_budget(settings, sample):
    calls = []
    def provider(request):
        payload = json.loads(json.loads(request.content)["messages"][1]["content"])
        calls.append(payload)
        if payload.get("operation") == "resolve":
            from test_builds import completion
            selected = payload["memories"][-1]["memory_id"]
            return completion(dict(status="sufficient", effective_memory_ids=[selected],
                decisions=[dict(memory_id=m["memory_id"], selected=m["memory_id"] == selected,
                    reason="Controlled applicable evidence") for m in payload["memories"]],
                explanation="Controlled selection"))
        return query_provider(request)
    local = settings.model_copy(update={"initial_k": 1})
    model = DeepSeekModel(local, api_key="synthetic-test-key", transport=httpx.MockTransport(provider))
    with TestClient(create_app(local, model=model, embedder=ControlledEmbedder())) as client:
        dataset_id, build_id = complete_build(client, sample)
        service = AblationService(client.app.state.queries)
        prepared = service.prepare(QueryRequest(dataset_id=dataset_id, sample_id="conv-a", build_id=build_id,
            question="Where does Alex live?"))
        calls.clear()
        traces = {arm: service.execute(prepared, arm, 1) for arm in ARMS}
        assert all(t["outcome"] == "succeeded" for t in traces.values())
        assert [p["operation"] for p in calls].count("answer") == 5
        assert [p["operation"] for p in calls].count("resolve") == 3
        assert all(p["operation"] in ("answer", "resolve") for p in calls)
        assert {t["prepared_fingerprint"] for t in traces.values()} == {prepared["fingerprint"]}
        assert len(traces["A"]["expanded"]["candidates"]) == len(traces["C"]["expanded"]["candidates"]) == 1
        assert len(traces["B"]["expanded"]["candidates"]) == len(traces["D"]["expanded"]["candidates"]) == 2
        assert traces["D"]["resolution_input"]["relations"]
        assert traces["E"]["resolution_input"]["relations"] == []
        assert traces["D"]["resolution_selected_memory_ids"]
        assert traces["D"]["answer_selected_memory_ids"] == traces["D"]["resolution_selected_memory_ids"]
        assert traces["D"]["answer_input"]["memories"] == traces["D"]["effective_memories"]
        assert "ANNOTATION ONLY" not in json.dumps(calls)
        assert all(t["extra_raw_retrieval"] is False for t in traces.values())
        tampered = json.loads(json.dumps(prepared))
        tampered["question"] = "A changed question"
        with pytest.raises(Exception, match="prepared_input_changed"):
            service.execute(tampered, "A", 1)


def test_invalid_resolution_fails_in_its_arm_without_raw_recovery(settings, sample):
    calls = []
    from test_builds import completion
    def provider(request):
        payload = json.loads(json.loads(request.content)["messages"][1]["content"])
        calls.append(payload.get("operation"))
        return completion({}) if payload.get("operation") == "resolve" else query_provider(request)
    local = settings.model_copy(update={"model_retries": 0})
    model = DeepSeekModel(local, api_key="synthetic-test-key", transport=httpx.MockTransport(provider))
    with TestClient(create_app(local, model=model, embedder=ControlledEmbedder())) as client:
        dataset_id, build_id = complete_build(client, sample)
        service = AblationService(client.app.state.queries)
        prepared = service.prepare(QueryRequest(dataset_id=dataset_id, sample_id="conv-a", build_id=build_id,
            question="Where does Alex live?"))
        calls.clear()
        trace = service.execute(prepared, "D", 1)
        assert trace["outcome"] == "failed"
        assert trace["error"] == {"stage": "resolve", "code": "invalid_output"}
        assert calls == ["resolve"]
        assert "strategy_recovery" not in trace
        assert client.app.state.queries.get(trace["trace_id"]) == trace


def test_opt_in_ablation_cannot_bypass_complete_resolution_input_limit(settings, sample):
    calls = []
    def provider(request):
        payload = json.loads(json.loads(request.content)['messages'][1]['content'])
        calls.append(payload.get('operation'))
        return query_provider(request)
    local = settings.model_copy(update={'resolution_input_budget': 1, 'model_retries': 0})
    model = DeepSeekModel(local, api_key='synthetic-test-key', transport=httpx.MockTransport(provider))
    with TestClient(create_app(local, model=model, embedder=ControlledEmbedder())) as client:
        dataset_id, build_id = complete_build(client, sample)
        service = AblationService(client.app.state.queries)
        prepared = service.prepare(QueryRequest(dataset_id=dataset_id, sample_id='conv-a', build_id=build_id,
                                               question='Where does Alex live?'))
        calls.clear()
        state = client.get(f'/builds/{build_id}/current-state').json()
        for arm in ('C', 'D', 'E'):
            trace = service.execute(prepared, arm, 1)
            assert trace['outcome'] == 'failed'
            assert trace['error'] == {'stage':'resolve', 'code':'complete_resolution_input_budget_exceeded'}
            assert trace['resolution_budgets']['resolve']['source_delivery']['status'] == 'not_sent'
            assert trace['resolution_input']['memories']
            assert client.app.state.queries.get(trace['trace_id']) == trace
        assert calls == []
        assert client.get(f'/builds/{build_id}/current-state').json() == state
