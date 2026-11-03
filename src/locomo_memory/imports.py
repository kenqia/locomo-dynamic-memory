"""Raw conversation import, with annotation storage isolated from build input."""

import hashlib
import json

from .database import Database
from .schemas import ImportRequest, ImportResult, RawTurn


def canonical_json(value) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def import_dataset(database: Database, request: ImportRequest, *, raw_bytes: bytes | None = None, provenance: dict | None = None) -> ImportResult:
    provenance = dict(provenance or {})
    provenance["unpaired_session_times"] = {sample.sample_id: {key: value for key, value in sample.conversation.items() if key.endswith("_date_time") and key.removesuffix("_date_time") not in sample.conversation} for sample in request.data}
    canonical_sources = []
    conversations = []
    for sample in request.data:
        c = sample.conversation
        keys = sorted((key for key in c if key.startswith("session_") and not key.endswith("_date_time")), key=lambda key: int(key.split("_")[1]))
        turns = []
        for key in keys:
            for raw_turn in c[key]:
                turn = RawTurn.model_validate(raw_turn)
                turns.append({"sample_id": sample.sample_id, "session_id": key,
                              "dia_id": turn.dia_id, "speaker": turn.speaker,
                              "session_time": c[f"{key}_date_time"], "text": turn.text,
                              "position": len(turns)})
        canonical_sources.append({"sample_id": sample.sample_id, "speaker_a": c["speaker_a"],
                                  "speaker_b": c["speaker_b"], "turns": turns})
        conversations.append((sample.sample_id, c["speaker_a"], c["speaker_b"], len(keys), len(turns)))
    canonical_sources.sort(key=lambda item: item["sample_id"])
    source_sha = hashlib.sha256(canonical_json(canonical_sources).encode()).hexdigest()
    identity = {"source_sha256": source_sha, "version": request.version, "license": request.license}
    dataset_id = hashlib.sha256(canonical_json(identity).encode()).hexdigest()[:24]
    artifact_bytes = raw_bytes if raw_bytes is not None else canonical_json([s.model_dump() for s in request.data]).encode()
    artifact_sha = hashlib.sha256(artifact_bytes).hexdigest()
    turn_count = sum(c[4] for c in conversations)
    annotations = [{"sample_id": sample.sample_id, **sample.model_dump(include={"qa", "event_summary", "observation", "session_summary"})} for sample in request.data]
    with database.connect() as db:
        reused = db.execute("SELECT 1 FROM datasets WHERE dataset_id=?", (dataset_id,)).fetchone() is not None
        if not reused:
            db.execute("INSERT INTO datasets VALUES (?, ?, ?, ?, ?, ?)", (dataset_id, source_sha, request.version, request.license, len(conversations), turn_count))
            db.executemany("INSERT INTO conversations VALUES (?, ?, ?, ?, ?, ?)", [(dataset_id, *row) for row in conversations])
            for item in canonical_sources:
                for turn in item["turns"]:
                    source_id = f"{dataset_id}/{turn['sample_id']}/{turn['dia_id']}"
                    db.execute("INSERT INTO source_turns VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                               (source_id, dataset_id, turn["sample_id"], turn["session_id"], turn["dia_id"], turn["speaker"], turn["session_time"], turn["text"], turn["position"]))
        db.execute("INSERT OR IGNORE INTO import_artifacts VALUES (?, ?, ?, ?, ?)",
                   (dataset_id, artifact_sha, "original_bytes" if raw_bytes is not None else "canonical_validated_json", canonical_json(provenance), canonical_json(annotations)))
    return ImportResult(dataset_id=dataset_id, artifact_sha256=artifact_sha, source_sha256=source_sha,
                        conversation_count=len(conversations), turn_count=turn_count, reused=reused)
