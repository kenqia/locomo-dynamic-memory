# 主工作树未提交文件逐项审查（Gate 2 · D）

审查时间：2026-11-09 约 19:10。主工作树 `/home/kenqia/my_folder/locomo-dynamic-memory`（main 检出，HEAD = `5519dd2` = origin/main；未提交改动叠加在其上）。**未修改、未移动、未提交主工作树任何文件。**
实际规模：20 个已修改文件 + **2,817 个**未跟踪文件（Phase 0 的"48 项"是目录级计数，已更正）。凭据扫描（`sk-…`、私钥头）：所有候选路径 0 命中。

## A. 建议提交（相关、无凭据、无受控原文）—— 待负责人批准

拟在新分支 `archive/m5-process-materials-20261109`（基于 origin/main `5519dd2`）按主题分 4 个提交，**复制**文件（主工作树原样保留），之后形成 PR 供审查，不直接进 main。

| # | 主题提交 | 文件 | 理由 | 检查 |
|---|---|---|---|---|
| A1 | `docs: add ADR-0003 and dynamic-validation decision records` | `docs/adr/0003-dynamic-memory-mechanism-validation.md`；`docs/decisions/dynamic-memory-validation-interview.md`、`dynamic-memory-validation-protocol.md`、`memory-quality-improvement-interview.md`、`top7-iteration-interview.md` | 报告 §9 研究演进与 E6 消融的决策依据；ADR 编号已被引用 | 0 凭据；无原文 |
| A2 | `docs: add domain terms for evidence loss and dynamic questions` | `CONTEXT.md`（+10 行：评测事实单元、证据损失、跨对话评测、跨会话状态演化、动态问题） | 报告 RQ3 术语；纯新增 | diff 已读，仅新增定义 |
| A3 | `process: archive M5 member reviews and Notion/review snapshots` | `process/m5/member-review-20261107/`（3 文件）；`process/snapshots/2026-11-07-*`（5）、`2026-11-08-*`（5）、`2026-11-09-member-quality-review.md` | 成员职责草稿的指定来源；过程完整性 | 0 凭据；内容为只读核查记录。`2026-11-08-sidecar-owner-human-review.md` 是**已撤回的空模板**，文首已注明，按原样归档 |
| A4 | `process: archive M3 process materials and top7 issue registry` | `process/m3/`（14 文件，1.4 MB）；`process/top7/`（17 文件，2.0 MB）；`tests/test_top7_records.py`（其依赖 `scripts/validate_top7.py` 已在 Git） | M3 过程材料目前只在本地；top7 登记表为 E7 档案的结构化索引 | 0 凭据；`process/top7` 的 `evidence` 字段为文件指针，不含 Gold 原文；需在新分支跑 `pytest tests/test_top7_records.py` 后再提交 |

## B. 不建议直接提交 / 需负责人判断

| 文件 | 原因 | 建议 |
|---|---|---|
| `docs/requirements/software-requirements-specification.md`（M） | diff 是**删减**：去掉了"v0.3 · 待团队复核"状态行、"需求存在不表示已经通过验收"、"本次未重新运行测试…须由成员复核"等限定语，日期改回 10-18。这看起来像为 M3 PDF 篇幅做的精简版，不是内容更新 | **不提交到 main 的 SRS**；如需保留，存为 `process/m3/` 下的排版副本。报告引用 Git 中已有的 SRS 版本 |
| `docs/design/m4-midterm-report.{md,docx}`、`deliverables/m4/*`（5 个二进制 + 2 JSON）、`process/m4/*`（6）、`scripts/build_m4_report.py`、`scripts/package_m4_materials.py`（813 行改动）、`process/m4-process-index.md`、`deliverables/PROJECT-MILESTONE3-…报告.pdf` | M4/M3 **已提交交付物被重新生成**，字节与提交给课程的版本不同。覆盖会使"已提交版本"身份丢失 | **不覆盖**已提交版本。若负责人确认这是交付后的修订版，另存为 `…-revised-20261109` 并在过程材料中说明 |
| `deliverables/m4/…演示视频.mp4`、`deliverables/PROJECT-MILESTONE3-…过程材料.zip`、`deliverables/process/m3,m4`（70 文件，13 MB）、`process/m4/materials`（56 文件，12 MB） | 大二进制 / 重复副本（`deliverables/process/m4` 与 `process/m4/materials` 内容重复） | 不进 Git；最终包时按 MANIFEST 只取需要的一份 |
| `experiments/top7-iteration-20261029/`（2,611 文件，76 MB） | 含针对 LoCoMo 人物的真实模型回答文本，可能含原文引用（如 `continuation/live-v2/conv30-event-answer.json`）；体积大 | **暂不提交**。需按 `DATA_POLICY.md` 做原文字面匹配扫描后再决定；本地保留，过程材料中以索引 + SHA 引用 |
| `experiments/pr-38-review-20261103/`（40 KB） | PR #38 旧 HEAD 的复审记录；与 Sidecar 研究候选相关 | 可提交（随 A3），但需先确认不含复审者私人意见；**待负责人确认** |

## C. 不提交

| 文件 | 原因 |
|---|---|
| `.scratch/`（14 文件） | 临时工作目录（`real-deepseek-baseline/approved|issues`）；属于草稿 |

## 引用规则（报告与过程材料）

- A 类获批并提交后，报告引用对应 commit SHA。
- 在此之前，报告只引用 Git 中已有路径；`process/m5/member-review-20261107/` 和 `process/snapshots/2026-11-0{7,8,9}-*` 在报告"团队分工"中标注为 **本地证据（未提交）**。
