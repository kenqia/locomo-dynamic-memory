"""Validated extraction contracts and durable build inspection schemas."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictStr, ValidationInfo, field_validator, model_validator


class TemporalInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")
    original_expression: str | None = None
    anchor_source_id: str | None = None
    event_start: date | None = None
    event_end: date | None = None
    valid_from: date | None = None
    valid_to: date | None = None
    basis: str | None = None

    @model_validator(mode="after")
    def dates_need_evidence(self):
        for start, end in ((self.event_start, self.event_end), (self.valid_from, self.valid_to)):
            if start is not None and end is not None and end < start:
                raise ValueError("Time interval is reversed")
        if any(value is not None for value in (self.event_start, self.event_end, self.valid_from, self.valid_to)):
            if not (self.original_expression or "").strip() or not self.anchor_source_id or not (self.basis or "").strip():
                raise ValueError("Interpreted time requires original expression, source anchor and basis")
        return self


class MemoryDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")
    content: StrictStr = Field(min_length=1)
    memory_type: Literal["event", "state"]
    statement_type: Literal["fact", "plan", "intention", "uncertain"]
    polarity: Literal["positive", "negative"]
    entity_id: StrictStr = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
    state_dimension: StrictStr = Field(pattern=r"^[a-z][a-z0-9_]*$")
    state_value: StrictStr | None = None
    source_ids: list[StrictStr] = Field(min_length=1)
    time: TemporalInfo = Field(default_factory=TemporalInfo)

    @field_validator("content")
    @classmethod
    def require_claim(cls, value: str):
        if not value.strip():
            raise ValueError("Memory content must contain a claim")
        return value

    @model_validator(mode="after")
    def check_source_evidence(self, info: ValidationInfo):
        if len(set(self.source_ids)) != len(self.source_ids):
            raise ValueError("Duplicate source reference")
        context = info.context or {}
        sources = context.get("sources")
        if sources is not None:
            if any(source_id not in sources for source_id in self.source_ids):
                raise ValueError("Unknown source or source from another conversation/fragment")
            anchor = self.time.anchor_source_id
            if anchor is not None:
                if anchor not in self.source_ids:
                    raise ValueError("Time anchor must be one of the cited sources")
                expression = self.time.original_expression
                if expression and expression.casefold() not in sources[anchor]["text"].casefold():
                    raise ValueError("Original time expression is absent from anchor text")
        return self


class ExtractionBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    memories: list[MemoryDraft]
    no_facts_reason: StrictStr | None = None

    @model_validator(mode="after")
    def explicit_no_facts(self):
        if not self.memories and not (self.no_facts_reason or "").strip():
            raise ValueError("An empty extraction needs an explicit no-facts reason")
        return self


class Memory(MemoryDraft):
    memory_id: str
    build_id: str
    dataset_id: str
    sample_id: str
    state_key: str
    session_times: list[str]


class BuildRequest(BaseModel):
    creation_token: StrictStr | None = Field(default=None, min_length=32, max_length=64)
    model_config = ConfigDict(extra="forbid")
    dataset_id: StrictStr = Field(min_length=1)
    sample_id: StrictStr = Field(min_length=1)


class BuildProgress(BaseModel):
    total: int
    succeeded: int
    failed: int
    pending: int


class BuildVersion(BaseModel):
    build_id: str
    dataset_id: str
    sample_id: str
    status: str
    phase: str
    query_ready: bool = False
    fingerprint: str
    source_sha256: str
    config: dict
    prompt_version: str
    schema_version: str
    model_metadata: dict
    created_at: str
    updated_at: str
    progress: BuildProgress


class BuildFragment(BaseModel):
    fragment_id: str
    ordinal: int
    source_ids: list[str]
    status: str
    attempts: int
    error_code: str | None
    error_message: str | None
    no_facts_reason: str | None
    model_metadata: dict
