import json

import httpx
from fastapi.testclient import TestClient

from locomo_memory.api import create_app
from locomo_memory.model import DeepSeekModel
from test_builds import completion, draft
from test_relations import relation
from test_retrieval import ControlledEmbedder, build


def query_provider(request):
    payload = json.loads(json.loads(request.content)["messages"][1]["content"])
    if "operation" not in payload:
        if "new_memory" in payload:
            new = payload["new_memory"]
            return completion({"judgments": [relation(old, new, label="SUPERSEDE", reason="Explicit move", support_quote="I moved from Paris to Rome on 2 May 2023.", applicability={"from_date": "2023-05-02", "time_anchor_source_id": new["source_ids"][0], "original_time_expression": "2 May 2023", "time_basis": "Explicit source date"}) for old in payload["history"]]})
        if "sources" in payload:
            sources = payload["sources"]
            return completion({"memories": [draft([sources[0]["source_id"]]), draft([sources[2]["source_id"]], content="Alex lives in Rome.", state_value="Rome")]})
        return completion({"entities": ["Alex"], "topic": "residence", "time": None, "keywords": []})
    if payload["operation"] == "resolve":
        value = "Paris" if payload["time"]["requested_date"] == "2023-05-01" else "Rome"
        selected = [m for m in payload["memories"] if m["state_value"] == value]
        return completion({"status": "sufficient", "effective_memory_ids": [m["memory_id"] for m in selected], "decisions": [{"memory_id": m["memory_id"], "reason": "Applicable before the explicit move" if value == "Paris" else "Explicit move applies as of the cutoff", "selected": m in selected} for m in payload["memories"]], "supplemental_relations": [], "explanation": "Source-backed temporal applicability"})
    memory = payload["memories"][0]
    return completion({"status": payload["status"], "answer": f"Alex lives in {memory['state_value']}.", "citations": [{"memory_id": memory["memory_id"], "source_ids": memory["source_ids"]}]})


def complete_build(client, sample):
    sample[0]["conversation"]["session_2"][0]["text"] = "I moved from Paris to Rome on 2 May 2023."
    build_id = build(client, sample)
    assert client.post(f"/builds/{build_id}/index").status_code == 201
    assert client.post(f"/builds/{build_id}/relations").status_code == 202
    result = client.post(f"/builds/{build_id}/publish")
    assert result.status_code == 200
    return result.json()["dataset_id"], build_id


def test_current_and_historical_answers_use_fixed_version_sources_without_global_mutation(settings, sample):
    settings = settings.model_copy(update={"initial_k": 1})
    model = DeepSeekModel(settings, api_key="synthetic-test-key", transport=httpx.MockTransport(query_provider))
    with TestClient(create_app(settings, model=model, embedder=ControlledEmbedder())) as client:
        dataset_id, build_id = complete_build(client, sample)
        state = client.get(f"/builds/{build_id}/current-state").json()
        relations = client.get(f"/builds/{build_id}/relations").json()
        for requested_date, expected in [(None, "Rome"), ("2023-05-01", "Paris"), (None, "Rome")]:
            response = client.post("/queries", json={"dataset_id": dataset_id, "sample_id": "conv-a", "question": "Where does Alex live?", "requested_date": requested_date})
            assert response.status_code == 201, response.text
            result = response.json()
            assert expected in result["answer"]["answer"]
            assert result["build_id"] == build_id
            assert result["time"]["cutoff"] == "2023-05-02T13:00:00"
            assert result["time"]["origin"] == ("explicit_request" if requested_date else "conversation_cutoff")
            assert len(result["initial"]["initial_candidates"]) == 1
            assert len(result["expanded"]["added_candidates"]) == 1
            assert len(result["expanded"]["candidates"]) == 2
            assert len(result["effective_memories"]) == 1
            memory = result["effective_memories"][0]
            assert memory["build_id"] == build_id
            assert result["answer"]["citations"] == [{"memory_id": memory["memory_id"], "source_ids": memory["source_ids"]}]
            assert client.get(f"/queries/{result['trace_id']}").json() == result
        assert client.get(f"/builds/{build_id}/current-state").json() == state
        assert client.get(f"/builds/{build_id}/relations").json() == relations


def test_invalid_resolver_scope_and_answer_citations_fail_with_safe_persisted_trace(settings, sample):
    for operation in ("resolve", "answer"):
        attempts = []
        def invalid_provider(request):
            payload = json.loads(json.loads(request.content)["messages"][1]["content"])
            if payload.get("operation") == operation:
                attempts.append(payload)
                if operation == "resolve":
                    return completion({"status": "sufficient", "effective_memory_ids": ["other-build/memory"], "decisions": [], "explanation": "Invalid scope", "supplemental_relations": []})
                return completion({"status": "sufficient", "answer": "Unsupported", "citations": [{"memory_id": payload["memories"][0]["memory_id"], "source_ids": ["other-conversation/source"]}]})
            return query_provider(request)
        local = settings.model_copy(update={"db_path": settings.db_path.parent / f"{operation}.sqlite3", "model_retries": 1})
        model = DeepSeekModel(local, api_key="synthetic-test-key", transport=httpx.MockTransport(invalid_provider))
        with TestClient(create_app(local, model=model, embedder=ControlledEmbedder())) as client:
            dataset_id, build_id = complete_build(client, sample)
            response = client.post("/queries", json={"dataset_id": dataset_id, "sample_id": "conv-a", "question": "Where does Alex live?"})
            assert response.status_code == 502
            error = response.json()["error"]
            assert error["code"] == "invalid_output"
            trace = client.get(f"/queries/{error['trace_id']}").json()
            assert trace["outcome"] == "failed"
            assert trace["error"]["stage"] == operation
            assert len(trace["operations"][operation]["calls"]) == 2
            assert "answer" not in trace
            assert len(attempts) == 2


def test_future_date_and_tiny_final_budget_preserve_uncertainty(settings, sample):
    observed = []
    def cautious_provider(request):
        payload = json.loads(json.loads(request.content)["messages"][1]["content"])
        if payload.get("operation") == "answer":
            observed.append(payload)
            if payload["status"] == "insufficient":
                return completion({"status": "insufficient", "answer": "Insufficient evidence to establish the requested reality.", "citations": []})
        return query_provider(request)
    for budget in (6000, 1):
        local = settings.model_copy(update={"db_path": settings.db_path.parent / f"budget-{budget}.sqlite3", "evidence_token_budget": budget})
        model = DeepSeekModel(local, api_key="synthetic-test-key", transport=httpx.MockTransport(cautious_provider))
        with TestClient(create_app(local, model=model, embedder=ControlledEmbedder())) as client:
            dataset_id, build_id = complete_build(client, sample)
            response = client.post("/queries", json={"dataset_id": dataset_id, "sample_id": "conv-a", "question": "Where will Alex live?", "requested_date": "2099-01-01"})
            assert response.status_code == 201, response.text
            trace = response.json()
            assert trace["answer"]["status"] == "insufficient"
            assert trace["time"]["beyond_cutoff"] is True
            assert trace["evidence_budget"]["truncated"] is (budget == 1)
            assert len(trace["effective_memories"]) == (0 if budget == 1 else 1)
            assert trace["config"]["evidence_token_budget"] == budget
            assert trace["evidence_budget"]["token_count"] <= budget
            assert observed[-1]["status"] == "insufficient"


def test_conflict_insufficient_plan_and_unknown_relations_keep_evidence_semantics(settings, sample):
    def scenario_provider(request):
        payload = json.loads(json.loads(request.content)["messages"][1]["content"])
        if "new_memory" in payload:
            return completion({"judgments": [relation(old, payload["new_memory"]) for old in payload["history"]]})
        if payload.get("operation") == "resolve":
            memories = payload["memories"]
            question = payload["question"]
            selected = [m for m in memories if m["statement_type"] == "fact"] if "conflict" in question else [m for m in memories if m["state_value"] == "Paris"]
            if "unknown" in question:
                selected = []
            status = "conflict" if "conflict" in question else "insufficient" if not selected else "sufficient"
            supplemental = []
            if len(memories) >= 2:
                supplemental = [relation(memories[0], memories[1])]
            return completion({"status": status, "effective_memory_ids": [m["memory_id"] for m in selected], "decisions": [{"memory_id": m["memory_id"], "selected": m in selected, "reason": "Plan is not an accomplished move" if m["statement_type"] == "plan" else "Applicable evidence for this question"} for m in memories], "supplemental_relations": supplemental, "explanation": "Unknown relations remain undetermined"})
        if payload.get("operation") == "answer":
            status = payload["status"]
            text = {"conflict": "Conflicting evidence: Paris and Rome; the residence is unresolved.", "insufficient": "No information available for this unknown question.", "sufficient": "Alex lives in Paris; the Tokyo plan is not accomplished."}[status]
            return completion({"status": status, "answer": text, "citations": [{"memory_id": m["memory_id"], "source_ids": m["source_ids"]} for m in payload["memories"]]})
        if "sources" in payload:
            sources = payload["sources"]
            return completion({"memories": [draft([sources[0]["source_id"]]), draft([sources[1]["source_id"]], content="Alex lives in Rome.", state_value="Rome"), draft([sources[2]["source_id"]], content="Alex plans to live in Tokyo.", state_value="Tokyo", statement_type="plan")]})
        return completion({"entities": [], "topic": None, "time": None, "keywords": []})
    sample[0]["conversation"]["session_1"][1].update(speaker="Alex", text="I live in Rome.")
    sample[0]["conversation"]["session_2"][0]["text"] = "I plan to move to Tokyo."
    model = DeepSeekModel(settings, api_key="synthetic-test-key", transport=httpx.MockTransport(scenario_provider))
    with TestClient(create_app(settings, model=model, embedder=ControlledEmbedder())) as client:
        build_id = build(client, sample)
        assert client.post(f"/builds/{build_id}/index").status_code == 201
        assert client.post(f"/builds/{build_id}/relations").status_code == 202
        dataset_id = client.post(f"/builds/{build_id}/publish").json()["dataset_id"]
        original = client.get(f"/builds/{build_id}/relations").json()
        for question, status in [("Describe the conflict.", "conflict"), ("Answer the unknown detail.", "insufficient"), ("Where does Alex actually live?", "sufficient")]:
            response = client.post("/queries", json={"dataset_id": dataset_id, "sample_id": "conv-a", "question": question})
            assert response.status_code == 201, response.text
            trace = response.json()
            assert trace["answer"]["status"] == status
            assert trace["resolution"]["supplemental_relations"][0]["label"] == "undetermined"
            if status == "sufficient":
                assert [m["statement_type"] for m in trace["effective_memories"]] == ["fact"]
                assert "not accomplished" in trace["answer"]["answer"]
            if status == "conflict":
                assert len(trace["answer"]["citations"]) == 2
            if status == "insufficient":
                assert trace["effective_memories"] == []
        assert client.get(f"/builds/{build_id}/relations").json() == original


def test_query_pins_complete_version_before_analysis_while_new_version_publishes(settings, sample):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    entered, release = Event(), Event()
    pause = {"enabled": False}
    def barrier_provider(request):
        payload = json.loads(json.loads(request.content)["messages"][1]["content"])
        if pause["enabled"] and set(payload) == {"question"}:
            entered.set()
            assert release.wait(timeout=15)
        return query_provider(request)
    model = DeepSeekModel(settings, api_key="synthetic-test-key", transport=httpx.MockTransport(barrier_provider))
    with TestClient(create_app(settings, model=model, embedder=ControlledEmbedder())) as client:
        dataset_id, old = complete_build(client, sample)
        pause["enabled"] = True
        with ThreadPoolExecutor(max_workers=1) as executor:
            pending = executor.submit(client.post, "/queries", json={"dataset_id": dataset_id, "sample_id": "conv-a", "question": "Where does Alex live?"})
            try:
                assert entered.wait(timeout=10)
                new = client.post("/builds", json={"dataset_id": dataset_id, "sample_id": "conv-a"}).json()["build_id"]
                assert client.post(f"/builds/{new}/index").status_code == 201
                assert client.post(f"/builds/{new}/relations").status_code == 202
                assert client.post(f"/builds/{new}/publish").status_code == 200
                assert client.get("/versions/pin", params={"dataset_id": dataset_id, "sample_id": "conv-a"}).json()["build_id"] == new
            finally:
                release.set()
            response = pending.result(timeout=10)
        assert response.status_code == 201, response.text
        trace = response.json()
        assert trace["build_id"] == trace["initial"]["build_id"] == trace["expanded"]["build_id"] == old
        assert {m["build_id"] for m in trace["effective_memories"]} == {old}
        cited = {c["memory_id"] for c in trace["answer"]["citations"]}
        assert cited <= {m["memory_id"] for m in trace["effective_memories"]}


def test_resolver_whitespace_reasons_are_rejected_as_invalid_output(settings, sample):
    def blank_reason(request):
        payload = json.loads(json.loads(request.content)["messages"][1]["content"])
        if payload.get("operation") == "resolve":
            return completion({"status": "insufficient", "effective_memory_ids": [], "decisions": [{"memory_id": m["memory_id"], "selected": False, "reason": "   "} for m in payload["memories"]], "explanation": "   ", "supplemental_relations": []})
        return query_provider(request)
    local = settings.model_copy(update={"model_retries": 0})
    model = DeepSeekModel(local, api_key="synthetic-test-key", transport=httpx.MockTransport(blank_reason))
    with TestClient(create_app(local, model=model, embedder=ControlledEmbedder())) as client:
        dataset_id, _ = complete_build(client, sample)
        result = client.post("/queries", json={"dataset_id": dataset_id, "sample_id": "conv-a", "question": "Where does Alex live?"})
        assert result.status_code == 502
        assert result.json()["error"]["code"] == "invalid_output"
        trace = client.get(f"/queries/{result.json()["error"]["trace_id"]}").json()
        assert trace["error"]["stage"] == "resolve"


def test_no_complete_version_and_non_english_are_explicit_errors(settings, sample):
    model = DeepSeekModel(settings, api_key="synthetic-test-key", transport=httpx.MockTransport(query_provider))
    with TestClient(create_app(settings, model=model, embedder=ControlledEmbedder())) as client:
        partial = build(client, sample)
        dataset_id = client.get(f"/builds/{partial}").json()["dataset_id"]
        payload = {"dataset_id": dataset_id, "sample_id": "conv-a", "question": "Where does Alex live?"}
        response = client.post("/queries", json=payload)
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "no_complete_version"
        response = client.post("/queries", json={**payload, "question": "他住在哪里？"})
        assert response.status_code == 422


def test_explicit_english_question_date_overrides_default_cutoff(settings, sample):
    model = DeepSeekModel(settings, api_key="synthetic-test-key", transport=httpx.MockTransport(query_provider))
    with TestClient(create_app(settings, model=model, embedder=ControlledEmbedder())) as client:
        dataset_id, _ = complete_build(client, sample)
        result = client.post("/queries", json={"dataset_id": dataset_id, "sample_id": "conv-a", "question": "Where did Alex live on 1 May 2023?"})
        assert result.status_code == 201
        trace = result.json()
        assert trace["time"]["origin"] == "explicit_question"
        assert trace["time"]["requested_date"] == "2023-05-01"
        assert "Paris" in trace["answer"]["answer"]
