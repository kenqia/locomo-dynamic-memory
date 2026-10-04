# Issue tracker: GitHub

Issues and specs for this repo live in GitHub Issues for `kenqia/locomo-dynamic-memory`. Use the `gh` CLI for issue operations. The local synchronization directory may not have a Git remote configured, so commands should target the repository explicitly when needed.

## Conventions

- **Create an issue**: `gh issue create --repo kenqia/locomo-dynamic-memory --title "..." --body "..."`. Use a heredoc for multi-line bodies.
- **Read an issue**: `gh issue view <number> --repo kenqia/locomo-dynamic-memory --comments`, filtering comments by `jq` and also fetching labels.
- **List issues**: `gh issue list --repo kenqia/locomo-dynamic-memory --state open --json number,title,body,labels,comments --jq '[.[] | {number, title, body, labels: [.labels[].name], comments: [.comments[].body]}]'` with appropriate `--label` and `--state` filters.
- **Comment on an issue**: `gh issue comment <number> --repo kenqia/locomo-dynamic-memory --body "..."`
- **Apply / remove labels**: `gh issue edit <number> --repo kenqia/locomo-dynamic-memory --add-label "..."` / `--remove-label "..."`
- **Close**: `gh issue close <number> --repo kenqia/locomo-dynamic-memory --comment "..."`

## Pull requests as a triage surface

**PRs as a request surface: no.**

When a skill says "publish to the issue tracker", create a GitHub issue. When it says "fetch the relevant ticket", run `gh issue view <number> --repo kenqia/locomo-dynamic-memory --comments`.
