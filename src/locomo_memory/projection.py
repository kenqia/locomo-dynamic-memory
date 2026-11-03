"""Recompute source-linked last-known claims without assuming unknown validity."""

import hashlib
import json

from .imports import canonical_json
from .temporal import conversation_cutoff

PROJECTION_VERSION = "current-state-v1"


def relation_applicability(relation: dict, cutoff: str, *, dated_change: bool) -> tuple[bool, str]:
    applicability = relation["applicability"]
    if applicability["condition"] and applicability["condition_satisfied"] is not True:
        return False, "condition_unresolved" if applicability["condition_satisfied"] is None else "condition_false"
    start, end = applicability["from_date"], applicability["to_date"]
    if dated_change and start is None:
        return False, "change_time_unknown"
    if start and start > cutoff:
        return False, "change_after_cutoff"
    if end and end < cutoff:
        return False, "outside_applicability_range"
    return True, "supported_applicability"


def create_projection(db, build: dict) -> dict:
    memories = {row["memory_id"]: json.loads(row["memory_json"]) for row in db.execute("SELECT memory_id,memory_json FROM memories WHERE build_id=? ORDER BY memory_id", (build["build_id"],))}
    relations = [json.loads(row["relation_json"]) for row in db.execute("SELECT relation_json FROM memory_relations WHERE build_id=? ORDER BY relation_id", (build["build_id"],))]
    cutoff, raw_cutoff = conversation_cutoff(db, build["dataset_id"], build["sample_id"])
    day = cutoff.date().isoformat()
    fingerprint = hashlib.sha256(canonical_json({"version": PROJECTION_VERSION, "build": build["fingerprint"], "cutoff": cutoff.isoformat(), "memories": list(memories.values()), "relations": relations}).encode()).hexdigest()
    items = {}
    for memory_id, memory in memories.items():
        status = "last_known" if memory["polarity"] == "positive" else "negative_claim"
        reason = "Last known factual claim; unknown validity does not establish continuous truth"
        if memory["statement_type"] != "fact":
            status, reason = "nonfactual", "Plan, intention or uncertain statement; not an accomplished factual state"
        elif memory["memory_type"] == "event":
            status, reason = "historical_event", "Event evidence remains part of history regardless of later state changes"
        elif memory["time"]["valid_from"] and memory["time"]["valid_from"] > day:
            status, reason = "future", "The supported validity interval starts after the known cutoff"
        elif memory["time"]["valid_to"] and memory["time"]["valid_to"] < day:
            status, reason = "expired", "The supported validity interval ends before the known cutoff"
        items[memory_id] = {"memory_id": memory_id, "status": status, "reason": reason, "source_ids": memory["source_ids"], "relation_ids": []}
    conditional, conflicts = [], []
    for relation in relations:
        for memory_id in (relation["old_memory_id"], relation["new_memory_id"]):
            items[memory_id]["relation_ids"].append(relation["relation_id"])
        if relation["label"] not in {"SUPERSEDE", "UPDATE"}:
            continue
        applicable, reason = relation_applicability(relation, day, dated_change=True)
        old, new = items[relation["old_memory_id"]], items[relation["new_memory_id"]]
        if not applicable or new["status"] in {"future", "expired", "nonfactual"}:
            conditional.append({"relation_id": relation["relation_id"], "reason": reason if not applicable else "new_claim_not_current_fact"})
            continue
        if memories[old["memory_id"]]["memory_type"] == "state" and old["status"] != "nonfactual":
            old["status"] = "superseded" if relation["label"] == "SUPERSEDE" else "advanced"
            old["reason"] = "Evidence-backed transition applies at the known cutoff; historical evidence retained"
    for relation in relations:
        if relation["label"] != "CONFLICT":
            continue
        applicable, reason = relation_applicability(relation, day, dated_change=False)
        endpoints = [items[relation[field]] for field in ("old_memory_id", "new_memory_id")]
        if not applicable:
            conditional.append({"relation_id": relation["relation_id"], "reason": reason})
        elif all(item["status"] in {"last_known", "negative_claim", "conflict"} for item in endpoints):
            conflicts.append({"relation_id": relation["relation_id"], "memory_ids": [item["memory_id"] for item in endpoints], "source_ids": relation["source_ids"]})
            for item in endpoints:
                item["status"], item["reason"] = "conflict", "Unresolved contradictory claims; both sources remain visible"
    result = {"build_id": build["build_id"], "fingerprint": fingerprint, "projection_version": PROJECTION_VERSION,
              "cutoff": cutoff.isoformat(), "cutoff_source_time": raw_cutoff,
              "current_states": [], "historical_states": [], "events": [], "nonfactual": [],
              "conflicts": conflicts, "conditional_relations": conditional,
              "assumptions": ["Cutoff is the selected conversation's last recorded session, not the host date", "Session timestamps have no asserted timezone", "Unknown validity is a last-known claim, not proof of continuous applicability", "RETAIN is never inferred from absence of new messages"]}
    for memory_id, memory in memories.items():
        item = items[memory_id]
        if memory["statement_type"] != "fact":
            result["nonfactual"].append(item)
        elif memory["memory_type"] == "event":
            result["events"].append(item)
        elif item["status"] in {"superseded", "advanced", "future", "expired"}:
            result["historical_states"].append(item)
        else:
            result["current_states"].append(item)
    return result
