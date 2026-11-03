"""Experimental five-arm queries; ordinary application routes retain their defaults."""
import hashlib
import json
import time
import uuid

from pydantic import ValidationError

from .builds import BuildError
from .imports import canonical_json
from .model import ModelFailure, utc_now
from .query_schemas import EffectiveResolution
from .resolution_delivery import complete_resolution_input, record_delivery
from .raw_retrieval import pinned_sources
from .temporal import conversation_cutoff, explicit_question_date, query_memory_times, TIME_AUTHORITY_VERSION

VERSION = "five-arm-paired-v2-complete-input-budget"
ARMS = {
    "A": dict(expand=False, resolve=False, stored_relations=False),
    "B": dict(expand=True, resolve=False, stored_relations=True),
    "C": dict(expand=False, resolve=True, stored_relations=True),
    "D": dict(expand=True, resolve=True, stored_relations=True),
    "E": dict(expand=True, resolve=True, stored_relations=False),
}


def digest(value):
    return hashlib.sha256(canonical_json(value).encode()).hexdigest()


class AblationService:
    def __init__(self, queries):
        self.queries = queries
        self.database = queries.database

    def prepare(self, request):
        """One paid analysis/retrieval, shared by all arms and repetitions."""
        q = self.queries
        bid = q.versions.pin(request.dataset_id, request.sample_id, request.build_id)
        sources, snapshot = pinned_sources(self.database, bid)
        with self.database.connect() as db:
            cutoff, raw_cutoff = conversation_cutoff(db, request.dataset_id, request.sample_id)
            relations = [json.loads(r[0]) for r in db.execute(
                "SELECT relation_json FROM memory_relations WHERE build_id=? ORDER BY relation_id", (bid,))]
        requested = request.requested_date or explicit_question_date(request.question)
        initial = q.retrieval.query(bid, request.question)
        pools = {
            "initial": q.expansion.expand(initial["query_id"], requested_date=requested,
                include_relations=False, include_state_history=False),
            "full": q.expansion.expand(initial["query_id"], requested_date=requested),
            "same_key": q.expansion.expand(initial["query_id"], requested_date=requested, include_relations=False),
        }
        union = {c["memory"]["memory_id"]: c["memory"] for p in pools.values() for c in p["candidates"]}
        source_map = {s["source_id"]: s for s in sources}
        normalized, diagnostics = query_memory_times(union, source_map)
        prepared = dict(version=VERSION, build_id=bid, dataset_id=request.dataset_id, sample_id=request.sample_id,
            question=request.question, initial=initial, pools=pools, relations=relations,
            memories=normalized, sources=source_map, snapshot=snapshot, time_diagnostics=diagnostics,
            time_authority_version=TIME_AUTHORITY_VERSION,
            time=dict(requested_date=requested.isoformat() if requested else None,
                anchor_date=(requested or cutoff.date()).isoformat(), cutoff=cutoff.isoformat(),
                cutoff_source_time=raw_cutoff, beyond_cutoff=bool(requested and requested > cutoff.date()),
                origin="explicit_request" if request.requested_date else "explicit_question" if requested else "conversation_cutoff"))
        prepared["fingerprint"] = digest(prepared)
        return prepared

    def execute(self, prepared, arm, repeat):
        if arm not in ARMS or repeat not in (1, 2, 3):
            raise ValueError("invalid_ablation_item")
        if prepared.get("version") != VERSION or digest({k: v for k, v in prepared.items() if k != "fingerprint"}) != prepared["fingerprint"]:
            raise BuildError("prepared_input_changed")
        q, controls = self.queries, ARMS[arm]
        q.versions.pin(prepared["dataset_id"], prepared["sample_id"], prepared["build_id"])
        _, current = pinned_sources(self.database, prepared["build_id"])
        if current != prepared["snapshot"]:
            raise BuildError("source_snapshot_changed")
        pool_name = "initial" if not controls["expand"] else "full" if controls["stored_relations"] else "same_key"
        pool = prepared["pools"][pool_name]
        memories = {c["memory"]["memory_id"]: prepared["memories"][c["memory"]["memory_id"]] for c in pool["candidates"]}
        sources = {sid: prepared["sources"][sid] for m in memories.values() for sid in m["source_ids"]}
        relations = [r for r in prepared["relations"] if controls["stored_relations"] and
            {r["old_memory_id"], r["new_memory_id"]} <= memories.keys()]
        trace = dict(trace_id=uuid.uuid4().hex, build_id=prepared["build_id"], dataset_id=prepared["dataset_id"],
            sample_id=prepared["sample_id"], question=prepared["question"], time=prepared["time"],
            ablation_version=VERSION, arm=arm, repeat=repeat, controls=controls, prepared_fingerprint=prepared["fingerprint"],
            initial=prepared["initial"], expanded=pool, operations={}, stage_seconds={}, outcome="running",
            started_at=utc_now(), config=q.settings.snapshot(), relations=relations, extra_raw_retrieval=False)
        started = tick = time.perf_counter()
        stage = "resolve" if controls["resolve"] else "answer"
        try:
            selected = list(memories.values())
            status = "sufficient" if selected else "insufficient"
            if controls["resolve"]:
                payload = dict(operation="resolve", question=prepared["question"], time=prepared["time"],
                    analysis=prepared["initial"]["analysis"], memories=selected, sources=list(sources.values()),
                    relations=relations, candidates_truncated=prepared["initial"]["initial_truncated"] or pool["truncated"])
                # Retain the actual safe business payload, not headers or credentials.
                trace["resolution_input"] = payload
                context, audit = complete_resolution_input(payload, q.settings)
                trace['resolution_budgets'] = {'resolve': audit}
                if not audit['within_budget']:
                    raise BuildError('complete_resolution_input_budget_exceeded', 422)
                try:
                    generation = q.model.generate("resolve", payload, EffectiveResolution, context=context)
                    trace["operations"][stage] = generation.metadata
                    result = EffectiveResolution.model_validate(generation.value.model_dump(mode="json"), context=context)
                    record_delivery(audit['source_delivery'], generation.metadata, accepted=True)
                except (ModelFailure, ValidationError) as error:
                    record_delivery(audit['source_delivery'], getattr(error, 'metadata', {}), accepted=False,
                                    error_code=getattr(error, 'code', 'invalid_output'))
                    raise
                trace["resolution"] = result.model_dump(mode="json")
                trace["resolution_selected_memory_ids"] = result.effective_memory_ids
                selected = [m for mid, m in memories.items() if mid in result.effective_memory_ids]
                status = result.status
                trace["stage_seconds"][stage] = time.perf_counter() - tick
            if prepared["time"]["beyond_cutoff"]:
                status = "insufficient"
            stage, tick = "answer", time.perf_counter()
            trace["answer_selected_memory_ids"] = [m["memory_id"] for m in selected]
            answer, delivered, budget = q.generate_answer(prepared["question"], prepared["time"], selected, sources, status,
                audit=trace, record_input=True)
            trace.update(answer=answer, effective_memories=delivered, evidence_budget=budget, outcome="succeeded")
            trace["operations"][stage] = budget["model_metadata"]
        except (ModelFailure, ValidationError, BuildError) as error:
            trace["outcome"] = "failed"
            trace["error"] = dict(stage=stage, code=getattr(error, "code", "invalid_output"))
            if isinstance(error, ModelFailure):
                trace["operations"][stage] = error.metadata
        trace["stage_seconds"][stage] = time.perf_counter() - tick
        trace.update(completed_at=utc_now(), elapsed_seconds=time.perf_counter() - started)
        q._save(trace)
        return trace
