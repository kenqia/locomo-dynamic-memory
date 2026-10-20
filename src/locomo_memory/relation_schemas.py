"""Evidence-validated historical judgments and bounded expansion contracts."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictStr, ValidationInfo, model_validator

from .diagnostics import domain_error

RELATION_SCHEMA_VERSION = "relation-v2-stage-evidence"


def relation_label_error(label: str, old: dict, new: dict) -> str | None:
    """Return the first violated label prerequisite, independent of source evidence."""
    if label in {"SUPERSEDE", "CONFLICT", "RETAIN"} and old["state_key"] != new["state_key"]:
        return "same_state_dimension_required"
    if label == "SUPERSEDE":
        if any(memory["memory_type"] != "state" or memory["statement_type"] != "fact" for memory in (old, new)):
            return "factual_states_required"
    if label in {"RETAIN", "UPDATE", "CONFLICT"} and old["statement_type"] == "fact" and new["statement_type"] != "fact":
        return "factual_resolution_required"
    return None


class Applicability(BaseModel):
    model_config = ConfigDict(extra="forbid")
    from_date: date | None = None
    to_date: date | None = None
    condition: str | None = None
    condition_satisfied: bool | None = None
    condition_source_ids: list[str] = Field(default_factory=list)
    time_anchor_source_id: str | None = None
    original_time_expression: str | None = None
    time_basis: str | None = None

    @model_validator(mode="after")
    def evidence_for_conditions_and_time(self):
        if self.from_date and self.to_date and self.to_date < self.from_date:
            raise domain_error("applicability_range_reversed")
        if self.from_date or self.to_date:
            if not self.time_anchor_source_id or not (self.original_time_expression or "").strip() or not (self.time_basis or "").strip():
                raise domain_error("applicability_time_evidence_required")
        if self.condition and self.condition_satisfied is True and not self.condition_source_ids:
            raise domain_error("condition_evidence_required")
        if not self.condition and self.condition_satisfied is not None:
            raise domain_error("explicit_condition_required")
        return self


class StageEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")
    description: StrictStr = Field(min_length=1)
    source_id: StrictStr
    quote: StrictStr = Field(min_length=1)


class UpdateEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")
    same_process: StrictBool
    real_stage_changed: StrictBool
    old_stage: StageEvidence
    new_stage: StageEvidence


class RelationDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")
    old_memory_id: StrictStr
    new_memory_id: StrictStr
    label: Literal["RETAIN", "UPDATE", "SUPERSEDE", "CONFLICT", "undetermined"]
    reason: StrictStr = Field(min_length=1)
    source_ids: list[str] = Field(min_length=1)
    support_quote: str | None = None
    applicability: Applicability = Field(default_factory=Applicability)
    update_evidence: UpdateEvidence | None = None

    @model_validator(mode="after")
    def validate_evidence(self, info: ValidationInfo):
        if not self.reason.strip():
            raise domain_error("nonblank_reason_required")
        if len(set(self.source_ids)) != len(self.source_ids):
            raise domain_error("unique_evidence_required")
        context = info.context or {}
        if self.label == "UPDATE":
            if self.update_evidence is None:
                # Legacy reads have no generation context; fresh judgments always do.
                if "new_memory" in context:
                    raise domain_error("update_stage_evidence_required")
            elif not (self.update_evidence.same_process and self.update_evidence.real_stage_changed):
                raise domain_error("update_real_stage_required")
        if "new_memory" not in context:
            return self
        new = context["new_memory"]
        history = {memory["memory_id"]: memory for memory in context["history"]}
        old = history.get(self.old_memory_id)
        if old is None or self.new_memory_id != new["memory_id"] or self.old_memory_id == self.new_memory_id:
            raise domain_error("comparison_endpoints_required")
        for field in ("build_id", "dataset_id", "sample_id", "entity_id"):
            if old[field] != new[field]:
                raise domain_error("same_endpoint_scope_required")
        sources = context["sources"]
        if any(source_id not in sources for source_id in self.source_ids):
            raise domain_error("known_source_required")
        if not set(self.source_ids).intersection(old["source_ids"]) or not set(self.source_ids).intersection(new["source_ids"]):
            raise domain_error("both_endpoints_evidence_required")
        label_error = relation_label_error(self.label, old, new)
        if label_error:
            raise domain_error(label_error)
        evidence_texts = [sources[source_id]["text"] for source_id in self.source_ids]
        if self.label == "UPDATE":
            for stage, endpoint in ((self.update_evidence.old_stage, old), (self.update_evidence.new_stage, new)):
                if (stage.source_id not in endpoint["source_ids"] or stage.source_id not in self.source_ids
                        or not stage.description.strip() or not stage.quote.strip()
                        or stage.quote not in sources[stage.source_id]["text"]):
                    raise domain_error("update_endpoint_stage_required")
        if self.label != "undetermined":
            if not (self.support_quote or "").strip() or not any(self.support_quote in text for text in evidence_texts):
                raise domain_error("verbatim_support_required")
        applicability = self.applicability
        anchor = applicability.time_anchor_source_id
        if anchor is not None:
            if anchor not in self.source_ids:
                raise domain_error("relation_time_anchor_required")
            expression = applicability.original_time_expression
            if expression and expression.casefold() not in sources[anchor]["text"].casefold():
                raise domain_error("source_time_expression_required")
        if any(source_id not in self.source_ids for source_id in applicability.condition_source_ids):
            raise domain_error("relation_condition_evidence_required")
        return self


class RelationBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    judgments: list[RelationDraft]

    @model_validator(mode="after")
    def every_candidate_is_explicit(self, info: ValidationInfo):
        context = info.context or {}
        if "history" in context:
            expected = {memory["memory_id"] for memory in context["history"]}
            actual = [judgment.old_memory_id for judgment in self.judgments]
            if set(actual) != expected or len(actual) != len(expected):
                raise domain_error("every_candidate_required")
        return self


class MemoryRelation(RelationDraft):
    relation_id: str
    build_id: str


class ExpansionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query_id: StrictStr = Field(min_length=1)
