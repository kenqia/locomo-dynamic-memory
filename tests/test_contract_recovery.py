"""Version recovery rejects a changed producer contract at public API boundaries."""
import json

import httpx
import pytest
from fastapi.testclient import TestClient

from conftest import import_sample
from locomo_memory.api import create_app
from locomo_memory.model import DeepSeekModel
import locomo_memory.model as model_contract
import locomo_memory.projection as projection_contract
import locomo_memory.relation_schemas as relation_contract
from test_builds import completion, draft
from test_queries import complete_build, query_provider
from test_retrieval import ControlledEmbedder


@pytest.mark.parametrize("stage", ["extraction", "relations"])
@pytest.mark.parametrize("module,field", [
    (model_contract, "EXTRACTION_PROMPT"),
    (model_contract, "EXTRACTION_PROMPT_VERSION"),
    (model_contract, "MEMORY_SCHEMA_VERSION"),
    (model_contract, "RELATION_PROMPT"),
    (model_contract, "RELATION_PROMPT_VERSION"),
    (relation_contract, "RELATION_SCHEMA_VERSION"),
    (projection_contract, "PROJECTION_VERSION"),
])
def test_failed_build_recovery_requires_unchanged_artifact_contract(settings, sample, monkeypatch, stage, module, field):
    settings = settings.model_copy(update={"fragment_turns": 1, "model_retries": 0})
    provider_calls = []

    def provider(request):
        provider_calls.append(request)
        payload = json.loads(json.loads(request.content)["messages"][1]["content"])
        if "new_memory" in payload:
            return httpx.Response(503)
        source = payload["sources"][0]
        if stage == "extraction" and source["dia_id"] == "D1:2":
            return httpx.Response(503)
        return completion({"memories": [draft([source["source_id"]])]})

    model = DeepSeekModel(settings, api_key="synthetic-test-key", transport=httpx.MockTransport(provider))
    with TestClient(create_app(settings, model=model, embedder=ControlledEmbedder())) as client:
        dataset_id = import_sample(client, sample).json()["dataset_id"]
        build_id = client.post("/builds", json={"dataset_id": dataset_id, "sample_id": "conv-a"}).json()["build_id"]
        path = f"/builds/{build_id}"
        endpoint = "retry"
        if stage == "relations":
            assert client.post(f"{path}/index").status_code == 201
            assert client.post(f"{path}/relations").status_code == 202
            endpoint = "relations"
        before = client.get(path).json()
        assert before["status"] == ("failed" if stage == "extraction" else "relations_failed")
        memories = client.get(f"{path}/memories").json()
        calls = len(provider_calls)
        monkeypatch.setattr(module, field, getattr(module, field) + "-revised")
        response = client.post(f"{path}/{endpoint}")
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "build_contract_changed"
        assert len(provider_calls) == calls
        assert client.get(path).json() == before
        assert client.get(f"{path}/memories").json() == memories
        # A fresh version captures the changed contract instead of mixing outputs.
        new_id = client.post("/builds", json={"dataset_id": dataset_id, "sample_id": "conv-a"}).json()["build_id"]
        assert client.get(f"/builds/{new_id}").json()["fingerprint"] != before["fingerprint"]


def test_complete_versions_remain_readable_after_producer_contract_changes(settings, sample, monkeypatch):
    model = DeepSeekModel(settings, api_key="synthetic-test-key", transport=httpx.MockTransport(query_provider))
    with TestClient(create_app(settings, model=model, embedder=ControlledEmbedder())) as client:
        dataset_id, build_id = complete_build(client, sample)
        before = client.get(f"/builds/{build_id}").json()
        monkeypatch.setattr(model_contract, "EXTRACTION_PROMPT", "Revised extraction contract")
        monkeypatch.setattr(projection_contract, "PROJECTION_VERSION", "revised-projection")
        assert client.get(f"/builds/{build_id}").json() == before
        assert client.get("/versions/pin", params={"dataset_id": dataset_id, "sample_id": "conv-a"}).json()["build_id"] == build_id
        response = client.post("/queries", json={"dataset_id": dataset_id, "sample_id": "conv-a", "question": "Where does Alex live?"})
        assert response.status_code == 201, response.text
        assert response.json()["answer"]["answer"] == "Alex lives in Rome."
