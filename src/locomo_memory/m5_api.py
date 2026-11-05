"""Explicit read-only Bonus routes; no provider calls or persistent changes."""
from datetime import date

from fastapi import Query
from pydantic import BaseModel, ConfigDict, Field

from .builds import BuildError
from .exports import ExportService
from .m5_compression import pack
from .m5_graph import neighborhood, expand_relations


class GraphRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    initial_ids: list[str]
    depth: int = Field(default=0, ge=0, le=3)
    max_candidates: int = Field(default=60, ge=1, le=500)
    token_budget: int = Field(default=12000, ge=1, le=100000)


def register_m5_routes(app, versions):
    exports = ExportService(versions)

    @app.get('/builds/{build_id}/bonus/graph')
    def graph(build_id: str, root: str | None = None, depth: int = Query(1, ge=0, le=2),
              at: date | None = None, max_nodes: int = Query(150, ge=1, le=500)):
        bundle = exports.export(build_id)
        if root is None:
            return dict(build_id=build_id, entities=sorted({m.entity_id for m in bundle.memories}),
                        memory_count=len(bundle.memories), relation_count=len(bundle.relations))
        try:
            return neighborhood(bundle, [root], depth=depth, at=at, max_nodes=max_nodes)
        except ValueError:
            raise BuildError('graph_roots_out_of_scope', 422) from None

    @app.post('/builds/{build_id}/bonus/graph-expand')
    def expand_graph(build_id: str, request: GraphRequest):
        try:
            return expand_relations(exports.export(build_id), request.initial_ids, depth=request.depth,
                max_candidates=request.max_candidates, token_budget=request.token_budget)
        except ValueError:
            raise BuildError('graph_scope_or_budget_invalid', 422) from None

    @app.get('/builds/{build_id}/bonus/compression')
    def compression(build_id: str):
        return pack([m.model_dump(mode='json') for m in exports.export(build_id).memories])

    @app.get('/builds/{build_id}/bonus/timeline')
    def timeline(build_id: str, entity: str, dimension: str):
        bundle = exports.export(build_id)
        memories = [m for m in bundle.memories if m.entity_id == entity and m.state_dimension == dimension]
        ids = {m.memory_id for m in memories}
        sources = {s.source_id: s.model_dump(mode='json') for s in bundle.sources}
        return dict(build_id=build_id, cutoff=bundle.projection.cutoff,
            memories=[m.model_dump(mode='json') for m in sorted(memories, key=lambda m: (
                min(sources[sid]['position'] for sid in m.source_ids), m.memory_id))],
            relations=[r.model_dump(mode='json') for r in bundle.relations
                       if {r.old_memory_id, r.new_memory_id} <= ids],
            sources={sid: sources[sid] for m in memories for sid in m.source_ids},
            projection=bundle.projection.model_dump(mode='json'),
            unknown_policy='Unknown; absence of a new report does not establish continuity.')
