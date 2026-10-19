"""SQLite storage. Connections are short lived; transactions make imports atomic."""

from contextlib import contextmanager
from pathlib import Path
import sqlite3


class Database:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS datasets (
                    dataset_id TEXT PRIMARY KEY, source_sha256 TEXT NOT NULL,
                    version TEXT NOT NULL, license TEXT NOT NULL,
                    conversation_count INTEGER NOT NULL, turn_count INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS import_artifacts (
                    dataset_id TEXT NOT NULL REFERENCES datasets(dataset_id),
                    artifact_sha256 TEXT NOT NULL, checksum_basis TEXT NOT NULL,
                    provenance_json TEXT NOT NULL, annotations_json TEXT NOT NULL,
                    PRIMARY KEY(dataset_id, artifact_sha256)
                );
                CREATE TABLE IF NOT EXISTS conversations (
                    dataset_id TEXT NOT NULL REFERENCES datasets(dataset_id),
                    sample_id TEXT NOT NULL, speaker_a TEXT NOT NULL, speaker_b TEXT NOT NULL,
                    session_count INTEGER NOT NULL, turn_count INTEGER NOT NULL,
                    PRIMARY KEY(dataset_id, sample_id)
                );
                CREATE TABLE IF NOT EXISTS source_turns (
                    source_id TEXT PRIMARY KEY, dataset_id TEXT NOT NULL,
                    sample_id TEXT NOT NULL, session_id TEXT NOT NULL, dia_id TEXT NOT NULL,
                    speaker TEXT NOT NULL, session_time TEXT NOT NULL, text TEXT NOT NULL,
                    position INTEGER NOT NULL,
                    UNIQUE(dataset_id, sample_id, dia_id),
                    FOREIGN KEY(dataset_id, sample_id) REFERENCES conversations(dataset_id, sample_id)
                );
                CREATE INDEX IF NOT EXISTS source_order ON source_turns(dataset_id, sample_id, position);
            """)

    @contextmanager
    def connect(self):
        connection = sqlite3.connect(self.path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        try:
            with connection:
                yield connection
        finally:
            connection.close()


@contextmanager
def backend_ownership(path: Path):
    """A kernel lock distinguishes a restart from a competing local backend."""
    import fcntl

    with path.with_suffix(path.suffix + ".runtime.lock").open("a") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError("Another backend owns this SQLite database") from None
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)
