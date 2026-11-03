# Repository-local skills

This repository carries a small copy of the team's workflow skills so members can use the same process without manually copying the files into their personal skill directory.

## Main commands

- `/grill-with-docs` sharpens a plan and records resolved domain terms and decisions.
- `/to-spec` turns the agreed conversation into a spec and publishes it to the configured GitHub issue tracker.
- `/to-tickets` turns a spec into independent tracer-bullet tickets and publishes them to the configured tracker.
- `/implement` implements approved work from a spec or tickets, then invokes code review.
- `/code-review` reviews a diff against repository standards and the originating spec.

## Bundled dependencies

The main commands are bundled with the small set of skills they call directly:

- `grilling`
- `domain-modeling`
- `tdd`
- `setup-matt-pocock-skills`

The repository also contains `docs/agents/issue-tracker.md`, `docs/agents/triage-labels.md`, and `docs/agents/domain.md`, which configure the tracker, labels, and domain-document rules consumed by these skills.

## Client setup

The canonical bundle path is `.agents/skills/`. Clients that support repository-local Agent Skills can discover the skills from that directory. A client that only scans a user-level directory must be configured to include this repository's `.agents/skills/` directory or use its own project-skill import mechanism.

The skill files do not install CLIs, authenticate GitHub, or create labels. To publish specs and tickets, each contributor still needs the `gh` CLI and access to `kenqia/locomo-dynamic-memory`.

## Updating and rollback

Treat the bundled copies as project files. Update them deliberately when the team agrees to a workflow change. To roll back this addition, remove `.agents/skills/` and this file, then remove the `Repository-local skills` subsection from `AGENTS.md`.
