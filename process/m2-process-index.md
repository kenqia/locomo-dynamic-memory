# M2 过程材料说明

团队：在阴雨天游泳，Team ID 3。整理日期：2026-10-06。

本包保存提案从初稿到本地制作稿的过程。报告正文独立提供，过程材料不计入报告 5 页。方案经组长确认全组接受，本轮文件仍待成员按清单复核；材料制作不代表任务已完成或已正式提交。

解压后进入 `PROJECT-MILESTONE2-3-在阴雨天游泳/`，打开 `process/m2/index.html`。可离线查看过程说明、图示、会议 PDF 与截图。报告 Word/PDF 单独交付，过程包保留当前报告 Markdown 作为迭代依据。

与组长提供的 M1 过程包一样，材料先存入仓库，再整合成 ZIP。包内保留仓库相对路径与原始内容，不在打包时改名、改正文或新增只存在于 ZIP 内的文件。阅读页、文件清单和校验值也先写入 `process/m2/`；脚本逐项检查 ZIP 与仓库文件相同。

| 包内目录 | 材料与作用 |
| --- | --- |
| `docs/requirements/` 与 `process/m2/iterations/` | 当前报告 Markdown、修改前初稿和修订说明；当前报告 Word/PDF 独立提供 |
| `docs/sources/m2-real-world-memory-research.md` | 联网调研、一手来源、方法依据及评测边界；调研前报告保存在迭代目录 |
| `docs/decisions/`、`CONTEXT.md`、`docs/requirements/assets/m2/` | 方案确认、术语和两张简化图的 PNG 与 SVG；制作与打包脚本位于 `scripts/` |
| `process/m2/reference-images/` | 本次附件中的四张参考架构图，不冒充实现截图 |
| `process/meetings/` 与 `docs/requirements/team-workflow.md` | 首次会议纪要的 Markdown、Word、PDF、原截图与共用团队流程，保留当时结论 |
| `process/snapshots/` 与 `process/m2/m2-tasks-historical-20261006.csv` | 原有历史快照的 Markdown、Word、PDF 与 M2 筛选 CSV，保留导出时间和状态 |
| `process/m2/source-notes.md`、`review-checklist.md`、`validation-record.md` | 来源依据、待成员复核清单、实际文档与打包检查 |
| `process/m2/version-record.md`、`git-history-baseline.txt`、`file-manifest.csv`、`file-sha256sums.txt` | 制作基准、版本说明、文件清单与校验值 |

## 本次确定的方案

记录采用结构化 Memory，保留人物、时间、来源和历史，维护状态关系及 Current State。查询先进行 LLM 辅助 Query Analysis，保留原始问题参与 BM25 与 Vector，结构化信号增强候选；再结合问题时间与状态关系选择有效证据。当前问题与历史问题可以采用不同 Memory；无法消解的冲突展示来源与不确定性。大模型辅助抽取和语义理解，规则核查可明确的字段、来源与时间。

M2 说明方法、流程、范围、可行性、功能路线与评测计划。数据库、接口、Prompt 和代码细节不在本轮锁定。Graph Memory 与多跳等扩展仍是候选。

## 本次制作与过程边界

本次整理真实已有会议材料和历史任务快照，并记录组长在本次讨论中的确认。没有补造新会议、成员贡献、复核签字、系统截图或实验结果。原有 M1 全员核对记录不能证明当前 M2 文件已经通过复核，因此不作为本轮 M2 验收证明。

原 Notion 截图含无关侧栏，本包以原导出数据及时间说明为任务证据。私人聊天、凭据和无关文件不进入包内。参考图片属于方案素材，不是可运行系统。

本轮只制作报告与过程包，不制作汇报文件。课程要求的汇报 PDF 与试讲保留为后续工作。实际展示场次、收件渠道与最终命名须核对最新通知。

## 尚未完成的外部工作

本轮已更新并重新读取 Notion，P01–P06 为待复核，验收未通过。成员非作者复核、合并与推送、正式提交和回执仍未完成。Issue/PR 尚未建立，本地文件尚无新远端交付链接，不编造链接或完成状态。

在线入口为私有仓库 `kenqia/locomo-dynamic-memory` 和团队既有 Notion 任务表；访问仍需授权。包内已有离线副本，阅读不依赖助教拥有线上权限。

## 审核后的同步材料

最新任务状态见 process/snapshots/2026-10-06-review-sync.md 与同名 CSV；更新及回读记录见 process/m2/notion-review-sync.json，更新前属性副本见 notion-before-review-sync.json。两份历史 CSV 保持原字节。旧快照的时间戳与会议后注记已分开说明，不作为同一时点证据。

成员实际检查范围与反馈登记见 process/m2/member-review-record.md，尚待填写。包内机器检查结果见 process/m2/package-check.json。当前文件总数以该结果为准；旧的 33、34、36、39 均指当时的阶段包。
