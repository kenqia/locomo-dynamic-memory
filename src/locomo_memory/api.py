"""FastAPI entry point. All app state is scoped to the factory's settings."""

from contextlib import asynccontextmanager
import hashlib
import json
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from .config import Settings, load_settings
from .database import Database, backend_ownership
from .build_api import register_build_routes
from .builds import BuildService
from .model import DeepSeekModel
from .embeddings import MiniLMEmbedder
from .retrieval import RetrievalService
from .retrieval_api import register_retrieval_routes
from .relations import RelationService
from .relation_api import register_relation_routes
from .versions import VersionsService
from .expansion import ExpansionService
from .imports import import_dataset
from .schemas import Conversation, Dataset, ErrorResponse, ImportRequest, ImportResult, Page, Session, SourceTurn

Limit = Annotated[int, Query(ge=1, le=100)]
Offset = Annotated[int, Query(ge=0)]
OFFICIAL_DIRECTORY = Path(__file__).resolve().parents[2] / "data/raw/locomo"


def create_app(settings: Settings | None = None, model=None, embedder=None) -> FastAPI:
    settings = settings or load_settings()
    database = Database(settings.db_path)
    model = model if model is not None else DeepSeekModel(settings)
    builds = BuildService(database, settings, model)
    embedder = embedder if embedder is not None else MiniLMEmbedder(settings)
    retrieval = RetrievalService(builds, settings, embedder, model)
    relations = RelationService(builds, model)
    versions = VersionsService(builds)
    expansion = ExpansionService(relations)

    @asynccontextmanager
    async def lifespan(app):
        with backend_ownership(settings.db_path):
            builds.recover_interrupted()
            relations.recover_interrupted()
            yield

    app = FastAPI(title="LoCoMo dynamic memory", lifespan=lifespan, responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}})
    app.state.settings = settings
    app.state.database = database
    app.state.model = model
    app.state.embedder = embedder
    app.state.builds = builds
    register_build_routes(app, builds)
    app.state.retrieval = retrieval
    register_retrieval_routes(app, retrieval)
    app.state.relations = relations
    app.state.versions = versions
    register_relation_routes(app, relations, versions, expansion)
    app.state.expansion = expansion

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request: Request, exc: RequestValidationError):
        # Never echo submitted data or validation context; either can contain secrets.
        return JSONResponse(status_code=422, content={"error": {"code": "invalid_input", "message": "Invalid request structure, fields, or source references"}})

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, exc: StarletteHTTPException):
        if isinstance(exc.detail, dict) and "code" in exc.detail:
            error = exc.detail
        else:
            error = {"code": "not_found" if exc.status_code == 404 else "request_failed", "message": "Resource not found" if exc.status_code == 404 else "Request could not be processed"}
        return JSONResponse(status_code=exc.status_code, content={"error": error})

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, exc: Exception):
        return JSONResponse(status_code=500, content={"error": {"code": "internal_error", "message": "An internal operation failed"}})

    def require_dataset(dataset_id: str):
        with database.connect() as db:
            row = db.execute("SELECT * FROM datasets WHERE dataset_id=?", (dataset_id,)).fetchone()
        if row is None:
            raise HTTPException(404)
        return dict(row)

    def require_conversation(dataset_id: str, sample_id: str):
        require_dataset(dataset_id)
        with database.connect() as db:
            row = db.execute("SELECT * FROM conversations WHERE dataset_id=? AND sample_id=?", (dataset_id, sample_id)).fetchone()
        if row is None:
            raise HTTPException(404)
        return dict(row)

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.post("/imports", response_model=ImportResult, status_code=201)
    def import_uploaded(request: ImportRequest):
        return import_dataset(database, request)

    @app.post("/imports/file", response_model=ImportResult, status_code=201)
    async def import_file(file: Annotated[UploadFile, File()], version: Annotated[str, Form()], license: Annotated[str, Form()]):
        raw = await file.read()
        try:
            request = ImportRequest(data=json.loads(raw), version=version, license=license)
        except (ValueError, TypeError, ValidationError):
            raise HTTPException(422, detail={"code": "invalid_input", "message": "Invalid LoCoMo JSON structure or metadata"}) from None
        return import_dataset(database, request, raw_bytes=raw)

    @app.post("/imports/official", response_model=ImportResult, status_code=201)
    def import_official():
        # Fixed repository files only: no arbitrary filesystem path from HTTP clients.
        try:
            raw = (OFFICIAL_DIRECTORY / "locomo10.json").read_bytes()
            license_bytes = (OFFICIAL_DIRECTORY / "LICENSE.txt").read_bytes()
            provenance = json.loads((OFFICIAL_DIRECTORY / "provenance.json").read_text())
            manifest = {item["path"]: item["sha256"] for item in provenance["files"]}
            if hashlib.sha256(raw).hexdigest() != manifest["locomo10.json"] or hashlib.sha256(license_bytes).hexdigest() != manifest["LICENSE.txt"]:
                raise ValueError("Official checksum mismatch")
            request = ImportRequest(data=json.loads(raw), version=provenance["commit"], license=provenance["license"])
        except (OSError, ValueError, KeyError, TypeError):
            raise HTTPException(400, detail={"code": "invalid_official_data", "message": "Official data, provenance, or license could not be validated"}) from None
        provenance["license_sha256"] = hashlib.sha256(license_bytes).hexdigest()
        return import_dataset(database, request, raw_bytes=raw, provenance=provenance)

    @app.get("/datasets", response_model=Page[Dataset])
    def datasets(limit: Limit = 20, offset: Offset = 0):
        with database.connect() as db:
            total = db.execute("SELECT COUNT(*) FROM datasets").fetchone()[0]
            rows = db.execute("SELECT * FROM datasets ORDER BY dataset_id LIMIT ? OFFSET ?", (limit, offset)).fetchall()
        return {"items": [dict(row) for row in rows], "total": total, "limit": limit, "offset": offset}

    @app.get("/datasets/{dataset_id}", response_model=Dataset)
    def dataset(dataset_id: str):
        return require_dataset(dataset_id)

    @app.get("/datasets/{dataset_id}/provenance")
    def provenance(dataset_id: str, limit: Limit = 20, offset: Offset = 0):
        require_dataset(dataset_id)
        with database.connect() as db:
            total = db.execute("SELECT COUNT(*) FROM import_artifacts WHERE dataset_id=?", (dataset_id,)).fetchone()[0]
            rows = db.execute("SELECT artifact_sha256, checksum_basis, provenance_json FROM import_artifacts WHERE dataset_id=? ORDER BY artifact_sha256 LIMIT ? OFFSET ?", (dataset_id, limit, offset)).fetchall()
        return {"items": [{"artifact_sha256": row["artifact_sha256"], "checksum_basis": row["checksum_basis"], "provenance": json.loads(row["provenance_json"])} for row in rows], "total": total, "limit": limit, "offset": offset}

    @app.get("/datasets/{dataset_id}/conversations", response_model=Page[Conversation])
    def conversations(dataset_id: str, limit: Limit = 20, offset: Offset = 0):
        ds = require_dataset(dataset_id)
        with database.connect() as db:
            rows = db.execute("SELECT * FROM conversations WHERE dataset_id=? ORDER BY sample_id LIMIT ? OFFSET ?", (dataset_id, limit, offset)).fetchall()
        return {"items": [dict(row) for row in rows], "total": ds["conversation_count"], "limit": limit, "offset": offset}

    @app.get("/datasets/{dataset_id}/conversations/{sample_id}/sessions", response_model=Page[Session])
    def sessions(dataset_id: str, sample_id: str, limit: Limit = 20, offset: Offset = 0):
        conversation = require_conversation(dataset_id, sample_id)
        with database.connect() as db:
            rows = db.execute("SELECT session_id, session_time, COUNT(*) AS turn_count FROM source_turns WHERE dataset_id=? AND sample_id=? GROUP BY session_id, session_time ORDER BY MIN(position) LIMIT ? OFFSET ?", (dataset_id, sample_id, limit, offset)).fetchall()
        return {"items": [dict(row) for row in rows], "total": conversation["session_count"], "limit": limit, "offset": offset}

    @app.get("/datasets/{dataset_id}/conversations/{sample_id}/turns", response_model=Page[SourceTurn])
    def turns(dataset_id: str, sample_id: str, session_id: str | None = None, limit: Limit = 20, offset: Offset = 0):
        require_conversation(dataset_id, sample_id)
        clause = "dataset_id=? AND sample_id=?"
        params = [dataset_id, sample_id]
        if session_id is not None:
            clause += " AND session_id=?"
            params.append(session_id)
        with database.connect() as db:
            total = db.execute(f"SELECT COUNT(*) FROM source_turns WHERE {clause}", params).fetchone()[0]
            if session_id is not None and total == 0:
                raise HTTPException(404)
            rows = db.execute(f"SELECT * FROM source_turns WHERE {clause} ORDER BY position LIMIT ? OFFSET ?", [*params, limit, offset]).fetchall()
        return {"items": [dict(row) for row in rows], "total": total, "limit": limit, "offset": offset}

    @app.get("/datasets/{dataset_id}/conversations/{sample_id}/turns/{dia_id}", response_model=SourceTurn)
    def turn(dataset_id: str, sample_id: str, dia_id: str):
        with database.connect() as db:
            row = db.execute("SELECT * FROM source_turns WHERE dataset_id=? AND sample_id=? AND dia_id=?", (dataset_id, sample_id, dia_id)).fetchone()
        if row is None:
            raise HTTPException(404)
        return dict(row)

    return app
