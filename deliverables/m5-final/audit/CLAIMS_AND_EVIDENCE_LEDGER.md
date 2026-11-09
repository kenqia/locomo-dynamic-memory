# Claims & Evidence Ledger (Phase 0 draft)

状态值：**VERIFIED-RECOMPUTED**（本审计从逐项数据重新计算并一致）、**VERIFIED-ARTIFACT**（与冻结工件字段逐字一致，未独立重算）、**DOC-ONLY**（仅文档陈述，未找到/未核对原始工件）、**PENDING**（依赖尚未完成的验证）、**NOT CLAIMABLE**（不得作为结论）。

E25 = Level E 独立留出评测：conv-43/44，400 题 × {Hybrid, Dynamic}，producer `0dbd98e7b296ef29d9998fa55d88d512f8ec85f1`，generation freeze SHA `3cab5d1b486290184e67906d61427f18803b415d82fe18f5f5f7190ae89664a6`，bootstrap seed 51104 × 2000（`tools/m5/offline.py:64 paired`），模型 alias `deepseek-flash`，thinking disabled。
主工件：`experiments/m5-development/level-e-results-v1/official-scores.json`（下称 OS）、`experiments/m5-development/level-e-runtime-terminal-v1.json`（下称 RT）。

## A. 主实验数字（参考值逐项核对）

| ID | Claim | Evidence | Version | Status | Allowed Wording |
|---|---|---|---|---|---|
| C01 | 类别 1–4 Hybrid 完整分母 token F1 = 0.402606 | OS `category_metrics.factual_f1.summary.hybrid_no_resolution.failure_zero_mean` = 0.40260599837767247；本审计由 OS `items`（301 题，失败记零）重算得同值 | E25 | VERIFIED-RECOMPUTED | "E25 留出集类别 1–4（每臂 301 题，失败记 0）上 Hybrid 的 token F1 为 0.402606" |
| C02 | Dynamic = 0.409151 | 同上 dynamic = 0.40915092114596374；重算一致 | E25 | VERIFIED-RECOMPUTED | 同上 |
| C03 | 差 +0.006545 | OS `paired_dynamic_minus_hybrid.mean` = 0.00654492276829121；重算一致 | E25 | VERIFIED-RECOMPUTED | "配对差 +0.006545" |
| C04 | 95% 配对区间 [−0.020133, +0.034035] | OS bootstrap95 = [−0.020132663918, 0.034034671620]；本审计用 numpy `default_rng(51104)`、2000 次按题重采样复现**逐位一致** | E25 | VERIFIED-RECOMPUTED | "95% 按题 bootstrap 区间 [−0.020133, +0.034035]，跨零；不支持稳定改善" |
| C05 | Hybrid 技术成功 394/400 | OS `summary.hybrid_no_resolution.succeeded`=394；items 计数 394 succeeded / 6 failed | E25 | VERIFIED-RECOMPUTED | "394/400（98.50%）" |
| C06 | Dynamic 技术成功 389/400 | 389 / 11；items 计数一致 | E25 | VERIFIED-RECOMPUTED | "389/400（97.25%）" |
| C07 | 17 失败 = 8 invalid_output + 9 model_http_error（HTTP 402 余额拒绝） | `level-e-failures-terminal-v1.json`；LEVEL_E_RESULTS_V1.md | E25 | VERIFIED-ARTIFACT（分类未独立重算） | "9 项为供应商余额拒绝（HTTP 402），非模型语义错误" |
| C08 | Dynamic 已报 usage 峰价约为 Hybrid 的 7.90 倍 | RT `groups.all/*.costs.all_attempts.adapter_reported.reported_usage_peak_cache_miss_upper_usd`：6.8800119 / 0.8705958 = 7.9026 | E25 | VERIFIED-RECOMPUTED | "按已报 usage 与全 cache-miss 峰价估算，Dynamic 查询费用约为 Hybrid 的 7.90 倍；非实际账单；另有 18 次 usage 未知请求（预约 USD 0.9522705）未计入" |
| C09 | 延迟 P50 约 3.51 倍 | RT `elapsed_seconds.p50`：8.314747 / 2.370230 = 3.508 | E25 | VERIFIED-RECOMPUTED | "单题耗时 p50 2.37 s vs 8.31 s（含失败项，离线串行运行），约 3.51 倍；不代表生产吞吐" |
| C10 | Dynamic 额外费用主要来自 Resolve | RT `dynamic.costs.by_operation.resolve` = 6.5111079 / 6.8800119 = 94.6% | E25 | VERIFIED-RECOMPUTED | "Resolve 阶段占 Dynamic 已报峰价的约 95%" |
| C11 | Resolve 阶段 p50 6.06 s | RT `dynamic.stage_seconds.resolve.p50` = 6.0630 | E25 | VERIFIED-ARTIFACT | — |
| C12 | 类别 5 字面拒答 H 0.858586 / D 0.808081，差 −0.050505，区间 [−0.101010, 0] | OS `adversarial_literal_refusal` | E25 | VERIFIED-ARTIFACT | 必须写"字面拒答规则"，不得称事实 F1 |
| C13 | 混合 400 题均值 H 0.515461 / D 0.507886，差 −0.007575 | OS `summary`、`paired_dynamic_minus_hybrid` | E25 | VERIFIED-ARTIFACT | "混合规则均值，非事实正确率" |
| C14 | 类别 1–4 配对：60 提升 / 56 退化 / 185 不变 | OS | E25 | VERIFIED-ARTIFACT | — |
| C15 | 物理请求 2,112；预约 USD 105.4516575；18 usage 未知 | OS `runtime_cost`、RT | E25 | VERIFIED-ARTIFACT | 区分预约 / 已报峰价 / 实际账单（未读取） |
| C16 | 共享 Build 920 请求、已知峰价 USD 6.6141915 | `level-e-shared-build-cost-v1.json` | E24/E25 | DOC-ONLY→需核字段 | — |
| C17 | 十阶段累计 3,975 请求、预约 USD 197.6108655、已报峰价 USD 18.1208100 | LEVEL_E_RESULTS_V1.md | M5 全程 | DOC-ONLY→需核字段 | "不是实际账户账单" |

## B. RQ3 证据保留

| ID | Claim | Evidence | Status | Allowed Wording |
|---|---|---|---|---|
| C20 | Source Recall@10（Memory-rank K）Dynamic initial 0.679678 → effective/delivered 0.534318；Hybrid delivered@10 0.681934 | OS items `source_recall`：本审计逐项重算 @5/@10/@20 四阶段全部一致 | VERIFIED-RECOMPUTED | "标注来源覆盖代理"，不得称事实召回或语义正确率 |
| C21 | 107/400 题在 Resolver input→Effective 失去至少一个标注 Source Turn；2 题在 Answer 预算阶段再失去 | `experiments/evidence-flow-20261109/audit.json` | VERIFIED-ARTIFACT | "107 题出现标注来源被排除"，**不得**称"误删率"——是否误删需人工语义核查（未完成） |
| C22 | 全部 400 条 Dynamic 解析输入均未被预算截断 | 同上 | VERIFIED-ARTIFACT | — |
| C23 | 来源盲审：原文支持 H 250/343、D 233/307；共同可判定 297 对净改善 10，区间 [−0.010101, +0.077525] 跨零 | `source-review-summary.json`、`source-review-paired.json` | VERIFIED-ARTIFACT | "单名非作者 AI 审阅，非人工/教师真值；条件分母" |

## C. 历史与开发实验（不可与 E25 直接比较）

| ID | Claim | Evidence | Status | Allowed Wording |
|---|---|---|---|---|
| C30 | E12 历史 757 题四策略完整分母 F1：FT 0.464869 / V 0.519714 / H 0.521886（unknown 记 0 下界，上界 0.523207）/ D 0.515133 | `3e64811:docs/team-v2/research-evidence.json`：successful_qa_mean × 成功数 / 757 重算四值一致；Hybrid `full_denominator_bounds` 字段一致；原 Run `a2abe1fb49be45ccba291728e1f6b3c9` | VERIFIED-RECOMPUTED（Gate 1 升级） | "旧 Run、开发对话、不同模型血缘与配置" |
| C31 | E12 成功子集：H 0.524659 / D 0.550008；D 成功 709/757 | research-evidence.json | VERIFIED-ARTIFACT | 必须与完整分母同列 |
| C32 | E12 Dynamic 查询费用 98.930522 CNY vs Hybrid 9.597679 CNY | 团队报告引 research-evidence.json | DOC-ONLY→需核 | 价格口径含 cache-hit（见 SUPPLEMENT_ERRATA），不可与 E25 USD 峰价混算 |
| C33 | E22 Level C v1 普通 80 题：H 0.399883 / D 0.228329（D 49 输入失败） | LEVEL_C_RESULTS.md | DOC-ONLY | — |
| C34 | E23 input v2：H 0.401172 / D 0.444702，差 +0.043530，CI [−0.008095, 0.095318] | LEVEL_C_INPUT_V2_RESULTS.md | DOC-ONLY | **E22→E23 同时改变三项配置**，不得单因素归因 |
| C35 | 11-09 真实回归：12 道已曝光题，普通 10 题 F1 0.517381→0.456314，差 −0.061067，CI [−0.313876, +0.233333] | `experiments/live-boundary-20261109/results.json` | VERIFIED-ARTIFACT | "已曝光数据上的小样本回归，无整体收益证据" |
| C36 | 时间解析边界 11/21→21/21 | evidence-flow-20261109 | VERIFIED-ARTIFACT | "工程解析回归，非 QA 指标" |

## D. Bonus / 扩展（研究候选）

| ID | Claim | Evidence | Status | Allowed Wording |
|---|---|---|---|---|
| C40 | Graph 两跳：757 回放来源覆盖 0.819920→0.823098，最终交付无增益 | RELEASE_COMPONENT_MATRIX / BONUS_FEATURES.md | DOC-ONLY | "已实现、默认关闭；未证明 QA 收益" |
| C41 | Compression wire：完整 messages 代理 tokens 省 0.02925% | 同上 | DOC-ONLY | "可忽略；非账单降本" |
| C42 | Adaptive：交付来源代理 −0.029349 | 同上 | DOC-ONLY | "拒绝默认采用" |
| C43 | Temporal soft priority：757 回放无总体代理收益 | 同上 | DOC-ONLY | — |
| C44 | E1 路由 757 项全部选择 Dynamic，配对增益 0 | research-evidence.json `e1` | VERIFIED-ARTIFACT（字段存在，未展开核对） | — |
| C45 | E5 缓存：冷编码 CPU −64.22%、本地检索 CPU −57.36%，provider token/费用节省 0 | research-evidence.json `e5` | VERIFIED-ARTIFACT（同上） | "仅本地计算收益" |
| C46 | Sidecar：conv-26/30 共 503 Memory、63,057 候选对全部 unknown；68 参考单元信息性正确 0/68 | `codex/sidecar-research-20261107:research/sidecar-20261107/REPORT.md`、run-v2-summary.json | DOC-ONLY（未进 main） | "研究候选，当前版本被研究本身建议拒绝接入" |

## E. 工程能力声明

| ID | Claim | Evidence | Status | Allowed Wording |
|---|---|---|---|---|
| C50 | 公共 `POST /queries` 与 Release 页面默认 Hybrid，Dynamic 显式可选 | `release_queries.py`、`docs/release/DEFAULTS_AND_ROLLBACK.md`、tests/release | VERIFIED-ARTIFACT（代码存在） | Implemented |
| C51 | Product Console（Overview / Memory / Query-Evidence / Experiments / Demo，离线 Replay）在 main | PR #41 merge `1549712`；`console_*.py`；作者外真人复核 xiaozhuozi39 绑定 `0401155`；CI run 42582449214 success | VERIFIED-ARTIFACT | Implemented and Accepted |
| C52 | main `5519dd2` CI 通过 | GitHub Actions "Checks" run 42582449214：completed/success（负责人提供，2026-11-09 本审计经 API 复核 head_sha=5519dd2） | VERIFIED-ARTIFACT | "main 5519dd2 的 CI 检查通过" |
| C52b | 本审计独立本地公开离线回归 | 第 1 次：1,018 项全 `.`、无 F/E，摘要/退出码未捕获；第 2 次带 JUnit 与退出码运行中（`/tmp/m5audit/pytest-5519dd2-r2.txt`） | PENDING | 完成后更新 |
| C53 | 六份真实 MemoryExport：2031 Memory / 37,445 关系 | `six-memory-exports-manifest.json` | VERIFIED-ARTIFACT | "完整性校验通过，不代表语义正确" |
| C54 | 60 关系单位 AI 诊断 50/60 | PERSONAL_EXPERIMENT_SUMMARY | DOC-ONLY | **NOT CLAIMABLE** 为四标签准确率（无 SUPERSEDE/CONFLICT 覆盖） |

## F. 明确不可宣称

- "Dynamic 优于 Hybrid" / "Dynamic 提升 X% 准确率"（C04 区间跨零）。
- Source Recall 作为语义正确率或事实召回。
- 107 题作为"误删率"。
- 任何费用作为实际账单。
- Sidecar / Graph / Compression / Adaptive 带来 QA 收益。
- E25 在 11-05 之后仍为"独立未曝光测试"——结果已曝光，后续只能称回归。
- 本地留出结果代表教师隐藏评分集。
