"""Validated settings loaded once by the backend and the Streamlit client."""

import os
from pathlib import Path
import tomllib

from pydantic import BaseModel, ConfigDict, Field


class Settings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    db_path: Path = Path("var/memory.sqlite3")
    api_url: str = "http://127.0.0.1:8000"
    model_name: str = "deepseek-flash"
    model_base_url: str = "https://api.deepseek.com"
    model_timeout_seconds: float = Field(default=60, gt=0)
    model_retries: int = Field(default=2, ge=0, le=10)
    model_temperature: float = Field(default=0, ge=0, le=2)
    model_max_tokens: int = Field(default=4096, gt=0)
    thinking_enabled: bool = False
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_revision: str = "c9745ed1d9f207416be6d2e6f8de32d1f16199bf"
    embedding_dimensions: int = Field(default=384, gt=0)
    embedding_max_tokens: int = Field(default=256, gt=0)
    fragment_turns: int = Field(default=20, gt=0)
    bm25_k: int = Field(default=20, gt=0)
    dense_k: int = Field(default=20, gt=0)
    initial_k: int = Field(default=20, gt=0)
    rrf_constant: int = Field(default=60, gt=0)
    expansion_max_candidates: int = Field(default=60, gt=0)
    candidate_token_budget: int = Field(default=12000, gt=0)
    evidence_token_budget: int = Field(default=6000, gt=0)

    def snapshot(self) -> dict:
        # No credential is accepted by this schema; adapters read protected env separately.
        return self.model_dump(mode="json")


def load_settings(path: str | Path | None = None) -> Settings:
    config_path = Path(path or os.environ.get("LOCOMO_CONFIG", "config.toml"))
    if config_path.exists():
        with config_path.open("rb") as stream:
            return Settings.model_validate(tomllib.load(stream))
    if path is not None or "LOCOMO_CONFIG" in os.environ:
        raise ValueError("The requested configuration file does not exist")
    return Settings()
