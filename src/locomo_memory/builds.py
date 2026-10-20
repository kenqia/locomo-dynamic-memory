"""Durable fragment extraction; extracted output is inspectable, not query-ready."""

from collections import Counter
import hashlib
import json
import sqlite3
import uuid

from .config import Settings
from .database import Database
from .imports import canonical_json
from .memory_schemas import ExtractionBatch, Memory
from . import model as model_contract, projection as projection_contract, relation_schemas as relation_contract
from .model import KNOWN_MODEL_VERSION, ModelFailure, utc_now
from .relation_schemas import RelationBatch


class BuildError(Exception):
    def __init__(self, code: str, status: int = 409):
        self.code = code
        self.status = status
        super().__init__(code)


class BuildService:
    def __init__(self, database: Database, settings: Settings, model):
        self.database = database
        self.settings = settings
        self.model = model
        with database.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS build_versions (
                    build_id TEXT PRIMARY KEY, dataset_id TEXT NOT NULL REFERENCES datasets(dataset_id),
                    sample_id TEXT NOT NULL, status TEXT NOT NULL, phase TEXT NOT NULL,
                    fingerprint TEXT NOT NULL, source_sha256 TEXT NOT NULL,
                    config_json TEXT NOT NULL, prompt_version TEXT NOT NULL, schema_version TEXT NOT NULL,
                    model_metadata_json TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                    FOREIGN KEY(dataset_id, sample_id) REFERENCES conversations(dataset_id, sample_id)
                );
                CREATE UNIQUE INDEX IF NOT EXISTS one_active_build ON build_versions((1)) WHERE status IN ('queued', 'running');
                CREATE TABLE IF NOT EXISTS build_fragments (
                    fragment_id TEXT PRIMARY KEY, build_id TEXT NOT NULL REFERENCES build_versions(build_id),
                    ordinal INTEGER NOT NULL, source_ids_json TEXT NOT NULL, status TEXT NOT NULL,
                    attempts INTEGER NOT NULL DEFAULT 0, error_code TEXT, error_message TEXT,
                    no_facts_reason TEXT, model_metadata_json TEXT NOT NULL DEFAULT '{}',
                    UNIQUE(build_id, ordinal)
                );
                CREATE TABLE IF NOT EXISTS memories (
                    memory_id TEXT PRIMARY KEY, build_id TEXT NOT NULL REFERENCES build_versions(build_id),
                    fragment_id TEXT NOT NULL REFERENCES build_fragments(fragment_id), dataset_id TEXT NOT NULL,
                    sample_id TEXT NOT NULL, content TEXT NOT NULL, entity_id TEXT NOT NULL,
                    state_dimension TEXT NOT NULL, state_key TEXT NOT NULL, memory_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS memory_sources (
                    memory_id TEXT NOT NULL REFERENCES memories(memory_id),
                    source_id TEXT NOT NULL REFERENCES source_turns(source_id),
                    PRIMARY KEY(memory_id, source_id)
                );
                CREATE INDEX IF NOT EXISTS memory_build ON memories(build_id, memory_id);
                CREATE INDEX IF NOT EXISTS memory_state ON memories(build_id, state_key);
                CREATE UNIQUE INDEX IF NOT EXISTS unique_build_creation_token ON build_versions(json_extract(model_metadata_json,'$.creation_token')) WHERE json_extract(model_metadata_json,'$.creation_token') IS NOT NULL;
            """)

    def fingerprint(self, source_sha256: str, sample_id: str) -> str:
        """Use the same producer contract for new builds and recovery checks."""
        contract = {
            "source": source_sha256, "sample_id": sample_id, "settings": self.settings.snapshot(),
            "prompt": model_contract.EXTRACTION_PROMPT,
            "prompt_version": model_contract.EXTRACTION_PROMPT_VERSION,
            "schema": ExtractionBatch.model_json_schema(), "schema_version": model_contract.MEMORY_SCHEMA_VERSION,
            "relation_prompt": model_contract.RELATION_PROMPT,
            "relation_prompt_version": model_contract.RELATION_PROMPT_VERSION,
            "relation_schema": RelationBatch.model_json_schema(),
            "relation_schema_version": relation_contract.RELATION_SCHEMA_VERSION,
            "projection_version": projection_contract.PROJECTION_VERSION,
        }
        return hashlib.sha256(canonical_json(contract).encode()).hexdigest()

    def require_current_contract(self, build: dict):
        if build["config"] != self.settings.snapshot():
            raise BuildError("build_configuration_changed")
        if build["fingerprint"] != self.fingerprint(build["source_sha256"], build["sample_id"]):
            raise BuildError("build_contract_changed")

    def recover_interrupted(self):
        # Called only by the exclusive backend owner at startup.
        with self.database.connect() as db:
            db.execute("UPDATE build_fragments SET status='interrupted', error_code='interrupted', error_message='Backend stopped before this fragment completed' WHERE status='running'")
            db.execute("UPDATE build_versions SET status='interrupted', updated_at=? WHERE status IN ('queued', 'running')", (utc_now(),))

    def start(self, dataset_id: str, sample_id: str, creation_token: str | None = None) -> dict:
        build_id = uuid.uuid4().hex
        now = utc_now()
        with self.database.connect() as db:
            dataset = db.execute("SELECT * FROM datasets WHERE dataset_id=?", (dataset_id,)).fetchone()
            turns = db.execute("SELECT * FROM source_turns WHERE dataset_id=? AND sample_id=? ORDER BY position", (dataset_id, sample_id)).fetchall()
            if dataset is None or not turns:
                raise BuildError("not_found", 404)
            snapshot = self.settings.snapshot()
            fingerprint = self.fingerprint(dataset["source_sha256"], sample_id)
            metadata = {"requested_model": self.settings.model_name, "known_service_version": KNOWN_MODEL_VERSION, "run_date": now[:10], "returned_models": [], "calls": [], "artifact_versions": {"relation_prompt_version": model_contract.RELATION_PROMPT_VERSION, "relation_schema_version": relation_contract.RELATION_SCHEMA_VERSION, "projection_version": projection_contract.PROJECTION_VERSION}}
            if creation_token is not None:
                metadata["creation_token"] = creation_token
            try:
                db.execute("INSERT INTO build_versions VALUES (?, ?, ?, 'queued', 'extraction', ?, ?, ?, ?, ?, ?, ?, ?)",
                           (build_id, dataset_id, sample_id, fingerprint, dataset["source_sha256"], canonical_json(snapshot), model_contract.EXTRACTION_PROMPT_VERSION, model_contract.MEMORY_SCHEMA_VERSION, canonical_json(metadata), now, now))
            except sqlite3.IntegrityError:
                raise BuildError("build_already_running") from None
            for ordinal, start in enumerate(range(0, len(turns), self.settings.fragment_turns)):
                ids = [turn["source_id"] for turn in turns[start:start + self.settings.fragment_turns]]
                db.execute("INSERT INTO build_fragments(fragment_id,build_id,ordinal,source_ids_json,status) VALUES (?, ?, ?, ?, 'pending')", (f"{build_id}:{ordinal}", build_id, ordinal, canonical_json(ids)))
        return self.get(build_id)

    def get(self, build_id: str) -> dict:
        with self.database.connect() as db:
            row = db.execute("SELECT * FROM build_versions WHERE build_id=?", (build_id,)).fetchone()
            states = db.execute("SELECT status, COUNT(*) AS n FROM build_fragments WHERE build_id=? GROUP BY status", (build_id,)).fetchall()
        if row is None:
            raise BuildError("not_found", 404)
        result = dict(row)
        result["config"] = json.loads(result.pop("config_json"))
        result["model_metadata"] = json.loads(result.pop("model_metadata_json"))
        counts = Counter({state["status"]: state["n"] for state in states})
        result["progress"] = {"total": sum(counts.values()), "succeeded": counts["succeeded"], "failed": counts["failed"] + counts["interrupted"], "pending": counts["pending"] + counts["running"]}
        result["query_ready"] = result["status"] == "complete"
        return result

    def retry(self, build_id: str) -> dict:
        build = self.get(build_id)
        if build["phase"] != "extraction" or build["status"] not in {"failed", "interrupted"}:
            raise BuildError("build_not_retryable")
        self.require_current_contract(build)
        with self.database.connect() as db:
            try:
                changed = db.execute("UPDATE build_versions SET status='queued',updated_at=? WHERE build_id=? AND status IN ('failed','interrupted')", (utc_now(), build_id)).rowcount
                if not changed:
                    raise BuildError("build_not_retryable")
            except sqlite3.IntegrityError:
                raise BuildError("build_already_running") from None
            db.execute("UPDATE build_fragments SET status='pending',error_code=NULL,error_message=NULL WHERE build_id=? AND status IN ('failed','interrupted')", (build_id,))
        return self.get(build_id)

    def run(self, build_id: str):
        with self.database.connect() as db:
            changed = db.execute("UPDATE build_versions SET status='running',updated_at=? WHERE build_id=? AND status='queued'", (utc_now(), build_id)).rowcount
            if not changed:
                return
            fragments = [dict(row) for row in db.execute("SELECT * FROM build_fragments WHERE build_id=? AND status='pending' ORDER BY ordinal", (build_id,))]
        for fragment in fragments:
            self._extract_fragment(build_id, fragment)
        with self.database.connect() as db:
            failed = db.execute("SELECT COUNT(*) FROM build_fragments WHERE build_id=? AND status!='succeeded'", (build_id,)).fetchone()[0]
            db.execute("UPDATE build_versions SET status=?, updated_at=? WHERE build_id=?", ("failed" if failed else "extracted", utc_now(), build_id))

    def _extract_fragment(self, build_id: str, fragment: dict):
        source_ids = json.loads(fragment["source_ids_json"])
        with self.database.connect() as db:
            db.execute("UPDATE build_fragments SET status='running', attempts=attempts+1 WHERE fragment_id=?", (fragment["fragment_id"],))
            sources = {source_id: dict(db.execute("SELECT * FROM source_turns WHERE source_id=?", (source_id,)).fetchone()) for source_id in source_ids}
        build = self.get(build_id)
        try:
            generated = self.model.generate("extract", {"sample_id": build["sample_id"], "sources": list(sources.values())}, ExtractionBatch, context={"sources": sources})
            # Injected adapters are also untrusted at the business boundary.
            batch = ExtractionBatch.model_validate(generated.value.model_dump(mode="json"), context={"sources": sources})
            with self.database.connect() as db:
                for index, draft in enumerate(batch.memories):
                    memory_id = hashlib.sha256(f"{fragment['fragment_id']}:{index}".encode()).hexdigest()[:24]
                    times = list(dict.fromkeys(sources[source_id]["session_time"] for source_id in draft.source_ids))
                    memory = Memory(**draft.model_dump(), memory_id=memory_id, build_id=build_id, dataset_id=build["dataset_id"], sample_id=build["sample_id"], state_key=f"{build['sample_id']}:{draft.entity_id}:{draft.state_dimension}", session_times=times)
                    db.execute("INSERT INTO memories VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (memory_id, build_id, fragment["fragment_id"], build["dataset_id"], build["sample_id"], memory.content, memory.entity_id, memory.state_dimension, memory.state_key, memory.model_dump_json()))
                    db.executemany("INSERT INTO memory_sources VALUES (?, ?)", [(memory_id, source_id) for source_id in memory.source_ids])
                db.execute("UPDATE build_fragments SET status='succeeded',no_facts_reason=?,model_metadata_json=? WHERE fragment_id=?", (batch.no_facts_reason, canonical_json(generated.metadata), fragment["fragment_id"]))
                self._append_metadata(db, build_id, generated.metadata)
        except Exception as error:
            metadata = error.metadata if isinstance(error, ModelFailure) else {"calls": []}
            code = error.code if isinstance(error, ModelFailure) else "invalid_output"
            with self.database.connect() as db:
                db.execute("UPDATE build_fragments SET status='failed',error_code=?,error_message=?,model_metadata_json=? WHERE fragment_id=?", (code, "Extraction failed; inspect the error code and retry explicitly", canonical_json(metadata), fragment["fragment_id"]))
                self._append_metadata(db, build_id, metadata)

    @staticmethod
    def _append_metadata(db, build_id: str, metadata: dict):
        existing = json.loads(db.execute("SELECT model_metadata_json FROM build_versions WHERE build_id=?", (build_id,)).fetchone()[0])
        existing["calls"].extend(metadata.get("calls", []))
        existing["returned_models"] = list(dict.fromkeys(call["returned_model"] for call in existing["calls"] if call.get("returned_model")))
        db.execute("UPDATE build_versions SET model_metadata_json=?,updated_at=? WHERE build_id=?", (canonical_json(existing), utc_now(), build_id))
