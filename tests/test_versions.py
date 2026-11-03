"""Version lifecycle assertions use HTTP; only generation and encoding are controlled."""
import json

import httpx
from fastapi.testclient import TestClient

from locomo_memory.api import create_app
from locomo_memory.model import DeepSeekModel
from test_builds import completion, draft
from test_relations import relation
from test_retrieval import ControlledEmbedder, build


def provider(request):
    payload = json.loads(json.loads(request.content)["messages"][1]["content"])
    if "new_memory" in payload:
        return completion({"judgments": [relation(old, payload["new_memory"]) for old in payload["history"]]})
    if "sources" in payload:
        ids = [source["source_id"] for source in payload["sources"]]
        return completion({"memories": [draft([ids[0], ids[2]]), draft([ids[0]], content="Alex likes Paris.", state_dimension="preference")]})
    return completion({"entities": [], "topic": None, "time": None, "keywords": []})


def model(settings, handler=provider):
    return DeepSeekModel(settings, api_key="synthetic-test-key", transport=httpx.MockTransport(handler))


def complete(client, sample):
    build_id = build(client, sample)
    assert client.post(f"/builds/{build_id}/index").status_code == 201
    assert client.post(f"/builds/{build_id}/relations").status_code == 202
    assert client.post(f"/builds/{build_id}/publish").status_code == 200
    return build_id


def test_explicit_complete_export_preserves_multisources_relations_and_old_version(settings, sample):
    with TestClient(create_app(settings, model=model(settings), embedder=ControlledEmbedder())) as client:
        first = complete(client, sample)
        response = client.get(f"/builds/{first}/export")
        assert response.status_code == 200
        exported = response.json()
        assert exported["schema_version"] == "memory-export-v2"
        assert exported["build"]["build_id"] == first
        assert exported["build"]["status"] == "complete"
        assert len(exported["memories"]) == 2
        assert sorted(len(item["source_ids"]) for item in exported["memories"]) == [1, 2]
        assert {item["session_id"] for item in exported["sources"]} == {"session_1", "session_2"}
        assert len(exported["relations"]) == 1
        assert exported["projection"]["build_id"] == first
        assert exported["index"]["build_id"] == first
        assert "ANNOTATION ONLY" not in response.text
        assert "synthetic-test-key" not in response.text
        assert "attachment" in response.headers["content-disposition"]
        partial = build(client, sample)
        assert client.get(f"/builds/{partial}/export").status_code == 409
        assert client.post(f"/builds/{partial}/publish").status_code == 409
        assert client.get(f"/builds/{first}/export").json() == exported
        second = complete(client, sample)
        pin = client.get("/versions/pin", params={"dataset_id": exported["build"]["dataset_id"], "sample_id": "conv-a"}).json()
        assert pin["build_id"] == second
        assert client.get(f"/builds/{first}/export").json() == exported


class RevisionEmbedder(ControlledEmbedder):
    def __init__(self, revision, selected=None):
        self.revision = revision
        self.selected = selected if selected is not None else []

    def identity(self):
        return {**super().identity(), "revision": self.revision}

    def for_identity(self, identity):
        self.selected.append(identity["revision"])
        return RevisionEmbedder(identity["revision"], self.selected)


def test_restart_selects_old_index_encoder_and_keeps_current_query_budget(settings, sample):
    old_encoder = RevisionEmbedder("old")
    with TestClient(create_app(settings, model=model(settings), embedder=old_encoder)) as client:
        first = complete(client, sample)
    changed = settings.model_copy(update={"embedding_revision": "a" * 40, "initial_k": 1})
    selected = []
    with TestClient(create_app(changed, model=model(changed), embedder=RevisionEmbedder("new", selected))) as client:
        second = build(client, sample)
        assert client.post(f"/builds/{second}/index").status_code == 201
        response = client.post("/candidate-queries", json={"build_id": first, "question": "Paris"})
        assert response.status_code == 201
        result = response.json()
        assert result["build_id"] == first
        assert result["config"]["initial_k"] == 1
        assert len(result["initial_candidates"]) == 1
        assert selected == ["old"]
        exported = client.get(f"/builds/{first}/export").json()
        assert exported["index"]["embedding"]["revision"] == "old"
        assert exported["build"]["config"]["initial_k"] == 20


def fragment_provider(request):
    payload = json.loads(json.loads(request.content)["messages"][1]["content"])
    if "new_memory" in payload:
        return completion({"judgments": [relation(old, payload["new_memory"]) for old in payload["history"]]})
    if "sources" in payload:
        return completion({"memories": [draft([payload["sources"][0]["source_id"]])]})
    return completion({"entities": [], "topic": None, "time": None, "keywords": []})


def crash_build(settings, sample, phase):
    """A real process exits at the external generation/encoding boundary."""
    import os

    calls = {"extract": 0, "relate": 0}

    def interrupted_provider(request):
        payload = json.loads(json.loads(request.content)["messages"][1]["content"])
        operation = "relate" if "new_memory" in payload else "extract"
        calls[operation] += 1
        if (phase == "extraction" and operation == "extract" and calls[operation] == 2) or (phase == "relations" and operation == "relate" and calls[operation] == 2):
            os._exit(73)
        return fragment_provider(request)

    class InterruptedEncoder(ControlledEmbedder):
        def encode(self, texts):
            if phase == "indexing":
                os._exit(73)
            return super().encode(texts)

    with TestClient(create_app(settings, model=model(settings, interrupted_provider), embedder=InterruptedEncoder())) as client:
        build_id = build(client, sample)
        client.post(f"/builds/{build_id}/index")
        client.post(f"/builds/{build_id}/relations")
    os._exit(74)


import pytest


@pytest.mark.parametrize("phase", ["extraction", "indexing", "relations"])
def test_actual_process_restart_and_explicit_phase_retry_preserve_successes(settings, sample, phase):
    import multiprocessing

    settings = settings.model_copy(update={"fragment_turns": 1})
    with TestClient(create_app(settings, model=model(settings, fragment_provider), embedder=ControlledEmbedder())) as client:
        first = complete(client, sample)
        baseline = client.get(f"/builds/{first}/export").json()
    worker = multiprocessing.get_context("spawn").Process(target=crash_build, args=(settings, sample, phase))
    worker.start()
    worker.join(20)
    if worker.is_alive():
        worker.terminate()
        worker.join(5)
        pytest.fail("Controlled interrupted backend did not exit")
    assert worker.exitcode == 73
    with TestClient(create_app(settings, model=model(settings, fragment_provider), embedder=ControlledEmbedder())) as client:
        versions = client.get("/builds").json()["items"]
        interrupted = next(item for item in versions if item["build_id"] != first)
        build_id = interrupted["build_id"]
        assert interrupted["status"] == "interrupted"
        assert interrupted["phase"] == phase
        before = client.get(f"/builds/{build_id}/fragments").json()["items"]
        assert client.get(f"/builds/{first}/export").json() == baseline
        assert client.get(f"/builds/{build_id}/export").status_code == 409
        assert client.post(f"/builds/{build_id}/publish").status_code == 409
        if phase == "relations":
            tasks_before = client.get(f"/builds/{build_id}/relation-tasks").json()["items"]
            assert tasks_before[0]["status"] == "succeeded"
        response = client.post(f"/builds/{build_id}/retry-phase")
        assert response.status_code == 202
        assert client.post(f"/builds/{build_id}/retry-phase").status_code == 409
        after = client.get(f"/builds/{build_id}/fragments").json()["items"]
        for previous, current in zip(before, after):
            if previous["status"] == "succeeded":
                assert current["attempts"] == previous["attempts"]
                assert current["source_ids"] == previous["source_ids"]
        if phase == "extraction":
            assert client.post(f"/builds/{build_id}/index").status_code == 201
        if phase != "relations":
            assert client.post(f"/builds/{build_id}/relations").status_code == 202
        else:
            tasks_after = client.get(f"/builds/{build_id}/relation-tasks").json()["items"]
            assert tasks_after[0]["attempts"] == tasks_before[0]["attempts"]
            assert tasks_after[1]["attempts"] == tasks_before[1]["attempts"] + 1
        assert client.get(f"/builds/{build_id}/memories").json()["total"] == 3
        assert client.get(f"/builds/{build_id}/relations").json()["total"] == 3
        assert client.post(f"/builds/{build_id}/publish").status_code == 200
        exported = client.get(f"/builds/{build_id}/export").json()
        assert exported["build"]["build_id"] == build_id
        assert len(exported["memories"]) == 3
        assert client.get(f"/builds/{first}/export").json() == baseline


def test_inflight_candidate_and_downloads_keep_pinned_artifacts_during_publication(settings, sample):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event

    entered, release = Event(), Event()

    class PausingEncoder(ControlledEmbedder):
        def encode(self, texts):
            if texts == ["Paris"]:
                entered.set()
                assert release.wait(15)
            return super().encode(texts)

    with TestClient(create_app(settings, model=model(settings), embedder=PausingEncoder())) as client:
        first = complete(client, sample)
        baseline = client.get(f"/builds/{first}/export").json()
        second = build(client, sample)
        assert client.post(f"/builds/{second}/index").status_code == 201
        assert client.post(f"/builds/{second}/relations").status_code == 202
        params = {"dataset_id": baseline["build"]["dataset_id"], "sample_id": "conv-a"}
        fixed = client.get("/versions/pin", params=params).json()["build_id"]
        with ThreadPoolExecutor(max_workers=4) as workers:
            query = workers.submit(client.post, "/candidate-queries", json={"build_id": fixed, "question": "Paris"})
            try:
                assert entered.wait(15)
                downloads = [workers.submit(client.get, f"/builds/{first}/export") for _ in range(6)]
                assert client.post(f"/builds/{second}/publish").status_code == 200
                assert client.get("/versions/pin", params=params).json()["build_id"] == second
                assert all(response.result().json() == baseline for response in downloads)
            finally:
                release.set()
            response = query.result()
        assert response.status_code == 201
        result = response.json()
        assert result["build_id"] == first
        assert result["index_fingerprint"] == baseline["index"]["fingerprint"]
        assert all(item["memory"]["build_id"] == first for item in result["initial_candidates"])


@pytest.mark.parametrize("phase", ["extraction", "indexing", "relations"])
def test_only_one_global_build_can_run_across_phases(settings, sample, phase):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event

    entered, release = Event(), Event()
    enabled = False

    def pausing_provider(request):
        payload = json.loads(json.loads(request.content)["messages"][1]["content"])
        current = "relations" if "new_memory" in payload else "extraction"
        if enabled and phase == current and "sources" in payload:
            entered.set()
            assert release.wait(15)
        return provider(request)

    class PausingEncoder(ControlledEmbedder):
        def encode(self, texts):
            if enabled and phase == "indexing" and len(texts) > 1:
                entered.set()
                assert release.wait(15)
            return super().encode(texts)

    with TestClient(create_app(settings, model=model(settings, pausing_provider), embedder=PausingEncoder())) as client:
        first = complete(client, sample)
        baseline = client.get(f"/builds/{first}/export").json()
        if phase != "extraction":
            pending = build(client, sample)
            if phase == "relations":
                assert client.post(f"/builds/{pending}/index").status_code == 201
        enabled = True
        with ThreadPoolExecutor(max_workers=2) as workers:
            if phase == "extraction":
                task = workers.submit(build, client, sample)
            else:
                path = "index" if phase == "indexing" else "relations"
                task = workers.submit(client.post, f"/builds/{pending}/{path}")
            try:
                assert entered.wait(15)
                rejected = client.post("/builds", json={"dataset_id": baseline["build"]["dataset_id"], "sample_id": "conv-a"})
                assert rejected.status_code == 409
                assert rejected.json()["error"]["code"] == "build_already_running"
                assert client.get(f"/builds/{first}/export").json() == baseline
                assert client.post("/candidate-queries", json={"build_id": first, "question": "Rome"}).status_code == 201
            finally:
                release.set()
            task.result()


import os


@pytest.mark.local_embedding
@pytest.mark.skipif(os.environ.get("LOCOMO_LOCAL_EMBEDDING") != "1", reason="Real cached MiniLM check requires opt-in")
def test_real_cached_old_revision_remains_queryable_when_current_revision_is_unavailable(settings, sample):
    from locomo_memory.embeddings import MiniLMEmbedder

    with TestClient(create_app(settings, model=model(settings), embedder=MiniLMEmbedder(settings))) as client:
        first = complete(client, sample)
        baseline = client.get(f"/builds/{first}/export").json()
    changed = settings.model_copy(update={"embedding_revision": "0" * 40, "embedding_local_files_only": True, "initial_k": 1})
    with TestClient(create_app(changed, model=model(changed), embedder=MiniLMEmbedder(changed))) as client:
        response = client.post("/candidate-queries", json={"build_id": first, "question": "Paris"})
        assert response.status_code == 201
        assert response.json()["build_id"] == first
        assert response.json()["config"]["initial_k"] == 1
        second = build(client, sample)
        failed = client.post(f"/builds/{second}/index")
        assert failed.status_code == 503
        assert failed.json()["error"]["code"] == "embedding_model_unavailable"
        assert client.get(f"/builds/{second}").json()["status"] == "index_failed"
        assert client.post("/candidate-queries", json={"build_id": first, "question": "Paris"}).status_code == 201
        assert client.get(f"/builds/{first}/export").json() == baseline


@pytest.mark.parametrize("phase", ["extraction", "indexing", "relations"])
def test_explicit_failed_phase_retry_keeps_old_version_available(settings, sample, phase):
    from locomo_memory.embeddings import EmbeddingFailure

    settings = settings.model_copy(update={"model_retries": 0})
    fail = False

    def failing_provider(request):
        payload = json.loads(json.loads(request.content)["messages"][1]["content"])
        current = "relations" if "new_memory" in payload else "extraction"
        if fail and phase == current and "sources" in payload:
            return completion({"invalid": "synthetic failure"})
        return provider(request)

    class FailingEncoder(ControlledEmbedder):
        def encode(self, texts):
            if fail and phase == "indexing" and len(texts) > 1:
                raise EmbeddingFailure("embedding_encode_failed", 503)
            return super().encode(texts)

    with TestClient(create_app(settings, model=model(settings, failing_provider), embedder=FailingEncoder())) as client:
        first = complete(client, sample)
        baseline = client.get(f"/builds/{first}/export").json()
        fail = phase == "extraction"
        second = build(client, sample)
        if phase != "extraction":
            fail = phase == "indexing"
            indexed = client.post(f"/builds/{second}/index")
            if phase == "indexing":
                assert indexed.status_code == 503
            else:
                assert indexed.status_code == 201
                fail = True
                assert client.post(f"/builds/{second}/relations").status_code == 202
        assert client.get(f"/builds/{second}").json()["status"] in {"failed", "index_failed", "relations_failed"}
        assert client.post(f"/builds/{second}/publish").status_code == 409
        assert client.get(f"/builds/{first}/export").json() == baseline
        assert client.post("/candidate-queries", json={"build_id": first, "question": "Paris"}).status_code == 201
        fail = False
        assert client.post(f"/builds/{second}/retry-phase").status_code == 202
        if phase == "extraction":
            assert client.post(f"/builds/{second}/index").status_code == 201
        if phase != "relations":
            assert client.post(f"/builds/{second}/relations").status_code == 202
        assert client.post(f"/builds/{second}/publish").status_code == 200
        assert len(client.get(f"/builds/{second}/export").json()["memories"]) == 2


def test_publication_rejects_invalid_encoder_artifact_without_moving_active_version(settings, sample):
    invalid = False

    class InvalidIdentityEncoder(ControlledEmbedder):
        def identity(self):
            return {**super().identity(), "normalized": not invalid}

    with TestClient(create_app(settings, model=model(settings), embedder=InvalidIdentityEncoder())) as client:
        first = complete(client, sample)
        baseline = client.get(f"/builds/{first}/export").json()
        invalid = True
        second = build(client, sample)
        assert client.post(f"/builds/{second}/index").status_code == 201
        assert client.post(f"/builds/{second}/relations").status_code == 202
        rejected = client.post(f"/builds/{second}/publish")
        assert rejected.status_code == 409
        assert rejected.json()["error"]["code"] == "version_not_publishable"
        params = {"dataset_id": baseline["build"]["dataset_id"], "sample_id": "conv-a"}
        assert client.get("/versions/pin", params=params).json()["build_id"] == first
        assert client.get(f"/builds/{second}").json()["status"] == "related"
        assert client.get(f"/builds/{second}/export").status_code == 409
        assert client.get(f"/builds/{first}/export").json() == baseline
