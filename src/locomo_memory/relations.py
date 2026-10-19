"""Durable, bounded historical comparisons followed by a conservative projection."""

import hashlib
import json
import sqlite3

from .builds import BuildError, BuildService
from .imports import canonical_json
from .model import ModelFailure, RELATION_PROMPT_VERSION, utc_now
from .relation_schemas import MemoryRelation, RelationBatch, RELATION_SCHEMA_VERSION


class RelationService:
    def __init__(self, builds: BuildService, model):
        self.builds = builds
        self.database = builds.database
        self.settings = builds.settings
        self.model = model
        with self.database.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS relation_phases (
                    build_id TEXT PRIMARY KEY REFERENCES build_versions(build_id), status TEXT NOT NULL,
                    prompt_version TEXT NOT NULL, schema_version TEXT NOT NULL, error_code TEXT
                );
                CREATE TABLE IF NOT EXISTS relation_tasks (
                    task_id TEXT PRIMARY KEY, build_id TEXT NOT NULL REFERENCES build_versions(build_id),
                    ordinal INTEGER NOT NULL, new_memory_id TEXT NOT NULL REFERENCES memories(memory_id),
                    history_ids_json TEXT NOT NULL, status TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0,
                    truncated_count INTEGER NOT NULL, error_code TEXT, metadata_json TEXT NOT NULL DEFAULT '{}'
                );
                CREATE TABLE IF NOT EXISTS memory_relations (
                    relation_id TEXT PRIMARY KEY, build_id TEXT NOT NULL REFERENCES build_versions(build_id),
                    old_memory_id TEXT NOT NULL REFERENCES memories(memory_id), new_memory_id TEXT NOT NULL REFERENCES memories(memory_id),
                    label TEXT NOT NULL, relation_json TEXT NOT NULL,
                    UNIQUE(build_id,old_memory_id,new_memory_id)
                );
                CREATE INDEX IF NOT EXISTS relation_old ON memory_relations(build_id,old_memory_id);
                CREATE INDEX IF NOT EXISTS relation_new ON memory_relations(build_id,new_memory_id);
                CREATE TABLE IF NOT EXISTS current_state_projections (
                    build_id TEXT PRIMARY KEY REFERENCES build_versions(build_id), fingerprint TEXT NOT NULL,
                    cutoff TEXT NOT NULL, projection_json TEXT NOT NULL
                );
            """)

    def recover_interrupted(self):
        with self.database.connect() as db:
            db.execute("UPDATE relation_tasks SET status='interrupted',error_code='interrupted' WHERE status='running'")
            db.execute("UPDATE relation_phases SET status='interrupted',error_code='interrupted' WHERE status IN ('queued','running')")

    def start(self, build_id: str) -> dict:
        build = self.builds.get(build_id)
        self.builds.require_current_contract(build)
        retryable = build["status"] == "relations_failed" or (build["status"] == "interrupted" and build["phase"] == "relations")
        if build["status"] != "indexed" and not retryable:
            raise BuildError("relations_not_ready")
        with self.database.connect() as db:
            index = db.execute("SELECT * FROM build_indexes WHERE build_id=?", (build_id,)).fetchone()
            if index is None or index["status"] != "ready" or index["build_fingerprint"] != build["fingerprint"]:
                raise BuildError("index_not_ready")
            try:
                changed = db.execute("UPDATE build_versions SET status='queued',phase='relations',updated_at=? WHERE build_id=? AND status IN ('indexed','relations_failed','interrupted')", (utc_now(), build_id)).rowcount
            except sqlite3.IntegrityError:
                raise BuildError("build_already_running") from None
            if not changed:
                raise BuildError("relations_not_ready")
            if retryable:
                db.execute("UPDATE relation_tasks SET status='pending',error_code=NULL WHERE build_id=? AND status IN ('failed','interrupted')", (build_id,))
                db.execute("UPDATE relation_phases SET status='queued',error_code=NULL WHERE build_id=?", (build_id,))
            else:
                db.execute("INSERT INTO relation_phases VALUES (?, 'queued', ?, ?, NULL)", (build_id, RELATION_PROMPT_VERSION, RELATION_SCHEMA_VERSION))
                rows = db.execute("SELECT m.memory_json,MIN(s.position) AS source_order FROM memories m JOIN memory_sources ms ON m.memory_id=ms.memory_id JOIN source_turns s ON s.source_id=ms.source_id WHERE m.build_id=? GROUP BY m.memory_id ORDER BY source_order,m.rowid", (build_id,)).fetchall()
                histories = {}
                for ordinal, row in enumerate(rows):
                    memory = json.loads(row["memory_json"])
                    previous = histories.setdefault(memory["entity_id"], [])
                    bounded = previous[-self.settings.relation_history_limit:]
                    if bounded:
                        db.execute("INSERT INTO relation_tasks(task_id,build_id,ordinal,new_memory_id,history_ids_json,status,truncated_count) VALUES (?,?,?,?,?,'pending',?)", (f"{build_id}:relation:{ordinal}", build_id, ordinal, memory["memory_id"], canonical_json([item["memory_id"] for item in bounded]), max(0, len(previous) - len(bounded))))
                    previous.append(memory)
        return self.progress(build_id)

    def progress(self, build_id: str) -> dict:
        build = self.builds.get(build_id)
        with self.database.connect() as db:
            phase = db.execute("SELECT * FROM relation_phases WHERE build_id=?", (build_id,)).fetchone()
            rows = db.execute("SELECT status,COUNT(*) AS n FROM relation_tasks WHERE build_id=? GROUP BY status", (build_id,)).fetchall()
            truncated = db.execute("SELECT COALESCE(SUM(truncated_count),0) FROM relation_tasks WHERE build_id=?", (build_id,)).fetchone()[0]
        if phase is None:
            raise BuildError("relations_not_ready")
        counts = {row["status"]: row["n"] for row in rows}
        return {**dict(phase), "progress": {"total": sum(counts.values()), "succeeded": counts.get("succeeded", 0), "failed": counts.get("failed", 0) + counts.get("interrupted", 0), "pending": counts.get("pending", 0) + counts.get("running", 0)}, "history_comparisons_truncated": truncated, "history_limit": build["config"]["relation_history_limit"]}

    def run(self, build_id: str):
        with self.database.connect() as db:
            if not db.execute("UPDATE build_versions SET status='running' WHERE build_id=? AND status='queued' AND phase='relations'", (build_id,)).rowcount:
                return
            db.execute("UPDATE relation_phases SET status='running' WHERE build_id=?", (build_id,))
            tasks = [dict(row) for row in db.execute("SELECT * FROM relation_tasks WHERE build_id=? AND status='pending' ORDER BY ordinal", (build_id,))]
        for task in tasks:
            self._judge(build_id, task)
        with self.database.connect() as db:
            failed = db.execute("SELECT COUNT(*) FROM relation_tasks WHERE build_id=? AND status!='succeeded'", (build_id,)).fetchone()[0]
        error_code = "relation_tasks_failed" if failed else None
        if not failed:
            try:
                self.rebuild_projection(build_id, internal=True)
            except BuildError as error:
                error_code = error.code
        with self.database.connect() as db:
            db.execute("UPDATE relation_phases SET status=?,error_code=? WHERE build_id=?", ("failed" if error_code else "succeeded", error_code, build_id))
            db.execute("UPDATE build_versions SET status=?,phase='relations',updated_at=? WHERE build_id=?", ("relations_failed" if error_code else "related", utc_now(), build_id))

    def _judge(self, build_id: str, task: dict):
        with self.database.connect() as db:
            db.execute("UPDATE relation_tasks SET status='running',attempts=attempts+1 WHERE task_id=?", (task["task_id"],))
            new = json.loads(db.execute("SELECT memory_json FROM memories WHERE memory_id=? AND build_id=?", (task["new_memory_id"], build_id)).fetchone()[0])
            history = [json.loads(db.execute("SELECT memory_json FROM memories WHERE memory_id=? AND build_id=?", (memory_id, build_id)).fetchone()[0]) for memory_id in json.loads(task["history_ids_json"])]
            ids = set(source_id for memory in [new, *history] for source_id in memory["source_ids"])
            sources = {source_id: dict(db.execute("SELECT * FROM source_turns WHERE source_id=?", (source_id,)).fetchone()) for source_id in sorted(ids)}
        context = {"new_memory": new, "history": history, "sources": sources}
        try:
            generated = self.model.generate("relate", {**context, "sources": list(sources.values())}, RelationBatch, context=context)
            validated = RelationBatch.model_validate(generated.value.model_dump(mode="json"), context=context)
            with self.database.connect() as db:
                for judgment in validated.judgments:
                    relation_id = hashlib.sha256(f"{build_id}:{judgment.old_memory_id}:{judgment.new_memory_id}".encode()).hexdigest()[:24]
                    relation = MemoryRelation(**judgment.model_dump(), relation_id=relation_id, build_id=build_id)
                    db.execute("INSERT INTO memory_relations VALUES (?,?,?,?,?,?)", (relation_id, build_id, judgment.old_memory_id, judgment.new_memory_id, judgment.label, relation.model_dump_json()))
                db.execute("UPDATE relation_tasks SET status='succeeded',metadata_json=? WHERE task_id=?", (canonical_json(generated.metadata), task["task_id"]))
                self.builds._append_metadata(db, build_id, generated.metadata)
        except Exception as error:
            code = error.code if isinstance(error, ModelFailure) else "invalid_relation_output"
            metadata = error.metadata if isinstance(error, ModelFailure) else {"calls": []}
            with self.database.connect() as db:
                db.execute("UPDATE relation_tasks SET status='failed',error_code=?,metadata_json=? WHERE task_id=?", (code, canonical_json(metadata), task["task_id"]))
                self.builds._append_metadata(db, build_id, metadata)

    def current_state(self, build_id: str) -> dict:
        self.builds.get(build_id)
        with self.database.connect() as db:
            row = db.execute("SELECT projection_json FROM current_state_projections WHERE build_id=?", (build_id,)).fetchone()
        if row is None:
            raise BuildError("projection_not_ready")
        return json.loads(row[0])

    def rebuild_projection(self, build_id: str, *, internal: bool = False) -> dict:
        from .projection import create_projection

        build = self.builds.get(build_id)
        if build["status"] == "complete" or (not internal and build["status"] != "related"):
            raise BuildError("projection_not_mutable")
        self.builds.require_current_contract(build)
        with self.database.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            status = db.execute("SELECT status FROM build_versions WHERE build_id=?", (build_id,)).fetchone()[0]
            if status == "complete" or (not internal and status != "related"):
                raise BuildError("projection_not_mutable")
            projection = create_projection(db, build)
            db.execute("INSERT OR REPLACE INTO current_state_projections VALUES (?,?,?,?)", (build_id, projection["fingerprint"], projection["cutoff"], canonical_json(projection)))
        return projection
