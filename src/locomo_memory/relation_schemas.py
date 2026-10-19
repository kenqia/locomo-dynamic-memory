"""Evidence-validated historical judgments and bounded expansion contracts."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictStr, ValidationInfo, model_validator

RELATION_SCHEMA_VERSION = "relation-v1"


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
            raise ValueError("Applicability range reversed")
        if self.from_date or self.to_date:
            if not self.time_anchor_source_id or not (self.original_time_expression or "").strip() or not (self.time_basis or "").strip():
                raise ValueError("Applicability dates need source anchor, original expression and basis")
        if self.condition and self.condition_satisfied is True and not self.condition_source_ids:
            raise ValueError("Satisfied condition requires source evidence")
        if not self.condition and self.condition_satisfied is not None:
            raise ValueError("Condition status requires an explicit condition")
        return self


class RelationDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")
    old_memory_id: StrictStr
    new_memory_id: StrictStr
    label: Literal["RETAIN", "UPDATE", "SUPERSEDE", "CONFLICT", "undetermined"]
    reason: StrictStr = Field(min_length=1)
    source_ids: list[str] = Field(min_length=1)
    support_quote: str | None = None
    applicability: Applicability = Field(default_factory=Applicability)

    @model_validator(mode="after")
    def validate_evidence(self, info: ValidationInfo):
        if not self.reason.strip() or len(set(self.source_ids)) != len(self.source_ids):
            raise ValueError("A relation needs a reason and unique evidence")
        context = info.context or {}
        if "new_memory" not in context:
            return self
        new = context["new_memory"]
        history = {memory["memory_id"]: memory for memory in context["history"]}
        old = history.get(self.old_memory_id)
        if old is None or self.new_memory_id != new["memory_id"] or self.old_memory_id == self.new_memory_id:
            raise ValueError("Relation endpoints must belong to the supplied historical comparison")
        for field in ("build_id", "dataset_id", "sample_id", "entity_id"):
            if old[field] != new[field]:
                raise ValueError("Relation endpoints cross version, conversation or entity scope")
        sources = context["sources"]
        if any(source_id not in sources for source_id in self.source_ids):
            raise ValueError("Relation cites an unknown source")
        if not set(self.source_ids).intersection(old["source_ids"]) or not set(self.source_ids).intersection(new["source_ids"]):
            raise ValueError("Relation evidence must support both endpoints")
        if self.label in {"SUPERSEDE", "CONFLICT", "RETAIN"} and old["state_key"] != new["state_key"]:
            raise ValueError("This judgment requires the same state dimension")
        if self.label == "SUPERSEDE":
            if any(memory["memory_type"] != "state" or memory["statement_type"] != "fact" for memory in (old, new)):
                raise ValueError("Only factual states can supersede factual states; preserve events and plans")
        if self.label in {"RETAIN", "UPDATE", "CONFLICT"} and old["statement_type"] == "fact" and new["statement_type"] != "fact":
            raise ValueError("A plan or uncertain claim cannot resolve an established factual state")
        evidence_texts = [sources[source_id]["text"] for source_id in self.source_ids]
        if self.label != "undetermined":
            if not (self.support_quote or "").strip() or not any(self.support_quote in text for text in evidence_texts):
                raise ValueError("A determined judgment requires a verbatim supporting source quote")
        applicability = self.applicability
        anchor = applicability.time_anchor_source_id
        if anchor is not None:
            if anchor not in self.source_ids:
                raise ValueError("Applicability anchor must be a relation source")
            expression = applicability.original_time_expression
            if expression and expression.casefold() not in sources[anchor]["text"].casefold():
                raise ValueError("Applicability expression absent from source")
        if any(source_id not in self.source_ids for source_id in applicability.condition_source_ids):
            raise ValueError("Condition proof is not among relation evidence")
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
                raise ValueError("Each supplied historical memory requires one judgment, including undetermined")
        return self


class MemoryRelation(RelationDraft):
    relation_id: str
    build_id: str


class ExpansionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query_id: StrictStr = Field(min_length=1)
