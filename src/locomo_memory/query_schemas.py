"""Query-only effective evidence and source-bounded answer contracts."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictStr, ValidationInfo, field_validator, model_validator

from .relation_schemas import RelationDraft
from .retrieval_schemas import CandidateQueryRequest
from .diagnostics import domain_error

RESOLUTION_SCHEMA_VERSION = "effective-resolution-v2-stage-evidence"
ANSWER_SCHEMA_VERSION = "evidence-answer-v4-separate-explanation"
EvidenceStatus = Literal["sufficient", "conflict", "insufficient"]

ANSWERABILITY_GUIDANCE = """
Check the question's person, time and requested fact for each requested part.
Related background alone is not a partial answer. Another season's intention cannot establish
a plan in the requested season. If no requested part is supported, answer exactly
"No information available."; put background and gaps in explanation.
Otherwise answer every supported part with citations; explain missing parts separately.
Do not replace all insufficient answers with abstention. Never invent missing items.
"""

MULTI_ITEM_GUIDANCE = """
List ALL distinct supported items for multi-item requests, including activities, locations,
instruments and events, and multiple items in one source. Keep people separate, plans separate
from participation, and known partial lists answerable.
Synthetic example: Dana kayaks and knits, Lee skis, Dana hopes to box.
Dana's activities: kayaking and knitting; skiing belongs to Lee, boxing is planned.
"""

SHORT_ANSWER_GUIDANCE = """
For a list question, answer with a compact, deduplicated list of item names, not one narrative
per source. Include every supported distinct item before adding detail. Unless the question
asks when, omit dates, relative-time calculations and trip chronology from answer; put any
necessary qualifications in explanation. Preserve uncertainty or negation that changes an item.
Synthetic example: Dana practiced chess on Monday and Friday and baked bread on Sunday.
Question: What activities does Dana do? Answer: Chess and baking.
"""

EVENT_IDENTITY_GUIDANCE = """
Report separate events separately unless delivered sources establish that they belong to
the same concrete undertaking. The same person, state_key, occupation, topic or later
report date alone does not establish an interview-to-offer or other stage progression.
When linkage is unknown, state the supported reports and leave their relationship unknown.
A report as of a date does not establish uninterrupted duration since that date.
Absence of a completion report does not prove the event did not occur.
Apply these boundaries to both the direct answer and its explanation.
"""


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
            raise domain_error("resolution_reason_required")
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
            raise domain_error("resolution_explanation_required")
        context = info.context or {}
        if "memories" not in context:
            return self
        memories = context["memories"]
        allowed = set(memories)
        selected = set(self.effective_memory_ids)
        raw_selected = set(getattr(self, "effective_source_ids", []))
        if not raw_selected <= set(context.get("raw_sources", {})):
            raise domain_error("resolution_raw_scope_required")
        if len(selected) != len(self.effective_memory_ids) or not selected <= allowed:
            raise domain_error("resolution_unique_supplied_ids_required")
        if {d.memory_id for d in self.decisions} != allowed or len(self.decisions) != len(allowed):
            raise domain_error("resolution_every_candidate_required")
        if {d.memory_id for d in self.decisions if d.selected} != selected:
            raise domain_error("resolution_selection_agreement_required")
        if self.status == "sufficient" and not (selected or raw_selected):
            raise domain_error("resolution_sufficient_evidence_required")
        if self.status == "conflict" and len(selected) + len(raw_selected) < 2:
            raise domain_error("resolution_conflict_sides_required")
        incomplete = {mid for relation in context.get('incomplete_relations', [])
                      if relation['label'] in context.get('required_relation_labels', ('CONFLICT', 'SUPERSEDE'))
                      for mid in (relation['old_memory_id'], relation['new_memory_id'])}
        if selected & incomplete and self.status != 'insufficient':
            raise domain_error('resolution_incomplete_relation_required')
        for judgment in self.supplemental_relations:
            old, new = memories.get(judgment.old_memory_id), memories.get(judgment.new_memory_id)
            if old is None or new is None:
                raise domain_error("resolution_supplemental_endpoints_required")
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
    explanation: StrictStr | None = Field(default=None, description="Evidence explanation, missing parts and scope; separate from the direct answer")

    @model_validator(mode="after")
    def citations_are_delivered_evidence(self, info: ValidationInfo):
        if not self.answer.strip():
            raise domain_error("answer_nonblank_required")
        context = info.context or {}
        if "memories" not in context:
            return self
        if self.status != context["status"] and not (context["status"] == "sufficient" and self.status == "insufficient"):
            raise domain_error("answer_evidence_status_required")
        if self.status in {"sufficient", "conflict"} and not self.citations:
            raise domain_error("answer_citations_required")
        memories = context["memories"]
        for citation in self.citations:
            if citation.memory_id is None and context.get("raw_sources") is not None:
                if not set(citation.source_ids) <= set(context["raw_sources"]) or len(set(citation.source_ids)) != len(citation.source_ids):
                    raise domain_error("answer_raw_citation_scope_required")
                continue
            memory = memories.get(citation.memory_id)
            if memory is None or not set(citation.source_ids) <= set(memory["source_ids"]) or len(set(citation.source_ids)) != len(citation.source_ids):
                raise domain_error("answer_memory_citation_scope_required")
        endpoints = {( "memory", c.memory_id) if c.memory_id is not None else ("source", sid)
                     for c in self.citations for sid in c.source_ids}
        if self.status == "conflict" and len(endpoints) < 2:
            raise domain_error("answer_conflict_sides_required")
        return self
