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
