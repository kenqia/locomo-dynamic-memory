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

## M2 项目提案

本轮制作中文报告和过程材料，暂不制作汇报文件。宏观方案由组长确认全组接受；当前文件属于本地制作版本，成员非作者复核、远端同步与正式提交按真实进度另行完成。

- [Markdown 源稿](docs/requirements/vision-and-scope.md)
- [可编辑 Word](docs/requirements/vision-and-scope.docx)
- [报告 PDF](docs/requirements/vision-and-scope.pdf)
- [方案确认记录](docs/decisions/m2-proposal-interview.md)
- [过程材料说明](process/m2-process-index.md)
- [过程材料离线阅读页](process/m2/index.html)
- [仓库与 ZIP 文件清单](process/m2/file-manifest.csv)
- [本地制作与打包验证](process/m2/validation-record.md)
- [报告与图示制作脚本](scripts/build_m2_report.py)

报告内两张简化图的 PNG 与可编辑 SVG 位于 `docs/requirements/assets/m2/`。过程材料、阅读页、文件清单与校验值全部在仓库留档，再通过 `python scripts/package_m2_materials.py` 整合为 ZIP；包内保留仓库路径和原始内容。报告 Word/PDF 独立提供，交付文件存放于 `deliverables/m2/`。

修改源稿后可运行 `python scripts/build_m2_report.py` 重建 Word 和图示，所需环境及 PDF 渲染方式见验证记录。当前分支 `codex/m2-proposal-materials` 用于本轮留档，正式合并、推送和提交仍按复核及授权执行。
