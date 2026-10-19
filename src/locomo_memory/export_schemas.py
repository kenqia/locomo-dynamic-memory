"""Allowlisted, source-checked complete-version JSON contract."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator

from .config import Settings
from .memory_schemas import Memory
from .relation_schemas import MemoryRelation
from .schemas import Dataset, SourceTurn


class ExportRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ExportBuild(ExportRecord):
    build_id: str
    dataset_id: str
    sample_id: str
    status: Literal["complete"]
    fingerprint: str
    source_sha256: str
    config: Settings
    prompt_version: str
    schema_version: str
    created_at: str
    updated_at: str


class EmbeddingIdentity(ExportRecord):
    model: str
    revision: str
    dimensions: int
    max_tokens: int
    length_policy: Literal["reject"]
    normalized: Literal[True]
    device: str


class ExportIndex(ExportRecord):
    build_id: str
    status: Literal["ready"]
    fingerprint: str
    build_fingerprint: str
    memory_count: int
    embedding: EmbeddingIdentity
    text_schema_version: str


class StateItem(ExportRecord):
    memory_id: str
    status: str
    reason: str
    source_ids: list[str]
    relation_ids: list[str]


class Conflict(ExportRecord):
    relation_id: str
    memory_ids: list[str]
    source_ids: list[str]


class ConditionalRelation(ExportRecord):
    relation_id: str
    reason: str


class ExportProjection(ExportRecord):
    build_id: str
    fingerprint: str
    projection_version: str
    cutoff: str
    cutoff_source_time: str
    current_states: list[StateItem]
    historical_states: list[StateItem]
    events: list[StateItem]
    nonfactual: list[StateItem]
    conflicts: list[Conflict]
    conditional_relations: list[ConditionalRelation]
    assumptions: list[str]


class MemoryExport(ExportRecord):
    schema_version: Literal["memory-export-v1"] = "memory-export-v1"
    dataset: Dataset
    build: ExportBuild
    memories: list[Memory]
    sources: list[SourceTurn]
    relations: list[MemoryRelation]
    projection: ExportProjection
    index: ExportIndex

    @model_validator(mode="after")
    def coherent_version_and_references(self):
        build = self.build
        memories = {item.memory_id: item for item in self.memories}
        sources = {item.source_id: item for item in self.sources}
        relations = {item.relation_id: item for item in self.relations}
        if len(memories) != len(self.memories) or len(sources) != len(self.sources) or len(relations) != len(self.relations):
            raise ValueError("Duplicate exported identity")
        if self.dataset.dataset_id != build.dataset_id or self.dataset.source_sha256 != build.source_sha256:
            raise ValueError("Dataset identity differs")
        if self.index.build_id != build.build_id or self.projection.build_id != build.build_id or self.index.build_fingerprint != build.fingerprint or self.index.memory_count != len(memories):
            raise ValueError("Artifact identity differs")
        if set(sources) != {source_id for memory in memories.values() for source_id in memory.source_ids}:
            raise ValueError("Export sources differ from Memory evidence union")
        for source in sources.values():
            if (source.dataset_id, source.sample_id) != (build.dataset_id, build.sample_id) or source.source_id != f"{source.dataset_id}/{source.sample_id}/{source.dia_id}":
                raise ValueError("Source belongs to another conversation")
        for memory in memories.values():
            if (memory.build_id, memory.dataset_id, memory.sample_id) != (build.build_id, build.dataset_id, build.sample_id) or not set(memory.source_ids) <= sources.keys():
                raise ValueError("Memory identity or evidence differs")
        for relation in relations.values():
            endpoints = {relation.old_memory_id, relation.new_memory_id}
            if relation.build_id != build.build_id or not endpoints <= memories.keys() or not set(relation.source_ids) <= sources.keys():
                raise ValueError("Relation identity or evidence differs")
            allowed = set(memories[relation.old_memory_id].source_ids + memories[relation.new_memory_id].source_ids)
            if relation.applicability.time_anchor_source_id and relation.applicability.time_anchor_source_id not in relation.source_ids:
                raise ValueError("Relation time anchor differs")
            if not set(relation.applicability.condition_source_ids) <= set(relation.source_ids):
                raise ValueError("Relation condition evidence differs")
            if not set(relation.source_ids) <= allowed:
                raise ValueError("Relation evidence is not endpoint evidence")
        projected = self.projection.current_states + self.projection.historical_states + self.projection.events + self.projection.nonfactual
        if len(projected) != len(memories) or {item.memory_id for item in projected} != memories.keys():
            raise ValueError("Projection collection differs")
        for item in projected:
            if set(item.source_ids) != set(memories[item.memory_id].source_ids) or not set(item.relation_ids) <= relations.keys():
                raise ValueError("Projection evidence differs")
        for item in self.projection.conflicts:
            if item.relation_id not in relations or not set(item.memory_ids) <= memories.keys() or not set(item.source_ids) <= sources.keys():
                raise ValueError("Conflict references differ")
        if any(item.relation_id not in relations for item in self.projection.conditional_relations):
            raise ValueError("Conditional relation differs")
        return self
