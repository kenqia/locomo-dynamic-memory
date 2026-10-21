"""Durable logical attempts and provider checkpoints for relation tasks."""

import json

from .imports import canonical_json
from .model import utc_now


class RelationAttempts:
    def __init__(self, builds):
        self.builds = builds
        self.database = builds.database
        with self.database.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS relation_attempts (
                    task_id TEXT NOT NULL REFERENCES relation_tasks(task_id),
                    logical_attempt INTEGER NOT NULL, status TEXT NOT NULL,
                    started_at TEXT NOT NULL, completed_at TEXT, error_code TEXT,
                    PRIMARY KEY(task_id,logical_attempt)
                );
                CREATE TABLE IF NOT EXISTS relation_provider_calls (
                    task_id TEXT NOT NULL, logical_attempt INTEGER NOT NULL,
                    provider_attempt INTEGER NOT NULL, metadata_json TEXT NOT NULL,
                    PRIMARY KEY(task_id,logical_attempt,provider_attempt),
                    FOREIGN KEY(task_id,logical_attempt) REFERENCES relation_attempts(task_id,logical_attempt)
                );
            """)

    def start(self, db, task_id: str) -> int:
        attempt = db.execute("UPDATE relation_tasks SET status='running',attempts=attempts+1 WHERE task_id=? RETURNING attempts", (task_id,)).fetchone()[0]
        db.execute("INSERT INTO relation_attempts VALUES (?,?,'running',?,NULL,NULL)", (task_id, attempt, utc_now()))
        return attempt

    def observer(self, build_id: str, task_id: str, logical_attempt: int):
        def record(call: dict):
            # All fields originate in the adapter's safe diagnostics, never responses.
            call.update(build_id=build_id, task_id=task_id, logical_attempt=logical_attempt,
                        provider_attempt=call["attempt"],
                        call_id=f"{task_id}:{logical_attempt}:{call['attempt']}")
            with self.database.connect() as db:
                db.execute("""INSERT INTO relation_provider_calls VALUES (?,?,?,?)
                    ON CONFLICT(task_id,logical_attempt,provider_attempt)
                    DO UPDATE SET metadata_json=excluded.metadata_json""",
                    (task_id, logical_attempt, call["attempt"], canonical_json(call)))
                self.builds._append_metadata(db, build_id, {"calls": [call]})
        return record

    @staticmethod
    def finish(db, task_id: str, attempt: int, status: str, error_code: str | None = None):
        db.execute("UPDATE relation_attempts SET status=?,completed_at=?,error_code=? WHERE task_id=? AND logical_attempt=?",
                   (status, utc_now(), error_code, task_id, attempt))

    def recover(self, db):
        rows = db.execute("""SELECT c.*,t.build_id FROM relation_provider_calls c
            JOIN relation_tasks t USING(task_id)
            WHERE json_extract(c.metadata_json,'$.status') IN ('started','response_observed')""").fetchall()
        for row in rows:
            call = json.loads(row["metadata_json"])
            if call["status"] in {"started", "response_observed"}:
                # Unknown outcome, duration and usage stay unknown. No completion timestamp.
                call.update(status="interrupted", outcome="interrupted", recovered_at=utc_now())
                db.execute("UPDATE relation_provider_calls SET metadata_json=? WHERE task_id=? AND logical_attempt=? AND provider_attempt=?",
                           (canonical_json(call), row["task_id"], row["logical_attempt"], row["provider_attempt"]))
                self.builds._append_metadata(db, row["build_id"], {"calls": [call]})
        db.execute("UPDATE relation_attempts SET status='interrupted',error_code='interrupted' WHERE status='running'")

    @staticmethod
    def history(db, task_id: str, attempts: int) -> dict:
        history = []
        for row in db.execute("SELECT * FROM relation_attempts WHERE task_id=? ORDER BY logical_attempt", (task_id,)):
            item = dict(row)
            item["calls"] = [json.loads(call[0]) for call in db.execute("SELECT metadata_json FROM relation_provider_calls WHERE task_id=? AND logical_attempt=? ORDER BY provider_attempt", (task_id, item["logical_attempt"]))]
            history.append(item)
        if history:
            status = "recorded" if history[0]["logical_attempt"] == 1 else "partial_legacy"
        else:
            status = "legacy_not_recorded" if attempts else "not_started"
        return {"diagnostic_history": history, "diagnostic_history_status": status}
