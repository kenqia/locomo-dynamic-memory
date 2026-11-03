"""Opt-in actual CPU MiniLM adapter check; never substitutes a fake encoder."""

import os

import numpy as np
import pytest

from locomo_memory.config import Settings
from locomo_memory.embeddings import EmbeddingFailure, MiniLMEmbedder
from locomo_memory.retrieval import indexing_text


@pytest.mark.local_embedding
@pytest.mark.skipif(os.environ.get("LOCOMO_LOCAL_EMBEDDING") != "1", reason="Real cached MiniLM check requires opt-in")
def test_actual_pinned_minilm_adapter_encodes_and_rejects_overlong_actual_text():
    embedder = MiniLMEmbedder(Settings())
    identity = embedder.identity()
    assert identity["revision"] == "c9745ed1d9f207416be6d2e6f8de32d1f16199bf"
    assert identity["max_tokens"] == 256
    assert identity["dimensions"] == 384
    vectors = embedder.encode(["Alex lives in Paris.", "Sam works in London."])
    assert vectors.shape == (2, 384)
    assert np.isfinite(vectors).all()
    assert np.linalg.norm(vectors, axis=1) == pytest.approx([1, 1])
    # The content alone fits, but its actual enriched indexing representation does not.
    content = "word " * 249
    assert embedder.encode([content]).shape == (1, 384)
    enriched = indexing_text({"entity_id": "Alex", "state_dimension": "residence", "state_value": "Paris", "content": content})
    with pytest.raises(EmbeddingFailure) as error:
        embedder.encode([enriched])
    assert error.value.code == "embedding_input_too_long"
    with pytest.raises(EmbeddingFailure):
        embedder.encode(["word " * 300])


@pytest.mark.local_embedding
@pytest.mark.skipif(os.environ.get("LOCOMO_LOCAL_EMBEDDING") != "1", reason="Real cached MiniLM check requires opt-in")
def test_actual_minilm_index_and_candidate_api(settings, sample):
    import httpx
    from fastapi.testclient import TestClient
    from locomo_memory.api import create_app
    from locomo_memory.model import DeepSeekModel
    from test_retrieval import build, provider

    model = DeepSeekModel(settings, api_key="synthetic-test-key", transport=httpx.MockTransport(provider))
    with TestClient(create_app(settings, model=model, embedder=MiniLMEmbedder(settings))) as client:
        build_id = build(client, sample)
        response = client.post(f"/builds/{build_id}/index")
        assert response.status_code == 201
        assert response.json()["embedding"]["dimensions"] == 384
        assert response.json()["embedding"]["revision"] == "c9745ed1d9f207416be6d2e6f8de32d1f16199bf"
        result = client.post("/candidate-queries", json={"build_id": build_id, "question": "Paris"})
        assert result.status_code == 201
        assert result.json()["initial_candidates"][0]["memory"]["content"] == "Alex lives in Paris."
        assert client.get(f"/builds/{build_id}").json()["query_ready"] is False
