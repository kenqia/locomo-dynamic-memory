## Agent skills

### Issue tracker

Issues and specs live in GitHub Issues for `kenqia/locomo-dynamic-memory`, using the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

Use the default labels `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, and `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

This is a single-context repo. Read the root `CONTEXT.md` and relevant `docs/adr/` entries before exploring or changing domain behavior. See `docs/agents/domain.md`.

### Repository-local skills

The workflow skills are bundled under `.agents/skills/`. Use `docs/agents/local-skills.md` for the supported commands, dependency
notes, and client setup.

## rules

### skills

使用`.agent/skills/to-spec`生成并且成功上传的specs，额外复制到`docs/specs/`内
使用`.agent/skills/to-tickets`生成并且成功上传的tickets，额外复制到`process/tickets/`内