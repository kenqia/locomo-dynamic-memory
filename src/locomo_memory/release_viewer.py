"""Read-only, source-validated MemoryExport catalog shared by Web and replay."""

import hashlib
import json
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import Response

from .export_schemas import MemoryExport
from .m5_graph import neighborhood
from .memory_schemas import MemoryDraft

DEMO = Path(__file__).with_name("demo")


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def load_export(path: Path) -> MemoryExport:
    bundle = MemoryExport.model_validate_json(path.read_bytes())
    if bundle.schema_version != "memory-export-v2":
        raise ValueError("memory-export-v2 required")
    sources = {s.source_id: s.model_dump(mode="json") for s in bundle.sources}
    for memory in bundle.memories:
        MemoryDraft.model_validate(
            {k: v for k, v in memory.model_dump(mode="json").items() if k in MemoryDraft.model_fields},
            context={"sources": sources},
        )
    # Schema parsing and a canonical serialization must preserve all typed fields.
    if MemoryExport.model_validate_json(bundle.model_dump_json()) != bundle:
        raise ValueError("Export roundtrip differs")
    return bundle


class ExportCatalog:
    def __init__(self, manifest: Path, directory: Path | None = None):
        self.manifest = json.loads(manifest.read_text(encoding="utf-8"))
        self.directory = (directory or manifest.parent).resolve()
        self.entries = {b["sample_id"]: b for b in self.manifest["builds"]}
        if len(self.entries) != len(self.manifest["builds"]):
            raise ValueError("Duplicate conversation identity")

    def path(self, sample_id: str) -> Path:
        entry = self.entries[sample_id]
        path = (self.directory / entry["file"]).resolve()
        if not path.is_relative_to(self.directory):
            raise ValueError("Export path escapes catalog directory")
        return path

    def read(self, sample_id: str) -> MemoryExport:
        entry, path = self.entries[sample_id], self.path(sample_id)
        if sha256(path) != entry["sha256"]:
            raise ValueError("Export SHA256 differs")
        bundle = load_export(path)
        if bundle.build.sample_id != sample_id:
            raise ValueError("Conversation identity differs")
        checks = {
            "build_id": bundle.build.build_id,
            "dataset_id": bundle.build.dataset_id,
            "build_fingerprint": bundle.build.fingerprint,
            "index_fingerprint": bundle.index.fingerprint,
            "projection_fingerprint": bundle.projection.fingerprint,
            "memories": len(bundle.memories),
            "relations": len(bundle.relations),
            "source_turns": len(bundle.sources),
        }
        for key, actual in checks.items():
            if key in entry and entry[key] != actual:
                raise ValueError(f"Export {key} differs")
        return bundle

    def verify(self) -> dict:
        rows = []
        for sample_id in self.entries:
            bundle = self.read(sample_id)
            rows.append({"sample_id": sample_id, "build_id": bundle.build.build_id,
                         "sha256": self.entries[sample_id]["sha256"],
                         "memories": len(bundle.memories), "relations": len(bundle.relations),
                         "source_turns": len(bundle.sources), "status": "PASS"})
        return {"status": "PASS", "builds": rows,
                "memories": sum(b["memories"] for b in rows),
                "relations": sum(b["relations"] for b in rows), "provider_requests": 0}


def create_replay_app(manifest: Path | None = None, directory: Path | None = None) -> FastAPI:
    """Independent factory: no SQLite, provider, embedding or write routes."""
    manifest = manifest or Path(os.environ.get("LOCOMO_REPLAY_MANIFEST", str(DEMO / "manifest.json")))
    directory = directory or (Path(os.environ["LOCOMO_REPLAY_DIRECTORY"]) if "LOCOMO_REPLAY_DIRECTORY" in os.environ else None)
    catalog = ExportCatalog(manifest, directory)
    app = FastAPI(title="Synthetic Offline Replay / read-only export viewer")
    app.state.catalog = catalog

    def read(sample_id):
        try:
            return catalog.read(sample_id)
        except KeyError:
            raise HTTPException(404, detail="Unknown conversation") from None
        except (ValueError, OSError):
            raise HTTPException(409, detail="Export integrity validation failed") from None

    @app.get("/health")
    def health():
        return {"status": "ok", "mode": "read_only", "provider_requests": 0}

    @app.get("/catalog")
    def listing():
        return catalog.manifest

    @app.get("/exports/{sample_id}")
    def export(sample_id: str):
        read(sample_id)
        return Response(catalog.path(sample_id).read_bytes(), media_type="application/json",
                        headers={"Content-Disposition": f'attachment; filename="{sample_id}.json"'})

    @app.get("/builds/{sample_id}/graph")
    def graph(sample_id: str, root: str | None = None):
        bundle = read(sample_id)
        try:
            return neighborhood(bundle, [root or bundle.memories[0].memory_id], depth=2, max_nodes=80)
        except (ValueError, IndexError):
            raise HTTPException(422, detail="Invalid graph root") from None

    @app.get("/sources/{sample_id}/{dia_id}")
    def source(sample_id: str, dia_id: str):
        for turn in read(sample_id).sources:
            if turn.dia_id == dia_id:
                return turn
        raise HTTPException(404, detail="Unknown Source Turn")

    return app
