import json

import httpx
import pytest
from fastapi.testclient import TestClient

from locomo_memory.api import create_app
from locomo_memory.model import DeepSeekModel
from test_builds import completion, draft
from test_relations import relation
from test_retrieval import ControlledEmbedder, build


@pytest.mark.parametrize("fault", [None, "missing", "no_transition", "different_process", "wrong_endpoint", "invented_quote", "string_boolean"])
def test_update_requires_two_source_supported_real_stages_and_exports_its_contract(settings, sample, fault):
    settings = settings.model_copy(update={"model_retries": 1})
    sample[0]["conversation"]["session_1"][0]["text"] = "I enrolled in a pottery class."
    sample[0]["conversation"]["session_2"][0]["text"] = "I made a vase in that pottery class."

    def provider(request):
        payload = json.loads(json.loads(request.content)["messages"][1]["content"])
        if "new_memory" in payload:
            old, new = payload["history"][0], payload["new_memory"]
            sources = {s["source_id"]: s for s in payload["sources"]}
            evidence = {"same_process": True, "real_stage_changed": True,
                "old_stage": {"description": "Enrolled in the course", "source_id": old["source_ids"][0], "quote": sources[old["source_ids"][0]]["text"]},
                "new_stage": {"description": "Made course work", "source_id": new["source_ids"][0], "quote": sources[new["source_ids"][0]]["text"]}}
            if fault == "no_transition":
                evidence["real_stage_changed"] = False
            if fault == "different_process":
                evidence["same_process"] = False
            if fault == "wrong_endpoint":
                evidence["old_stage"]["source_id"] = new["source_ids"][0]
            if fault == "invented_quote":
                evidence["old_stage"]["quote"] = "invented quotation"
            if fault == "string_boolean":
                evidence["same_process"] = "true"
            return completion({"judgments": [relation(old, new, label="UPDATE", support_quote=sources[new["source_ids"][0]]["text"], reason="Work was produced in the enrolled course", **({"update_evidence": evidence} if fault != "missing" else {}))]})
        sources = payload["sources"]
        return completion({"memories": [draft([sources[0]["source_id"]], content=sources[0]["text"], memory_type="event", state_dimension="enrollment"),
            draft([sources[2]["source_id"]], content=sources[2]["text"], memory_type="event", state_dimension="course_work")]})

    model = DeepSeekModel(settings, api_key="synthetic-test-key", transport=httpx.MockTransport(provider))
    with TestClient(create_app(settings, model=model, embedder=ControlledEmbedder())) as client:
        bid = build(client, sample)
        client.post(f"/builds/{bid}/index")
        client.post(f"/builds/{bid}/relations")
        if fault:
            assert client.get(f"/builds/{bid}").json()["status"] == "relations_failed"
            task = client.get(f"/builds/{bid}/relation-tasks").json()["items"][0]
            assert len(task["model_metadata"]["calls"]) == 2
            assert client.get(f"/builds/{bid}/relations").json()["total"] == 0
            assert client.post(f"/builds/{bid}/publish").status_code == 409
            return
        assert client.get(f"/builds/{bid}").json()["status"] == "related"
        assert client.post(f"/builds/{bid}/publish").status_code == 200
        bundle = client.get(f"/builds/{bid}/export").json()
        assert bundle["relation_contract_version"] == "relation-v2-stage-evidence"
        assert bundle["relations"][0]["update_evidence"]["real_stage_changed"] is True
        from locomo_memory.export_schemas import MemoryExport
        bundle["schema_version"] = "memory-export-v1"
        bundle.pop("relation_contract_version")
        bundle["relations"][0].pop("update_evidence")
        legacy = MemoryExport.model_validate(bundle)
        assert legacy.relation_contract_version == "relation-v1"
        assert legacy.relations[0].update_evidence is None
