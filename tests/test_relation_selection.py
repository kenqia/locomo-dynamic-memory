import json

import httpx
import pytest
from fastapi.testclient import TestClient

from locomo_memory.api import create_app
from locomo_memory.model import DeepSeekModel
from test_builds import completion, draft
from test_relations import relation
from test_retrieval import ControlledEmbedder, build


@pytest.mark.parametrize("cap", [1, 2, 20])
def test_old_same_dimension_fact_and_cross_dimension_process_survive_recent_noise_and_retry(settings, sample, cap):
    texts = ["I work at Cedar.", "I enrolled in a pottery class."]
    texts += [f"I plan to work for employer number {i}." for i in range(24)]
    texts += ["I still work at Cedar.", "I made a vase in that pottery class."]
    sample[0]["conversation"]["session_1"] = [{"dia_id": f"D1:{i+1}", "speaker": "Alex", "text": t} for i, t in enumerate(texts)]
    del sample[0]["conversation"]["session_2"]
    del sample[0]["conversation"]["session_2_date_time"]
    local = settings.model_copy(update={"fragment_turns": 100, "model_retries": 0, "relation_history_limit": cap})
    observed, retry = {}, False

    def provider(request):
        payload = json.loads(json.loads(request.content)["messages"][1]["content"])
        if "new_memory" in payload:
            new = payload["new_memory"]
            observed.setdefault(new["content"], []).append(payload["history"])
            if new["content"] == texts[-1] and not retry:
                return completion({"judgments": []})
            return completion({"judgments": [relation(old, new) for old in payload["history"]]})
        memories = []
        for source in payload["sources"]:
            text = source["text"]
            pottery = "pottery" in text
            memories.append(draft([source["source_id"]], content=text,
                state_dimension="course_enrollment" if "enrolled" in text else "pottery_work" if pottery else "employment",
                state_value="pottery" if pottery else "Cedar" if "Cedar" in text else None,
                statement_type="plan" if "plan" in text else "fact",
                memory_type="event" if pottery else "state"))
        return completion({"memories": memories})

    model = DeepSeekModel(local, api_key="synthetic-test-key", transport=httpx.MockTransport(provider))
    with TestClient(create_app(local, model=model, embedder=ControlledEmbedder())) as client:
        bid = build(client, sample)
        assert client.post(f"/builds/{bid}/index").status_code == 201
        assert client.post(f"/builds/{bid}/relations").status_code == 202
        assert texts[0] in {m["content"] for m in observed[texts[-2]][0]}
        assert texts[1] in {m["content"] for m in observed[texts[-1]][0]}
        tasks = client.get(f"/builds/{bid}/relation-tasks", params={"limit": 100}).json()["items"]
        last = next(t for t in tasks if t["status"] == "failed")
        assert last["selection"]["algorithm_version"]
        assert last["selection"]["omitted_count"] > 0
        assert len(last["history_ids"]) == len(set(last["history_ids"])) == cap
        retry = True
        client.post(f"/builds/{bid}/relations")
        assert observed[texts[-1]][0] == observed[texts[-1]][1]
        assert client.get(f"/builds/{bid}").json()["status"] == "related"
