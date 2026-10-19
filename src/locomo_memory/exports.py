"""Read a pinned immutable collection in one SQLite snapshot, without annotations."""
import json

from pydantic import ValidationError

from .builds import BuildError
from .export_schemas import ExportBuild, ExportIndex, MemoryExport


def read_bundle(db, build: dict) -> MemoryExport:
    """Validate the same allowlisted artifact contract at publication and download."""
    try:
        fixed = build["build_id"]
        dataset = dict(db.execute("SELECT * FROM datasets WHERE dataset_id=?", (build["dataset_id"],)).fetchone())
        memories = [json.loads(row[0]) for row in db.execute("SELECT memory_json FROM memories WHERE build_id=? ORDER BY memory_id", (fixed,))]
        relations = [json.loads(row[0]) for row in db.execute("SELECT relation_json FROM memory_relations WHERE build_id=? ORDER BY relation_id", (fixed,))]
        sources = [dict(row) for row in db.execute("SELECT DISTINCT s.* FROM source_turns s JOIN memory_sources ms ON ms.source_id=s.source_id JOIN memories m ON m.memory_id=ms.memory_id WHERE m.build_id=? ORDER BY s.position", (fixed,))]
        projection = json.loads(db.execute("SELECT projection_json FROM current_state_projections WHERE build_id=?", (fixed,)).fetchone()[0])
        index = dict(db.execute("SELECT * FROM build_indexes WHERE build_id=?", (fixed,)).fetchone())
        index.update(json.loads(index.pop("metadata_json")))
        # Runtime/provider dictionaries never become export metadata.
        return MemoryExport.model_validate({"dataset": dataset,
            "build": {field: build[field] for field in ExportBuild.model_fields},
            "memories": memories, "sources": sources, "relations": relations,
            "projection": projection, "index": {field: index[field] for field in ExportIndex.model_fields}})
    except (ValidationError, ValueError, KeyError, TypeError):
        raise BuildError("invalid_export", 409) from None


class ExportService:
    def __init__(self, versions):
        self.versions = versions
        self.database = versions.database

    def export(self, build_id: str) -> MemoryExport:
        build = self.versions.builds.get(build_id)
        self.versions.pin(build["dataset_id"], build["sample_id"], build_id)
        with self.database.connect() as db:
            db.execute("BEGIN")
            return read_bundle(db, build)
