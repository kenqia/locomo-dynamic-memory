# M4 过程材料说明

团队：在阴雨天游泳，Team ID 3。整理日期：2026-10-22。

本包保存 M4 报告从初稿到 v0.3 的修订、需求与设计依据、已有系统测试和真实展示结果、页面证据及文档校验。报告 PDF 独立提供，含参考索引共 5 页；过程材料不计入报告页数限制。过程包已在本地整理，但不表示成员复核、阶段验收、Notion 同步或正式提交完成。

解压 `PROJECT-MILESTONE4-3-在阴雨天游泳-过程材料.zip`，进入同名阶段目录，打开 `process/m4/index.html`。阅读页内嵌主要 Markdown 说明并链接随包 JSON、CSV 和图片，无需网络即可检查主要证据。包内源文件保留仓库路径和原字节；未选入的仓库补充链接在阅读页中转为固定实现版本的 GitHub 链接，明确需要网络和私有仓库权限。

## 材料组织

| 类别 | 主要位置 | 作用 |
| --- | --- | --- |
| 报告与版本演进 | docs/design/m4-midterm-report.md、process/m4/iterations/、version-record.md | 当前源稿、v0.1/v0.2 历史稿与修改依据；Word/PDF 独立交付 |
| 需求与设计依据 | CONTEXT.md、docs/adr/、docs/specs/、docs/app/、架构图 | 说明约束和实现选择；正式 M3 文档引用仍待填写，历史 Issue 副本不改写 |
| 实验与初步测试 | experiments/current-showcase/results/、plan.json、process/prs/、已有验证记录 | 五策略 100 项、40 题 Recall、动态与来源审阅、工程回归及统计口径 |
| 页面与可运行证据 | experiments/current-showcase/web-recorded/、web-controlled/ | 真实保存结果只读回放与受控边界场景分列，均保留机器记录及截图 |
| 版本、审查与校验 | process/m4/ | Git 历史基准、AI 历史审查、报告页数与来源指标、清单和包校验 |
| 人工复核与交付待补 | member-review-record.md、review-checklist.md、status-snapshot.json | 真实意见填写位置及本地材料状态；不是已签字证明或 Notion 导出 |

## 结果与使用边界

当前报告依据实现主线 `ffb2657`。2026-10-21 的展示复用已发布的 conv-26 Build，20 题五策略共 100 项成功；类别 1–4 的 16 题 F1 分别为 0.3490、0.4911、0.5124、0.5100、0.3997。40 题初始 RRF Recall@5/10/20 为 64.17%、72.92%、77.92%。结果来自同一开发对话单轮，不证明稳定优劣或隐藏评分集表现。

10 个真实动态查询和 20 条回答来源审阅由开发助手核对，不能当作独立人类动态真值。当前真实 Build 没有 SUPERSEDE/CONFLICT；合成冲突案例只说明工程路径。Dynamic 两题实际触发原文备用，不能视作禁用备用的纯动态消融。原 757 题、3,028 项全量计划已取消，当前展示不替代原验收。

本轮只整理已有记录、报告和过程包，没有重跑模型、构建或业务测试。历史失败和已取消范围保留；工具检查、原始结果与作者语义审阅分别说明。

## 缺少的真实材料

尚未取得本次 M4 的正式 M3 文档路径、成员非作者复核记录、最新 Notion 阶段导出、M4 新会议纪要或截图、展示环境本轮复测及正式提交回执。包内设置明确的待补记录，不复制 M1/M2 的会议、签字或旧任务快照充当 M4 证据。

M4 演示文件另由团队安排，本轮不制作。正式提交前核对最新助教通知、报告及演示版本、过程包、收件方式和负责人；只在实际完成后补录状态。

## 清单、校验与重建

- [主要来源与边界](m4/source-notes.md)
- [本地版本记录](m4/version-record.md)
- [人工复核待填表](m4/member-review-record.md)与[复核清单](m4/review-checklist.md)
- [本地验证说明](m4/validation-record.md)
- [包内文件清单](m4/file-manifest.csv)、[包内 SHA-256](m4/file-sha256sums.txt)、[报告文件校验](m4/report-sha256sums.txt)
- [机器打包检查](m4/package-check.json)、[离线入口](m4/index.html)
- [编写与报告校验记录](m4/draft-evidence.md)

清单不包含自身和 file-sha256sums.txt，避免自引用；包内哈希文件覆盖其余全部文件。独立交付的 PDF、Word 和 ZIP 的校验见 deliverables/m4/sha256sums.txt。所有源文件先存仓库，再原样打包，包内没有仅存在于 ZIP 的原始材料。

修改已选材料后，重新运行 `python scripts/package_m4_materials.py`。脚本检查实际 PDF 页数、源稿与导出哈希、逐项指标、ZIP CRC、文件清单、安全相对路径、仓库字节一致性、离线链接和图片。自动检查不替代成员复核；历史 Git 日志的捕获范围单独标明。
