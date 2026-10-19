"""Minimal atomic publication and complete-version pinning for query callers."""

import json

from .builds import BuildError, BuildService
from .projection import create_projection
from .model import utc_now


class VersionsService:
    def __init__(self, builds: BuildService):
        self.builds = builds
        self.database = builds.database
        with self.database.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS active_versions(dataset_id TEXT NOT NULL, sample_id TEXT NOT NULL, build_id TEXT NOT NULL REFERENCES build_versions(build_id), PRIMARY KEY(dataset_id,sample_id))")

    def publish(self, build_id: str) -> dict:
        with self.database.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM build_versions WHERE build_id=?", (build_id,)).fetchone()
            if row is None:
                raise BuildError("not_found", 404)
            if row["status"] != "related":
                raise BuildError("version_not_publishable")
            incomplete = db.execute("SELECT COUNT(*) FROM build_fragments WHERE build_id=? AND status!='succeeded'", (build_id,)).fetchone()[0]
            phase = db.execute("SELECT status FROM relation_phases WHERE build_id=?", (build_id,)).fetchone()
            pending = db.execute("SELECT COUNT(*) FROM relation_tasks WHERE build_id=? AND status!='succeeded'", (build_id,)).fetchone()[0]
            index = db.execute("SELECT * FROM build_indexes WHERE build_id=?", (build_id,)).fetchone()
            projection = db.execute("SELECT * FROM current_state_projections WHERE build_id=?", (build_id,)).fetchone()
            if incomplete or pending or phase is None or phase["status"] != "succeeded" or index is None or index["status"] != "ready" or index["build_fingerprint"] != row["fingerprint"] or projection is None:
                raise BuildError("version_not_publishable")
            memory_ids = {item[0] for item in db.execute("SELECT memory_id FROM memories WHERE build_id=?", (build_id,))}
            indexed_ids = {item[0] for item in db.execute("SELECT memory_id FROM index_entries WHERE build_id=?", (build_id,))}
            if memory_ids != indexed_ids or len(memory_ids) != index["memory_count"]:
                raise BuildError("version_not_publishable")
            expected = create_projection(db, dict(row))
            if expected["fingerprint"] != projection["fingerprint"]:
                raise BuildError("version_not_publishable")
            db.execute("UPDATE build_versions SET status='complete',phase='complete',updated_at=? WHERE build_id=?", (utc_now(), build_id))
            db.execute("INSERT INTO active_versions VALUES (?,?,?) ON CONFLICT(dataset_id,sample_id) DO UPDATE SET build_id=excluded.build_id", (row["dataset_id"], row["sample_id"], build_id))
        return self.builds.get(build_id)

    def pin(self, dataset_id: str, sample_id: str, build_id: str | None = None) -> str:
        with self.database.connect() as db:
            db.execute("BEGIN")
            if build_id is None:
                row = db.execute("SELECT build_id FROM active_versions WHERE dataset_id=? AND sample_id=?", (dataset_id, sample_id)).fetchone()
                if row is None:
                    raise BuildError("no_complete_version")
                build_id = row["build_id"]
            row = db.execute("SELECT status FROM build_versions WHERE build_id=? AND dataset_id=? AND sample_id=?", (build_id, dataset_id, sample_id)).fetchone()
            if row is None or row["status"] != "complete":
                raise BuildError("no_complete_version")
        return build_id

    def pin_details(self, dataset_id: str, sample_id: str, build_id: str | None = None) -> dict:
        fixed = self.pin(dataset_id, sample_id, build_id)
        with self.database.connect() as db:
            cutoff = db.execute("SELECT cutoff FROM current_state_projections WHERE build_id=?", (fixed,)).fetchone()[0]
            index = db.execute("SELECT fingerprint FROM build_indexes WHERE build_id=?", (fixed,)).fetchone()[0]
        return {"build_id": fixed, "dataset_id": dataset_id, "sample_id": sample_id, "cutoff": cutoff, "index_fingerprint": index}
