"""Pin one complete version, resolve bounded history, answer and retain an audit Trace."""

from datetime import date, datetime
import json
import hashlib
import re
import time
import uuid

from pydantic import ValidationError

from .builds import BuildError
from .embeddings import EmbeddingFailure
from .imports import canonical_json
from .model import ModelFailure, utc_now, RESOLUTION_PROMPT, ANSWER_PROMPT, KNOWN_MODEL_VERSION
from .query_schemas import EffectiveResolution, EvidenceAnswer, RESOLUTION_SCHEMA_VERSION, ANSWER_SCHEMA_VERSION
from .retrieval import budget_tokens, TOKEN_BUDGET_METHOD
from .temporal import conversation_cutoff

RESOLUTION_PROMPT_VERSION = "effective-resolution-v1"
ANSWER_PROMPT_VERSION = "evidence-answer-v2-raw-sources"


def explicit_question_date(question):
    """Recognize one exact date; ambiguous ranges stay in the original question."""
    matches = []
    patterns = [
        (r"\b\d{4}-\d{2}-\d{2}\b", ("%Y-%m-%d",)),
        (r"\b\d{1,2} [A-Za-z]+,? \d{4}\b", ("%d %B %Y", "%d %b %Y")),
        (r"\b[A-Za-z]+ \d{1,2},? \d{4}\b", ("%B %d %Y", "%b %d %Y")),
    ]
    for pattern, formats in patterns:
        for match in re.finditer(pattern, question):
            for format in formats:
                try:
                    matches.append(datetime.strptime(match.group().replace(",", ""), format).date())
                    break
                except ValueError:
                    continue
    unique = set(matches)
    return matches[0] if len(unique) == 1 else None


class QueryFailure(BuildError):
    def __init__(self, code, trace_id, status=502):
        super().__init__(code, status)
        self.trace_id = trace_id


class QueryService:
    def __init__(self, versions, retrieval, expansion, model):
        self.versions, self.retrieval, self.expansion, self.model = versions, retrieval, expansion, model
        self.database, self.settings = retrieval.database, retrieval.settings
        with self.database.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS query_traces(trace_id TEXT PRIMARY KEY, build_id TEXT NOT NULL REFERENCES build_versions(build_id), result_json TEXT NOT NULL)")

    def get(self, trace_id):
        with self.database.connect() as db:
            row = db.execute("SELECT result_json FROM query_traces WHERE trace_id=?", (trace_id,)).fetchone()
        if row is None:
            raise BuildError("not_found", 404)
        return json.loads(row[0])

    def _save(self, trace):
        calls = [call for operation in trace["operations"].values() for call in operation.get("calls", [])]
        trace["usage_summary"] = {"calls": len(calls), "calls_without_reported_usage": sum(not call.get("usage") for call in calls),
            "reported_tokens": {field: sum(call.get("usage", {}).get(field, 0) for call in calls)
                                for field in ("prompt_tokens", "completion_tokens", "total_tokens")}}
        with self.database.connect() as db:
            db.execute("INSERT INTO query_traces VALUES (?,?,?)", (trace["trace_id"], trace["build_id"], canonical_json(trace)))

    def generate_answer(self, question, time_condition, memories, sources, status, *, audit=None, raw_sources=None):
        """Shared final evidence budget and answer operation for controlled comparisons.

        Return the validated answer, delivered memories, and budget/provider metadata.
        The caller must supply memories and sources from one already pinned version.
        """
        delivered, used, omitted = [], 0, []
        for memory in memories:
            item_sources = [sources[sid] for sid in memory["source_ids"]]
            # Include every field actually delivered, not just a shorter indexing string.
            cost = budget_tokens(canonical_json({"memory": memory, "sources": item_sources}))
            if used + cost > self.settings.evidence_token_budget:
                omitted.append(memory["memory_id"])
                continue
            delivered.append(memory)
            used += cost
        raw_delivered = []
        if raw_sources is not None:
            for source in raw_sources:
                cost = budget_tokens(canonical_json(source))
                if used + cost > self.settings.evidence_token_budget:
                    omitted.append(source["source_id"])
                    continue
                used += cost
                raw_delivered.append(source)
        effective_status = "insufficient" if omitted or not (delivered or raw_delivered) else status
        delivered_sources = {sid: sources[sid] for memory in delivered for sid in memory["source_ids"]}
        if raw_sources is not None:
            delivered_sources = {s["source_id"]: s for s in raw_delivered}
        context = {"status": effective_status, "memories": {m["memory_id"]: m for m in delivered}}
        if raw_sources is not None:
            context["raw_sources"] = delivered_sources
        payload = {"operation": "answer", "question": question, "time": time_condition, "status": effective_status,
                   "memories": delivered, "sources": list(delivered_sources.values()), "evidence_truncated": bool(omitted)}
        budget = {"token_count": used, "budget": self.settings.evidence_token_budget,
                  "token_budget_method": TOKEN_BUDGET_METHOD, "truncated": bool(omitted),
                  "omitted_memory_ids": omitted, "truncation_reasons": ["evidence_token_budget"] if omitted else []}
        if audit is not None:
            audit["effective_memories"], audit["evidence_budget"] = delivered, budget
        generation = self.model.generate("answer", payload, EvidenceAnswer, context=context)
        answer = EvidenceAnswer.model_validate(generation.value.model_dump(mode="json"), context=context)
        budget["model_metadata"] = generation.metadata
        if raw_sources is not None:
            budget["omitted_source_ids"] = budget.pop("omitted_memory_ids")
        return answer.model_dump(mode="json"), raw_delivered if raw_sources is not None else delivered, budget

    def query(self, request):
        # Pin before analysis, embeddings or generation. Never re-read the active pointer.
        build_id = self.versions.pin(request.dataset_id, request.sample_id, request.build_id)
        started = time.perf_counter()
        trace = {"trace_id": uuid.uuid4().hex, "build_id": build_id, "dataset_id": request.dataset_id,
                 "sample_id": request.sample_id, "question": request.question, "started_at": utc_now(),
                 "outcome": "running", "config": self.settings.snapshot(), "operations": {}, "stage_seconds": {},
                 "prompts": {"resolve": RESOLUTION_PROMPT_VERSION, "answer": ANSWER_PROMPT_VERSION},
                 "schemas": {"resolve": RESOLUTION_SCHEMA_VERSION, "answer": ANSWER_SCHEMA_VERSION},
                 "known_service_version": KNOWN_MODEL_VERSION,
                 "query_fingerprint": hashlib.sha256(canonical_json({"settings": self.settings.snapshot(),
                     "resolve_prompt": RESOLUTION_PROMPT, "answer_prompt": ANSWER_PROMPT,
                     "resolve_schema": EffectiveResolution.model_json_schema(), "answer_schema": EvidenceAnswer.model_json_schema()}).encode()).hexdigest()}
        stage, tick = "retrieval", started
        try:
            with self.database.connect() as db:
                cutoff, cutoff_raw = conversation_cutoff(db, request.dataset_id, request.sample_id)
                projection = db.execute("SELECT fingerprint FROM current_state_projections WHERE build_id=?", (build_id,)).fetchone()
            requested = request.requested_date or explicit_question_date(request.question)
            origin = "explicit_request" if request.requested_date else "explicit_question" if requested else "conversation_cutoff"
            trace["time"] = {"requested_date": requested.isoformat() if requested else None, "anchor_date": (requested or cutoff.date()).isoformat(),
                             "origin": origin, "cutoff": cutoff.isoformat(), "cutoff_source_time": cutoff_raw,
                             "beyond_cutoff": bool(requested and requested > cutoff.date())}
            trace["projection_fingerprint"] = projection[0]
            tick = time.perf_counter()
            initial = self.retrieval.query(build_id, request.question)
            trace["initial"] = initial
            trace["index_fingerprint"] = initial["index_fingerprint"]
            trace["operations"]["query_analysis"] = initial["analysis"]["model_metadata"]
            trace["stage_seconds"][stage] = time.perf_counter() - tick
            stage, tick = "expansion", time.perf_counter()
            expanded = self.expansion.expand(initial["query_id"])
            trace["expanded"] = expanded
            trace["stage_seconds"][stage] = time.perf_counter() - tick
            memories = {item["memory"]["memory_id"]: item["memory"] for item in expanded["candidates"]}
            with self.database.connect() as db:
                sources = {}
                for memory in memories.values():
                    if (memory["build_id"], memory["dataset_id"], memory["sample_id"]) != (build_id, request.dataset_id, request.sample_id):
                        raise BuildError("invalid_query_scope", 422)
                    for sid in memory["source_ids"]:
                        source = db.execute("SELECT * FROM source_turns WHERE source_id=? AND dataset_id=? AND sample_id=?", (sid, request.dataset_id, request.sample_id)).fetchone()
                        if source is None:
                            raise BuildError("invalid_query_scope", 422)
                        sources[sid] = dict(source)
                relations = [json.loads(row[0]) for row in db.execute("SELECT relation_json FROM memory_relations WHERE build_id=? ORDER BY relation_id", (build_id,))]
            trace["relations"] = [r for r in relations if r["old_memory_id"] in memories and r["new_memory_id"] in memories]
            trace["relation_fingerprint"] = hashlib.sha256(canonical_json(trace["relations"]).encode()).hexdigest()
            stage, tick = "resolve", time.perf_counter()
            context = {"memories": memories, "sources": sources}
            payload = {"operation": "resolve", "question": request.question, "time": trace["time"], "analysis": initial["analysis"],
                       "memories": list(memories.values()), "sources": list(sources.values()), "relations": trace["relations"],
                       "candidates_truncated": initial["initial_truncated"] or expanded["truncated"]}
            generation = self.model.generate("resolve", payload, EffectiveResolution, context=context)
            trace["operations"][stage] = generation.metadata
            resolution = EffectiveResolution.model_validate(generation.value.model_dump(mode="json"), context=context)
            trace["resolution"] = resolution.model_dump(mode="json")
            trace["stage_seconds"][stage] = time.perf_counter() - tick
            selected = [memory for mid, memory in memories.items() if mid in resolution.effective_memory_ids]
            status = "insufficient" if trace["time"]["beyond_cutoff"] else resolution.status
            if trace["time"]["beyond_cutoff"]:
                trace["time"]["limitation"] = "Requested date exceeds known conversation evidence; plans do not establish future reality"
            stage, tick = "answer", time.perf_counter()
            answer, delivered, budget = self.generate_answer(request.question, trace["time"], selected, sources, status, audit=trace)
            trace["answer"], trace["effective_memories"], trace["evidence_budget"] = answer, delivered, budget
            trace["operations"][stage] = budget["model_metadata"]
            trace["stage_seconds"][stage] = time.perf_counter() - tick
            trace["outcome"] = "succeeded"
        except (ModelFailure, ValidationError, BuildError, EmbeddingFailure) as error:
            trace["stage_seconds"][stage] = time.perf_counter() - tick
            trace["outcome"] = "failed"
            trace["error"] = {"stage": stage, "code": error.code if hasattr(error, "code") else "invalid_output"}
            if isinstance(error, ModelFailure):
                trace["operations"][stage] = error.metadata
            trace["completed_at"], trace["elapsed_seconds"] = utc_now(), time.perf_counter() - started
            self._save(trace)
            raise QueryFailure(trace["error"]["code"], trace["trace_id"], getattr(error, "status", 502)) from None
        trace["completed_at"], trace["elapsed_seconds"] = utc_now(), time.perf_counter() - started
        self._save(trace)
        return trace
