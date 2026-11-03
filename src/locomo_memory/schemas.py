"""Source contracts; evaluation annotations never become SourceTurn fields."""

import re
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field, StrictStr, model_validator


class SourceTurn(BaseModel):
    source_id: str
    dataset_id: str
    sample_id: str
    session_id: str
    dia_id: str
    speaker: str
    session_time: str
    text: str
    position: int


class RawTurn(BaseModel):
    dia_id: StrictStr = Field(pattern=r"^D[1-9]\d*:[1-9]\d*$")
    speaker: StrictStr = Field(min_length=1)
    text: StrictStr = Field(min_length=1)
    # Image metadata supplied upstream is not text extraction input.


class RawSample(BaseModel):
    sample_id: StrictStr = Field(pattern=r"^[A-Za-z0-9_-]+$")
    conversation: dict[str, Any]
    qa: Any = None
    event_summary: Any = None
    observation: Any = None
    session_summary: Any = None

    @model_validator(mode="after")
    def validate_conversation(self):
        c = self.conversation
        for name in ("speaker_a", "speaker_b"):
            if not isinstance(c.get(name), str) or not c[name].strip():
                raise ValueError("Conversation requires two named speakers")
        if c["speaker_a"] == c["speaker_b"]:
            raise ValueError("Conversation speakers must differ")
        session_keys = [key for key in c if re.fullmatch(r"session_[1-9]\d*", key)]
        if not session_keys:
            raise ValueError("Conversation must contain a session")
        timestamp_keys = {key for key in c if re.fullmatch(r"session_[1-9]\d*_date_time", key)}
        allowed = {"speaker_a", "speaker_b"} | set(session_keys) | timestamp_keys
        if any(not isinstance(c[key], str) or not c[key].strip() for key in timestamp_keys):
            raise ValueError("Session timestamps must be nonempty strings")
        if set(c) - allowed:
            raise ValueError("Unrecognized conversation field or unmatched session timestamp")
        seen = set()
        for key in session_keys:
            stamp = c.get(f"{key}_date_time")
            if not isinstance(stamp, str) or not stamp.strip():
                raise ValueError("Every session needs its original timestamp")
            turns = c[key]
            if not isinstance(turns, list) or not turns:
                raise ValueError("Every session needs at least one turn")
            for value in turns:
                turn = RawTurn.model_validate(value)
                if turn.speaker not in (c["speaker_a"], c["speaker_b"]):
                    raise ValueError("Turn speaker is not a conversation participant")
                if turn.dia_id in seen:
                    raise ValueError("Duplicate dialogue ID within conversation")
                if turn.dia_id.split(":")[0][1:] != key.removeprefix("session_"):
                    raise ValueError("Dialogue ID belongs to another session")
                seen.add(turn.dia_id)
        return self


class ImportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    data: list[RawSample] = Field(min_length=1)
    version: StrictStr = Field(min_length=1)
    license: StrictStr = Field(min_length=1)

    @model_validator(mode="after")
    def distinct_samples(self):
        if len({s.sample_id for s in self.data}) != len(self.data):
            raise ValueError("Duplicate sample_id in dataset")
        return self


class ImportResult(BaseModel):
    dataset_id: str
    artifact_sha256: str
    source_sha256: str
    conversation_count: int
    turn_count: int
    reused: bool


class Dataset(BaseModel):
    dataset_id: str
    source_sha256: str
    version: str
    license: str
    conversation_count: int
    turn_count: int


class Conversation(BaseModel):
    sample_id: str
    speaker_a: str
    speaker_b: str
    session_count: int
    turn_count: int


class Session(BaseModel):
    session_id: str
    session_time: str
    turn_count: int


T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorDetail
