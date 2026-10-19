"""HTTP inspection and explicit lifecycle controls for durable builds."""

import json
from typing import Annotated

from fastapi import BackgroundTasks, FastAPI, Query, Request
from fastapi.responses import JSONResponse

from .builds import BuildError, BuildService
from .memory_schemas import BuildFragment, BuildRequest, BuildVersion, Memory
from .schemas import Page

Limit = Annotated[int, Query(ge=1, le=100)]
Offset = Annotated[int, Query(ge=0)]


def register_build_routes(app: FastAPI, service: BuildService):
    database = service.database

    @app.exception_handler(BuildError)
    async def build_error(request: Request, error: BuildError):
        messages = {"invalid_export": "The selected complete version has inconsistent artifacts or source references", "not_found": "Resource not found", "build_already_running": "Another build is active", "build_not_retryable": "Only failed or interrupted extraction can use this retry; later stages have separate controls", "build_configuration_changed": "Settings changed; create a new build to preserve version identity", "index_not_ready": "This version has no ready index", "build_not_indexable": "Indexing requires extracted memories or an interrupted index phase", "index_fingerprint_mismatch": "The index and current model identity differ; use a matching version", "index_failed": "Index construction failed", "relations_not_ready": "Relation construction requires an indexed version or an explicit relation retry", "projection_not_ready": "The current-state projection is not ready", "projection_not_mutable": "Only an incomplete related version can explicitly rebuild its projection", "version_not_publishable": "Extraction, index, relations and projection must all validate before publication", "no_complete_version": "No matching complete version is available", "invalid_session_time": "The original session timestamp could not be interpreted"}
        return JSONResponse(status_code=error.status, content={"error": {"code": error.code, "message": messages.get(error.code, "Build operation failed")}})

    @app.post("/builds", response_model=BuildVersion, status_code=202)
    def start_build(request: BuildRequest, tasks: BackgroundTasks):
        build = service.start(request.dataset_id, request.sample_id)
        tasks.add_task(service.run, build["build_id"])
        return build

    @app.get("/builds", response_model=Page[BuildVersion])
    def list_builds(dataset_id: str | None = None, sample_id: str | None = None, limit: Limit = 20, offset: Offset = 0):
        predicates, values = [], []
        for field, value in (("dataset_id", dataset_id), ("sample_id", sample_id)):
            if value is not None:
                predicates.append(field + "=?")
                values.append(value)
        where = " WHERE " + " AND ".join(predicates) if predicates else ""
        with database.connect() as db:
            total = db.execute("SELECT COUNT(*) FROM build_versions" + where, values).fetchone()[0]
            ids = db.execute("SELECT build_id FROM build_versions" + where + " ORDER BY created_at DESC,build_id LIMIT ? OFFSET ?", [*values, limit, offset]).fetchall()
        return {"items": [service.get(row["build_id"]) for row in ids], "total": total, "limit": limit, "offset": offset}

    @app.get("/builds/{build_id}", response_model=BuildVersion)
    def inspect_build(build_id: str):
        return service.get(build_id)

    @app.post("/builds/{build_id}/retry", response_model=BuildVersion, status_code=202)
    def retry_build(build_id: str, tasks: BackgroundTasks):
        build = service.retry(build_id)
        tasks.add_task(service.run, build_id)
        return build

    @app.get("/builds/{build_id}/fragments", response_model=Page[BuildFragment])
    def fragments(build_id: str, limit: Limit = 20, offset: Offset = 0):
        service.get(build_id)
        with database.connect() as db:
            total = db.execute("SELECT COUNT(*) FROM build_fragments WHERE build_id=?", (build_id,)).fetchone()[0]
            rows = db.execute("SELECT * FROM build_fragments WHERE build_id=? ORDER BY ordinal LIMIT ? OFFSET ?", (build_id, limit, offset)).fetchall()
        items = []
        for row in rows:
            item = dict(row)
            item["source_ids"] = json.loads(item.pop("source_ids_json"))
            item["model_metadata"] = json.loads(item.pop("model_metadata_json"))
            items.append(item)
        return {"items": items, "total": total, "limit": limit, "offset": offset}

    @app.get("/builds/{build_id}/memories", response_model=Page[Memory])
    def memories(build_id: str, limit: Limit = 20, offset: Offset = 0):
        service.get(build_id)
        with database.connect() as db:
            total = db.execute("SELECT COUNT(*) FROM memories WHERE build_id=?", (build_id,)).fetchone()[0]
            rows = db.execute("SELECT m.memory_json FROM memories m JOIN build_fragments f ON m.fragment_id=f.fragment_id WHERE m.build_id=? ORDER BY f.ordinal,m.rowid LIMIT ? OFFSET ?", (build_id, limit, offset)).fetchall()
        return {"items": [json.loads(row["memory_json"]) for row in rows], "total": total, "limit": limit, "offset": offset}

    @app.get("/builds/{build_id}/memories/{memory_id}", response_model=Memory)
    def memory(build_id: str, memory_id: str):
        with database.connect() as db:
            row = db.execute("SELECT memory_json FROM memories WHERE build_id=? AND memory_id=?", (build_id, memory_id)).fetchone()
        if row is None:
            raise BuildError("not_found", 404)
        return json.loads(row["memory_json"])
