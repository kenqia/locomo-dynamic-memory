"""Read-only allowlisted file/archive integrity checks; no paid replay."""

import json
from pathlib import Path
import sqlite3
import tarfile

from .release_viewer import sha256


def verify_files(manifest: Path, directory: Path, *, private=False):
    entries = json.loads(manifest.read_text(encoding="utf-8"))["files"]
    root = directory.resolve()
    checked = []
    for entry in entries:
        path = (root / entry["path"]).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            raise ValueError("Missing or out-of-scope evidence file")
        if sha256(path) != entry["sha256"] or path.stat().st_size != entry["bytes"]:
            raise ValueError("Evidence integrity mismatch")
        kind = entry.get("kind", path.suffix.lower())
        if kind == ".json":
            json.loads(path.read_text(encoding="utf-8"))
        if private and kind in {".sqlite3", ".sqlite", ".db"}:
            with sqlite3.connect(path.as_uri() + "?mode=ro", uri=True) as db:
                if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                    raise ValueError("Archive SQLite integrity differs")
        if private and (path.name.endswith(".tar.gz") or path.name.endswith(".tgz")):
            with tarfile.open(path, "r:gz") as archive:
                members = []
                for member in archive:
                    name = Path(member.name)
                    if name.is_absolute() or ".." in name.parts or not (member.isfile() or member.isdir()):
                        raise ValueError("Unsafe archive member")
                    if member.isfile():
                        stream = archive.extractfile(member)
                        digest = __import__("hashlib").file_digest(stream, "sha256").hexdigest()
                        members.append({"path": member.name, "sha256": digest, "bytes": member.size})
                expected_members = [{k: m[k] for k in ("path", "sha256", "bytes")} for m in entry.get("members", [])]
                if "members" in entry and members != expected_members:
                    raise ValueError("Archive member hashes differ")
        checked.append({"path": entry["path"], "sha256": entry["sha256"], "status": "PASS"})
    return {"status": "PASS", "files": checked, "provider_requests": 0,
            "scope": "SHA/size/JSON; private mode adds SQLite quick_check and safe tar/member SHA"}
