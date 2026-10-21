# conv-26 relation failure diagnosis

2026-10-20. Read-only source inspection and public GET `/builds/91f1f50938064972820e3ab7b390d9dd/relation-tasks?limit=40`; no credential access, database access, new model calls or source changes.

No proven root cause. The request contains new Memory, same-entity bounded history and the union of their raw Source Turns. A valid response exists for every supplied pair: `undetermined` with both endpoint source references. There is no demonstrated unsatisfiable schema/payload combination.

Concrete prompt coverage gap: `model.py:55–57` requests reason and sources covering both endpoints only “For a determined judgment”; `relation_schemas.py:64–65` requires both endpoint references even for `undetermined`. This context-aware validator does not appear in the supplied JSON schema. The same-state-key RETAIN/CONFLICT constraint (`:66–67`) and fact→plan/uncertainty restrictions on RETAIN/UPDATE/CONFLICT (`:71–72`) are also more specific than the prompt. These gaps are hypotheses about possible invalid outputs, not evidence that the failed responses violated them.

Public observations: task ordinal 2, with one historical candidate, failed all three attempts as `invalid_output`; ordinal 33, with twenty historical candidates, succeeded on the first attempt. The evidence does not support history size alone as an explanation. Reported completion tokens below 4096 do not identify the rejected validation rule or prove a valid stop reason.

The retained metadata cannot distinguish malformed provider JSON, non-stop finish reason, malformed message, schema failure or semantic/context validation failure: `model.py:187–188` merges them into `invalid_output`. Failed response text and validation details are not retained. Consequently the exact cause cannot be reconstructed from current evidence without additional observation.

Keep this baseline identity and failures intact. A later independently versioned diagnostic improvement could retain only safe failure-stage identifiers and validator codes/field locations, without response content, input values or exception strings. No prompt, schema, output budget or parameter change is justified as a proven fix by the available evidence.
