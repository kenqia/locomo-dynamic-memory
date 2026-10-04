# Project instructions

这是软件需求工程课程项目。开始工作前阅读 `CONTEXT.md`、相关 spec、对应 ticket 和 `docs/ai-workflow.md`。

## 硬约束

- 先理解需求，再修改文件或生成代码。需求不清时先提出问题。
- 交付必须对应 ticket 的验收标准，并记录验证结果。
- 不提交 API key、token、cookie、真实 `.env`、私密聊天或含凭据的日志。
- 不把课程 QA 标准答案当作可检索记忆，不用独立测试集调参。
- 未经团队确认，不改变项目范围、公共接口、数据格式、验收标准或里程碑提交版本。
- 仓库内置的 workflow skills 位于 `.agents/skills/`；使用前遵循各 skill 的当前说明。

## 入口

- 术语：`CONTEXT.md`
- AI 协作草稿：`docs/ai-workflow.md`
- 需求与范围：`docs/requirements/`
- spec：`docs/specs/`
- tickets：`process/tickets/`
- 实时任务状态：Notion 项目页

## Agent skills

### Issue tracker

Issues and specs live in GitHub Issues for `kenqia/locomo-dynamic-memory`, using the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

Use the default labels `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, and `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

This is a single-context repo. Read the root `CONTEXT.md` and relevant `docs/adr/` entries before exploring or changing domain behavior. See `docs/agents/domain.md`.

### Repository-local skills

The workflow skills are bundled under `.agents/skills/`. Use `docs/agents/local-skills.md` for the supported commands, dependency notes, and client setup.
