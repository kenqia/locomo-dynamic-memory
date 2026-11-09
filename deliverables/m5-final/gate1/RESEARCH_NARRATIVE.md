# Research Narrative — Gate 1 审稿稿

状态：DRAFT，待负责人在 Gate 1 冻结。版本基准 main `5519dd2`（PR #41 合并后；GitHub Actions "Checks" run 42582449214 = success）。
数字均引用 `METRIC_LEDGER.md` 的 M-ID，证据等级沿用 Phase 0（VERIFIED-RECOMPUTED / VERIFIED-ARTIFACT / DOC-ONLY / PENDING / NOT CLAIMABLE）。

## 1. 一句话定位

我们研究在长期、多会话对话里，**能否用"带来源、带时间语义、保留历史关系"的结构化记忆，加上查询期的动态证据解析，提高回答的历史适用性与可追溯性**；并用预先锁定配置的独立留出实验检验这种动态解析是否值得它的代价。

**核心发现（拟冻结）**：结构化记忆与来源追溯链路是可实现、可验证的工程成果；但查询期 Dynamic Resolution 在留出集上**没有表现出稳定的质量提升**（类别 1–4 F1 差 +0.006545，95% 区间 [−0.020133, +0.034035] 跨零），同时带来约 7.90 倍的已报 usage 峰价估算费用和约 3.51 倍的单题中位延迟，且冻结 Trace 中标注来源覆盖的主要下降发生在解析步骤本身。因此系统采用 **Hybrid 默认、Dynamic 显式可选**。

## 2. 研究主线

```
Problem → Hypothesis → Design → Implementation → Experiment → Observation → Failure Analysis → Engineering Decision
```

| 环节 | 内容 | 证据 |
|---|---|---|
| Problem | 长期对话中同一人物的状态随时间变化（搬家、换工作、计划/取消、矛盾陈述）。只按相似度检索，容易把历史事实用于当前问题，或把计划当成已发生事件；回答也无法回指原文 | CONTEXT.md；ADR-0001 |
| H1 | 把对话拆成**原子 Memory**并绑定 **Source Turn**，构建期保留 **MemoryRelation**（RETAIN/UPDATE/SUPERSEDE/CONFLICT/未确定），可在不丢失历史的情况下表达当前状态 | ADR-0001 |
| H2 | 在 Hybrid 检索 + 历史扩展的候选上，再做查询期**有效证据解析**（Dynamic），能比直接回答（Hybrid）更好地选出"对该问题、该时间有效"的证据，从而提高 QA 质量 | ADR-0001 §双阶段职责 |
| Design | Build：Import → Atomic Extraction → 校验 → BM25+Dense 索引 → Relation → CurrentState 投影 → 完整版本发布。Query：Query Analysis → BM25/Dense 各 20 → RRF(60) → 初始 20 → 一跳关系/同 state_key 历史扩展（≤60）→ [Dynamic: Resolve] → Answer + Citations + Trace | docs/release/ARCHITECTURE.md |
| Implementation | FastAPI + Streamlit + SQLite，固定 MiniLM-L6-v2（384 维，revision 固定），DeepSeek `deepseek-flash`；Product Console（PR #41）提供 Memory/Timeline/Source/四阶段 Trace/冻结实验比较/离线 Replay | RELEASE_COMPONENT_MATRIX.md；PR #41 |
| Experiment | 四层：E12 历史 757 题四策略（开发对话）→ E22/E23 开发 100 题双臂 → **E25 独立留出 400 题双臂（主结果）** → 11-09 已曝光数据上的诊断与小回归 | EXPERIMENT_ARCHIVE_INDEX.md |
| Observation | E25：Dynamic − Hybrid = +0.006545，CI 跨零；技术成功 389 vs 394；峰价估算 7.90×；p50 3.51× | M01–M10 |
| Failure Analysis | 标注来源覆盖下降主要在 Resolver input → Effective（107/400 题失去至少一个标注 Source Turn）；Answer 预算仅额外造成 2 题；候选覆盖增加不能带来同等交付覆盖 | M20–M25 |
| Decision | 公共入口默认 Hybrid；Dynamic 显式可选；Graph 两跳 / Compression wire / Adaptive / Temporal soft priority 默认关闭；Sidecar 保持研究候选 | DEFAULTS_AND_ROLLBACK.md |

## 3. 研究问题（拟冻结）

**RQ1 — Answer Quality.** 在独立留出对话上，Dynamic Resolution 是否比 Hybrid Retrieval 稳定地提高长期对话 QA 质量？
- 主指标：E25 类别 1–4 官方 token F1，完整分母（失败记 0），按题配对 bootstrap（seed 51104，2000 次）。
- 辅助：类别 5 字面拒答（单列）；单名非作者 AI 来源盲审（条件分母）。
- **答案：没有证据表明稳定提升。** 点估计 +0.006545，区间跨零；60 题提升 / 56 退化 / 185 不变。类别 5 为 −0.050505（区间 [−0.101010, 0]）。来源盲审共同可判定 297 对净改善 10，区间跨零。

**RQ2 — Efficiency and Reliability.** Dynamic 带来多少 token / 费用 / 延迟 / 可靠性变化？
- **答案：成本显著更高，可靠性略低。** 已报 usage 峰价估算 USD 6.8800119 vs 0.8705958（7.90×；Resolve 占 Dynamic 约 95%）；单题 p50 8.31 s vs 2.37 s（3.51×，含失败项，离线串行）；技术成功 389/400 vs 394/400。均为估算或离线观测，**非账单、非生产吞吐**。

**RQ3 — Evidence Preservation.** 标注证据在哪一阶段被遗漏、排除或未送达？
- 指标：Memory-rank Source Recall **代理**（initial / expanded / effective / delivered），冻结 Trace 只读审计。
- **答案：主要下降在解析步骤。** Dynamic Recall@10 initial 0.679678 → effective/delivered 0.534318；107/400 题在解析后失去至少一个标注 Source Turn，仅 2 题因 Answer 预算再失去。**107 题是"标注来源被排除"，不是"误删"**：20 案逐案人工语义核查未完成，部分案例（如问 Tim 而标注来源谈 John）的排除可能正确。

## 4. 叙事必须包含的十点（→ 报告章节）

1. **长期对话的核心困难** — 状态演化、计划与否定、矛盾陈述、"现在"的定义。→ §2
2. **为什么相似度检索不够** — 相关 ≠ 有效；旧住所与新住所对"住在哪"同样相似。→ §2、§6
3. **为什么保留 Memory 历史** — SUPERSEDE 后旧证据仍要回答历史日期问题；CurrentState 是可重算投影。→ §5
4. **为什么需要 Source Turn** — 回答可回指原文；合法 ID ≠ 语义支持，因此另做来源盲审。→ §7
5. **为什么需要 Relation** — 区分替代、推进、冲突与未确定，避免按时间新旧覆盖。→ §5
6. **Hybrid 与 Dynamic 的差异** — 共享检索与扩展；Dynamic 增加一次全候选 Resolve 调用与有效集合。→ §6
7. **实验如何验证** — 先锁配置 → 冻结生成 → 根与非作者终态审计 → 再读 Gold；完整分母；失败保留。→ §9
8. **Dynamic 为什么没被认定更优** — 区间跨零 + 成本/延迟 + 可靠性 + 解析阶段来源覆盖下降。→ §10–§12
9. **为什么默认 Hybrid** — 质量无可辨差异、已报峰价低约一个数量级、失败更少、可回退；Dynamic 保留为显式选项。→ §12 末
10. **扩展的价值与边界** — Graph/Compression/Adaptive/Temporal 已实现、默认关闭、无 QA 收益证据；Sidecar 自身研究建议拒绝接入。→ §13

## 5. 研究贡献（拟冻结）

| # | 贡献 | 类别 | 依据 |
|---|---|---|---|
| K1 | 从 Source Turn → 原子 Memory → MemoryRelation → CurrentState 投影 → 固定完整 Build → 带引用回答与四阶段 Trace 的可追溯记忆系统，含 Product Console 与无 key 离线回放 | A Implemented & Accepted | main `5519dd2`；PR #40/#41；CI 42582449214 success；本地回归 M50 |
| K2 | 预先锁定配置、生成冻结后再评分的 Hybrid vs Dynamic 独立留出对照（400 题 × 2 臂），完整分母、失败保留、质量/成本/延迟/可靠性同表 | B Experimentally Validated（结论为无稳定提升） | E25，M01–M15 |
| K3 | 阶段化证据损失审计：Source 覆盖在 initial/expanded/effective/delivered 分列，并以冻结 Trace 定位损失阶段 | B（方法与观测）；排除是否合理 → C | M20–M25 |
| K4 | 研究可信度工程：E0–E25 档案、生成冻结 SHA、非作者终态审计、数值独立重算（282 叶 0 差异）、勘误保留 | A（过程资产） | EXPERIMENT_ARCHIVE_INDEX；SUPPLEMENT_ERRATA |
| K5 | 扩展模块（Graph 两跳、可逆压缩、Adaptive、Temporal soft priority）与 Sidecar 的实现和离线/真实 Build 评估，含负面结果 | C Research Candidate | M40–M46（多为 DOC-ONLY） |

**不列为贡献**：任何"Dynamic 提升准确率"、"压缩降本"、"Graph 提升 QA"、"Sidecar 改善时间推理"。

## 6. 局限（→ 报告 §14）

- 留出集仅 2 段对话（conv-43/44），bootstrap 按题，不支持对话级泛化，不代表教师隐藏评分集。
- E25 已曝光；之后的修复与重跑只能称**回归**（如 11-09 12 题回归 F1 0.517381→0.456314）。
- 无人工/教师动态标签；来源盲审每项仅一名非作者 AI；关系四标签准确率未测（60 单位诊断无 SUPERSEDE/CONFLICT 覆盖）。
- Atomic Fact Recall/Retention、有效选择准确率均 `not_measured`。
- 费用为预约 / 已报 usage 峰价估算，实际账单未读取；18 次 usage 未知请求另列。
- `deepseek-flash` 是服务别名，不是固定权重。
- E12/E22/E23/E25 样本、配置、模型血缘不同，不做严格因果比较；E22→E23 同时改了三项配置。
- 仅支持英文检索。

## 7. 时间语义口径（全稿统一）

- **reported_at / session time**：该轮对话的会话时刻（信息被说出的时间）。
- **event_time**：事件实际发生时间，可为日期、区间或 unknown；由原始表达 + 会话锚点推导，不把会话时刻当作事件时刻。
- **已知状态截止时间**：未指定日期时，"现在" = 所选对话最后一次会话时间。
- 计划 ≠ 已完成；否定保留；SUPERSEDE 不删除历史。

## 8. 功能分类（全稿与 PPT 统一）

| 功能 | 分类 | 说明 |
|---|---|---|
| 导入 / 原子抽取 / Build / 索引 / 版本发布 | A | main |
| MemoryRelation + CurrentState 投影 + 历史扩展 | A | main；关系语义准确率未测 |
| Hybrid 默认问答 + 引用 + Trace | A | main |
| Dynamic Resolution | A（可用）；B（无稳定收益） | 显式可选 |
| Product Console（Overview / Memory / Query / Experiments / Demo） | A | PR #41；作者外真人复核；CI success |
| 独立 MemoryExport Replay | A | main |
| Bonus A 冲突/多版本/时间线只读展示 | A | QA 收益未测 |
| Bonus B Graph 浏览 | A | 显式打开 |
| Graph 两跳 / Compression wire / Adaptive / Temporal soft priority | C | 默认关闭，无 QA 收益证据 |
| Temporal / Event Sidecar | C | 未合并 main（PR #38 open draft）；研究建议拒绝接入 |
| Hindsight / Cross-Encoder / PropMem | C | 研究档案，未进 App |
| 人工动态标签、Atomic Fact Recall、跨语言、对话级泛化 | D | Future Work |

## 9. Gate 1 待负责人决定

1. **RQ 与答案措辞**：是否接受三条 RQ 及 RQ1 "无稳定提升"的表述。
2. **主结果唯一性**：报告以 E25 为唯一主结果，E12/E23 仅作"研究演进"背景（推荐）。
3. **E12 未核数字**（Full Text / Vector / Hybrid 完整分母）：(a) 只引用已核字段并标 DOC-ONLY；(b) Gate 2 前从 `research-process-archive@3e64811` 补核（推荐，时间不足退回 a）。
4. **Bonus DOC-ONLY 数字**：报告中只作定性描述，具体数字留 Supplement（推荐）。
5. **K3 分类**：同意"证据损失审计"为方法贡献（B），排除合理性判定明确为未完成（C）。
6. **团队分工数据源**：请指定（候选：`process/snapshots/2026-11-0{7,8,9}-member-quality-review.*`、`process/m5/member-review-20261107/`）；AI 不按 commit 数推断。
