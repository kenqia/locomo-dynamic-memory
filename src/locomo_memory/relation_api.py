"""Source-linked relation/state inspection and explicit complete publication."""

import json
from typing import Annotated

from fastapi import BackgroundTasks, FastAPI, Query

from .builds import BuildError
from .relation_schemas import ExpansionRequest, MemoryRelation
from .relations import RelationService
from .schemas import Page
from .versions import VersionsService

Limit = Annotated[int, Query(ge=1, le=100)]
Offset = Annotated[int, Query(ge=0)]


def register_relation_routes(app: FastAPI, service: RelationService, versions: VersionsService, expansion):
    database = service.database

    @app.post("/builds/{build_id}/relations", status_code=202)
    def construct_relations(build_id: str, tasks: BackgroundTasks):
        result = service.start(build_id)
        tasks.add_task(service.run, build_id)
        return result

    @app.get("/builds/{build_id}/relation-progress")
    def progress(build_id: str):
        return service.progress(build_id)

    @app.get("/builds/{build_id}/relation-tasks")
    def tasks(build_id: str, limit: Limit = 20, offset: Offset = 0):
        service.progress(build_id)
        with database.connect() as db:
            db.execute("BEGIN")
            total = db.execute("SELECT COUNT(*) FROM relation_tasks WHERE build_id=?", (build_id,)).fetchone()[0]
            rows = db.execute("SELECT * FROM relation_tasks WHERE build_id=? ORDER BY ordinal LIMIT ? OFFSET ?", (build_id, limit, offset)).fetchall()
            items = []
            for row in rows:
                item = dict(row)
                item["history_ids"] = json.loads(item.pop("history_ids_json"))
                item["model_metadata"] = json.loads(item.pop("metadata_json"))
                item.update(service.attempts.history(db, item["task_id"], item["attempts"]))
                items.append(item)
        return {"items": items, "total": total, "limit": limit, "offset": offset}

    @app.get("/builds/{build_id}/relations", response_model=Page[MemoryRelation])
    def relations(build_id: str, limit: Limit = 20, offset: Offset = 0):
        service.builds.get(build_id)
        with database.connect() as db:
            total = db.execute("SELECT COUNT(*) FROM memory_relations WHERE build_id=?", (build_id,)).fetchone()[0]
            rows = db.execute("SELECT relation_json FROM memory_relations WHERE build_id=? ORDER BY relation_id LIMIT ? OFFSET ?", (build_id, limit, offset)).fetchall()
        return {"items": [json.loads(row["relation_json"]) for row in rows], "total": total, "limit": limit, "offset": offset}

    @app.get("/builds/{build_id}/current-state")
    def current_state(build_id: str):
        return service.current_state(build_id)

    @app.post("/builds/{build_id}/current-state/rebuild")
    def rebuild_current_state(build_id: str):
        return service.rebuild_projection(build_id)

    @app.post("/builds/{build_id}/publish")
    def publish(build_id: str):
        return versions.publish(build_id)

    @app.get("/versions/pin")
    def pin(dataset_id: str, sample_id: str, build_id: str | None = None):
        return versions.pin_details(dataset_id, sample_id, build_id)


    @app.post("/candidate-expansions", status_code=201)
    def expand_candidates(request: ExpansionRequest):
        return expansion.expand(request.query_id)

    @app.get("/candidate-expansions/{expansion_id}")
    def inspect_expansion(expansion_id: str):
        with database.connect() as db:
            row = db.execute("SELECT result_json FROM candidate_expansions WHERE expansion_id=?", (expansion_id,)).fetchone()
        if row is None:
            raise BuildError("not_found", 404)
        return json.loads(row[0])
