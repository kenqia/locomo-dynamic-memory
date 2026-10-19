# Issue #4 implementation record

Implementation started on 2026-10-19. Integration branch:
`codex/issue-4-integration`. Starting application baseline: `53f116e`.

## Scope and verification boundary

The specification is `docs/specs/issue-4-m3-m4-dynamic-memory.md`.
The unmodified ticket copies are under `process/tickets/`.
Remote issue snapshots, including comments, were read before implementation.

The dependency graph is #5 → #6 → #7 → #8; #9 and #10 follow #8;
#11 follows #9; #12 follows #10 and #11.
Each implementation ticket uses its own local branch and worktree, based on
the integration branch. Local merges consolidate the deliverable.

Automated acceptance uses FastAPI public APIs with real SQLite, BM25,
NumPy ranking, history expansion and version isolation. Only the generation
and embedding boundaries use controlled adapters. Protocol tests can exercise
the model adapter with a controlled HTTP transport. These tests do not establish
real model quality.

Browser checks and real model checks have separate results. Live generation
requires protected credentials; no credentials are read or displayed in this
record. Official LoCoMo data is used for import/provenance checks, not strategy
tuning or a fabricated course development/test split.

## External completion conditions

- Course-selected six conversation IDs, the 4/2 split, dynamic labels and final
  metric definitions have not been supplied. Formal course metrics remain unrun.
- The specification identifies no linked M3/M4 Notion task. Status updates cannot
  be synchronized until a record is linked; M1/M2 records are not substitutes.
- Remote writes require explicit authorization. Local implementation and review
  do not close GitHub tickets, publish a PR or establish human acceptance.
- Non-author team review, merge verification and course submission remain
  separate from agent tests and code review.

## Results

Results are recorded below as each ticket is integrated. Pending work is not
reported as passing.

### Initial checks

- The local parent specification and all eight ticket bodies match the GitHub
  issue bodies, ignoring only trailing whitespace. All nine issues were open
  and had no comments when read.
- All five upstream file hashes match `data/raw/locomo/provenance.json`.
- Only the presence of the `DEEPSEEK_API_KEY` environment variable was checked.
  It was absent. No real DeepSeek request was made during these checks.
- The existing MiniLM snapshot directory has revision
  `c9745ed1d9f207416be6d2e6f8de32d1f16199bf`. Its presence is not a load or
  encoding result.

### Issue #5: import and source browsing

Integrated with merge commit `3a1f697`. See
`experiments/issue-5-import-validation.md` for the ticket's test record.
The integration directory reran `tests/test_imports.py` against its source:
11 passed, with one upstream Starlette/HTTPX deprecation warning.

An isolated Chromium smoke test started separate FastAPI and Streamlit
processes using a temporary SQLite database. Clicking the official import
button displayed 10 conversations and 5,882 turns. The source locator requested
`D1:1` successfully through FastAPI. No browser page exceptions were captured.
The first run exposed official orphan session timestamps; the validator was
corrected and the same scenario passed on rerun. This does not verify the
downstream build, query or evaluation pages.

### Issue #6: atomic memory construction

Integrated with merge commit `c754a28`. `uv sync --locked` passed in the
integration directory, followed by `uv run pytest -q --tb=short`:
27 passed, 1 opt-in live model test skipped, 1 upstream deprecation warning.
See `experiments/issue-6-extraction-validation.md` for protocol, provenance,
retry and partial-build cases. This ticket's page was not separately exercised
in a browser; cumulative browser verification remains part of #12.
No real DeepSeek call was made.

### Issue #7: hybrid candidate inspection

Integrated with merge commit `dc3e9c5`. Default integration installation and
tests passed: `uv sync --locked`, then `uv run pytest -q --tb=short` produced
39 passed, 3 opt-in checks skipped, 1 upstream deprecation warning.
The default installation did not install Torch. In the ticket worktree,
`LOCOMO_LOCAL_EMBEDDING=1 HF_HUB_OFFLINE=1 uv run --extra embedding --locked
pytest tests/test_local_embedding.py -q` passed both real MiniLM checks.
These exercised the actual application adapter and actual SQLite/BM25/dense/RRF
API path, with only the generation HTTP response controlled. Enriched input
over the tokenizer limit was rejected even when its plain content fit.
See `experiments/issue-7-retrieval-validation.md`.

### Issue #8: relations, projection and bounded expansion

Integrated with merge commit `81d2ecf`. Fresh integration commands
`uv sync --locked` and `uv run pytest -q --tb=short` passed:
62 passed, 3 opt-in checks skipped, 1 upstream deprecation warning.
Tests include dated supersession with history retained, conservative unknown/
future/conditional applicability, conflicts and compatible claims, source safety,
durable relation retry, actual retrieval omission recovery and an unextracted
counterexample, one-hop/original-seed expansion, configurable budgets and version
publication gates. See `experiments/issue-8-relations-validation.md`.
No separate browser or paid model check was executed for this ticket.

### Issues #9 and #10: answering, recovery and export

Question answering was integrated with merge commit `59f7102`:
70 passed, 3 opt-in checks skipped in fresh default tests.
Recovery and export were then integrated with merge commit `5dfca1b`:
`uv sync --locked` and `uv run pytest -q --tb=short` passed with
83 passed, 4 opt-in checks skipped and the same upstream warning.

See `experiments/issue-9-query-validation.md` and
`experiments/issue-10-version-validation.md`. Cases include current/history
interleaving without global writes, strict reference validation, failure Trace,
future/insufficient/conflict handling, immutable complete-version queries,
three-phase process interruption and idempotent recovery, concurrent publication,
old encoder identity selection and schema-validated coherent JSON export.
Browser and paid model checks were not part of these ticket runs.

The integration directory then installed the locked optional CPU embedding
dependencies and ran:

```sh
uv sync --locked --extra embedding
LOCOMO_LOCAL_EMBEDDING=1 HF_HUB_OFFLINE=1 uv run --extra embedding --locked pytest -m local_embedding -q --tb=short
```

Result: **3 passed, 84 deselected**, with the same upstream warning. These
real-model checks include the application adapter, enriched-text/query length
rejection, actual index/candidate APIs, and querying an old complete version
after restarting with an unavailable current revision. The latter loads the
stored cached encoder identity. Generation responses remain controlled; no
DeepSeek call was made. This result applies to the integrated #10 code, before
the later evaluation and browser changes.

### Issue #11: scoring and baselines

Integrated with merge commit `a7830ca`. The resulting tracked tree exactly
matched tested ticket `c524a78`. The ticket's fresh full run produced
90 passed, 4 opt-in checks skipped. Integration installation, the seven
evaluation API tests, `git diff --check` and `compileall` also passed.
The full run was not redundantly repeated on the identical tree.

The ticket compared 80 scoring cases with the retained upstream functions and
reconciled all official QA source mappings without tuning retrieval. A real
local Uvicorn/SQLite + Streamlit AppTest HTTP check ran all four strategies,
comparison display and persisted-result reading. This is not browser or model
quality verification. NLTK supplies Porter stemming without corpus downloads.
See `experiments/issue-11-evaluation-validation.md`.

### Real MiniLM preflight

An independent Python 3.12 environment loaded the existing pinned snapshot
offline on CPU with `trust_remote_code=False` and `token=False`.
Versions were Torch `2.14.1+cpu`, sentence-transformers `6.1.0`, transformers
`5.20.1`, NumPy `2.5.4`. Two short English sentences encoded to shape
`(2, 384)`, all finite, with normalized vector lengths `1.0`.
The tokenizer measured a synthetic long input at 302 tokens against
`max_seq_length=256`; that input was not encoded. This preflight establishes
model availability and dimensionality, not the application's overlength
rejection policy, retrieval quality or answer quality.

### Official evidence mapping preflight

A read-only structural check of all 1,986 supplied QA records found 1,977
samples with reliably resolvable evidence, 4 with missing/empty evidence and
5 with unmappable evidence. Four samples use valid composite evidence
elements, split only at whitespace or semicolons and validated individually.
The five unresolved elements match the retained provenance positions:
`conv-42/58`, `conv-42/88`, `conv-43/18`, `conv-47/38`, `conv-50/69`, using
zero-based QA positions. Original IDs and source files were not modified.
This check is source mapping coverage, not retrieval Recall or course scoring.

### Implementation references

The official [FastAPI testing guide](https://fastapi.tiangolo.com/tutorial/testing/)
supports the agreed TestClient/HTTPX and pytest boundary. Pydantic validation
uses the [model contracts](https://docs.pydantic.dev/latest/concepts/models/).
The [DeepSeek thinking guide](https://api-docs.deepseek.com/guides/thinking_mode/)
and [JSON guide](https://api-docs.deepseek.com/guides/json_mode/) govern the
explicit request settings and validation. The
[MiniLM model card](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2)
and [pinned revision metadata](https://huggingface.co/api/models/sentence-transformers/all-MiniLM-L6-v2/revision/c9745ed1d9f207416be6d2e6f8de32d1f16199bf)
provide model identity and length constraints. QA scoring follows the retained
upstream evaluator at commit `3eb6f2c585f5e1699204e3c3bdf7adc5c28cb376`, with
explicit unavailable-evidence handling required by this project's spec.
