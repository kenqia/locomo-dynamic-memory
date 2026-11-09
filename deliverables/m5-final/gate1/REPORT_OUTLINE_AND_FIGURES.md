# Final Technical Report — 大纲与图表规划（Gate 1 修订版 r2）

标题：**Dynamic Memory Management for Long-term Conversations: System Design, Implementation, and Evidence-grounded Evaluation**
中文：面向长期对话的动态记忆管理：系统设计、实现与证据约束评测
正文 10–12 页 A4（约 7,500–8,500 汉字 + 7 图 + 4 表），10.5 pt；附录 = 勘误 + 复现 + 39 页 Research Supplement。
版本绑定：main `5519dd2`（冻结前若打 tag，统一替换）。

## 一级章节（10 节）

| § | 标题 | 页 | 内容 | 图/表 |
|---|---|---:|---|---|
| — | 摘要 | 0.3 | 问题、方法、E25 正式结论、默认策略 | — |
| 1 | 引言 | 0.8 | 长期对话的困难；相关≠有效；RQ1–3；贡献 K1–K4；探索性研究另列 | — |
| 2 | 需求与系统概览 | 0.9 | 需求 → 模块映射（一段 + 一表）；架构；技术栈 | F1 架构；T1 需求–实现–验证 |
| 3 | 记忆模型与时间语义 | 1.1 | SourceTurn / Memory / MemoryRelation / CurrentState / Build；reported_at vs event_time；合成 Alex 例 | F2 数据模型与关系 |
| 4 | 检索、解析与证据追溯 | 1.1 | Build Pipeline；Query Pipeline；Hybrid vs Dynamic 唯一差异 = Resolve；四阶段 Trace；引用身份 | F3 Build + Query 双流程 |
| 5 | Web 应用与工程验证 | 0.8 | Product Console 五页；离线 Replay；默认 Hybrid 与回滚；CI + 1,018 本地回归 | F4 Console 截图组 |
| 6 | 实验方法 | 1.0 | 数据划分；E25 流程；指标与分母；bootstrap；费用口径；E12/E22/E23 的角色 | T2 实验层次（不排行） |
| 7 | 实验结果（RQ1、RQ2） | 1.5 | E25 主表；F1 + CI；类别 5 与来源盲审；成本 / 延迟 / 可靠性（含 HTTP 402） | F5 F1 + CI；F6 成本与延迟；T3 E25 主结果 |
| 8 | 证据损失分析（RQ3） | 1.1 | 三阶段固定 K@10；成功子集不限 K 四阶段（另图分面，不连线）；107/2；真实案例；已观察 vs 未完成判断 | F7 证据损失（两面板）；T4 案例 |
| 9 | 研究演进、探索性研究与默认策略 | 0.9 | E0→E25 关键转折；扩展与 Sidecar 定性结论；默认 Hybrid 的理由 | （正文表述，图在 Supplement f01/f16） |
| 10 | 局限、结论与未来工作 | 0.8 | 局限；回答三个 RQ；未来工作 | — |
| — | 复现与发布、团队与 AI 协作、参考文献 | 0.6 | tag/SHA、命令、数据政策；成员职责草稿（待团队确认）；AI 边界 | — |

合计约 11 页。

## 图（7 张）

数据图由 `deliverables/m5-final/figures/make_figures.py` 从冻结 JSON 只读生成，输出 SHA 入 MANIFEST；PPT 使用同一文件。

| ID | 图 | 数据 / 依据 |
|---|---|---|
| F1 | 系统架构 | docs/release/ARCHITECTURE.md；console_ui.py；release_viewer.py |
| F2 | 数据模型与关系（含合成 Alex 时间轴） | memory-export-schema.json；demo_fixture/product-v1 |
| F3 | Build 与 Query 流程（Hybrid / Dynamic 分叉 + Trace 四阶段） | builds.py；queries.py；release_queries.py；Settings |
| F4 | Console 截图组（Memory+Source、Query+Trace） | main 5519dd2 离线 Replay，1920×1080，已载入案例 |
| F5 | E25 类别 1–4 F1 + 配对差 CI | M01–M02 |
| F6 | 成本（按 operation）与延迟 p50/p95 | M07–M10 |
| F7 | 证据损失：(a) 固定 K=10、三阶段 initial→effective→delivered，两臂；(b) 成功子集不限 K 四阶段，Dynamic；两面板独立坐标、标题写明口径 | (a) M20–M22（expanded = initial，见 M20b，文字说明）；(b) M25 |

## 表（4 张）

T1 需求–实现–验证；T2 实验层次（E12 / E22 / E23 / E25 / 11-09 回归：样本、配置、角色，**不列可比分数排行**）；T3 E25 主结果；T4 证据损失案例。

## 写作约束（Gate 2 逐条核对）

- [ ] 每个数字可在 METRIC_LEDGER 找到且口径齐全。
- [ ] RQ1 使用正式结论措辞，不写"Dynamic 无效"或"Dynamic 更好"。
- [ ] 7.90× 写"已报 usage 峰价估算比例"；成功率差注明 9 个 HTTP 402。
- [ ] "Recall" 写"来源覆盖代理"；107 题写"标注来源被排除"，并区分已观察现象与未完成判断。
- [ ] F7 两种口径分面，不连线。
- [ ] E12 数字标注 aggregate-derived，且仅出现在研究演进语境。
- [ ] 11-09 结果写"已曝光数据上的回归"。
- [ ] Sidecar 写"研究候选，未进入 main"。
- [ ] 合成示例标"合成"；Console 实验页数据标"E12 历史 Run"。

## 修订记录

| 日期 | 修订 | 原因 |
|---|---|---|
| 2026-11-09 | r1：17 节 / 10 图 / 5 表 | 初稿 |
| 2026-11-09 Gate 1 审稿后 | r2：10 个一级章节、7 图、4 表、约 8,000 字；F9 改为 F7 两面板分口径；去掉 Timeline 与 Setup 独立图（转 Supplement）；贡献 K1–K4，K5 改为探索性研究 | 负责人意见二.1–二.3 |
