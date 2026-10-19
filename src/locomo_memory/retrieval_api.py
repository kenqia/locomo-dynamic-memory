"""Candidate inspection endpoints; these do not publish or answer complete builds."""

import json

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .builds import BuildError
from .embeddings import EmbeddingFailure
from .retrieval import RetrievalService
from .retrieval_schemas import CandidateQueryRequest, CandidateQueryResult, IndexInspection


def register_retrieval_routes(app: FastAPI, service: RetrievalService):
    @app.exception_handler(EmbeddingFailure)
    async def embedding_error(request: Request, error: EmbeddingFailure):
        messages = {"embedding_input_too_long": "Embedding input exceeds the checked word-piece limit; no text was silently truncated", "embedding_dependency_missing": "Install the optional embedding dependencies before indexing", "embedding_model_unavailable": "The pinned local embedding model could not be loaded", "invalid_embedding_vector": "Embedding output has invalid dimensions, values, or normalization", "embedding_dimension_mismatch": "Embedding model dimensions do not match configuration"}
        return JSONResponse(status_code=error.status, content={"error": {"code": error.code, "message": messages.get(error.code, "Embedding operation failed")}})

    @app.post("/builds/{build_id}/index", response_model=IndexInspection, status_code=201)
    def create_index(build_id: str):
        return service.create_index(build_id)

    @app.get("/builds/{build_id}/index", response_model=IndexInspection)
    def inspect_index(build_id: str):
        return service.index_info(build_id)

    @app.post("/candidate-queries", response_model=CandidateQueryResult, status_code=201)
    def candidates(request: CandidateQueryRequest):
        return service.query(request.build_id, request.question)

    @app.get("/candidate-queries/{query_id}", response_model=CandidateQueryResult)
    def inspect_candidates(query_id: str):
        with service.database.connect() as db:
            row = db.execute("SELECT result_json FROM candidate_queries WHERE query_id=?", (query_id,)).fetchone()
        if row is None:
            raise BuildError("not_found", 404)
        return json.loads(row["result_json"])
