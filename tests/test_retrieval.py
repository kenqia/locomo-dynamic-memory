import json

import httpx
import numpy as np
import pytest
from fastapi.testclient import TestClient

from conftest import import_sample
from locomo_memory.api import create_app
from locomo_memory.model import DeepSeekModel
from test_builds import completion, draft


class ControlledEmbedder:
    def identity(self):
        return {"model": "controlled-test", "revision": "fixture-v1", "dimensions": 384, "max_tokens": 256, "length_policy": "reject", "normalized": True, "device": "test"}

    def encode(self, texts):
        vectors = np.zeros((len(texts), 384), dtype=np.float32)
        for index, text in enumerate(texts):
            if "Paris" in text:
                vectors[index, 0] = 1
            elif "London" in text:
                vectors[index, 1] = 1
            else:
                vectors[index, 0] = -1
        return vectors


def provider(request):
    payload = json.loads(json.loads(request.content)["messages"][1]["content"])
    if "sources" in payload:
        sources = payload["sources"]
        return completion({"memories": [
            draft([sources[0]["source_id"]]),
            draft([sources[1]["source_id"]], content="Sam works in London.", entity_id="Sam", state_dimension="employment", state_value="London"),
            draft([sources[2]["source_id"]], content="Alex enjoys cycling.", state_dimension="hobby", state_value="cycling"),
        ]})
    return completion({"entities": ["Alex"], "topic": "residence", "time": None, "keywords": ["Paris"]})


def build(client, sample):
    dataset_id = import_sample(client, sample).json()["dataset_id"]
    return client.post("/builds", json={"dataset_id": dataset_id, "sample_id": "conv-a"}).json()["build_id"]


def test_user_inspects_real_hybrid_candidates_and_rank_fusion(settings, sample):
    settings = settings.model_copy(update={"rrf_constant": 10, "initial_k": 2, "bm25_k": 3, "dense_k": 3})
    model = DeepSeekModel(settings, api_key="synthetic-test-key", transport=httpx.MockTransport(provider))
    with TestClient(create_app(settings, model=model, embedder=ControlledEmbedder())) as client:
        build_id = build(client, sample)
        indexed = client.post(f"/builds/{build_id}/index")
        assert indexed.status_code == 201
        assert indexed.json()["status"] == "ready"
        response = client.post("/candidate-queries", json={"build_id": build_id, "question": "Paris"})
        assert response.status_code == 201
        result = response.json()
        assert result["question"] == "Paris"
        assert result["build_id"] == build_id
        assert result["analysis"]["status"] == "succeeded"
        assert len(result["channels"]["bm25"]) == 3
        assert len(result["channels"]["dense"]) == 3
        assert len(result["initial_candidates"]) == 2
        first = result["initial_candidates"][0]
        assert first["memory"]["content"] == "Alex lives in Paris."
        assert first["channel_ranks"] == {"bm25": 1, "dense": 1}
        assert first["rrf_score"] == pytest.approx(0.18181818181818182)
        assert first["memory"]["source_ids"]
        assert result["config"]["initial_k"] == 2
        assert client.get(f"/candidate-queries/{result['query_id']}").json() == result
        assert client.get(f"/builds/{build_id}").json()["query_ready"] is False


def test_analysis_failure_keeps_original_question_in_actual_retrieval(settings, sample):
    def analysis_fails(request):
        user_input = json.loads(json.loads(request.content)["messages"][1]["content"])
        if "sources" in user_input:
            return provider(request)
        return httpx.Response(503, text="synthetic-private-provider-message")

    model = DeepSeekModel(settings.model_copy(update={"model_retries": 0}), api_key="synthetic-test-key", transport=httpx.MockTransport(analysis_fails))
    with TestClient(create_app(settings, model=model, embedder=ControlledEmbedder())) as client:
        build_id = build(client, sample)
        assert client.post(f"/builds/{build_id}/index").status_code == 201
        response = client.post("/candidate-queries", json={"build_id": build_id, "question": "Paris"})
        assert response.status_code == 201
        result = response.json()
        assert result["analysis"]["status"] == "fallback"
        assert result["question"] == "Paris"
        assert result["initial_candidates"][0]["memory"]["content"] == "Alex lives in Paris."
        assert "synthetic-private-provider-message" not in response.text


def test_analysis_inferred_conditions_do_not_filter_history(settings, sample):
    def misleading_analysis(request):
        user_input = json.loads(json.loads(request.content)["messages"][1]["content"])
        if "sources" in user_input:
            return provider(request)
        return completion({"entities": ["SomeoneNotInTheConversation"], "topic": "unrelated", "time": "2099-01-01", "keywords": []})

    model = DeepSeekModel(settings, api_key="synthetic-test-key", transport=httpx.MockTransport(misleading_analysis))
    with TestClient(create_app(settings, model=model, embedder=ControlledEmbedder())) as client:
        build_id = build(client, sample)
        client.post(f"/builds/{build_id}/index")
        result = client.post("/candidate-queries", json={"build_id": build_id, "question": "Paris"}).json()
        assert result["analysis"]["result"]["time"] == "2099-01-01"
        assert len(result["initial_candidates"]) == 3
        assert result["initial_candidates"][0]["memory"]["content"] == "Alex lives in Paris."


def test_retrieval_budget_and_stable_ties_are_recorded_per_query(settings, sample):
    settings = settings.model_copy(update={"bm25_k": 1, "dense_k": 2, "initial_k": 1, "candidate_token_budget": 100})
    model = DeepSeekModel(settings, api_key="synthetic-test-key", transport=httpx.MockTransport(provider))
    embedder = ControlledEmbedder()
    with TestClient(create_app(settings, model=model, embedder=embedder)) as client:
        build_id = build(client, sample)
        index = client.post(f"/builds/{build_id}/index").json()
        first = client.post("/candidate-queries", json={"build_id": build_id, "question": "Paris"}).json()
        second = client.post("/candidate-queries", json={"build_id": build_id, "question": "Paris"}).json()
        assert first["channels"] == second["channels"]
        assert first["initial_candidates"] == second["initial_candidates"]
        assert len(first["channels"]["bm25"]) == 1
        assert len(first["channels"]["dense"]) == 2
        assert len(first["initial_candidates"]) == 1
        assert first["initial_truncated"] is True
        assert first["truncation_reasons"] == ["initial_k"]
    smaller = settings.model_copy(update={"initial_k": 3, "candidate_token_budget": 1})
    with TestClient(create_app(smaller, model=model, embedder=embedder)) as client:
        response = client.post("/candidate-queries", json={"build_id": build_id, "question": "Paris"})
        result = response.json()
        assert result["initial_candidates"] == []
        assert result["candidate_token_count"] == 0
        assert result["truncation_reasons"] == ["candidate_token_budget"]
        assert result["config"]["candidate_token_budget"] == 1
        assert result["index_fingerprint"] == index["fingerprint"]


@pytest.mark.parametrize("kind", ["wrong_dimensions", "nan", "zero"])
def test_invalid_embedding_outputs_fail_index_without_losing_memories(settings, sample, kind):
    class InvalidEmbedder(ControlledEmbedder):
        def encode(self, texts):
            if kind == "wrong_dimensions":
                return np.ones((len(texts), 3))
            if kind == "nan":
                return np.full((len(texts), 384), np.nan)
            return np.zeros((len(texts), 384))

    model = DeepSeekModel(settings, api_key="synthetic-test-key", transport=httpx.MockTransport(provider))
    with TestClient(create_app(settings, model=model, embedder=InvalidEmbedder())) as client:
        build_id = build(client, sample)
        response = client.post(f"/builds/{build_id}/index")
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "invalid_embedding_vector"
        assert client.get(f"/builds/{build_id}/index").json()["status"] == "failed"
        assert client.get(f"/builds/{build_id}").json()["status"] == "index_failed"
        assert client.get(f"/builds/{build_id}/memories").json()["total"] == 3
    with TestClient(create_app(settings, model=model, embedder=ControlledEmbedder())) as client:
        assert client.post(f"/builds/{build_id}/index").status_code == 201
        assert client.post("/candidate-queries", json={"build_id": build_id, "question": "Paris"}).status_code == 201


def test_length_errors_are_visible_and_query_does_not_silently_truncate(settings, sample):
    from locomo_memory.embeddings import EmbeddingFailure

    class LengthCheckingEmbedder(ControlledEmbedder):
        def encode(self, texts):
            if any(len(text.split()) > 256 for text in texts):
                raise EmbeddingFailure("embedding_input_too_long")
            return super().encode(texts)

    analysis_calls = []

    def counting_provider(request):
        user_input = json.loads(json.loads(request.content)["messages"][1]["content"])
        if "question" in user_input:
            analysis_calls.append(request)
        return provider(request)

    model = DeepSeekModel(settings, api_key="synthetic-test-key", transport=httpx.MockTransport(counting_provider))
    with TestClient(create_app(settings, model=model, embedder=LengthCheckingEmbedder())) as client:
        build_id = build(client, sample)
        assert client.post(f"/builds/{build_id}/index").status_code == 201
        response = client.post("/candidate-queries", json={"build_id": build_id, "question": "Paris " * 300})
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "embedding_input_too_long"
        assert analysis_calls == []


def test_unindexed_and_non_english_queries_are_explicit_errors(settings, sample):
    model = DeepSeekModel(settings, api_key="synthetic-test-key", transport=httpx.MockTransport(provider))
    with TestClient(create_app(settings, model=model, embedder=ControlledEmbedder())) as client:
        build_id = build(client, sample)
        response = client.post("/candidate-queries", json={"build_id": build_id, "question": "Paris"})
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "index_not_ready"
        for question in ("他住在哪里？", "", "   "):
            response = client.post("/candidate-queries", json={"build_id": build_id, "question": question})
            assert response.status_code == 422
            assert response.json()["error"]["code"] == "invalid_input"


def test_index_rejects_changed_build_configuration_before_mutating_artifacts(settings, sample):
    model = DeepSeekModel(settings, api_key="synthetic-test-key", transport=httpx.MockTransport(provider))
    with TestClient(create_app(settings, model=model, embedder=ControlledEmbedder())) as client:
        build_id = build(client, sample)
        original_build = client.get(f"/builds/{build_id}").json()
    changed = settings.model_copy(update={"embedding_revision": "a" * 40})
    with TestClient(create_app(changed, model=model, embedder=ControlledEmbedder())) as client:
        response = client.post(f"/builds/{build_id}/index")
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "build_configuration_changed"
        assert client.get(f"/builds/{build_id}").json()["status"] == "extracted"
        assert client.get(f"/builds/{build_id}").json()["config"] == original_build["config"]
        assert client.get(f"/builds/{build_id}/index").status_code == 409


def test_empty_extracted_library_is_indexable_without_fake_candidates(settings, sample):
    def no_facts_provider(request):
        user_input = json.loads(json.loads(request.content)["messages"][1]["content"])
        if "sources" in user_input:
            return completion({"memories": [], "no_facts_reason": "Only a greeting"})
        return provider(request)

    conversation = sample[0]["conversation"]
    conversation["session_1"] = [{"speaker": "Alex", "dia_id": "D1:1", "text": "Hi!"}]
    del conversation["session_2"]
    del conversation["session_2_date_time"]
    model = DeepSeekModel(settings, api_key="synthetic-test-key", transport=httpx.MockTransport(no_facts_provider))
    with TestClient(create_app(settings, model=model, embedder=ControlledEmbedder())) as client:
        build_id = build(client, sample)
        index = client.post(f"/builds/{build_id}/index")
        assert index.status_code == 201
        assert index.json()["memory_count"] == 0
        result = client.post("/candidate-queries", json={"build_id": build_id, "question": "Paris"}).json()
        assert result["channels"] == {"bm25": [], "dense": []}
        assert result["initial_candidates"] == []


def test_index_identity_cannot_be_reused_with_another_embedding_revision(settings, sample):
    class DifferentIdentity(ControlledEmbedder):
        def identity(self):
            return {**super().identity(), "revision": "fixture-v2"}

    model = DeepSeekModel(settings, api_key="synthetic-test-key", transport=httpx.MockTransport(provider))
    with TestClient(create_app(settings, model=model, embedder=ControlledEmbedder())) as client:
        build_id = build(client, sample)
        assert client.post(f"/builds/{build_id}/index").status_code == 201
    with TestClient(create_app(settings, model=model, embedder=DifferentIdentity())) as client:
        response = client.post("/candidate-queries", json={"build_id": build_id, "question": "Paris"})
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "index_fingerprint_mismatch"
