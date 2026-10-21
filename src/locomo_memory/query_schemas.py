"""Query-only effective evidence and source-bounded answer contracts."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictStr, ValidationInfo, field_validator, model_validator

from .relation_schemas import RelationDraft
from .retrieval_schemas import CandidateQueryRequest

RESOLUTION_SCHEMA_VERSION = "effective-resolution-v2-stage-evidence"
ANSWER_SCHEMA_VERSION = "evidence-answer-v3-delivered-sufficiency"
EvidenceStatus = Literal["sufficient", "conflict", "insufficient"]


class QueryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    dataset_id: StrictStr = Field(min_length=1)
    sample_id: StrictStr = Field(min_length=1)
    build_id: StrictStr | None = Field(default=None, min_length=1)
    question: StrictStr = Field(min_length=1, max_length=10000)
    requested_date: date | None = None
    evidence_profile: Literal["expanded", "focused"] = "expanded"
    strategy: Literal["dynamic", "dynamic_raw_fallback"] = "dynamic"

    @model_validator(mode="after")
    def english_question(self):
        if self.evidence_profile == "focused" and self.strategy != "dynamic_raw_fallback":
            raise ValueError("Focused evidence is scoped to dynamic_raw_fallback")
        CandidateQueryRequest(build_id="validation", question=self.question)
        return self


class EvidenceDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    memory_id: StrictStr
    selected: bool
    reason: StrictStr = Field(min_length=1)


    @field_validator("reason")
    @classmethod
    def nonblank_reason(cls, value):
        if not value.strip():
            raise ValueError("Evidence applicability explanation cannot be blank")
        return value


class EffectiveResolution(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: EvidenceStatus
    effective_memory_ids: list[StrictStr]
    decisions: list[EvidenceDecision]
    supplemental_relations: list[RelationDraft] = Field(default_factory=list)
    explanation: StrictStr = Field(min_length=1)

    @model_validator(mode="after")
    def exact_candidate_scope(self, info: ValidationInfo):
        if not self.explanation.strip():
            raise ValueError("Resolution explanation cannot be blank")
        context = info.context or {}
        if "memories" not in context:
            return self
        memories = context["memories"]
        allowed = set(memories)
        selected = set(self.effective_memory_ids)
        raw_selected = set(getattr(self, "effective_source_ids", []))
        if not raw_selected <= set(context.get("raw_sources", {})):
            raise ValueError("Raw evidence outside supplied scope")
        if len(selected) != len(self.effective_memory_ids) or not selected <= allowed:
            raise ValueError("Effective evidence must use unique supplied IDs")
        if {d.memory_id for d in self.decisions} != allowed or len(self.decisions) != len(allowed):
            raise ValueError("Explain every candidate exactly once")
        if {d.memory_id for d in self.decisions if d.selected} != selected:
            raise ValueError("Selection and decisions disagree")
        if self.status == "sufficient" and not (selected or raw_selected):
            raise ValueError("Sufficient answer requires evidence")
        if self.status == "conflict" and len(selected) + len(raw_selected) < 2:
            raise ValueError("Conflict requires both evidence sides")
        for judgment in self.supplemental_relations:
            old, new = memories.get(judgment.old_memory_id), memories.get(judgment.new_memory_id)
            if old is None or new is None:
                raise ValueError("Supplemental endpoints outside candidates")
            RelationDraft.model_validate(judgment.model_dump(), context={"new_memory": new, "history": [old], "sources": context["sources"]})
        return self


class Citation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    memory_id: StrictStr | None = None
    source_ids: list[StrictStr] = Field(min_length=1)


class EvidenceAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: EvidenceStatus
    answer: StrictStr = Field(min_length=1)
    citations: list[Citation]

    @model_validator(mode="after")
    def citations_are_delivered_evidence(self, info: ValidationInfo):
        if not self.answer.strip():
            raise ValueError("Answer cannot be blank")
        context = info.context or {}
        if "memories" not in context:
            return self
        if self.status != context["status"] and not (context["status"] == "sufficient" and self.status == "insufficient"):
            raise ValueError("Answer must preserve evidence uncertainty")
        if self.status in {"sufficient", "conflict"} and not self.citations:
            raise ValueError("Evidence-backed answer needs citations")
        memories = context["memories"]
        for citation in self.citations:
            if citation.memory_id is None and context.get("raw_sources") is not None:
                if not set(citation.source_ids) <= set(context["raw_sources"]) or len(set(citation.source_ids)) != len(citation.source_ids):
                    raise ValueError("Raw citation outside delivered sources")
                continue
            memory = memories.get(citation.memory_id)
            if memory is None or not set(citation.source_ids) <= set(memory["source_ids"]) or len(set(citation.source_ids)) != len(citation.source_ids):
                raise ValueError("Citation outside delivered effective evidence")
        endpoints = {( "memory", c.memory_id) if c.memory_id is not None else ("source", sid)
                     for c in self.citations for sid in c.source_ids}
        if self.status == "conflict" and len(endpoints) < 2:
            raise ValueError("Cite both unresolved conflict sides")
        return self
