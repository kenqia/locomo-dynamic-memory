# M4 过程材料说明

团队：在阴雨天游泳，Team ID 3。整理日期：2026-10-23。

当前[报告 v0.6](../docs/design/m4-midterm-report.md)提供[可编辑 Word](../docs/design/m4-midterm-report.docx)和[5 页 PDF](../deliverables/m4/PROJECT-MILESTONE4-3-在阴雨天游泳-报告.pdf)，独立于过程 ZIP 交付。

## 阅读与维护入口

| 文件 | 只在此处维护的内容 |
| --- | --- |
| [修订记录](m4/draft-evidence.md) | 写作要求、版本基准、v0.1–v0.6 的内容变化及保存依据 |
| [来源说明](m4/source-notes.md) | 原始实验、测试、页面证据的链接和统计口径 |
| [验证说明](m4/validation-record.md) | 导出与打包命令、机器检查及校验文件的用途 |
| [复核与交付登记](m4/member-review-record.md) | 待办清单、真实成员意见和提交回执；当前仍待填写 |

版本说明已集中到修订记录，复核清单已并入登记表。原 version-record.md、iterations/revision-notes.md、review-checklist.md 不再单独维护。

## 保留的原件与自动文件

- iterations/report-v0.1.md、report-v0.2.md：从 Git 读取的历史稿，保留原字节，内容不同于当前定稿。
- [code-review.md](m4/code-review.md)：仅针对其中固定提交的 v0.2 AI 审查原件。
- git-history-baseline.txt、status-snapshot.json：打包时捕获的 Git 和本地材料状态；不是 Notion 导出。
- pdf-validation.json、source-validation.json、package-check.json：页数、指标及包检查结果。
- file-manifest.csv、file-sha256sums.txt、report-sha256sums.txt：载荷清单与校验；按[验证说明](m4/validation-record.md)重建，不逐份手工编辑。

原始实验和页面材料按仓库路径随包保存，入口见来源说明。M1/M2 只作组织形式参考，不将其会议或旧任务快照当作 M4 证据。

## 离线使用

解压 [过程 ZIP](../deliverables/m4/PROJECT-MILESTONE4-3-在阴雨天游泳-过程材料.zip)，进入同名阶段目录，打开 process/m4/index.html。主要说明已内嵌，JSON、CSV 和截图随包；标为“在线补充”的链接固定到文档引用版本 cf422fe，需要网络及仓库权限。

修改材料后运行 `python scripts/package_m4_materials.py`。包内文件与工作区原件逐字节校验；独立交付的 PDF、Word、ZIP 摘要见 deliverables/m4/sha256sums.txt。实际复核和提交状态以登记表为准。
