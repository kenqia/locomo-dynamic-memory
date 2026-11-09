# Metric Ledger — Gate 1

每个进入报告/PPT/视频的数字必须在此有 M-ID。报告与 PPT 中的数字须与本表**逐字一致**（报告保留 6 位小数，PPT 可取 3 位但不得改变符号或区间端点关系）。
等级：**RC** = VERIFIED-RECOMPUTED（本次从逐项/冻结数据重算一致）；**VA** = VERIFIED-ARTIFACT（与冻结工件字段一致，未独立重算）；**DOC** = DOC-ONLY（仅在文档表格中，不得升级）；**PEND** = 待验证。

## E25 — Level E 独立留出（主结果）

口径（每次引用必须带上）：conv-43/44，400 题 × {Hybrid, Dynamic}；配置于读 Gold 前锁定；generation freeze `3cab5d1b…89664a6`；producer `0dbd98e`；`deepseek-flash`，thinking disabled；Bonus 关闭；失败记 0；bootstrap 按题 seed 51104 × 2000。
主工件 OS = `experiments/m5-development/level-e-results-v1/official-scores.json`；RT = `experiments/m5-development/level-e-runtime-terminal-v1.json`。

| ID | 指标 | Hybrid | Dynamic | Δ / 比 | 分母 | 来源字段 | 等级 |
|---|---|---:|---:|---:|---|---|---|
| M01 | 类别 1–4 token F1（完整分母） | 0.402606 | 0.409151 | +0.006545 | 301/臂 | OS `category_metrics.factual_f1` | RC |
| M02 | M01 配对 95% CI | — | — | [−0.020133, +0.034035] | 301 对 | OS `…paired_dynamic_minus_hybrid.bootstrap95`；numpy 复现逐位一致 | RC |
| M03 | M01 配对变化 | — | — | 60 升 / 56 降 / 185 平 | 301 | 同上 | VA |
| M04 | 类别 1–4 仅成功子集 F1 | 0.405299 | 0.417473 | — | 299 / 295 | OS summary | VA（不得替代 M01） |
| M05 | 技术成功 | 394/400 (98.50%) | 389/400 (97.25%) | +1.25 pp 失败率 | 400 | OS items 计数 | RC |
| M06 | 失败构成 | — | — | 17 = 8 invalid_output + 9 model_http_error（HTTP 402 余额拒绝） | 17 | `level-e-failures-terminal-v1.json` | VA |
| M07 | 已报 usage 峰价估算（全 cache-miss 上界）USD | 0.8705958 | 6.8800119 | 7.90× | 全部尝试 | RT `costs.all_attempts.adapter_reported.reported_usage_peak_cache_miss_upper_usd` | RC |
| M08 | Dynamic Resolve 阶段峰价 USD | — | 6.5111079 | 占 Dynamic 94.6% | — | RT `dynamic.costs.by_operation.resolve` | RC |
| M09 | 单题耗时 p50（含失败，离线串行）s | 2.370230 | 8.314747 | 3.51× | 400 | RT `elapsed_seconds.p50` | RC |
| M10 | 单题耗时 p95 s | 3.935324 | 12.403791 | — | 400 | LEVEL_E_RESULTS_V1 表 | VA |
| M11 | Resolve 阶段 p50 s | — | 6.062975 | — | — | RT `stage_seconds.resolve.p50` | VA |
| M12 | 类别 5 字面拒答 | 0.858586 | 0.808081 | −0.050505，CI [−0.101010, 0] | 99/臂 | OS `adversarial_literal_refusal` | VA |
| M13 | 混合规则 400 题均值（非事实正确率） | 0.515461 | 0.507886 | −0.007575，CI [−0.032061, +0.017161] | 400 | OS summary | VA |
| M14 | 物理请求 / usage 未知 | 851 / 8 | 1,261 / 10 | 合计 2,112 / 18 | — | RT；OS `runtime_cost` | VA |
| M15 | 未知 usage 完整预约 USD | 0.3424887 | 0.6097818 | 0.9522705 | 18 次 | LEVEL_E_RESULTS_V1 | VA |
| M16 | 已报输入 tokens / 成功项 | 6,603.579 | 51,849.473 | — | — | LEVEL_E_RESULTS_V1 | VA |
| M17 | 共享 Build：920 请求，已知峰价 USD 6.6141915 | — | — | — | — | `level-e-shared-build-cost-v1.json` | DOC→Gate 2 前核 |
| M18 | 十阶段累计：3,975 请求，预约 USD 197.6108655，已报峰价 USD 18.1208100 | — | — | — | — | LEVEL_E_RESULTS_V1 | DOC |

费用写法固定为："按已报 usage 与全 cache-miss 峰价估算，非实际账单；18 次 usage 未知请求另列预约"。

## RQ3 — 证据保留（Source Recall 为**来源覆盖代理**）

K 单位 = Memory 排名；分子 = 唯一 Source Turn 覆盖；每臂 399/400 可映射，1 题 null 不补零；失败记 0。

| ID | 指标 | Hybrid @5/@10/@20 | Dynamic @5/@10/@20 | 来源 | 等级 |
|---|---|---|---|---|---|
| M20 | initial | 0.601211 / 0.681934 / 0.730436 | 0.598204 / 0.679678 / 0.725173 | OS items `source_recall` | RC |
| M21 | effective | N/A | 0.516670 / 0.534318 / 0.536511 | 同上 | RC |
| M22 | answer delivered | 0.601211 / 0.681934 / 0.719367 | 0.516670 / 0.534318 / 0.535884 | 同上 | RC |
| M23 | 解析后失去 ≥1 标注 Source Turn 的题数 | — | **107**/400（**非误删率**） | `experiments/evidence-flow-20261109/audit.json` summary | VA |
| M24 | Answer 预算再失去标注来源的题数 / Answer 截断题数 | — | 2 / 12 | 同上 | VA |
| M25 | 成功子集不限 K 覆盖 initial→expanded→effective→delivered | — | 0.745732 → 0.787377 → 0.552580 → 0.551077 | 同上（口径与 M20–22 不同，不可混用） | VA |
| M26 | 来源盲审：原文支持 | 250/343 (72.89%) | 233/307 (75.90%) | `source-review-summary.json` | VA |
| M27 | 来源盲审配对：原文支持 D−H | — | +0.033670，CI [−0.010101, +0.077525]，297 对（28 改善 / 18 退化） | `source-review-paired.json` | VA |

盲审写法固定为："每项一名非作者 AI，条件分母，非人工/教师真值"。

## 历史与开发（研究演进背景，不与 E25 做因果比较）

| ID | 指标 | 值 | 口径 | 来源 | 等级 |
|---|---|---|---|---|---|
| M30 | E12 757 题完整分母 F1：Full Text / Vector / Hybrid / Dynamic | 0.464869 / 0.519714 / 0.521886 / 0.515133 | 旧 Run `a2abe1fb…`，conv-26/30/41/42；失败与 unknown 记 0（Hybrid 为下界，上界 0.523207） | `3e64811:docs/team-v2/research-evidence.json`：successful_qa_mean × 成功数 / 757 重算一致；Hybrid bounds 字段 [0.521886, 0.523207] | RC（**由 Phase 0 的 DOC 升级**） |
| M31 | E12 成功子集 QA：H / D；D 成功 | 0.524659 / 0.550008；709/757 | — | 同上 | VA |
| M32 | E12 共同成功 705 对配对差 | +0.026074（136 胜 / 110 负 / 459 平） | 成功子集，受选择影响 | 同上 `paired` | VA |
| M33 | E12 查询费用估算 CNY：H / D | 9.597679 / 98.930522 | 含 cache-hit/miss 报价，**与 M07 USD 峰价口径不同** | V2-05.md | DOC |
| M34 | E22 Level C v1 普通 80 题：H / D | 0.399883 / 0.228329 | D 49 输入失败保留 | LEVEL_C_RESULTS.md | DOC |
| M35 | E23 input v2 普通 80 题：H / D；差；CI | 0.401172 / 0.444702；+0.043530；[−0.008095, 0.095318] | **E22→E23 同时改三项配置**，不可单因素归因 | LEVEL_C_INPUT_V2_RESULTS.md | DOC |
| M36 | 11-09 已曝光 12 题回归：普通 10 题 F1 | 0.517381 → 0.456314；差 −0.061067；CI [−0.313876, +0.233333] | **回归，非留出**；62 次请求 | `experiments/live-boundary-20261109/results.json` | VA |
| M37 | 时间解析边界 | 11/21 → 21/21 | 工程解析回归，非 QA | evidence-flow-20261109 | VA |

## 扩展（研究候选；报告中仅定性，数字留 Supplement）

| ID | 指标 | 值 | 来源 | 等级 |
|---|---|---|---|---|
| M40 | 757 回放 Graph 两跳：来源代理 0.819920 → 0.823098，交付 0.773801 不变 | — | `docs/m5-development/EXPERIMENT_RESULTS.md:26–27` | DOC |
| M41 | Compression wire：完整 messages 代理 tokens 5,558,932 → 5,557,306（−0.02925%） | — | 同上 :36 | DOC |
| M42 | Adaptive：交付来源代理 −0.029349 | — | 同上 :29 | DOC |
| M43 | Temporal soft priority：交付代理 Δ 0 | — | 同上 :30 | DOC |
| M44 | E1 路由 757 项全选 Dynamic，配对增益 0 | — | research-evidence.json `e1` | VA |
| M45 | E5 缓存：冷编码 CPU −64.22%，本地检索 CPU −57.36%，provider token/费用节省 0 | — | research-evidence.json `e5` | VA |
| M46 | Sidecar（conv-26/30）：503 Memory、63,057 候选对全部 unknown；68 参考单元信息性正确 0/68 | — | `codex/sidecar-research-20261107:research/sidecar-20261107/REPORT.md` | DOC（未进 main） |

## 工程

| ID | 指标 | 值 | 来源 | 等级 |
|---|---|---|---|---|
| M50 | main `5519dd2` GitHub Actions "Checks" | completed / success | run 42582449214（负责人提供，本审计 API 复核） | VA |
| M51 | main `5519dd2` 本地公开离线回归（排除 live_model / local_embedding / controlled_data） | 第 1 次：1,018 项全部 `.`，无 F/E，摘要行与退出码未捕获；第 2 次（含 JUnit 与退出码）运行中 | `/tmp/m5audit/pytest-5519dd2*.txt` → 完成后复制入 `audit/` | PEND |
| M52 | PR #41 作者端记录：1018 passed、28 deselected、899.01 s | — | `docs/release/PRODUCT_FREEZE.md` | VA |
| M53 | 六份真实 MemoryExport：2,031 Memory / 37,445 关系 / 1,465 引用 Source | — | `six-memory-exports-manifest.json` | VA |
