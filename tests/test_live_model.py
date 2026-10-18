"""Opt-in paid integration check; never runs on the default verification path."""

import os

from fastapi.testclient import TestClient
import pytest

from conftest import import_sample
from locomo_memory.api import create_app


@pytest.mark.live_model
@pytest.mark.skipif(os.environ.get("LOCOMO_LIVE_MODEL") != "1", reason="Real DeepSeek call requires explicit opt-in")
def test_real_deepseek_build_preserves_evidence(settings, sample):
    if not os.environ.get("DEEPSEEK_API_KEY"):
        pytest.skip("A protected local DeepSeek credential is required")
    settings = settings.model_copy(update={"model_retries": 0, "model_max_tokens": 2048, "model_timeout_seconds": 30})
    with TestClient(create_app(settings)) as client:
        dataset_id = import_sample(client, sample).json()["dataset_id"]
        build_id = client.post("/builds", json={"dataset_id": dataset_id, "sample_id": "conv-a"}).json()["build_id"]
        build = client.get(f"/builds/{build_id}").json()
        assert build["status"] == "extracted"
        memories = client.get(f"/builds/{build_id}/memories").json()["items"]
        assert memories
        for memory in memories:
            for source_id in memory["source_ids"]:
                source_dataset, sample_id, dia_id = source_id.split("/")
                response = client.get(f"/datasets/{source_dataset}/conversations/{sample_id}/turns/{dia_id}")
                assert response.status_code == 200
