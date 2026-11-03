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

### Local model credentials

For credential discovery or authorized live model calls, first read `docs/agents/local-credentials.md`.
A missing process variable does not establish that no local credential exists.

## rules

### skills

使用`.agents/skills/to-spec`生成并且成功上传的specs，额外复制到`docs/specs/`内
使用`.agents/skills/to-tickets`生成并且成功上传的tickets，额外复制到`process/tickets/`内

### Notion 任务更新

AI 在获授权创建、领取、送审、标记阻塞或验收任务时，同步更新已关联的 Notion 任务记录和 Issue/PR 链接；只有非作者复核通过且合并、验证完成后才标记“完成”。缺少关联、权限或更新失败时，明确报告未同步项，由负责人补录，不宣称已同步；不重复复制 spec、ticket 正文，也不持续后台运行。
