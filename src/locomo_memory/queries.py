"""Pin one complete version, resolve bounded history, answer and retain an audit Trace."""

import json
import hashlib
import time
import uuid

from pydantic import ValidationError

from .builds import BuildError
from .embeddings import EmbeddingFailure
from .imports import canonical_json
from .model import ModelFailure, utc_now, RESOLUTION_PROMPT, ANSWER_PROMPT, KNOWN_MODEL_VERSION
from .query_schemas import EffectiveResolution, EvidenceAnswer, RESOLUTION_SCHEMA_VERSION, ANSWER_SCHEMA_VERSION
from .retrieval import budget_tokens, TOKEN_BUDGET_METHOD
from .temporal import conversation_cutoff, explicit_question_date
from .retry_feedback import VALIDATION_RETRY_FEEDBACK_VERSION
from .query_payload import QUERY_PAYLOAD_VERSION
from .resolution_delivery import complete_resolution_input, record_delivery, COMPLETE_INPUT_VERSION
from .usage import provider_usage

RESOLUTION_PROMPT_VERSION = "effective-resolution-v5-brief-decisions"
ANSWER_PROMPT_VERSION = "evidence-answer-v8-event-boundaries"
QUERY_EXECUTION_VERSION = "dynamic-complete-input-no-implicit-fallback-v2"
ANSWER_EVIDENCE_BUDGET_VERSION = "unique-source-payload-v2"


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
        trace["usage_summary"] = {"calls": len(calls), **provider_usage(calls)}
        with self.database.connect() as db:
            db.execute("INSERT INTO query_traces VALUES (?,?,?)", (trace["trace_id"], trace["build_id"], canonical_json(trace)))

    def generate_answer(self, question, time_condition, memories, sources, status, *, audit=None, raw_sources=None,
                        record_input=False):
        """Shared answer contract, with bounded RAG evidence or complete raw sources.

        Return the validated answer, delivered memories, and budget/provider metadata.
        The caller must supply memories and sources from one already pinned version.
        """
        delivered, used, omitted, delivered_sources = [], 0, [], {}
        for memory in memories:
            candidate_sources = {**delivered_sources, **{sid: sources[sid] for sid in memory["source_ids"]}}
            # Count the actual evidence object: atomic memories share source text.
            cost = budget_tokens(canonical_json({"memories": [*delivered, memory],
                                                 "sources": list(candidate_sources.values())}))
            if cost > self.settings.evidence_token_budget:
                omitted.append(memory["memory_id"])
                continue
            delivered.append(memory)
            delivered_sources, used = candidate_sources, cost
        raw_delivered = []
        if raw_sources is not None:
            for source in raw_sources:
                cost = budget_tokens(canonical_json(source))
                used += cost
                raw_delivered.append(source)
        conflict_truncated = raw_sources is None and status == "conflict" and bool(omitted)
        if conflict_truncated:
            # We cannot identify complete conflict sides from arbitrary surviving IDs.
            delivered, delivered_sources, used = [], {}, 0
            omitted = [memory["memory_id"] for memory in memories]
        effective_status = status if conflict_truncated else "insufficient" if not (delivered or raw_delivered) else status
        if raw_sources is not None:
            delivered_sources = {s["source_id"]: s for s in raw_delivered}
        context = {"status": effective_status, "memories": {m["memory_id"]: m for m in delivered}}
        if raw_sources is not None:
            context["raw_sources"] = delivered_sources
        payload = {"operation": "answer", "question": question, "time": time_condition, "status": effective_status,
                   "memories": delivered, "sources": list(delivered_sources.values()), "evidence_truncated": bool(omitted)}
        budget = {"token_count": used, "budget": None if raw_sources is not None else self.settings.evidence_token_budget,
                  "algorithm_version": ANSWER_EVIDENCE_BUDGET_VERSION,
                  "scope": "complete_raw_sources" if raw_sources is not None else "rag_evidence",
                  "token_budget_method": TOKEN_BUDGET_METHOD, "truncated": bool(omitted),
                  "omitted_memory_ids": omitted, "truncation_reasons": ["evidence_token_budget"] if omitted else []}
        if raw_sources is not None:
            budget["omitted_source_ids"] = budget.pop("omitted_memory_ids")
        if audit is not None:
            if record_input:
                audit["answer_input"] = payload
            audit["effective_memories"], audit["evidence_budget"] = delivered, budget
            if raw_sources is not None:
                audit["answer_context_sources"] = raw_delivered
                audit["source_delivery"] = {"expected_source_ids": [s["source_id"] for s in raw_sources],
                    "delivered_source_ids": [], "attempted_source_ids": [],
                    "status": "not_sent", "provider_accepted": None}
        if conflict_truncated:
            budget["failure_reason"] = "conflict_evidence_budget_exceeded"
            budget["model_metadata"] = {"calls": []}
            raise ModelFailure("conflict_evidence_budget_exceeded", {"calls": []})
        try:
            generation = self.model.generate("answer", payload, EvidenceAnswer, context=context)
        except ModelFailure as error:
            budget["model_metadata"] = error.metadata
            if audit is not None and raw_sources is not None and error.metadata.get("calls"):
                response_received = any(call.get("response_received") for call in error.metadata["calls"])
                audit["source_delivery"].update(attempted_source_ids=list(delivered_sources),
                    delivered_source_ids=list(delivered_sources) if response_received else [],
                    status="request_attempted", provider_accepted=False if error.code == "context_length_exceeded" else None)
            if error.code == "context_length_exceeded":
                budget["context_limit_exceeded"] = True
            raise
        if audit is not None and raw_sources is not None:
            audit["source_delivery"].update(attempted_source_ids=list(delivered_sources),
                delivered_source_ids=list(delivered_sources), status="accepted", provider_accepted=True)
        answer = EvidenceAnswer.model_validate(generation.value.model_dump(mode="json"), context=context)
        budget["model_metadata"] = generation.metadata
        return answer.model_dump(mode="json"), raw_delivered if raw_sources is not None else delivered, budget

    def query(self, request, *, research_router=None):
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
                     "query_execution_version": QUERY_EXECUTION_VERSION,
                     "answer_evidence_budget_version": ANSWER_EVIDENCE_BUDGET_VERSION,
                     "validation_retry_feedback_version": VALIDATION_RETRY_FEEDBACK_VERSION,
                     "query_payload_version": QUERY_PAYLOAD_VERSION,
                     "complete_resolution_input_version": COMPLETE_INPUT_VERSION,
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
            expanded = self.expansion.expand(initial["query_id"], requested_date=requested)
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
            from .temporal import query_memory_times, TIME_AUTHORITY_VERSION
            memories, trace["time_diagnostics"] = query_memory_times(memories, sources)
            trace["time_authority_version"] = TIME_AUTHORITY_VERSION
            trace["query_fingerprint"] = hashlib.sha256(canonical_json({
                "fingerprint":trace["query_fingerprint"], "time_authority":TIME_AUTHORITY_VERSION}).encode()).hexdigest()
            trace["relations"] = [r for r in relations
                if ({r["old_memory_id"], r["new_memory_id"]} & memories.keys()
                    if request.strategy == "dynamic_raw_fallback" else
                    {r["old_memory_id"], r["new_memory_id"]} <= memories.keys())]
            trace["relation_fingerprint"] = hashlib.sha256(canonical_json(trace["relations"]).encode()).hexdigest()
            if request.strategy == "dynamic_raw_fallback":
                from .raw_queries import run_raw_query
                from .raw_retrieval import pinned_sources
                snapshot = pinned_sources(self.database, build_id)
                stage, tick = "resolve", time.perf_counter()
                run_raw_query(self,request,trace,memories,sources,snapshot)
            else:
                stage, tick = "resolve", time.perf_counter()
                payload = {"operation": "resolve", "question": request.question, "time": trace["time"], "analysis": initial["analysis"],
                           "memories": list(memories.values()), "sources": list(sources.values()), "relations": trace["relations"],
                           "candidates_truncated": initial["initial_truncated"] or expanded["truncated"]}
                context, audit = complete_resolution_input(payload, self.settings)
                delivery = audit['source_delivery']
                trace.setdefault('resolution_budgets', {})['resolve'] = audit
                decision = None
                if research_router is not None:
                    # Research injection only; API/UI never supplies this object.
                    # Initial observations and Build-time relations are available
                    # before Resolution. Exact preflight is local, not free.
                    decision = research_router.route(question=request.question, initial=initial, sources=sources,
                        relations=relations, time_condition=trace['time'], complete_budget={
                            key: audit[key] for key in ('input_token_count','input_budget','within_budget')})
                    trace['research_routing'] = decision.to_dict()
                    trace['research_routing']['preflight_scope'] = 'complete_expanded_packet_before_resolution_http'
                    trace['query_fingerprint'] = hashlib.sha256(canonical_json({
                        'base':trace['query_fingerprint'], 'router_version':decision.router_version,
                        'threshold':decision.observed_features['coverage_threshold']}).encode()).hexdigest()
                if decision is not None and decision.path == 'hybrid':
                    # Match the research Hybrid baseline: same expansion and
                    # answer budget/validator, skip only paid Resolution.
                    selected = [c['memory'] for c in expanded['candidates']]
                    status = 'insufficient' if trace['time']['beyond_cutoff'] or not selected else 'sufficient'
                    trace['resolution'] = {'status':'not_applied', 'reason':'opt_in_e1_hybrid'}
                else:
                    if not audit['within_budget']:
                        raise BuildError('complete_resolution_input_budget_exceeded', 422)
                    try:
                        generation = self.model.generate("resolve", payload, EffectiveResolution, context=context)
                        trace["operations"][stage] = generation.metadata
                        resolution = EffectiveResolution.model_validate(generation.value.model_dump(mode="json"), context=context)
                        record_delivery(delivery, generation.metadata, accepted=True)
                    except (ModelFailure, ValidationError) as error:
                        record_delivery(delivery, getattr(error, 'metadata', trace['operations'].get(stage, {})), accepted=False,
                                        error_code=getattr(error, 'code', 'invalid_output'))
                        raise
                    trace["resolution"] = resolution.model_dump(mode="json")
                    selected = [memory for mid, memory in memories.items() if mid in resolution.effective_memory_ids]
                    status = "insufficient" if trace["time"]["beyond_cutoff"] else resolution.status
                trace["stage_seconds"][stage] = time.perf_counter() - tick
                if trace["time"]["beyond_cutoff"]:
                    trace["time"]["limitation"] = "Requested date exceeds known conversation evidence; plans do not establish future reality"
                stage, tick = "answer", time.perf_counter()
                answer_time = ({key:value for key,value in trace['time'].items() if key != 'origin'}
                               if decision is not None and decision.path == 'hybrid' else trace['time'])
                answer, delivered, budget = self.generate_answer(request.question, answer_time, selected, sources, status, audit=trace)
                trace["answer"], trace["effective_memories"], trace["evidence_budget"] = answer, delivered, budget
                trace["operations"][stage] = budget["model_metadata"]
                trace["stage_seconds"][stage] = time.perf_counter() - tick
            trace["outcome"] = "succeeded"
        except (ModelFailure, ValidationError, BuildError, EmbeddingFailure) as error:
            stage = trace.pop("_active_stage", stage)
            stage_started = trace.pop("_stage_started", tick)
            trace["stage_seconds"][stage] = time.perf_counter() - stage_started
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
