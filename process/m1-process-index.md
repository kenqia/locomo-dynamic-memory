# M1过程材料说明

团队：在阴雨天游泳，Team ID 3。首次整理日期：2026-10-06；本轮更新日期：2026-10-08。

本包保存首次线上会议、工具访问、任务快照、成员反馈和文档版本记录。当前M1报告PDF为4页，Word/PDF独立交付，过程材料不计入报告不超过5页的限制。包内历史证据保留原记录日期，不代表本轮已重新取得成员确认。

| 材料 | 包内分类文件夹 | 仓库来源与作用 |
| --- | --- | --- |
| 首次会议 | 首次会议/ | process/meetings/first-meeting.md及同名PDF；first-meeting-participants.png原始会议画面显示四位成员参会 |
| 仓库与成员访问 | 仓库与成员访问/ | process/access/m1-access.md及screenshots/中的三张GitHub截图；说明私有仓库与成员权限 |
| 任务快照 | 任务快照/ | process/snapshots/2026-10-06-m1-m2和2026-10-06-review-sync的CSV、Markdown和PDF；保留历史20项任务及后续同步快照 |
| Notion原始截图 | Notion原始截图/ | process/snapshots/screenshots/notion-board-before-update.png；该图截取范围未覆盖全部20项，且早于本轮状态更新 |
| 成员反馈 | 成员反馈/ | process/reviews/m1-member-review.md及PDF；保留2026-10-06历史全员核对结果与文档修改记录，不代表本轮复核通过 |
| 版本记录 | 版本记录/ | process/versions/m1-version-record.md与git-history.txt；说明历史提交及本地修订，另附report-sha256sums.txt关联独立交付的报告 |

## 在线入口

- [GitHub私有仓库](https://github.com/kenqia/locomo-dynamic-memory)
- [Notion项目页](https://www.notion.so/3ef583f94406818181b0c07c27fd7d20)
- [Notion完整任务表](https://www.notion.so/2c97eb4f233c4680841aa98df2a13fe5)

读取私有资源需要授权。过程包包含可离线阅读的文件与原始截图，不依赖助教已经取得Notion访问权。

## 本轮范围

2026-10-08，本轮工作已完成以下本地修订：

- 完善Team Workflow正文，聚焦稳定的团队规则、职责与里程碑计划；报告Word/PDF同步更新，分页由5页调整为4页。
- 将近期材料职责与M1/M2行动安排保存在process/process-record/m1-m2-action-plan.md，不再混入报告正文。
- 按本说明的六类材料重组M1过程ZIP，移除仓库目录层级和清单之外的附件，保留历史来源；包内共24个文件。
- 更新本材料说明及版本记录，重新生成离线入口、文件清单、来源映射和哈希。

报告修订及行动安排迁移已随提交a8eef22推送至docs/m1-workflow-finalization，关联Issue #1和PR #2。本次六类目录重组及说明更新仍为该提交之后的本地修改，尚未提交或推送，不能将a8eef22当作本轮重打包的交付版本。

2026-10-06的会议、访问、快照和成员反馈属于历史证据。组长当时确认成员Notion访问可用、会议时间与记录人，以及全员核对无问题；历史材料版本1373c10与随后更新1799d54的记录保留在版本说明中，不能据此认定2026-10-08修订已完成成员复核。

讨论中的图谱、结构化记录和搜索方式属于M2候选方案，未写为已实现功能。正式交付形式按课程课件和助教通知核对，M1报告与M2展示材料分别整理。

## 历史快照与本轮状态

process/snapshots/2026-10-06-m1-m2和2026-10-06-review-sync保留当日读取数据与后续注记，原CSV不改写。其中review-sync是2026-10-06的同步后快照，不是2026-10-08的实时看板。本轮未读取或更新在线Notion，需负责人补录本轮Issue/PR链接和实际任务状态。

2026-10-08已核对PR #2为OPEN，远端待审提交为a8eef22，尚未合并。本轮材料重组、说明更新仍待提交及另一位未参与本轮修改的成员复核，并由组长批准阶段交付版本；课程正式提交尚未执行。

关联任务：[Issue #1](https://github.com/kenqia/locomo-dynamic-memory/issues/1)；待审入口：[PR #2](https://github.com/kenqia/locomo-dynamic-memory/pull/2)。

## 本地检查与交付依据

当前报告4页，已逐页查看分页与图表。打包脚本检查ZIP CRC、六类目录结构、文件清单、包内和仓库来源哈希、离线HTML与Markdown链接、PNG可读性和凭据模式。自动检查不替代成员复核或组长批准。

本轮包内文件及来源映射见process/m1/file-manifest.csv；报告哈希见process/m1/report-sha256sums.txt；独立交付的Word、PDF和ZIP哈希见deliverables/m1/sha256sums.txt。文件检查结论只对应本次打包时的文件，后续修改必须重新打包。

## 包内目录与清单

ZIP内只设置上述六个分类文件夹，每类文件直接放在对应文件夹下，不保留docs/、process/、scripts/等仓库目录层级。

根目录放置本说明m1-process-index.md、离线入口index.html、file-manifest.csv、file-sha256sums.txt和package-check.json。解压后打开根目录index.html即可按分类浏览材料。仓库中的process/m1/index.html是该包内入口的生成副本，离线浏览请使用解压后的入口。

文件清单分别记录包内路径、仓库来源、字节数、包内SHA-256及来源SHA-256；仓库来源为空的条目为自动生成的索引或校验结果。清单不列自身及file-sha256sums.txt，避免自引用；哈希文件覆盖其余全部文件（包括清单），不记录自身。根目录5个文件加六类中的19个文件，共24个文件，清单共22条记录。

会议和访问记录的包内Markdown副本仅将截图链接改为同目录文件名，以便离线打开；仓库原始记录保持不变。其他来源文件原样复制。报告正文、报告配图、Word副本、生成脚本、Notion同步JSON和近期行动安排不在此六类清单范围内，不收入过程包；近期行动安排仍保存在仓库process/process-record/，报告Word/PDF仍独立交付。

历史报告复核结论不覆盖本轮修订，当前可自动验证的文件检查见包内根目录package-check.json（仓库副本为process/m1/package-check.json）；成员真实检查意见另行补录。本次打包不读取或同步在线Notion，也不更新Git历史，历史快照不能证明本轮已同步。
