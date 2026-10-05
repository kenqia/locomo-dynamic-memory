# locomo-dynamic-memory

软件需求工程课程项目仓库。

## 目录

| 目录 | 预计内容 |
| --- | --- |
| `docs/sources/` | 经确认可共享的课程原始材料、来源说明 |
| `docs/requirements/` | 审阅后的 Team Workflow、Vision & Scope，后续需求规格 |
| `docs/specs/` | skills 生成并成功发布到 GitHub Issues 的 spec 正文副本 |
| `docs/design/` | 后续模块设计、接口约定、数据结构和实现方案 |
| `docs/decisions/` | 团队协作、工作流程和项目范围等决定的背景、理由及待确认项 |
| `docs/agents/` | Agent 的项目约定，包括 Issue tracker、标签、领域文档和本地 skills 使用说明 |
| `.agents/` | 仓库内置的 Agent 资源；`skills/` 保存 workflow skills 及其依赖 |
| `process/tickets/` | skills 生成并成功发布到 GitHub Issues 的 ticket 正文副本，每个 ticket 单独保存 |
| `process/meetings/` | 会议纪要模板、真实会议记录及经检查的截图 |
| `process/snapshots/` | Notion 阶段任务快照、阶段复盘和提交记录 |
| `presentations/` | 审阅后的汇报源文件与导出 PDF |
| `src/` | 后续项目源代码 |
| `tests/` | 后续测试代码与不含敏感信息的样例 |
| `experiments/` | 后续评测说明、运行配置记录和实验结果 |

`docs/decisions/` 记录为什么作出某项决定，`docs/design/` 说明具体如何设计。两者可以通过链接关联，同一份决策正文只保留在一个位置。架构与领域决策按现有 Agent 约定存入 `docs/adr/`，在首次需要时创建。

空目录用 `.gitkeep` 保留。spec 和 ticket 正文副本原样复制，不做润色。

## 材料

预计材料见 `docs/upload-plan.md`。

- Notion 保存实时任务状态；仓库只保存注明导出时间的阶段快照。

## M1 Team Workflow

- [Markdown 源稿](docs/requirements/team-workflow.md)
- [可编辑 Word](docs/requirements/team-workflow.docx)
- [PDF](docs/requirements/team-workflow.pdf)
