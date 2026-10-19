"""Persisted dense index, real BM25/cosine channels and stable rank fusion."""

import hashlib
import json
import re
import sqlite3
import uuid

import numpy as np
from rank_bm25 import BM25Okapi

from .builds import BuildError, BuildService
from .config import Settings
from .embeddings import EmbeddingFailure, normalize_vectors
from .imports import canonical_json
from .model import ModelFailure, QUERY_ANALYSIS_PROMPT_VERSION, utc_now
from .retrieval_schemas import QueryAnalysis

TEXT_SCHEMA_VERSION = "entity-dimension-value-content-v1"
QUERY_PROMPT_VERSION = QUERY_ANALYSIS_PROMPT_VERSION
TOKEN_BUDGET_METHOD = "regex-word-punctuation-v1"


def tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+(?:'[a-z]+)?", text.lower())


def budget_tokens(text: str) -> int:
    return len(re.findall(r"\w+|[^\w\s]", text))


def indexing_text(memory: dict) -> str:
    return f"{memory['entity_id']}. {memory['state_dimension'].replace('_', ' ')}: {memory['state_value'] or ''}. {memory['content']}"


class RetrievalService:
    def __init__(self, builds: BuildService, settings: Settings, embedder, model):
        self.builds = builds
        self.database = builds.database
        self.settings = settings
        self.embedder = embedder
        self.model = model
        with self.database.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS build_indexes (
                    build_id TEXT PRIMARY KEY REFERENCES build_versions(build_id), status TEXT NOT NULL,
                    fingerprint TEXT NOT NULL, build_fingerprint TEXT NOT NULL,
                    memory_count INTEGER NOT NULL, metadata_json TEXT NOT NULL, created_at TEXT NOT NULL, error_code TEXT
                );
                CREATE TABLE IF NOT EXISTS index_entries (
                    build_id TEXT NOT NULL REFERENCES build_versions(build_id),
                    memory_id TEXT NOT NULL REFERENCES memories(memory_id), index_text TEXT NOT NULL, vector BLOB NOT NULL,
                    PRIMARY KEY(build_id,memory_id)
                );
                CREATE TABLE IF NOT EXISTS candidate_queries (
                    query_id TEXT PRIMARY KEY, build_id TEXT NOT NULL REFERENCES build_versions(build_id), result_json TEXT NOT NULL
                );
            """)

    def index_info(self, build_id: str) -> dict:
        self.builds.get(build_id)
        with self.database.connect() as db:
            row = db.execute("SELECT * FROM build_indexes WHERE build_id=?", (build_id,)).fetchone()
        if row is None:
            raise BuildError("index_not_ready", 409)
        result = dict(row)
        result.update(json.loads(result.pop("metadata_json")))
        return result

    def create_index(self, build_id: str) -> dict:
        build = self.builds.get(build_id)
        if build["config"] != self.settings.snapshot():
            raise BuildError("build_configuration_changed")
        if build["status"] not in {"extracted", "indexed", "index_failed"} and not (build["status"] == "interrupted" and build["phase"] == "indexing"):
            raise BuildError("build_not_indexable")
        with self.database.connect() as db:
            try:
                changed = db.execute("UPDATE build_versions SET status='running',phase='indexing',updated_at=? WHERE build_id=? AND status NOT IN ('queued','running','complete')", (utc_now(), build_id)).rowcount
            except sqlite3.IntegrityError:
                raise BuildError("build_already_running") from None
            if not changed:
                raise BuildError("build_not_indexable")
            memories = [json.loads(row["memory_json"]) for row in db.execute("SELECT memory_json FROM memories WHERE build_id=? ORDER BY memory_id", (build_id,))]
        fingerprint = ""
        metadata = {"embedding": {}, "text_schema_version": TEXT_SCHEMA_VERSION}
        try:
            identity = self.embedder.identity()
            if identity.get("dimensions") != self.settings.embedding_dimensions:
                raise EmbeddingFailure("embedding_dimension_mismatch")
            metadata["embedding"] = identity
            texts = [indexing_text(memory) for memory in memories]
            vectors = normalize_vectors(self.embedder.encode(texts), len(texts), self.settings.embedding_dimensions)
            fingerprint = hashlib.sha256(canonical_json({"build_fingerprint": build["fingerprint"], "embedding": identity, "text_schema": TEXT_SCHEMA_VERSION, "entries": [(memory["memory_id"], text) for memory, text in zip(memories, texts)]}).encode()).hexdigest()
            with self.database.connect() as db:
                db.execute("DELETE FROM index_entries WHERE build_id=?", (build_id,))
                db.executemany("INSERT INTO index_entries VALUES (?, ?, ?, ?)", [(build_id, memory["memory_id"], text, vector.tobytes()) for memory, text, vector in zip(memories, texts, vectors)])
                db.execute("INSERT OR REPLACE INTO build_indexes VALUES (?, 'ready', ?, ?, ?, ?, ?, NULL)", (build_id, fingerprint, build["fingerprint"], len(memories), canonical_json(metadata), utc_now()))
                db.execute("UPDATE build_versions SET status='indexed',phase='indexed',updated_at=? WHERE build_id=?", (utc_now(), build_id))
        except Exception as error:
            code = error.code if isinstance(error, EmbeddingFailure) else "index_failed"
            with self.database.connect() as db:
                db.execute("INSERT OR REPLACE INTO build_indexes VALUES (?, 'failed', ?, ?, ?, ?, ?, ?)", (build_id, fingerprint, build["fingerprint"], len(memories), canonical_json(metadata), utc_now(), code))
                db.execute("UPDATE build_versions SET status='index_failed',phase='indexing',updated_at=? WHERE build_id=?", (utc_now(), build_id))
            if isinstance(error, EmbeddingFailure):
                raise
            raise BuildError("index_failed", 503) from None
        return self.index_info(build_id)

    def query(self, build_id: str, question: str) -> dict:
        build = self.builds.get(build_id)
        with self.database.connect() as db:
            # Pin the index identity and vectors to the same SQLite read snapshot.
            db.execute("BEGIN")
            row = db.execute("SELECT * FROM build_indexes WHERE build_id=?", (build_id,)).fetchone()
            if row is None or row["status"] != "ready":
                raise BuildError("index_not_ready")
            info = dict(row)
            info.update(json.loads(info.pop("metadata_json")))
            rows = [dict(row) for row in db.execute("SELECT e.*,m.memory_json FROM index_entries e JOIN memories m ON e.memory_id=m.memory_id WHERE e.build_id=? ORDER BY e.memory_id", (build_id,))]
        if info["build_fingerprint"] != build["fingerprint"] or info["embedding"] != self.embedder.identity():
            raise BuildError("index_fingerprint_mismatch")
        memories = {row["memory_id"]: json.loads(row["memory_json"]) for row in rows}
        # Reject an overlong query before an optional paid analysis request.
        query_vector = normalize_vectors(self.embedder.encode([question]), 1, self.settings.embedding_dimensions)[0] if rows else None
        analysis = {"status": "fallback", "result": None, "error_code": None, "model_metadata": {"calls": []}, "prompt_version": QUERY_PROMPT_VERSION}
        try:
            generated = self.model.generate("query_analysis", {"question": question}, QueryAnalysis)
            parsed = QueryAnalysis.model_validate(generated.value.model_dump(mode="json"))
            analysis.update(status="succeeded", result=parsed.model_dump(mode="json"), model_metadata=generated.metadata)
        except Exception as error:
            analysis["error_code"] = error.code if isinstance(error, ModelFailure) else "analysis_failed"
            if isinstance(error, ModelFailure):
                analysis["model_metadata"] = error.metadata
        query_terms = tokenize(question)
        if analysis["result"]:
            query_terms += tokenize(" ".join(analysis["result"]["keywords"]))
        channels = {"bm25": [], "dense": []}
        if rows:
            corpus = [tokenize(row["index_text"]) for row in rows]
            bm25_scores = BM25Okapi(corpus).get_scores(query_terms) if any(corpus) else np.zeros(len(rows))
            vectors = normalize_vectors(np.vstack([np.frombuffer(row["vector"], dtype=np.float32) for row in rows]), len(rows), self.settings.embedding_dimensions)
            dense_scores = vectors @ query_vector
            for name, scores, limit in (("bm25", bm25_scores, self.settings.bm25_k), ("dense", dense_scores, self.settings.dense_k)):
                order = sorted(range(len(rows)), key=lambda index: (-float(scores[index]), rows[index]["memory_id"]))[:limit]
                channels[name] = [{"memory_id": rows[index]["memory_id"], "rank": rank, "score": float(scores[index])} for rank, index in enumerate(order, 1)]
        ranks, fused = {}, {}
        for channel, items in channels.items():
            for item in items:
                memory_id = item["memory_id"]
                ranks.setdefault(memory_id, {})[channel] = item["rank"]
                fused[memory_id] = fused.get(memory_id, 0) + 1 / (self.settings.rrf_constant + item["rank"])
        order = sorted(fused, key=lambda memory_id: (-fused[memory_id], memory_id))
        reasons, candidates, used = [], [], 0
        if len(order) > self.settings.initial_k:
            reasons.append("initial_k")
        for memory_id in order[:self.settings.initial_k]:
            cost = budget_tokens(indexing_text(memories[memory_id]))
            if used + cost > self.settings.candidate_token_budget:
                reasons.append("candidate_token_budget")
                break
            used += cost
            candidates.append({"memory": memories[memory_id], "channel_ranks": ranks[memory_id], "rrf_score": fused[memory_id]})
        result = {"query_id": uuid.uuid4().hex, "build_id": build_id, "index_fingerprint": info["fingerprint"], "question": question,
                  "created_at": utc_now(), "analysis": analysis, "channels": channels, "initial_candidates": candidates,
                  "initial_truncated": bool(reasons), "truncation_reasons": reasons, "candidate_token_count": used,
                  "token_budget_method": TOKEN_BUDGET_METHOD, "config": self.settings.snapshot()}
        with self.database.connect() as db:
            db.execute("INSERT INTO candidate_queries VALUES (?, ?, ?)", (result["query_id"], build_id, canonical_json(result)))
        return result
