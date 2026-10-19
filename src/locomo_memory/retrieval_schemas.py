"""Candidate inspection schemas; analysis conditions never hard-filter history."""

from datetime import date
import re

from pydantic import BaseModel, ConfigDict, Field, StrictStr, field_validator

from .memory_schemas import Memory


class QueryAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid")
    entities: list[str] = Field(default_factory=list)
    topic: str | None = None
    time: date | None = None
    keywords: list[str] = Field(default_factory=list)


class CandidateQueryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    build_id: StrictStr = Field(min_length=1)
    question: StrictStr = Field(min_length=1, max_length=10000)

    @field_validator("question")
    @classmethod
    def english_only(cls, value: str):
        if not re.search(r"[A-Za-z]", value) or re.search(r"[\u3400-\u9fff\u3040-\u30ff\uac00-\ud7af\u0400-\u04ff]", value):
            raise ValueError("Only English retrieval questions are supported")
        return value


class InitialCandidate(BaseModel):
    memory: Memory
    channel_ranks: dict[str, int]
    rrf_score: float


class CandidateQueryResult(BaseModel):
    query_id: str
    build_id: str
    index_fingerprint: str
    question: str
    created_at: str
    analysis: dict
    channels: dict[str, list[dict]]
    initial_candidates: list[InitialCandidate]
    initial_truncated: bool
    truncation_reasons: list[str]
    candidate_token_count: int
    token_budget_method: str
    config: dict


class IndexInspection(BaseModel):
    build_id: str
    status: str
    fingerprint: str
    build_fingerprint: str
    memory_count: int
    embedding: dict
    text_schema_version: str
    created_at: str
    error_code: str | None = None
