# Frozen protocol: real Sidecar diagnostic study v1

This is exposed-development diagnostic/regression research, not unseen test or teacher scoring. Linked work: #24, #30–#33, PR #38. Preparation inspected aggregate adaptation only (503 claims, zero recognized); this is explicitly an exploratory follow-up on those same Builds.

## Question and falsifiable decision

Does the bounded deterministic Sidecar provide usable, source-supported event/time/state diagnostics on frozen real conversation Memory, compared with its existing supplied-fields-only control? Hypothesis H1: informative reference-matching diagnostic coverage reaches at least 10% of the 68 frozen units, without incorrect positive event links, exact dates or sufficient-state answers. H1 fails below that coverage or with any such severe false assertion. H2: off/on/off leaves responses and exports byte-identical; any mutation or escaped enabled failure rejects use. Zero unknown error is not accuracy: coverage and conditional correctness have separate denominators. If all outputs are unknown, H1 fails and conditional precision is undefined.

## Frozen inputs, sample and implementation

Use only validated MemoryExport v2 for conv-26 and conv-30, selected as the first two exposed development conversations, with different conversation size/history. Exact manifest, Build fingerprints, raw SHA and deterministic samples are in frozen-input-plan.json. SHA256 ranking seed/salt is sidecar-diagnostic-real-v1-20261107; no outcome-guided resampling.

Evaluate all 503 claims and every unordered pair in each full Build. max_event_pairs=50000 per Build is an explicitly recorded exhaustive research setting; the shipped default remains1000. Also report the default cap's omitted-pair count from preflight. Reference sample:20 Memory per Build (40),10 same-entity/state-dimension event pairs per Build (20), two fixed template questions for each of two deterministic existing speakers per Build (8). These questions are invented research probes, not official QA questions. No new QA/Answer/Resolve calls.

The comparison is existing baseline_fields versus repaired diagnostic_only Sidecar; neither changes production QA or constitutes a new QA score. Code must be committed and its SHA plus source hashes frozen before running the main study. Do not tune after viewing predictions. Correctness regressions are separate synthetic data and do not enter real denominators.

## Independent reference judgments

User explicitly authorized 68 session-internal non-author AI judgments with external Provider budget0. Use separate agents not involved in implementation, blind to diagnostic outputs, one per Build. One pass, no result-driven relabeling or extra model calls. Record actual agent identity. No human, double-review agreement or teacher truth claim.

Each reference unit must carry unit_id, kind, rationale and evidence source IDs. claim: source_support=supported/contradicted/unknown; time_status=known/range/unknown and ISO bounds when defensible; completion=supported/denied/unknown; attendance=supported/denied/unknown; note ambiguity and plans. pair: event_link=same_event/different_event/unknown using source evidence, not topic similarity. query: evidence_status=sufficient/conflict/insufficient/unknown; answer only if sources prove it; otherwise null. Missing/open-world evidence uses unknown, not a fabricated negative. Preserve all units even if malformed or failure. Review source text independently; do not treat extracted metadata or existing relation labels as truth.

## Execution and stopping

One primary enabled diagnostic pass and one supplied-fields pass per Build plus each of8 probes. Abort on any export SHA/schema/identity/time-anchor mismatch, unexpected external request, attempted SQLite open or source file mutation. Per-Build wall limit120s; reference68 units max; no paid calls or retries. Technical failures remain failures and in denominator. No successor sample. Stop rather than run paid QA while diagnostic_only cannot change answers.

Measure CPU process_time, wall perf_counter, peak RSS with Linux resource metadata, input bytes, output bytes, source/Memory/pair counts and truncation. RSS is process cumulative peak, not per-arm resource attribution. Cold import/validation separately reported; no cross-machine performance claim.

## Analysis and adoption

Report all planned/run/success/failure, known/range/unknown/refusal, recognized-source coverage, pair decisions and unsupported/qualified-time outputs. On68 judgments compare both arms with full denominator, definite errors, informative matches, unknown/abstention and unknown-on-answerable misses; conditional precision only when asserted. Include improved/degraded/unchanged units. Mixed diagnostic dimensions are not one accuracy. No inferential bootstrap needed for this small exploratory fixed slice; no conversation-level generalization.

Produce reproducible commands, public aggregate/hashes and controlled per-unit inputs/outputs/labels, error analysis, adoption decision and ADR recommendation. Distinguish research closure from final task acceptance, which still needs a genuine non-author team member, owner decision and required integration verification. Keep production default and historical SQLite unchanged.
