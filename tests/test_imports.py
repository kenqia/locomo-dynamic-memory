from conftest import import_sample


def test_import_preserves_sources_and_separates_annotations(client, sample):
    response = import_sample(client, sample)
    assert response.status_code == 201
    imported = response.json()
    assert imported["conversation_count"] == 1
    assert imported["turn_count"] == 3
    dataset_id = imported["dataset_id"]
    conversations = client.get(f"/datasets/{dataset_id}/conversations").json()
    assert conversations["items"][0]["sample_id"] == "conv-a"
    response = client.get(f"/datasets/{dataset_id}/conversations/conv-a/turns")
    assert response.status_code == 200
    page = response.json()
    assert page["total"] == 3
    assert page["items"][0] == {
        "source_id": f"{dataset_id}/conv-a/D1:1", "dataset_id": dataset_id,
        "sample_id": "conv-a", "session_id": "session_1", "dia_id": "D1:1",
        "speaker": "Alex", "session_time": "1:00 pm on 1 May, 2023",
        "text": "I live in Paris.", "position": 0,
    }
    assert "ANNOTATION ONLY" not in response.text


def test_unknown_session_has_consistent_not_found_error(client, sample):
    imported = import_sample(client, sample).json()
    response = client.get(f"/datasets/{imported['dataset_id']}/conversations/conv-a/turns", params={"session_id": "session_99"})
    assert response.status_code == 404
    assert response.json() == {"error": {"code": "not_found", "message": "Resource not found"}}


def test_file_import_records_original_bytes_checksum(client, sample):
    import hashlib
    import json

    raw = (json.dumps(sample, indent=3) + "\n").encode()
    response = client.post("/imports/file", files={"file": ("fixture.json", raw, "application/json")}, data={"version": "file-v1", "license": "test-only"})
    assert response.status_code == 201
    result = response.json()
    assert result["artifact_sha256"] == hashlib.sha256(raw).hexdigest()
    provenance = client.get(f"/datasets/{result['dataset_id']}/provenance").json()
    assert provenance["items"][0]["checksum_basis"] == "original_bytes"


def test_sources_persist_across_app_restart(settings, sample):
    from fastapi.testclient import TestClient
    from locomo_memory.api import create_app

    with TestClient(create_app(settings)) as first:
        dataset_id = import_sample(first, sample).json()["dataset_id"]
    with TestClient(create_app(settings)) as restarted:
        result = restarted.get(f"/datasets/{dataset_id}/conversations/conv-a/turns/D2:1")
        assert result.status_code == 200
        assert result.json()["text"] == "I moved to Rome."


def test_pagination_preserves_order_and_session_filter(client, sample):
    dataset_id = import_sample(client, sample).json()["dataset_id"]
    base = f"/datasets/{dataset_id}/conversations/conv-a"
    page = client.get(f"{base}/turns", params={"limit": 1, "offset": 1}).json()
    assert page["total"] == 3
    assert page["limit"] == 1 and page["offset"] == 1
    assert [turn["dia_id"] for turn in page["items"]] == ["D1:2"]
    sessions = client.get(f"{base}/sessions", params={"limit": 1, "offset": 1}).json()
    assert sessions == {"items": [{"session_id": "session_2", "session_time": "1:00 pm on 2 May, 2023", "turn_count": 1}], "total": 2, "limit": 1, "offset": 1}
    filtered = client.get(f"{base}/turns", params={"session_id": "session_2"}).json()
    assert [turn["dia_id"] for turn in filtered["items"]] == ["D2:1"]
    assert client.get(f"{base}/turns", params={"offset": 99}).json()["items"] == []


def test_annotation_changes_reuse_identical_source_view(client, sample):
    first = import_sample(client, sample).json()
    path = f"/datasets/{first['dataset_id']}/conversations/conv-a/turns"
    original = client.get(path).json()
    sample[0]["qa"] = [{"answer": "DIFFERENT", "evidence": ["invalid"]}]
    sample[0]["observation"] = "DIFFERENT"
    sample[0]["session_summary"] = "DIFFERENT"
    sample[0]["event_summary"] = "DIFFERENT"
    second = import_sample(client, sample).json()
    assert second["reused"] is True
    assert first["dataset_id"] == second["dataset_id"]
    assert first["source_sha256"] == second["source_sha256"]
    assert first["artifact_sha256"] != second["artifact_sha256"]
    assert client.get(path).json() == original
    assert client.get("/datasets").json()["total"] == 1
    assert client.get(f"/datasets/{first['dataset_id']}/provenance").json()["total"] == 2
    third = import_sample(client, sample).json()
    assert third["reused"] is True
    assert client.get(f"/datasets/{first['dataset_id']}/provenance").json()["total"] == 2


def test_same_names_and_dialogue_ids_stay_in_their_conversations(client, sample):
    from copy import deepcopy

    second = deepcopy(sample[0])
    second["sample_id"] = "conv-b"
    second["conversation"]["session_1"][0]["text"] = "I live in Berlin."
    sample.append(second)
    dataset_id = import_sample(client, sample).json()["dataset_id"]
    base = f"/datasets/{dataset_id}/conversations"
    original = client.get(f"{base}/conv-a/turns/D1:1").json()
    other = client.get(f"{base}/conv-b/turns/D1:1").json()
    assert original["text"] == "I live in Paris."
    assert other["text"] == "I live in Berlin."
    assert original["source_id"] != other["source_id"]
    assert client.get(base, params={"limit": 1, "offset": 1}).json()["items"][0]["sample_id"] == "conv-b"


def test_invalid_imports_fail_atomically_and_do_not_echo_input(client, sample):
    from copy import deepcopy

    mutations = []
    duplicate = deepcopy(sample)
    duplicate[0]["conversation"]["session_1"].append(duplicate[0]["conversation"]["session_1"][0])
    mutations.append(duplicate)
    missing = deepcopy(sample)
    del missing[0]["conversation"]["session_1"][0]["text"]
    mutations.append(missing)
    missing_time = deepcopy(sample)
    del missing_time[0]["conversation"]["session_1_date_time"]
    mutations.append(missing_time)
    duplicate_sample = deepcopy(sample)
    duplicate_sample.extend(deepcopy(sample))
    mutations.append(duplicate_sample)
    unknown_speaker = deepcopy(sample)
    unknown_speaker[0]["conversation"]["session_1"][0]["speaker"] = "synthetic-private-marker"
    mutations.append(unknown_speaker)
    for invalid in mutations:
        response = import_sample(client, invalid)
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "invalid_input"
        assert "synthetic-private-marker" not in response.text
        assert client.get("/datasets").json()["total"] == 0


def test_list_errors_have_consistent_shapes(client):
    for path in ("/datasets?limit=0", "/datasets?offset=-1", "/datasets?limit=101"):
        response = client.get(path)
        assert response.status_code == 422
        assert set(response.json()["error"]) == {"code", "message"}
    response = client.get("/datasets/nonexistent")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_invalid_file_json_has_safe_error(client):
    response = client.post("/imports/file", files={"file": ("fixture.json", b'{invalid synthetic-private-marker', "application/json")}, data={"version": "v1", "license": "test"})
    assert response.status_code == 422
    assert "synthetic-private-marker" not in response.text


def test_official_data_provenance_and_source_mapping(client):
    response = client.post("/imports/official")
    assert response.status_code == 201
    result = response.json()
    assert result["conversation_count"] == 10
    assert result["turn_count"] == 5882
    assert result["artifact_sha256"] == "79fa87e90f04081343b8c8debecb80a9a6842b76a7aa537dc9fdf651ea698ff4"
    dataset_id = result["dataset_id"]
    metadata = client.get(f"/datasets/{dataset_id}").json()
    assert metadata["version"] == "3eb6f2c585f5e1699204e3c3bdf7adc5c28cb376"
    assert metadata["license"] == "CC-BY-NC-4.0"
    artifact = client.get(f"/datasets/{dataset_id}/provenance").json()["items"][0]
    assert artifact["provenance"]["license_sha256"] == "41003d4a74749c0220e33dd415042164b5a1093ed401f36277234f772d22d3d0"
    source = client.get(f"/datasets/{dataset_id}/conversations/conv-26/turns/D1:1").json()
    assert source["speaker"] == "Caroline"
    assert source["text"] == "Hey Mel! Good to see you! How have you been?"
    assert source["session_time"] == "1:56 pm on 8 May, 2023"
