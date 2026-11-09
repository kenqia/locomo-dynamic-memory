"""Public Hybrid adapter reusing the frozen evaluation baseline implementation."""

import hashlib
import time
import uuid

from .evaluation import EvaluationFailure
from .imports import canonical_json
from .model import utc_now
from .queries import QueryFailure


def hybrid_query(evaluation, request):
    service = evaluation.queries
    build_id = service.versions.pin(request.dataset_id, request.sample_id, request.build_id)
    request = request.model_copy(update={"build_id": build_id})
    started = time.perf_counter()
    trace = {
        "trace_id": uuid.uuid4().hex,
        "build_id": build_id,
        "dataset_id": request.dataset_id,
        "sample_id": request.sample_id,
        "question": request.question,
        "strategy": "hybrid_no_resolution",
        "started_at": utc_now(),
        "config": service.settings.snapshot(),
        "query_fingerprint": hashlib.sha256(canonical_json({
            "adapter": "release-hybrid-v1", "request": request.model_dump(mode="json"),
            "settings": service.settings.snapshot(),
        }).encode()).hexdigest(),
        "effective_memories": [],
        "resolution": {"status": "not_applied", "explanation": "Hybrid does not assert query-specific validity."},
    }
    failure = None
    try:
        result = evaluation.baseline(request, "hybrid_no_resolution")
    except EvaluationFailure as error:
        result = error.trace
        failure = error
    trace.update(result)
    trace["initial"] = result.get("retrieval", {})
    trace["expanded"] = result.get("expansion", {})
    trace["answer_context_items"] = result.get("answer_context_items", result.get("delivered_memories", []))
    trace["effective_memories"] = []
    trace["completed_at"] = utc_now()
    trace["elapsed_seconds"] = time.perf_counter() - started
    if failure:
        trace["error"] = {"code": failure.code, "stage": "hybrid_baseline"}
    service._save(trace)
    if failure:
        raise QueryFailure(failure.code, trace["trace_id"], failure.status)
    return trace
