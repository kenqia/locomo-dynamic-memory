"""Release acceptance at real HTTP/file/process boundaries, synthetic inputs only."""

import hashlib
import json
from pathlib import Path
import socket
import sqlite3
import sys

from fastapi.testclient import TestClient
import httpx
import jsonschema
import pytest
from streamlit.testing.v1 import AppTest

from locomo_memory.api import create_app
from locomo_memory.model import DeepSeekModel
from locomo_memory.release_cli import check_ports, doctor
from locomo_memory.release_viewer import DEMO, ExportCatalog, create_replay_app, load_export
from locomo_memory.export_schemas import MemoryExport
from test_builds import completion
from test_queries import complete_build, query_provider
from test_retrieval import ControlledEmbedder


def test_hybrid_is_public_default_but_dynamic_stays_explicit(settings, sample):
    operations = []

    def provider(request):
        payload = json.loads(json.loads(request.content)["messages"][1]["content"])
        operations.append(payload.get("operation", "query_analysis"))
        return query_provider(request)

    model = DeepSeekModel(settings, api_key="synthetic-test-only", transport=httpx.MockTransport(provider))
    with TestClient(create_app(settings, model, ControlledEmbedder())) as client:
        ds, bid = complete_build(client, sample)
        before = client.get(f"/builds/{bid}/current-state").json()
        operations.clear()
        body = {"dataset_id": ds, "sample_id": "conv-a", "question": "Where did Alex live?", "requested_date": "2023-05-01"}
        result = client.post("/queries", json=body)
        assert result.status_code == 201, result.text
        trace = result.json()
        assert trace["strategy"] == "hybrid_no_resolution"
        assert operations == ["query_analysis", "answer"]
        assert trace["time"]["requested_date"] == "2023-05-01"
        assert trace["resolution"]["status"] == "not_applied"
        assert trace["effective_memories"] == []
        assert trace["answer_context_items"]
        assert client.get("/queries/" + trace["trace_id"]).json() == trace
        operations.clear()
        assert client.post("/queries", json={**body, "strategy": "dynamic"}).status_code == 201
        assert operations == ["query_analysis", "resolve", "answer"]
        assert client.get(f"/builds/{bid}/current-state").json() == before


def test_hybrid_failure_persists_trace(settings, sample):
    def provider(request):
        payload = json.loads(json.loads(request.content)["messages"][1]["content"])
        if payload.get("operation") == "answer":
            return completion({"invalid": "synthetic contract rejection"})
        return query_provider(request)

    local = settings.model_copy(update={"model_retries": 0})
    model = DeepSeekModel(local, api_key="synthetic-only", transport=httpx.MockTransport(provider))
    with TestClient(create_app(local, model, ControlledEmbedder())) as client:
        ds, bid = complete_build(client, sample)
        result = client.post("/queries", json={"dataset_id": ds, "sample_id": "conv-a", "question": "Where?"})
        assert result.status_code == 502
        trace = client.get("/queries/" + result.json()["error"]["trace_id"]).json()
        assert trace["outcome"] == "failed" and trace["strategy"] == "hybrid_no_resolution"
        assert trace["usage_summary"]["calls"] >= 1
        assert trace["answer_context_items"]


def test_replay_has_no_model_database_or_mutation_surface(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("offline replay crossed a forbidden boundary")

    monkeypatch.setattr(DeepSeekModel, "generate", forbidden)
    monkeypatch.setattr(sqlite3, "connect", forbidden)
    with TestClient(create_replay_app()) as client:
        assert client.get("/health").json()["provider_requests"] == 0
        assert client.get("/catalog").json()["kind"] == "Synthetic / Offline Replay"
        export = client.get("/exports/conv-a")
        assert export.status_code == 200
        bundle = MemoryExport.model_validate(export.json())
        assert client.get("/sources/conv-a/" + bundle.sources[0].dia_id).status_code == 200
        assert client.get("/sources/conv-a/missing").status_code == 404
        assert client.get("/exports/missing").status_code == 404
        assert client.get("/builds/conv-a/graph?root=other-build").status_code == 422
        assert client.get("/builds/conv-a/graph").json()["edges"]
        for path in ("/queries", "/builds", "/imports", "/resolve", "/answer"):
            assert client.post(path, json={}).status_code in (404, 405)


def test_replay_ui_all_controls_without_network_database_or_credentials(monkeypatch):
    monkeypatch.setitem(sys.modules, "__main__", sys.modules["__main__"])
    monkeypatch.delenv("LOCOMO_REPLAY_MANIFEST", raising=False)
    monkeypatch.delenv("LOCOMO_REPLAY_DIRECTORY", raising=False)

    def forbidden(*args, **kwargs):
        raise AssertionError("offline viewer attempted network or database access")

    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(sqlite3, "connect", forbidden)
    app = AppTest.from_file(str(Path(__file__).parents[2] / "src/locomo_memory/replay_ui.py"), default_timeout=30).run()
    assert not app.exception
    for checkbox in app.checkbox:
        checkbox.set_value(True)
    app.run()
    assert not app.exception
    app.selectbox[-1].set_value("Failed Trace").run()
    assert not app.exception and any("invalid_source_id" in e.value for e in app.error)


def test_export_json_schema_and_source_time_anchor():
    bundle = load_export(DEMO / "conv-a.json")
    jsonschema.Draft202012Validator(MemoryExport.model_json_schema()).validate(bundle.model_dump(mode="json"))
    assert ExportCatalog(DEMO / "manifest.json").verify()["status"] == "PASS"


@pytest.mark.parametrize("fault", ["sha", "build", "path", "missing", "time"])
def test_catalog_rejects_corruption_and_scope_escape(tmp_path, fault):
    manifest = json.loads((DEMO / "manifest.json").read_text())
    data = json.loads((DEMO / "conv-a.json").read_text())
    target = tmp_path / "conv-a.json"
    if fault == "build":
        manifest["builds"][0]["build_id"] = "wrong-build"
    if fault == "path":
        manifest["builds"][0]["file"] = "../conv-a.json"
    if fault == "time":
        data["memories"][0]["time"] = {"original_expression": "fabricated timestamp", "anchor_source_id": data["memories"][0]["source_ids"][0]}
    target.write_text(json.dumps(data))
    manifest["builds"][0]["sha256"] = hashlib.sha256(target.read_bytes()).hexdigest()
    if fault == "sha":
        manifest["builds"][0]["sha256"] = "0" * 64
    if fault == "missing":
        target.unlink()
    m = tmp_path / "manifest.json"
    m.write_text(json.dumps(manifest))
    with pytest.raises((ValueError, OSError)):
        ExportCatalog(m).read("conv-a")


def test_port_collision_and_corrupt_database_doctor(tmp_path):
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        with pytest.raises(ValueError, match="occupied"):
            check_ports([sock.getsockname()[1]])
    with pytest.raises(ValueError, match="differ"):
        check_ports([8511, 8511])
    db = tmp_path / "corrupt.sqlite3"
    db.write_bytes(b"not a sqlite database")
    config = tmp_path / "config.toml"
    config.write_text('db_path = ' + json.dumps(str(db)))
    assert doctor(config) == 1
    assert db.read_bytes() == b"not a sqlite database"


def test_controlled_viewer_never_labels_real_exports_as_synthetic(tmp_path, monkeypatch):
    import shutil
    manifest = json.loads((DEMO / "manifest.json").read_text())
    manifest["kind"] = "Controlled MemoryExport / Offline read-only"
    manifest["replays"] = []
    shutil.copyfile(DEMO / "conv-a.json", tmp_path / "conv-a.json")
    m = tmp_path / "manifest.json"
    m.write_text(json.dumps(manifest))
    monkeypatch.setenv("LOCOMO_REPLAY_MANIFEST", str(m))
    monkeypatch.setenv("LOCOMO_REPLAY_DIRECTORY", str(tmp_path))
    app = AppTest.from_file(str(Path(__file__).parents[2] / "src/locomo_memory/replay_ui.py"), default_timeout=30).run()
    assert not app.exception
    assert not any("合成来源" in w.value for w in app.warning)
    assert any("Controlled MemoryExport" in i.value for i in app.info)
    assert any("不会创建新的回答" in i.value for i in app.info)
