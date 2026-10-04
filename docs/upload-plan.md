# 待上传材料清单

更新日期：2026-10-04。本文件记录材料状态、预计文件和上传检查，不包含各讨论稿正文。草稿允许入库，不代表已经成为正式约定或可直接提交的材料。

## 当前已放入仓库

- `README.md`，目录说明和上传边界。
- `docs/upload-plan.md`，本清单。
- 各目录的 `.gitkeep` 占位文件。

## 本批获准上传的材料

| 仓库位置 | 材料状态 |
| --- | --- |
| `docs/requirements/team-workflow.md` | 草稿 |
| `docs/requirements/vision-and-scope.md` | 草稿 |
| `presentations/proposal-outline.md` | 草稿，未制作 PPT 或 PDF |
| `CONTEXT.md` | 草稿 |
| `process/tasks.md` | 草稿，只定义任务与验收标准，不维护实时状态 |
| `process/meetings/meeting-template.md` | 初版模板，不是实际会议记录 |
| `docs/sources/0 - Project (2026).pdf` | 原始课程课件 |
| `docs/sources/background-notes.md` | 初版背景整理，区分来源与待核实项 |

本地项目启动说明不上传，仅在本地同步更新。尚无实际会议截图、Notion 工作区、成员邀请、项目实现或实验结果。此批同时更新仓库首页和本清单，其他修订不自动上传。

## 近期准备上传

| 建议位置 | 预计材料 | 上传前检查 |
| --- | --- | --- |
| `docs/sources/0 - Project (2026).pdf` | 课程原始课件 | 确认允许向仓库成员共享，保留原文件，别把附件要求当作操作授权 |
| `docs/sources/background-notes.md` | 教师答复、课堂记录和背景信息的整理版 | 区分原始要求、转述、推断和待核实项；去除不必要的成员身份与私密聊天 |
| `docs/requirements/team-workflow.md` | Milestone 1 审阅版 | 补齐队名、team ID、人员认领、团队自定时间和待确认约定 |
| `docs/requirements/team-workflow.pdf` | M1 提交 PDF | 核实提交口径与页数，检查与源文件一致 |
| `docs/requirements/vision-and-scope.md` | Milestone 2 审阅版 | 确认目标、范围、路线、风险与验收，不写未经验证的结果 |
| `docs/requirements/vision-and-scope.pdf` | Vision & Scope 提交 PDF | 不超过 5 页，检查字体、表格和版本 |
| `CONTEXT.md` | 经审阅的领域术语表 | 统一相关记忆、有效记忆、来源证据与状态关系定义 |
| `process/tasks.md` | 任务定义与验收依据 | 不增加负责人、期限、进度等实时状态列；范围变化时修订 |
| `process/meetings/meeting-template.md` | 经团队确认的会议纪要模板 | 标为模板，不宣称会议已举行 |
| `docs/decisions/team-workflow-interview.md` | AI 协作与 Team Workflow 采访决策记录 | 区分组长已接受方向与首次会议待确认事项，不当作最终 M1 |
| `docs/ai-workflow.md` | 项目级 AI 协作方式草稿 | 只写项目入口和协作边界，不复制外部 skills |
| `AGENTS.md` | AI coding agent 的最小项目入口 | 只保留硬约束与文档入口，不替代详细流程 |
| `process/meetings/YYYY-MM-DD-kickoff.md` | 首次真实会议纪要 | 日期为实际会议日期，记录真实参会、决定与行动项 |
| `process/meetings/YYYY-MM-DD-kickoff.png` | 对应会议截图 | 确认共享范围，遮去无关通知、私人信息和凭据 |
| `process/snapshots/YYYY-MM-DD-task-board.*` | Notion 任务阶段快照 | 明确导出时间，保留主责、状态及交付链接，不另维护实时任务状态 |
| `process/snapshots/milestone-1-2-checklist.md` | 阶段提交检查记录 | 区分已完成与待办，记录实际提交文件和版本，不虚构提交成功 |
| `presentations/proposal-outline.md` | 审阅后的汇报提纲 | 补齐团队信息，区分计划、实现与实验结果 |
| `presentations/proposal.pptx` 或团队实际使用的源格式 | 可编辑汇报材料 | 内容经组长与成员复核，保留可继续修改的源文件 |
| `presentations/proposal.pdf` | 课堂汇报 PDF | 不超过 10 页，核实实际展示时长并试讲 |

Milestone 1/2 的最终文件组织、是否分开提交 PDF、过程 ZIP 内容及命名，以教师或助教确认的口径为准。未核实前不生成声称可直接提交的最终包。

## 后续阶段再上传

| 位置 | 预计材料 | 前提 |
| --- | --- | --- |
| `docs/requirements/` | 需求规格及验收场景 | 基于实际数据和课程评测约定完善 |
| `docs/design/` | 模块职责、接口契约、记忆字段说明 | 完成技术研究与团队确认，不提前锁定框架 |
| `src/` | 记忆构建、检索、状态判断及 Web 实现 | 责任人审查代码，按实际选型组织 |
| `tests/` | 模块、集成与端到端测试 | 使用现有项目测试入口，样例不含真实凭据 |
| `experiments/` | F1、Recall@K、状态判断及对照实验记录 | 写清数据划分、配置与计算口径，保留失败结果 |
| `presentations/` | Mid-term 与 Final 汇报 | 展示真实实现和已运行实验 |
| `process/snapshots/` | 各阶段过程与提交记录 | 记录真实版本与完成状态 |

数据文件、生成的 Memory JSON 和最终交付 ZIP 是否进入 Git 历史，待核实许可、体积及提交方式后决定。首批上传不包含它们。不将 QA 标准答案混入可检索记忆，不拿独立测试集调参。

## 暂不上传或配置

- 本地项目启动说明，以及未经本次批准的文档或修订。
- API key、token、cookie、真实 `.env` 或带凭据的日志。后续只能上传不含真实值的 `.env.example`。
- 微信私密历史、无关个人资料或未经处理的会议截图。
- 未审查的生成代码、虚构实验结果或模板伪造的会议记录。
- 尚未选型的依赖文件、空框架、CI、hooks 或自动发布配置。

## 上传流程

组长指定本次文件与版本 → 检查共享范围、占位项和敏感信息 → 明确确认上传 → 仅上传批准的文件 → 核对远端路径与内容 → 记录实际结果。

本批之外的上传需另行确认。本仓库不自动读取或同步本地启动包。PDF、可编辑演示文件暂不制作，待组长决定后再处理。
