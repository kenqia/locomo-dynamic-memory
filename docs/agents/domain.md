# Domain docs

This repository uses the single-context layout. Domain context lives at the repository root, with architecture decisions under `docs/adr/`.

## Before exploring

- Read `CONTEXT.md` at the repository root.
- Read the entries in `docs/adr/` that touch the area being explored or changed.
- If either location is missing, proceed without blocking the work. Create them only when the relevant domain terms or decisions have been resolved.

## Vocabulary

Use the glossary terms defined in `CONTEXT.md` when naming domain concepts in issues, specs, refactoring proposals, and tests. If the needed concept is missing, treat that as a domain-modeling gap instead of silently inventing a synonym.

## Conflicts

If a proposed change conflicts with an existing ADR, call out the conflict explicitly and explain whether the ADR should be reopened. Do not silently override the decision.
