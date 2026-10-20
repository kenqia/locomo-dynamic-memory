import json

import httpx
from fastapi.testclient import TestClient

from locomo_memory.api import create_app
from locomo_memory.model import DeepSeekModel
from test_builds import completion, draft
from test_retrieval import ControlledEmbedder, build


def relation(old, new, **changes):
    return {"old_memory_id": old["memory_id"], "new_memory_id": new["memory_id"], "label": "undetermined", "reason": "The evidence does not establish a transition", "source_ids": list(dict.fromkeys(old["source_ids"] + new["source_ids"])), "support_quote": None, "applicability": {}, **changes}


def test_source_supported_supersession_preserves_history_and_publishes_complete_version(settings, sample):
    sample[0]["conversation"]["session_2"][0]["text"] = "I moved from Paris to Rome on 2 May 2023."

    def provider(request):
        payload = json.loads(json.loads(request.content)["messages"][1]["content"])
        if "sources" in payload and "new_memory" not in payload:
            return completion({"memories": [draft([payload["sources"][0]["source_id"]]), draft([payload["sources"][2]["source_id"]], content="Alex lives in Rome.", state_value="Rome")]})
        if "new_memory" in payload:
            old, new = payload["history"][0], payload["new_memory"]
            return completion({"judgments": [relation(old, new, label="SUPERSEDE", reason="The speaker explicitly moved from Paris to Rome", support_quote="I moved from Paris to Rome on 2 May 2023.", applicability={"from_date": "2023-05-02", "time_anchor_source_id": new["source_ids"][0], "original_time_expression": "2 May 2023", "time_basis": "Explicit date in source"})]})
        return completion({"entities": [], "topic": None, "time": None, "keywords": []})

    model = DeepSeekModel(settings, api_key="synthetic-test-key", transport=httpx.MockTransport(provider))
    with TestClient(create_app(settings, model=model, embedder=ControlledEmbedder())) as client:
        build_id = build(client, sample)
        assert client.post(f"/builds/{build_id}/index").status_code == 201
        response = client.post(f"/builds/{build_id}/relations")
        assert response.status_code == 202
        assert client.get(f"/builds/{build_id}").json()["status"] == "related"
        judgments = client.get(f"/builds/{build_id}/relations").json()
        assert judgments["total"] == 1
        assert judgments["items"][0]["label"] == "SUPERSEDE"
        memories = client.get(f"/builds/{build_id}/memories").json()["items"]
        paris = next(memory for memory in memories if memory["state_value"] == "Paris")
        rome = next(memory for memory in memories if memory["state_value"] == "Rome")
        state = client.get(f"/builds/{build_id}/current-state").json()
        assert state["cutoff"] == "2023-05-02T13:00:00"
        assert [item["memory_id"] for item in state["current_states"]] == [rome["memory_id"]]
        assert state["historical_states"][0]["memory_id"] == paris["memory_id"]
        assert state["historical_states"][0]["status"] == "superseded"
        assert client.post(f"/builds/{build_id}/current-state/rebuild").json() == state
        published = client.post(f"/builds/{build_id}/publish")
        assert published.status_code == 200
        assert published.json()["query_ready"] is True
        dataset_id = published.json()["dataset_id"]
        pinned = client.get("/versions/pin", params={"dataset_id": dataset_id, "sample_id": "conv-a"})
        assert pinned.status_code == 200
        assert pinned.json()["build_id"] == build_id
        assert client.post(f"/builds/{build_id}/index").status_code == 409
        assert client.post(f"/builds/{build_id}/relations").status_code == 409
        assert client.post(f"/builds/{build_id}/current-state/rebuild").status_code == 409


def adoption_provider(omit_research=False):
    def provider(request):
        payload = json.loads(json.loads(request.content)["messages"][1]["content"])
        if "sources" in payload and "new_memory" not in payload:
            sources = payload["sources"]
            memories = [draft([sources[1]["source_id"]], content="Alex submitted an adoption application.", state_dimension="adoption_status", state_value="application"), draft([sources[2]["source_id"]], content="Alex passed the adoption interview.", state_dimension="adoption_status", state_value="interview")]
            if not omit_research:
                memories.insert(0, draft([sources[0]["source_id"]], content="Alex investigated local agencies.", state_dimension="adoption_status", state_value="research"))
            return completion({"memories": memories})
        if "new_memory" in payload:
            new = payload["new_memory"]
            quote = next(source["text"] for source in payload["sources"] if source["source_id"] == new["source_ids"][0])
            return completion({"judgments": [relation(old, new, label="UPDATE", reason="These are documented stages of the same adoption process", support_quote=quote) for old in payload["history"]]})
        return completion({"entities": ["Alex"], "topic": "adoption", "time": None, "keywords": []})
    return provider


class AdoptionEmbedder(ControlledEmbedder):
    def encode(self, texts):
        import numpy as np
        vectors = np.zeros((len(texts), 384), dtype=np.float32)
        for index, text in enumerate(texts):
            vectors[index, 0 if "application" in text.lower() else 1] = 1
        return vectors


import pytest


@pytest.mark.parametrize("omit_research", [False, True])
def test_expansion_recovers_actual_missed_research_but_never_unextracted_memory(settings, sample, omit_research):
    settings = settings.model_copy(update={"bm25_k": 2, "dense_k": 1, "initial_k": 1})
    sample[0]["conversation"]["session_1"][0]["text"] = "I investigated local agencies."
    sample[0]["conversation"]["session_1"][1]["text"] = "Alex submitted an adoption application."
    sample[0]["conversation"]["session_2"][0]["text"] = "I passed the adoption interview."
    model = DeepSeekModel(settings, api_key="synthetic-test-key", transport=httpx.MockTransport(adoption_provider(omit_research)))
    with TestClient(create_app(settings, model=model, embedder=AdoptionEmbedder())) as client:
        build_id = build(client, sample)
        client.post(f"/builds/{build_id}/index")
        client.post(f"/builds/{build_id}/relations")
        initial = client.post("/candidate-queries", json={"build_id": build_id, "question": "application"}).json()
        assert [item["memory"]["state_value"] for item in initial["initial_candidates"]] == ["application"]
        response = client.post("/candidate-expansions", json={"query_id": initial["query_id"]})
        assert response.status_code == 201
        expanded = response.json()
        research = [item for item in expanded["added_candidates"] if item["memory"]["state_value"] == "research"]
        if omit_research:
            assert research == []
        else:
            assert len(research) == 1
            assert any(origin["kind"] == "relation" and origin["label"] == "UPDATE" for origin in research[0]["origins"])
        assert len({item["memory"]["memory_id"] for item in expanded["candidates"]}) == len(expanded["candidates"])
        assert expanded["initial_candidates"] == initial["initial_candidates"]
        assert client.get(f"/candidate-expansions/{expanded['expansion_id']}").json() == expanded


@pytest.mark.parametrize("invalid", ["foreign_endpoint", "unknown_source", "unrelated_source", "cross_dimension", "plan", "event", "invented_quote", "reversed_dates"])
def test_unsafe_model_relations_fail_then_retry_without_reextracting(settings, sample, invalid):
    settings = settings.model_copy(update={"model_retries": 0})
    fixed = False
    extraction_calls = []
    sample[0]["conversation"]["session_2"][0]["text"] = "I moved from Paris to Rome on 2 May 2023."

    def provider(request):
        payload = json.loads(json.loads(request.content)["messages"][1]["content"])
        if "sources" in payload and "new_memory" not in payload:
            extraction_calls.append(request)
            new_changes = {"content": "Alex lives in Rome.", "state_value": "Rome"}
            if invalid == "cross_dimension":
                new_changes["state_dimension"] = "business"
            if invalid == "plan":
                new_changes["statement_type"] = "plan"
            if invalid == "event":
                new_changes["memory_type"] = "event"
            return completion({"memories": [draft([payload["sources"][0]["source_id"]]), draft([payload["sources"][2]["source_id"]], **new_changes)]})
        new, old = payload["new_memory"], payload["history"][0]
        if fixed:
            return completion({"judgments": [relation(old, new)]})
        output = relation(old, new, label="SUPERSEDE", reason="Explicit replacement", support_quote="I moved from Paris to Rome on 2 May 2023.", applicability={"from_date": "2023-05-02", "time_anchor_source_id": new["source_ids"][0], "original_time_expression": "2 May 2023", "time_basis": "Explicit source date"})
        if invalid == "foreign_endpoint":
            output["old_memory_id"] = "other-version-memory"
        if invalid == "unknown_source":
            output["source_ids"].append("another-conversation/D1:1")
        if invalid == "unrelated_source":
            output["source_ids"] = new["source_ids"]
        if invalid == "invented_quote":
            output["support_quote"] = "Invented evidence"
        if invalid == "reversed_dates":
            output["applicability"]["to_date"] = "2023-05-01"
        return completion({"judgments": [output]})

    model = DeepSeekModel(settings, api_key="synthetic-test-key", transport=httpx.MockTransport(provider))
    with TestClient(create_app(settings, model=model, embedder=ControlledEmbedder())) as client:
        build_id = build(client, sample)
        client.post(f"/builds/{build_id}/index")
        client.post(f"/builds/{build_id}/relations")
        assert client.get(f"/builds/{build_id}").json()["status"] == "relations_failed"
        assert client.get(f"/builds/{build_id}/relations").json()["total"] == 0
        progress = client.get(f"/builds/{build_id}/relation-progress").json()
        assert progress["progress"]["failed"] == 1
        task = client.get(f"/builds/{build_id}/relation-tasks").json()["items"][0]
        call = task["diagnostic_history"][0]["calls"][0]
        expected_codes = {
            "foreign_endpoint": "comparison_endpoints_required",
            "unknown_source": "known_source_required",
            "unrelated_source": "both_endpoints_evidence_required",
            "cross_dimension": "same_state_dimension_required",
            "plan": "factual_states_required", "event": "factual_states_required",
            "invented_quote": "verbatim_support_required",
            "reversed_dates": "applicability_range_reversed",
        }
        assert call["failure_stage"] == "domain_validation"
        assert call["error_code"] == expected_codes[invalid]
        assert call["field_path"] == ("judgments[0].applicability" if invalid == "reversed_dates" else "judgments[0]")
        assert client.post(f"/builds/{build_id}/publish").status_code == 409
        fixed = True
        assert client.post(f"/builds/{build_id}/relations").status_code == 202
        assert client.get(f"/builds/{build_id}").json()["status"] == "related"
        assert client.get(f"/builds/{build_id}/relations").json()["items"][0]["label"] == "undetermined"
        assert len(extraction_calls) == 1
        assert client.get(f"/builds/{build_id}/memories").json()["total"] == 2
        assert client.get(f"/builds/{build_id}/relation-tasks").json()["items"][0]["attempts"] == 2


@pytest.mark.parametrize("applicability", [{}, {"condition": "The relocation permit is approved", "condition_satisfied": None}, {"from_date": "2024-05-02", "time_anchor_source_id": "NEW", "original_time_expression": "2 May 2024", "time_basis": "Explicit future date"}])
def test_unknown_conditional_and_future_replacements_do_not_hide_old_state(settings, sample, applicability):
    sample[0]["conversation"]["session_2"][0]["text"] = "I will move from Paris to Rome on 2 May 2024 if my relocation permit is approved."

    def provider(request):
        payload = json.loads(json.loads(request.content)["messages"][1]["content"])
        if "new_memory" not in payload:
            return completion({"memories": [draft([payload["sources"][0]["source_id"]]), draft([payload["sources"][2]["source_id"]], content="Alex reports a replacement residence in Rome.", state_value="Rome")]})
        old, new = payload["history"][0], payload["new_memory"]
        conditions = {**applicability}
        if conditions.get("time_anchor_source_id") == "NEW":
            conditions["time_anchor_source_id"] = new["source_ids"][0]
        quote = next(source["text"] for source in payload["sources"] if source["source_id"] == new["source_ids"][0])
        return completion({"judgments": [relation(old, new, label="SUPERSEDE", reason="Conditional or time-limited transition", support_quote=quote, applicability=conditions)]})

    model = DeepSeekModel(settings, api_key="synthetic-test-key", transport=httpx.MockTransport(provider))
    with TestClient(create_app(settings, model=model, embedder=ControlledEmbedder())) as client:
        build_id = build(client, sample)
        client.post(f"/builds/{build_id}/index")
        client.post(f"/builds/{build_id}/relations")
        state = client.get(f"/builds/{build_id}/current-state").json()
        assert len(state["current_states"]) == 2
        assert state["historical_states"] == []
        assert len(state["conditional_relations"]) == 1


def test_conflicts_compatible_jobs_events_and_plans_remain_source_linked(settings, sample):
    claims = [
        ("I work for Acme.", "employment", "Acme", "state", "fact", "positive"),
        ("I also work for Beta.", "employment", "Beta", "state", "fact", "positive"),
        ("I lost a job last year.", "employment_history", "lost job", "event", "fact", "positive"),
        ("I opened an online store.", "business", "online store", "event", "fact", "positive"),
        ("I live in Paris.", "residence", "Paris", "state", "fact", "positive"),
        ("I live in Rome.", "residence", "Rome", "state", "fact", "positive"),
        ("I plan to move to Madrid.", "residence", "Madrid", "state", "plan", "positive"),
        ("I do not work for Gamma.", "employment", "Gamma", "state", "fact", "negative"),
    ]
    sample[0]["conversation"]["session_1"] = [{"speaker": "Alex", "dia_id": f"D1:{index+1}", "text": claim[0]} for index, claim in enumerate(claims)]
    sample[0]["conversation"]["session_2"] = [{"speaker": "Alex", "dia_id": "D2:1", "text": "Hello again."}]

    def provider(request):
        payload = json.loads(json.loads(request.content)["messages"][1]["content"])
        if "new_memory" not in payload:
            return completion({"memories": [draft([payload["sources"][index]["source_id"]], content=claim[0], state_dimension=claim[1], state_value=claim[2], memory_type=claim[3], statement_type=claim[4], polarity=claim[5]) for index, claim in enumerate(claims)]})
        new = payload["new_memory"]
        judgments = []
        for old in payload["history"]:
            output = relation(old, new)
            if old["state_value"] == "Paris" and new["state_value"] == "Rome":
                output.update(label="CONFLICT", reason="Both assert incompatible residences under the same conditions", support_quote="I live in Rome.")
            judgments.append(output)
        return completion({"judgments": judgments})

    model = DeepSeekModel(settings, api_key="synthetic-test-key", transport=httpx.MockTransport(provider))
    with TestClient(create_app(settings, model=model, embedder=ControlledEmbedder())) as client:
        build_id = build(client, sample)
        client.post(f"/builds/{build_id}/index")
        client.post(f"/builds/{build_id}/relations")
        assert client.get(f"/builds/{build_id}").json()["status"] == "related"
        state = client.get(f"/builds/{build_id}/current-state").json()
        memories = {item["memory_id"]: item for item in client.get(f"/builds/{build_id}/memories").json()["items"]}
        current_values = [memories[item["memory_id"]]["state_value"] for item in state["current_states"]]
        assert all(value in current_values for value in ("Acme", "Beta", "Paris", "Rome", "Gamma"))
        assert len(state["events"]) == 2
        assert [memories[item["memory_id"]]["state_value"] for item in state["nonfactual"]] == ["Madrid"]
        assert len(state["conflicts"]) == 1
        assert len(state["conflicts"][0]["source_ids"]) == 2
        judgments = client.get(f"/builds/{build_id}/relations", params={"limit": 100}).json()["items"]
        assert {item["label"] for item in judgments} == {"undetermined", "CONFLICT"}
        assert client.get(f"/builds/{build_id}/memories").json()["total"] == 8
        assert client.get(f"/builds/{build_id}/relations", params={"limit": 1, "offset": 1}).json()["total"] == 28


class GraphEmbedder(ControlledEmbedder):
    def encode(self, texts):
        import numpy as np
        vectors = np.zeros((len(texts), 384), dtype=np.float32)
        for index, text in enumerate(texts):
            vectors[index, 0 if "submitted" in text or text == "application" else 1] = 1
        return vectors


def graph_provider(request):
    payload = json.loads(json.loads(request.content)["messages"][1]["content"])
    if "sources" in payload and "new_memory" not in payload:
        claims = [("Alex submitted the application.", "application", "A"), ("Alex advanced to interview.", "interview", "B"), ("Alex entered preparation.", "preparation", "C"), ("Alex drafted paperwork.", "application", "D"), ("Alex attended orientation.", "orientation", "E")]
        return completion({"memories": [draft([payload["sources"][index]["source_id"]], content=text, state_dimension=dimension, state_value=value) for index, (text, dimension, value) in enumerate(claims)]})
    if "new_memory" in payload:
        new = payload["new_memory"]
        judgments = []
        for old in payload["history"]:
            output = relation(old, new)
            if (old["state_value"], new["state_value"]) in {("A", "B"), ("B", "C"), ("D", "E")}:
                quote = next(source["text"] for source in payload["sources"] if source["source_id"] == new["source_ids"][0])
                output.update(label="UPDATE", reason="Explicitly supported progression in the same application process", support_quote=quote)
            judgments.append(output)
        return completion({"judgments": judgments})
    return completion({"entities": ["Alex"], "topic": None, "time": None, "keywords": []})


@pytest.mark.parametrize("depth,cap,scan_limit,expected,truncated", [(1, 60, 200, {"A", "B", "D"}, False), (0, 60, 200, {"A", "D"}, False), (1, 2, 200, {"A", "B"}, True), (0, 2, 200, {"A", "D"}, False), (1, 60, 1, {"A", "B"}, True)])
def test_expansion_never_uses_added_endpoints_or_same_key_supplements_as_new_seeds(settings, sample, depth, cap, scan_limit, expected, truncated):
    settings = settings.model_copy(update={"bm25_k": 1, "dense_k": 1, "initial_k": 1, "expansion_depth": depth, "expansion_max_candidates": cap, "expansion_scan_limit": scan_limit})
    sample[0]["conversation"]["session_1"] = [{"speaker": "Alex", "dia_id": f"D1:{index+1}", "text": text} for index, text in enumerate(("I submitted the application.", "I advanced to interview after the application.", "I entered preparation after the interview.", "I drafted paperwork.", "I attended orientation after drafting paperwork."))]
    del sample[0]["conversation"]["session_2"]
    del sample[0]["conversation"]["session_2_date_time"]
    model = DeepSeekModel(settings, api_key="synthetic-test-key", transport=httpx.MockTransport(graph_provider))
    with TestClient(create_app(settings, model=model, embedder=GraphEmbedder())) as client:
        build_id = build(client, sample)
        client.post(f"/builds/{build_id}/index")
        client.post(f"/builds/{build_id}/relations")
        initial = client.post("/candidate-queries", json={"build_id": build_id, "question": "application"}).json()
        assert [item["memory"]["state_value"] for item in initial["initial_candidates"]] == ["A"]
        expanded = client.post("/candidate-expansions", json={"query_id": initial["query_id"]}).json()
        assert {item["memory"]["state_value"] for item in expanded["candidates"]} == expected
        assert expanded["truncated"] is truncated
        assert expanded["relation_depth"] == depth
        assert expanded["scanned"] <= scan_limit
        repeated = client.post("/candidate-expansions", json={"query_id": initial["query_id"]}).json()
        assert repeated["candidates"] == expanded["candidates"]
        for item in expanded["added_candidates"]:
            assert all(origin["seed_memory_id"] == initial["initial_candidates"][0]["memory"]["memory_id"] for origin in item["origins"])


def test_relation_retry_keeps_successful_judgments_and_small_history_limit_is_explicit(settings, sample):
    settings = settings.model_copy(update={"model_retries": 0, "relation_history_limit": 1})
    retry_enabled, relation_calls = False, []
    base_provider = adoption_provider()

    def provider(request):
        payload = json.loads(json.loads(request.content)["messages"][1]["content"])
        if "new_memory" in payload:
            value = payload["new_memory"]["state_value"]
            relation_calls.append(value)
            if value == "interview" and not retry_enabled:
                return completion({"judgments": []})
        return base_provider(request)

    model = DeepSeekModel(settings, api_key="synthetic-test-key", transport=httpx.MockTransport(provider))
    with TestClient(create_app(settings, model=model, embedder=AdoptionEmbedder())) as client:
        build_id = build(client, sample)
        client.post(f"/builds/{build_id}/index")
        client.post(f"/builds/{build_id}/relations")
        before = client.get(f"/builds/{build_id}/relations").json()["items"]
        assert len(before) == 1
        assert client.get(f"/builds/{build_id}/relation-progress").json()["history_comparisons_truncated"] == 1
        retry_enabled = True
        client.post(f"/builds/{build_id}/relations")
        after = client.get(f"/builds/{build_id}/relations").json()["items"]
        assert len(after) == 2
        assert before[0] in after
        assert relation_calls.count("application") == 1
        assert relation_calls.count("interview") == 2
        assert client.get(f"/builds/{build_id}").json()["status"] == "related"


def test_expansion_shared_token_budget_preserves_raw_initial_record_and_global_state(settings, sample):
    settings = settings.model_copy(update={"bm25_k": 2, "dense_k": 1, "initial_k": 1})
    model = DeepSeekModel(settings, api_key="synthetic-test-key", transport=httpx.MockTransport(adoption_provider()))
    with TestClient(create_app(settings, model=model, embedder=AdoptionEmbedder())) as client:
        build_id = build(client, sample)
        client.post(f"/builds/{build_id}/index")
        client.post(f"/builds/{build_id}/relations")
        initial = client.post("/candidate-queries", json={"build_id": build_id, "question": "application"}).json()
        before = client.get(f"/builds/{build_id}/current-state").json()
        relations_before = client.get(f"/builds/{build_id}/relations").json()
    smaller = settings.model_copy(update={"candidate_token_budget": 1, "relation_history_limit": 1})
    with TestClient(create_app(smaller, model=model, embedder=AdoptionEmbedder())) as client:
        result = client.post("/candidate-expansions", json={"query_id": initial["query_id"]}).json()
        assert result["initial_candidates"] == initial["initial_candidates"]
        assert result["candidates"] == []
        assert result["candidate_token_count"] == 0
        assert result["truncation_reasons"] == ["candidate_token_budget"]
        assert result["config"]["candidate_token_budget"] == 1
        assert client.get(f"/builds/{build_id}/relation-progress").json()["history_limit"] == settings.relation_history_limit
        assert client.get(f"/builds/{build_id}/current-state").json() == before
        assert client.get(f"/builds/{build_id}/relations").json() == relations_before


def test_failed_rebuild_keeps_previous_published_pointer_and_scoped_pin(settings, sample):
    settings = settings.model_copy(update={"model_retries": 0})
    fail = False
    base_provider = adoption_provider()

    def provider(request):
        payload = json.loads(json.loads(request.content)["messages"][1]["content"])
        if fail and "new_memory" in payload:
            return httpx.Response(503, text="synthetic-private-provider-error")
        return base_provider(request)

    model = DeepSeekModel(settings, api_key="synthetic-test-key", transport=httpx.MockTransport(provider))
    with TestClient(create_app(settings, model=model, embedder=AdoptionEmbedder())) as client:
        first = build(client, sample)
        client.post(f"/builds/{first}/index")
        client.post(f"/builds/{first}/relations")
        published = client.post(f"/builds/{first}/publish").json()
        scope = {"dataset_id": published["dataset_id"], "sample_id": "conv-a"}
        assert client.get("/versions/pin", params=scope).json()["build_id"] == first
        fail = True
        second = build(client, sample)
        client.post(f"/builds/{second}/index")
        client.post(f"/builds/{second}/relations")
        assert client.get(f"/builds/{second}").json()["status"] == "relations_failed"
        assert client.post(f"/builds/{second}/publish").status_code == 409
        assert client.get("/versions/pin", params=scope).json()["build_id"] == first
        assert client.get("/versions/pin", params={**scope, "build_id": second}).status_code == 409
        assert client.get("/versions/pin", params={**scope, "sample_id": "conv-other", "build_id": first}).status_code == 409
        assert client.post(f"/builds/{first}/retry").status_code == 409
