"""Public question answering and persistent Trace inspection."""

from typing import Literal

from fastapi import Request
from fastapi.responses import JSONResponse

from .queries import QueryFailure
from .query_schemas import QueryRequest


class PublicQueryRequest(QueryRequest):
    strategy: Literal["hybrid_no_resolution", "dynamic", "dynamic_raw_fallback"] = "hybrid_no_resolution"


def register_query_routes(app, service):
    @app.exception_handler(QueryFailure)
    async def query_error(request: Request, error: QueryFailure):
        return JSONResponse(status_code=error.status, content={"error": {"code": error.code, "message": "Query failed; inspect its Trace", "trace_id": error.trace_id}})

    @app.post("/queries", status_code=201)
    def answer(request: PublicQueryRequest):
        if request.strategy == "hybrid_no_resolution":
            from .release_queries import hybrid_query
            return hybrid_query(app.state.evaluation, request)
        return service.query(request)

    @app.get("/queries/{trace_id}")
    def trace(trace_id: str):
        return service.get(trace_id)
