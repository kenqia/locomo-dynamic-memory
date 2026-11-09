# Delivery Gap Analysis (Phase 0)

审计时间：2026-11-09 约 16:10（Asia/Shanghai）。基准 main `5519dd2`。

## 0. 决定性约束：时间

课程原文 `docs/sources/0 - Project (2026).pdf`：Milestone 5 "Final Presentation (Week 8) & Final Report"，截止 **24:00 Nov 9, 2026**，邮件发送 TA，命名 `PROJECT-MILESTONE[n]-[team_id]-[team_name]`，Presentation PDF ≤ 10 页。
距截止约 **8 小时**。主提示词中的六阶段逐阶段确认流程（尤其 12–18 页报告、真人录制视频、完整归档）在此时间内**无法全部按原标准完成**。需要负责人决定范围（见 §5）。

## 1. 交付物缺口

| 交付物 | 现状 | 缺口 | 工作量估计 |
|---|---|---|---|
| Final Presentation PDF（≤10 页） | 15 页 v2（11-08），数字正确，Product 页基于旧 `44d20dc` 截图 | 压缩为 10 页；替换为 main 5519dd2 真实 Console 截图；更新版本身份 | 2–3 h |
| Final Technical Report | 5 页中文 v2（11-08），数字正确，版本身份过时 | 扩写为研究型报告（RQ1–3、方法、结果、失败分析、局限）；更新 PR #41 已合并、Sidecar 未合并 | 12–18 页需 4–6 h；8–10 页约 3 h |
| Demo 视频 | 4:30，PPT + 旁白，无真实 UI 操作 | 真人操作 Console 录制（需负责人本人录制）；脚本/分镜/字幕由 AI 准备 | 脚本 1 h + 录制剪辑 1.5–2 h（人工） |
| Research Supplement | 39 页，已更新至 11-09 | 已足够，只需在包内附勘误入口 | 0.2 h |
| 过程材料 ZIP | M1–M4 有；M5 分散在 docs/m5-development、process/snapshots、experiments | 建 M5 索引与 10 类目录；导出 PR #38–#41 快照 | 1.5–2 h |
| 最终包 / MANIFEST / SHA256 | 无 | 生成 + 隐私扫描 + 验证 | 1 h |
| Release Tag | 无 | 需在 main 上打 tag（需批准，push 属外部操作） | 0.1 h |

## 2. 证据缺口

| 缺口 | 影响 | 处理 |
|---|---|---|
| main 5519dd2 公开回归 | C52 PENDING | 本审计已在 delivery worktree 后台运行；CI 也在运行。完成前不写"通过" |
| PR #41 合并后的 Console 实际截图 | PPT/报告/视频都依赖 | Phase 3 前启动 Replay 截图（无 key） |
| Issue #23/#26–#29 | 已核：2026-11-09 07:55Z 随 #41 自动关闭 | 无 |
| E12 H/V/FT 完整分母 F1 的原始字段 | C30 部分 DOC-ONLY | 从 `research-process-archive@3e64811` 核对或在报告中只引用已核字段 |
| Bonus 数字（C40–C43） | DOC-ONLY | 报告中引用时附来源文档；时间不够则只做定性描述 |
| 107 题来源排除是否合理 | RQ3 结论强度 | 已知未完成；报告写成开放问题 |
| 莫远序 18 对人工核查中的"待裁定项" | live-boundary 段落措辞 | 原样写"部分待裁定" |
| 团队贡献确认 | 报告分工章节 | 必须来自成员确认，不由 Git 计数推断；现有 member-review 快照可作依据，缺失部分标"待确认" |

## 3. 功能状态（计划纳入 vs 实际验收）

| 功能 | 计划纳入 | 实际 | 最终分类 |
|---|---|---|---|
| Product Console | 是 | **已合并 main（PR #41）**；作者外真人复核绑定 `0401155`；测试 PENDING | A（待测试结果确认） |
| Temporal / Event Sidecar | 是 | **未合并**（PR #38 open draft，CHANGES_REQUESTED 针对旧 HEAD）；自身研究建议拒绝接入 | C — Research Candidate（负面结果） |
| Hybrid 默认 / Dynamic 可选 | 是 | main 代码 + 测试 | A |
| Graph / Compression / Adaptive / Temporal soft priority | 是（作扩展） | 已实现，默认关闭，无 QA 收益证据 | A（工程）+ C（研究收益） |
| Hindsight / CE / PropMem | 研究档案 | 未进 App | C |

## 4. 风险

1. **截止时间**：最大风险。建议负责人立即确定范围（§5）。
2. **真人视频**：AI 无法替代录制；若负责人今晚无法录制，只能提交旧视频并明确标注为"PPT 讲解视频"，或不提交视频——不能伪称真实操作。
3. **受控数据**：`data/raw/locomo/locomo10.json` 在 Git 中；若用 GitHub 链接或整个仓库 ZIP 交付，会连带分发 CC-BY-NC 原始数据。最终包必须用 allowlist 源码包。
4. **主仓未提交修改**：ADR-0003、SRS 修改、CONTEXT.md 新术语、M3/M4 包修改、process/m5 等 48 项不在 main。若报告引用它们，需先由负责人提交，否则引用会指向不存在的提交。
5. **版本漂移**：审计期间 main 已从 `ba349cf` 前进到 `5519dd2`。最终冻结前需再次确认 HEAD 并打 tag。
6. **CI 在 1549712 上被取消**，5519dd2 上仍在跑；若失败需先修复再冻结。
7. **旧 PPT/报告作者是 VanadisssSSS**：重做时应保留其原件于过程材料并在贡献中注明。

## 5. 建议的执行顺序（今晚）

按重要度与可独立推进程度排列：

1. **(负责人, 5 min)** 确认范围选项与主仓 48 项未提交修改的处理。
2. **(AI, 0.5 h)** Phase 1 精简：Research Narrative + Metric Ledger 一页定稿；数字已在 Phase 0 完成核对，可直接冻结。
3. **(AI, 并行)** 启动 Replay/Console，采集真实截图。
4. **(AI, 2.5 h)** 报告 Markdown 初稿（建议 10–12 页正文，以 Supplement 39 页作附录承载细节）→ 负责人审阅 → PDF/DOCX。
5. **(AI, 2 h)** 10 页 PPT（复用 v2 图表与版式）+ Presenter Notes + Q&A。
6. **(AI 0.5 h → 负责人 1.5 h)** 视频脚本/分镜/SRT → 负责人真人录制。
7. **(AI, 1 h)** 过程材料索引 + 包结构 + MANIFEST/SHA256 + 隐私扫描 + 验收清单。
8. **(负责人)** 打 tag、发送邮件提交（AI 不代发）。

报告、PPT 与视频脚本可在步骤 2 之后并行推进。
