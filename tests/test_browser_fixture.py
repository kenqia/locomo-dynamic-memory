"""Exercise browser evidence with real retrieval, independent of insertion order."""

import json
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from browser import server
from locomo_memory.api import create_app
from locomo_memory.model import DeepSeekModel


@pytest.mark.parametrize("memory_order", [(0, 1, 2, 3), (3, 2, 1, 0), (2, 0, 3, 1)])
def test_browser_fixture_retrieves_and_expands_evidence_across_fresh_builds(settings, monkeypatch, memory_order):
    sample = json.loads((Path(__file__).parent / "browser/sample.json").read_text())
    settings = settings.model_copy(update={"initial_k": 1, "model_retries": 0})
    # The browser checks failure/retry separately; this regression covers ranking.
    monkeypatch.setattr(server, "_failed_first_extraction", True)

    def provider(request):
        response = server.provider(request)
        envelope = response.json()
        value = json.loads(envelope["choices"][0]["message"]["content"])
        if "memories" in value:
            value["memories"] = [value["memories"][i] for i in memory_order]
            envelope["choices"][0]["message"]["content"] = json.dumps(value)
            return httpx.Response(200, json=envelope)
        return response

    model = DeepSeekModel(settings, api_key="synthetic-fixture-test", transport=httpx.MockTransport(provider))
    with TestClient(create_app(settings, model=model, embedder=server.BrowserEmbedder())) as client:
        imported = client.post("/imports", json={"data": sample, "version": "browser-fixture-v1", "license": "test-only"})
        assert imported.status_code == 201
        dataset_id = imported.json()["dataset_id"]
        build_ids = set()
        for _ in range(2):
            created = client.post("/builds", json={"dataset_id": dataset_id, "sample_id": "conv-a"})
            assert created.status_code == 202
            build_id = created.json()["build_id"]
            assert build_id not in build_ids
            build_ids.add(build_id)
            assert client.post(f"/builds/{build_id}/index").status_code == 201
            assert client.post(f"/builds/{build_id}/relations").status_code == 202
            assert client.post(f"/builds/{build_id}/publish").status_code == 200
            for question, extra, expected in [
                ("Where does Alex live?", {}, "sufficient"),
                ("Where did Alex live?", {"requested_date": "2023-05-01"}, "sufficient"),
                ("What is Sam's birth year?", {}, "conflict"),
                ("What is Alex's passport number?", {}, "insufficient"),
            ]:
                response = client.post("/queries", json={"dataset_id": dataset_id, "sample_id": "conv-a", "build_id": build_id, "question": question, **extra})
                assert response.status_code == 201, response.text
                trace = response.json()
                assert trace["build_id"] == build_id
                assert trace["answer"]["status"] == expected
                assert len(trace["initial"]["initial_candidates"]) == 1
                expanded = {item["memory"]["state_value"] for item in trace["expanded"]["candidates"]}
                if expected == "sufficient":
                    assert trace["initial"]["initial_candidates"][0]["memory"]["state_value"] == "Rome"
                    assert expanded == {"Rome", "Paris"}
                    assert ("Paris" if extra else "Rome") in trace["answer"]["answer"]
                elif expected == "conflict":
                    assert expanded == {"1990", "1992"}
                    assert {c["memory_id"] for c in trace["answer"]["citations"]} == set(trace["resolution"]["effective_memory_ids"])
                    assert len(trace["answer"]["citations"]) == 2
                else:
                    assert trace["effective_memories"] == []
                    assert trace["answer"]["citations"] == []
