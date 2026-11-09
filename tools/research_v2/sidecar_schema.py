"""ARCH-01 data contract only. No inference, provider calls, or production writes.

Source and Memory identifiers are accepted from an explicitly scoped snapshot.
Expected fixture outputs are held separately and must never be inference inputs.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, StrictStr, model_validator

NonEmpty = StrictStr

class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

class Provenance(Contract):
    dataset_id: NonEmpty = Field(min_length=1)
    sample_id: NonEmpty = Field(min_length=1)
    build_id: NonEmpty = Field(min_length=1)
    build_fingerprint: NonEmpty = Field(pattern=r"^[0-9a-f]{64}$")
    rule_version: NonEmpty = Field(min_length=1)
    origin: Literal["synthetic", "source_snapshot"]

class SourceEvidence(Contract):
    source_id: NonEmpty = Field(min_length=1)
    session_id: NonEmpty = Field(min_length=1)
    turn_id: NonEmpty = Field(min_length=1)
    speaker: NonEmpty = Field(min_length=1)
    reported_at: datetime
    text: NonEmpty = Field(min_length=1)

class TimeInterval(Contract):
    status: Literal["known", "range", "unknown"] = "unknown"
    start: date | None = None
    end: date | None = None
    original_expression: str | None = None
    anchor_source_id: str | None = None
    basis: str | None = None

    @model_validator(mode="after")
    def validate_time(self):
        if self.status == "unknown":
            if self.start is not None or self.end is not None:
                raise ValueError("Unknown time cannot contain asserted dates")
        else:
            if self.start is None or self.end is None:
                raise ValueError("Known/range time needs both bounds")
            if self.end < self.start:
                raise ValueError("Time interval is reversed")
            if self.status == "known" and self.start != self.end:
                raise ValueError("Known day must have equal bounds")
            if not all(x and x.strip() for x in
                       (self.original_expression, self.anchor_source_id, self.basis)):
                raise ValueError("Asserted dates need expression, source anchor and basis")
        return self

class StateClaim(Contract):
    memory_id: NonEmpty = Field(min_length=1)
    entity_id: NonEmpty = Field(min_length=1)
    state_dimension: NonEmpty = Field(min_length=1)
    state_value: str | None = None
    content: NonEmpty = Field(min_length=1)
    memory_type: Literal["event", "state"]
    statement_type: Literal["fact", "plan", "intention", "uncertain"]
    polarity: Literal["positive", "negative"]
    source_ids: tuple[str, ...] = Field(min_length=1)
    event_time: TimeInterval = Field(default_factory=TimeInterval)

    @model_validator(mode="after")
    def unique_sources(self):
        if len(set(self.source_ids)) != len(self.source_ids):
            raise ValueError("Duplicate source references")
        if self.event_time.anchor_source_id and self.event_time.anchor_source_id not in self.source_ids:
            raise ValueError("Time anchor must be one of the claim's sources")
        return self

class EventLink(Contract):
    left_memory_id: NonEmpty = Field(min_length=1)
    right_memory_id: NonEmpty = Field(min_length=1)
    decision: Literal["same_event", "different_event", "unknown"]
    reason_code: NonEmpty = Field(min_length=1)
    reason: NonEmpty = Field(min_length=1)
    source_ids: tuple[str, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def distinct_endpoints(self):
        if self.left_memory_id == self.right_memory_id:
            raise ValueError("Self link is not an event comparison")
        if len(set(self.source_ids)) != len(self.source_ids):
            raise ValueError("Duplicate link sources")
        return self

class SidecarInput(Contract):
    provenance: Provenance
    sources: tuple[SourceEvidence, ...] = ()
    claims: tuple[StateClaim, ...] = ()
    question: str | None = None
    as_of: date | None = None

    @model_validator(mode="after")
    def validate_snapshot(self):
        sources = {s.source_id: s for s in self.sources}
        if len(sources) != len(self.sources):
            raise ValueError("Duplicate source identity; normalize duplicates explicitly upstream")
        if len({c.memory_id for c in self.claims}) != len(self.claims):
            raise ValueError("Duplicate memory identity")
        for claim in self.claims:
            if any(s not in sources for s in claim.source_ids):
                raise ValueError("Missing source or source outside supplied snapshot")
            t = claim.event_time
            if t.anchor_source_id:
                source = sources[t.anchor_source_id]
                if t.original_expression and t.original_expression.casefold() not in source.text.casefold():
                    raise ValueError("Time expression is absent from cited anchor text")
        return self

class SidecarRecord(Contract):
    schema_version: Literal["temporal-event-sidecar-v0"] = "temporal-event-sidecar-v0"
    enabled: bool = False
    mode: Literal["diagnostic_only"] = "diagnostic_only"
    snapshot: SidecarInput
    event_links: tuple[EventLink, ...] = ()

    @model_validator(mode="after")
    def validate_links(self):
        if not self.enabled and self.event_links:
            raise ValueError("Disabled contract must not carry computed links")
        claims = {c.memory_id: c for c in self.snapshot.claims}
        seen = set()
        for link in self.event_links:
            if link.left_memory_id not in claims or link.right_memory_id not in claims:
                raise ValueError("Link endpoint is outside supplied snapshot")
            pair = frozenset((link.left_memory_id, link.right_memory_id))
            if pair in seen:
                raise ValueError("Duplicate event comparison")
            seen.add(pair)
            endpoints = set(claims[link.left_memory_id].source_ids) | set(claims[link.right_memory_id].source_ids)
            if not set(link.source_ids) <= endpoints:
                raise ValueError("Link evidence must belong to its endpoint claims")
        return self
