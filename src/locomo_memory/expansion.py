"""One-hop evidence history expansion from immutable original hybrid seeds."""

import json
import re
import uuid

from .builds import BuildError
from .imports import canonical_json
from .model import utc_now
from .retrieval import budget_tokens, indexing_text, TOKEN_BUDGET_METHOD


class ExpansionService:
    def __init__(self, relations):
        self.relations = relations
        self.database = relations.database
        self.settings = relations.settings
        with self.database.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS candidate_expansions(expansion_id TEXT PRIMARY KEY, query_id TEXT NOT NULL REFERENCES candidate_queries(query_id), build_id TEXT NOT NULL REFERENCES build_versions(build_id),result_json TEXT NOT NULL)")

    def expand(self, query_id: str) -> dict:
        with self.database.connect() as db:
            db.execute("BEGIN")
            row = db.execute("SELECT result_json FROM candidate_queries WHERE query_id=?", (query_id,)).fetchone()
            if row is None:
                raise BuildError("not_found", 404)
            query = json.loads(row[0])
            build_id = query["build_id"]
            phase = db.execute("SELECT status FROM relation_phases WHERE build_id=?", (build_id,)).fetchone()
            if phase is None or phase[0] != "succeeded":
                raise BuildError("relations_not_ready")
            seeds = query["initial_candidates"]
            selected, by_id, reasons, used, scanned = [], {}, [], 0, 0

            def append(memory: dict, origin: dict, initial: bool = False):
                nonlocal used
                memory_id = memory["memory_id"]
                if memory["build_id"] != build_id:
                    raise BuildError("invalid_expansion_scope")
                if memory_id in by_id:
                    if origin not in by_id[memory_id]["origins"]:
                        by_id[memory_id]["origins"].append(origin)
                    return True
                if len(selected) >= self.settings.expansion_max_candidates:
                    if "candidate_count" not in reasons:
                        reasons.append("candidate_count")
                    return False
                cost = budget_tokens(indexing_text(memory))
                if used + cost > self.settings.candidate_token_budget:
                    if "candidate_token_budget" not in reasons:
                        reasons.append("candidate_token_budget")
                    return False
                used += cost
                item = {"memory": memory, "origins": [origin], "is_initial": initial}
                selected.append(item)
                by_id[memory_id] = item
                return True

            for seed in seeds:
                if not append(seed["memory"], {"kind": "initial", "seed_memory_id": seed["memory"]["memory_id"], "reason": "Original hybrid candidate"}, initial=True):
                    break
            # The original list alone is the frontier. New endpoints never become seeds.
            if self.settings.expansion_depth == 1:
                for seed in seeds:
                    seed_id = seed["memory"]["memory_id"]
                    remaining = max(0, self.settings.expansion_scan_limit - scanned)
                    edges = db.execute("SELECT relation_json FROM memory_relations WHERE build_id=? AND (old_memory_id=? OR new_memory_id=?) AND label!='undetermined' ORDER BY relation_id LIMIT ?", (build_id, seed_id, seed_id, remaining + 1)).fetchall()
                    if len(edges) > remaining and "scan_limit" not in reasons:
                        reasons.append("scan_limit")
                    for row in edges[:remaining]:
                        scanned += 1
                        relation = json.loads(row[0])
                        other = relation["new_memory_id"] if relation["old_memory_id"] == seed_id else relation["old_memory_id"]
                        memory_row = db.execute("SELECT memory_json FROM memories WHERE build_id=? AND memory_id=?", (build_id, other)).fetchone()
                        if memory_row is None:
                            raise BuildError("invalid_expansion_scope")
                        memory = json.loads(memory_row[0])
                        append(memory, {"kind": "relation", "seed_memory_id": seed_id, "relation_id": relation["relation_id"], "label": relation["label"], "reason": "One-hop evidence-backed historical relation; applicability remains explicit context", "applicability": relation["applicability"]})
            # Supplements also originate only in the initial set's state keys.
            # Explicit question dates may prioritize an interval, never hard-filter history.
            explicit = re.search(r"\b\d{4}-\d{2}-\d{2}\b", query["question"])
            date_text = explicit.group(0) if explicit else ""
            for seed in seeds:
                seed_id, key = seed["memory"]["memory_id"], seed["memory"]["state_key"]
                remaining = max(0, self.settings.expansion_scan_limit - scanned)
                rows = db.execute("SELECT m.memory_json,MIN(s.position) AS source_order FROM memories m JOIN memory_sources ms ON m.memory_id=ms.memory_id JOIN source_turns s ON ms.source_id=s.source_id WHERE m.build_id=? AND m.state_key=? AND m.memory_id!=? GROUP BY m.memory_id ORDER BY CASE WHEN json_extract(m.memory_json,'$.time.valid_from')<=? AND (json_extract(m.memory_json,'$.time.valid_to') IS NULL OR json_extract(m.memory_json,'$.time.valid_to')>=?) THEN 0 ELSE 1 END,source_order,m.memory_id LIMIT ?", (build_id, key, seed_id, date_text, date_text, remaining + 1)).fetchall()
                if len(rows) > remaining and "scan_limit" not in reasons:
                    reasons.append("scan_limit")
                for row in rows[:remaining]:
                    scanned += 1
                    append(json.loads(row[0]), {"kind": "state_key", "seed_memory_id": seed_id, "state_key": key, "reason": "Same entity and state dimension historical supplement; unknown dates remain eligible"})
        result = {"expansion_id": uuid.uuid4().hex, "query_id": query_id, "build_id": build_id, "question": query["question"],
                  "index_fingerprint": query["index_fingerprint"], "created_at": utc_now(),
                  "initial_candidates": seeds, "added_candidates": [item for item in selected if not item["is_initial"]],
                  "candidates": selected, "truncated": bool(reasons), "truncation_reasons": reasons,
                  "candidate_token_count": used, "token_budget_method": TOKEN_BUDGET_METHOD,
                  "relation_depth": self.settings.expansion_depth, "scanned": scanned, "config": self.settings.snapshot()}
        with self.database.connect() as db:
            db.execute("INSERT INTO candidate_expansions VALUES (?,?,?,?)", (result["expansion_id"], query_id, build_id, canonical_json(result)))
        return result
