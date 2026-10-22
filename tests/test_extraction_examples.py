import json

import httpx
import pytest
from fastapi.testclient import TestClient

from conftest import import_sample
from locomo_memory.api import create_app
from locomo_memory.memory_schemas import ExtractionBatch
from locomo_memory.model import DeepSeekModel
from test_builds import completion


@pytest.mark.parametrize('first_failure', ['anchor', 'length'])
def test_extraction_retry_explains_existing_source_and_identifier_constraints(settings, first_failure):
    from test_builds import draft
    sources = {'s1': {'source_id': 's1', 'text': 'I moved.'},
               's2': {'source_id': 's2', 'text': 'Yesterday I moved.'}}
    requests = []
    def provider(request):
        body = json.loads(request.content)
        requests.append(body)
        payload = json.loads(body['messages'][1]['content'])
        if len(requests) > 1:
            feedback = payload['retry_feedback']
            assert feedback['field_path'] == ('memories[0]' if first_failure == 'anchor' else None)
            assert 'anchor_source_id must also occur in that memory' in feedback['instruction']
            assert 'entity_id' in feedback['instruction'] and 'state_dimension' in feedback['instruction']
        memory = draft(['s1'] if len(requests) == 1 else ['s1', 's2'],
                       time={'anchor_source_id': 's2', 'original_expression': 'Yesterday'})
        return completion({'memories': [memory]}, finish='length' if first_failure == 'length' and len(requests) == 1 else 'stop')
    model = DeepSeekModel(settings, api_key='synthetic', transport=httpx.MockTransport(provider))
    result = model.generate('extract', {'sources': list(sources.values())}, ExtractionBatch, context={'sources': sources})
    assert len(requests) == 2
    assert result.value.memories[0].source_ids == ['s1', 's2']
    assert requests[0]['thinking'] == requests[1]['thinking'] == {'type': 'disabled'}


def test_extraction_request_examples_are_valid_and_do_not_leak_into_saved_memories(settings, sample):
    observed = []

    def provider(request):
        messages = json.loads(request.content)["messages"]
        examples = json.loads(messages[0]["content"].split("Synthetic examples JSON:\n")[1].split("\nJSON schema:")[0])
        for example in examples:
            ExtractionBatch.model_validate(example["output"], context={"sources": {s["source_id"]: s for s in example["sources"]}})
        observed.extend(examples)
        sources = json.loads(messages[1]["content"])["sources"]
        output = examples[0]["output"]
        output["memories"][0]["source_ids"] = [sources[0]["source_id"]]
        return completion(output)

    model = DeepSeekModel(settings, api_key="synthetic-test-key", transport=httpx.MockTransport(provider))
    with TestClient(create_app(settings, model=model)) as client:
        dataset = import_sample(client, sample).json()["dataset_id"]
        build = client.post("/builds", json={"dataset_id": dataset, "sample_id": "conv-a"}).json()
        result = client.get(f"/builds/{build['build_id']}").json()
        assert result["status"] == "extracted"
        assert result["prompt_version"] != "extract-v1"
        memories = client.get(f"/builds/{build['build_id']}/memories").json()["items"]
        assert len(memories) == 1
        assert memories[0]["statement_type"] == "plan"
        assert memories[0]["time"]["event_start"] is None
        assert memories[0]["source_ids"] == [f"{dataset}/conv-a/D1:1"]
        assert len(observed) == 4
        # Independently expected semantic boundaries of the synthetic examples.
        assert observed[1]["output"]["memories"][0]["statement_type"] == "fact"
        assert observed[1]["output"]["memories"][1]["polarity"] == "negative"
        assert observed[2]["output"]["memories"][0]["entity_id"] == "Sam"
        assert [m["state_value"] for m in observed[3]["output"]["memories"]] == ["research", "application", "interview"]
