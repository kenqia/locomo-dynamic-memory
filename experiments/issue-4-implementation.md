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
