import json

import httpx
import pytest
from fastapi.testclient import TestClient

from conftest import import_sample
from locomo_memory.api import create_app


def draft(source_ids, **changes):
    return {
        "content": "Alex lives in Paris.", "memory_type": "state", "statement_type": "fact",
        "polarity": "positive", "entity_id": "Alex", "state_dimension": "residence",
        "state_value": "Paris", "source_ids": source_ids, "time": {}, **changes,
    }


def test_user_builds_and_inspects_atomic_memories_with_real_sources(settings, sample):
    from locomo_memory.model import DeepSeekModel

    def provider(request):
        payload = json.loads(request.content)
        assert payload["model"] == "deepseek-flash"
        assert payload["thinking"] == {"type": "disabled"}
        assert payload["response_format"] == {"type": "json_object"}
        user_input = json.loads(payload["messages"][1]["content"])
        assert "ANNOTATION ONLY" not in request.content.decode()
        sources = user_input["sources"]
        output = {"memories": [
            draft([sources[0]["source_id"]]),
            draft([sources[0]["source_id"], sources[2]["source_id"]], content="Alex moved from Paris to Rome.", memory_type="event", state_dimension="relocation", state_value="Rome"),
        ]}
        return httpx.Response(200, json={"model": "deepseek-flash-service-test", "choices": [{"finish_reason": "stop", "message": {"content": json.dumps(output)}}], "usage": {"prompt_tokens": 100, "completion_tokens": 60, "total_tokens": 160}})

    model = DeepSeekModel(settings, api_key="synthetic-test-key", transport=httpx.MockTransport(provider))
    with TestClient(create_app(settings, model=model)) as client:
        dataset_id = import_sample(client, sample).json()["dataset_id"]
        response = client.post("/builds", json={"dataset_id": dataset_id, "sample_id": "conv-a"})
        assert response.status_code == 202
        build_id = response.json()["build_id"]
        build = client.get(f"/builds/{build_id}").json()
        assert build["status"] == "extracted"
        assert build["query_ready"] is False
        assert build["progress"] == {"total": 1, "succeeded": 1, "failed": 0, "pending": 0}
        memories = client.get(f"/builds/{build_id}/memories").json()
        assert memories["total"] == 2
        first, second = memories["items"]
        assert first["state_key"] == "conv-a:Alex:residence"
        assert first["state_value"] == "Paris"
        assert first["session_times"] == ["1:00 pm on 1 May, 2023"]
        assert len(second["source_ids"]) == 2
        assert second["memory_type"] == "event"
        assert first["memory_id"] != second["memory_id"]
        assert "synthetic-test-key" not in json.dumps(build)
        assert build["model_metadata"]["returned_models"] == ["deepseek-flash-service-test"]


def test_malformed_provider_document_is_retried_finitely(settings, sample):
    from locomo_memory.model import DeepSeekModel

    settings = settings.model_copy(update={"model_retries": 1})
    attempts = []

    def provider(request):
        attempts.append(request)
        return httpx.Response(200, json=[])

    model = DeepSeekModel(settings, api_key="synthetic-test-key", transport=httpx.MockTransport(provider))
    with TestClient(create_app(settings, model=model)) as client:
        dataset_id = import_sample(client, sample).json()["dataset_id"]
        build_id = client.post("/builds", json={"dataset_id": dataset_id, "sample_id": "conv-a"}).json()["build_id"]
        build = client.get(f"/builds/{build_id}").json()
        assert build["status"] == "failed"
        assert len(attempts) == 2
        assert len(build["model_metadata"]["calls"]) == 2
        assert client.get(f"/builds/{build_id}/memories").json()["total"] == 0


def completion(output, *, finish="stop"):
    return httpx.Response(200, json={"model": "deepseek-test", "choices": [{"finish_reason": finish, "message": {"content": json.dumps(output)}}], "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}})


def test_invalid_source_is_retried_before_any_memory_is_saved(settings, sample):
    from copy import deepcopy
    from locomo_memory.model import DeepSeekModel

    other = deepcopy(sample[0])
    other["sample_id"] = "conv-b"
    sample.append(other)

    attempts = []

    def provider(request):
        payload = json.loads(request.content)
        sources = json.loads(payload["messages"][1]["content"])["sources"]
        attempts.append(request)
        bad_or_good = sources[0]["source_id"].replace("/conv-a/", "/conv-b/") if len(attempts) == 1 else sources[0]["source_id"]
        return completion({"memories": [draft([bad_or_good])]})

    model = DeepSeekModel(settings, api_key="synthetic-test-key", transport=httpx.MockTransport(provider))
    with TestClient(create_app(settings, model=model)) as client:
        dataset_id = import_sample(client, sample).json()["dataset_id"]
        build_id = client.post("/builds", json={"dataset_id": dataset_id, "sample_id": "conv-a"}).json()["build_id"]
        build = client.get(f"/builds/{build_id}").json()
        assert build["status"] == "extracted"
        assert len(attempts) == 2
        assert [call["outcome"] for call in build["model_metadata"]["calls"]] == ["invalid_output", "succeeded"]
        memories = client.get(f"/builds/{build_id}/memories").json()
        assert memories["total"] == 1
        assert memories["items"][0]["source_ids"] == [f"{dataset_id}/conv-a/D1:1"]


def test_plan_negation_and_imprecise_time_survive_extraction(settings, sample):
    from locomo_memory.model import DeepSeekModel

    sample[0]["conversation"]["session_1"][0]["text"] = "I live in Paris and work part time. I plan to move next month. I do not work for Acme. I might volunteer."

    def provider(request):
        source_id = json.loads(json.loads(request.content)["messages"][1]["content"])["sources"][0]["source_id"]
        return completion({"memories": [
            draft([source_id]),
            draft([source_id], content="Alex works part time.", state_dimension="employment", state_value="part time"),
            draft([source_id], content="Alex plans to move next month.", statement_type="plan", state_value=None,
                  time={"original_expression": "next month", "anchor_source_id": source_id, "event_start": "2023-06-01", "event_end": "2023-06-30", "basis": "Next calendar month relative to the May session; day unknown"}),
            draft([source_id], content="Alex does not work for Acme.", polarity="negative", state_dimension="employment", state_value="Acme"),
            draft([source_id], content="Alex might volunteer.", statement_type="uncertain", state_dimension="volunteering", state_value=None),
        ]})

    model = DeepSeekModel(settings, api_key="synthetic-test-key", transport=httpx.MockTransport(provider))
    with TestClient(create_app(settings, model=model)) as client:
        dataset_id = import_sample(client, sample).json()["dataset_id"]
        build_id = client.post("/builds", json={"dataset_id": dataset_id, "sample_id": "conv-a"}).json()["build_id"]
        items = client.get(f"/builds/{build_id}/memories").json()["items"]
        assert len(items) == 5
        assert len(items[0]["source_ids"]) == 1 and items[0]["source_ids"] == items[1]["source_ids"]
        assert items[0]["time"]["event_start"] is None
        plan = items[2]
        assert plan["statement_type"] == "plan"
        assert plan["time"]["event_start"] == "2023-06-01"
        assert plan["time"]["event_end"] == "2023-06-30"
        assert plan["time"]["valid_from"] is None
        assert items[3]["polarity"] == "negative"
        assert items[4]["statement_type"] == "uncertain"
        assert items[1]["state_key"] == items[3]["state_key"]
        assert items[1]["state_value"] != items[3]["state_value"]


def test_failed_fragment_retry_preserves_successful_memories(settings, sample):
    from locomo_memory.model import DeepSeekModel

    settings = settings.model_copy(update={"fragment_turns": 1, "model_retries": 1})
    retry_enabled = False
    seen = []

    def provider(request):
        source = json.loads(json.loads(request.content)["messages"][1]["content"])["sources"][0]
        seen.append(source["dia_id"])
        if source["dia_id"] == "D1:2" and not retry_enabled:
            return completion({"memories": [draft(["wrong-conversation/D1:1"])]})
        return completion({"memories": [draft([source["source_id"]], content=source["text"])]})

    model = DeepSeekModel(settings, api_key="synthetic-test-key", transport=httpx.MockTransport(provider))
    with TestClient(create_app(settings, model=model)) as client:
        dataset_id = import_sample(client, sample).json()["dataset_id"]
        build_id = client.post("/builds", json={"dataset_id": dataset_id, "sample_id": "conv-a"}).json()["build_id"]
        path = f"/builds/{build_id}"
        build = client.get(path).json()
        assert build["status"] == "failed"
        assert build["progress"] == {"total": 3, "succeeded": 2, "failed": 1, "pending": 0}
        before = client.get(f"{path}/memories").json()["items"]
        assert len(before) == 2
        failed_fragment = client.get(f"{path}/fragments", params={"limit": 1, "offset": 1}).json()["items"][0]
        assert failed_fragment["status"] == "failed"
        assert failed_fragment["error_code"] == "invalid_output"
        retry_enabled = True
        assert client.post(f"{path}/retry").status_code == 202
        recovered = client.get(path).json()
        assert recovered["status"] == "extracted"
        assert recovered["fingerprint"] == build["fingerprint"]
        after = client.get(f"{path}/memories").json()["items"]
        assert len(after) == 3
        assert {m["memory_id"] for m in before}.issubset({m["memory_id"] for m in after})
        assert seen.count("D1:1") == 1 and seen.count("D2:1") == 1
        assert seen.count("D1:2") == 3
        assert client.post(f"{path}/retry").status_code == 409
        assert client.get("/builds", params={"dataset_id": dataset_id}).json()["total"] == 1
    with TestClient(create_app(settings, model=model)) as restarted:
        assert restarted.get(path).json()["status"] == "extracted"
        assert restarted.get(f"{path}/memories").json()["total"] == 3


def test_empty_extraction_requires_a_reason_and_is_not_a_provider_empty_reply(settings, sample):
    from locomo_memory.model import DeepSeekModel

    conversation = sample[0]["conversation"]
    conversation["session_1"] = [{"speaker": "Alex", "dia_id": "D1:1", "text": "Hi!"}]
    del conversation["session_2"]
    del conversation["session_2_date_time"]

    def provider(request):
        return completion({"memories": [], "no_facts_reason": "Only greetings in this controlled example"})

    model = DeepSeekModel(settings, api_key="synthetic-test-key", transport=httpx.MockTransport(provider))
    with TestClient(create_app(settings, model=model)) as client:
        dataset_id = import_sample(client, sample).json()["dataset_id"]
        build_id = client.post("/builds", json={"dataset_id": dataset_id, "sample_id": "conv-a"}).json()["build_id"]
        assert client.get(f"/builds/{build_id}").json()["status"] == "extracted"
        fragment = client.get(f"/builds/{build_id}/fragments").json()["items"][0]
        assert fragment["no_facts_reason"] == "Only greetings in this controlled example"
        assert client.get(f"/builds/{build_id}/memories").json()["total"] == 0


def test_only_one_build_can_be_active_while_partial_progress_is_visible(settings, sample):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    from locomo_memory.model import DeepSeekModel

    started, release = Event(), Event()

    def provider(request):
        source = json.loads(json.loads(request.content)["messages"][1]["content"])["sources"][0]
        started.set()
        release.wait(5)
        return completion({"memories": [draft([source["source_id"]])]})

    model = DeepSeekModel(settings, api_key="synthetic-test-key", transport=httpx.MockTransport(provider))
    with TestClient(create_app(settings, model=model)) as client:
        dataset_id = import_sample(client, sample).json()["dataset_id"]
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(client.post, "/builds", json={"dataset_id": dataset_id, "sample_id": "conv-a"})
            try:
                assert started.wait(5)
                running = client.get("/builds").json()["items"][0]
                assert running["status"] == "running"
                assert running["progress"]["pending"] == 1
                second = client.post("/builds", json={"dataset_id": dataset_id, "sample_id": "conv-a"})
                assert second.status_code == 409
                assert second.json()["error"]["code"] == "build_already_running"
            finally:
                release.set()
            assert future.result(timeout=5).status_code == 202


@pytest.mark.parametrize("failure", ["empty_content", "truncated", "invalid_json", "invalid_schema", "blank_memory", "empty_without_reason", "timeout", "http_error"])
def test_provider_failures_are_bounded_and_sanitized(settings, sample, failure):
    from locomo_memory.model import DeepSeekModel

    settings = settings.model_copy(update={"model_retries": 1, "model_timeout_seconds": 0.25})
    attempts = []

    def provider(request):
        assert request.extensions["timeout"]["read"] == 0.25
        attempts.append(request)
        if failure == "timeout":
            raise httpx.ReadTimeout("synthetic-private-marker", request=request)
        if failure == "http_error":
            return httpx.Response(503, text="synthetic-private-marker")
        if failure == "blank_memory":
            source = json.loads(json.loads(request.content)["messages"][1]["content"])["sources"][0]
            return completion({"memories": [draft([source["source_id"]], content="  ")]})
        if failure == "truncated":
            return completion({"memories": []}, finish="length")
        content = {"empty_content": "", "invalid_json": "synthetic-private-marker", "invalid_schema": '{"unknown_field":"synthetic-private-marker"}', "empty_without_reason": '{"memories":[]}'}[failure]
        return httpx.Response(200, json={"model": "deepseek-test", "choices": [{"finish_reason": "stop", "message": {"content": content}}]})

    model = DeepSeekModel(settings, api_key="synthetic-test-key", transport=httpx.MockTransport(provider))
    with TestClient(create_app(settings, model=model)) as client:
        dataset_id = import_sample(client, sample).json()["dataset_id"]
        build_id = client.post("/builds", json={"dataset_id": dataset_id, "sample_id": "conv-a"}).json()["build_id"]
        build = client.get(f"/builds/{build_id}").json()
        fragments = client.get(f"/builds/{build_id}/fragments")
        assert build["status"] == "failed"
        assert len(attempts) == 2
        assert len(build["model_metadata"]["calls"]) == 2
        assert "synthetic-private-marker" not in fragments.text
        assert "synthetic-test-key" not in json.dumps(build)
        assert client.get(f"/builds/{build_id}/memories").json()["total"] == 0


def test_missing_credential_is_a_visible_failure_without_a_model_call(settings, sample, monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "")
    with TestClient(create_app(settings)) as client:
        dataset_id = import_sample(client, sample).json()["dataset_id"]
        build_id = client.post("/builds", json={"dataset_id": dataset_id, "sample_id": "conv-a"}).json()["build_id"]
        build = client.get(f"/builds/{build_id}").json()
        assert build["status"] == "failed"
        assert build["model_metadata"]["calls"] == []
        fragment = client.get(f"/builds/{build_id}/fragments").json()["items"][0]
        assert fragment["error_code"] == "missing_credentials"
        assert build["query_ready"] is False
