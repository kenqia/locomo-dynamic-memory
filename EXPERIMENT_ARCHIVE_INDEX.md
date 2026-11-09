# E0–E25 实验档案索引

2026-11-09 新增[证据损失与边界回归](experiments/evidence-flow-20261109/README.md)：400 条冻结 Dynamic Trace 只读诊断、20 案完整证据包、21 个时间解析边界前后对比与固定决策 K 前缀回放。0 模型调用；已曝光数据上的回归，不属于 E25 独立测试，也不改变历史成绩。

原件保留，未重新评分/生成。机器索引 `experiments/personal-release/experiment-archive-index.json` 逐条保存文档SHA、配置、commit、Build/Run、分母、审阅及成本原字段；缺字段不补造。历史源文档未必在公开包，明确in_public_package；它们可从固定Git对象或本机受控归档定位。

| 实验 | 研究单元 | 来源（按记录时HEAD/本地SHA） | 归档/测量边界 |
|---|---|---|---|
| E0 | 10-19–10-19 系统构造与工程验证 | ENG-01.md, ENG-02.md, ENG-03.md, ENG-04.md, ENG-05.md, ENG-06.md, ENG-07.md, ENG-08.md | 免费校验；原文/Gold受控；付费重跑不允许 |
| E1 | 10-20–10-20 首次完整构建与关系契约 | R15-01.md, R15-02.md, R15-03.md, R15-04.md | 免费校验；原文/Gold受控；付费重跑不允许 |
| E2 | 10-20–10-20 质量增量 A–E | R15-04.md | 免费校验；原文/Gold受控；付费重跑不允许 |
| E3 | 10-20–10-21 10 题四策略与输出修复 | R15-05.md, R15-06.md | 免费校验；原文/Gold受控；付费重跑不允许 |
| E4 | 10-21–10-21 证据覆盖优化与回滚 | R15-07.md, R15-08.md | 免费校验；原文/Gold受控；付费重跑不允许 |
| E5 | 10-21–10-21 五策略现状展示 | SHOW-01.md | 免费校验；原文/Gold受控；付费重跑不允许 |
| E6 | 10-27–10-29 五组动态机制消融 | DYN-01.md, DYN-02.md, DYN-03.md, DYN-04.md | 免费校验；原文/Gold受控；付费重跑不允许 |
| E7 | 10-29–10-29 回答诊断与 Top7 | DIAG-01.md, TOP7-01.md, TOP7-02.md, TOP7-03.md, TOP7-04.md | 免费校验；原文/Gold受控；付费重跑不允许 |
| E8 | 10-29–10-30 原文分块替代 | VERB-01.md | 免费校验；原文/Gold受控；付费重跑不允许 |
| E9 | 10-29–10-30 Top145 系列 | TOP145-01.md, TOP145-02.md, TOP145-03.md, TOP145-04.md | 免费校验；原文/Gold受控；付费重跑不允许 |
| E10 | 10-31–11-01 RC1/RC2 与 Production v1 | INT-01.md, INT-02.md | 免费校验；原文/Gold受控；付费重跑不允许 |
| E11 | 11-01–11-01 三轮预算 smoke | V2-01.md | 免费校验；原文/Gold受控；付费重跑不允许 |
| E12 | 11-01–11-03 757 题全量基线 | V2-02.md, V2-03.md | 免费校验；原文/Gold受控；付费重跑不允许 |
| E13 | 11-03–11-03 失败图谱与 H/D 配对 | V2-04.md, V2-05.md | 免费校验；原文/Gold受控；付费重跑不允许 |
| E14 | 11-03–11-03 E1 路由 / E5 缓存 / E6 表示 | V2-06.md, V2-07.md, V2-08.md, V2-09.md | 免费校验；原文/Gold受控；付费重跑不允许 |
| E15 | 11-03–11-03 Phase 5 canary 与 Phase 6 | PHASE5_CANARY_RESULTS.md, PHASE6_E7_OFFLINE_RESULTS.md, PHASE5_CANARY_EVIDENCE_REVIEW.md, PHASE5_LIVE_EXECUTOR_REVIEW.md | 免费校验；原文/Gold受控；付费重跑不允许 |
| E16 | 11-03–11-03 Phase 7 事实审阅 | PHASE7_FACTUAL_QUALITY_REVIEW.md, PHASE7_FAILURE_ATTRIBUTION_AND_CANDIDATE.md | 免费校验；原文/Gold受控；付费重跑不允许 |
| E17 | 11-03–11-03 Phase 7 D1/D2 消融 | PHASE7_SYSTEM_QUALITY_AUDIT.md | 免费校验；原文/Gold受控；付费重跑不允许 |
| E18 | 11-04–11-04 Phase 8 CE 重排 | PHASE8_RESULTS.md, PHASE8_DECISION.md | 免费校验；原文/Gold受控；付费重跑不允许 |
| E19 | 11-04–11-04 Phase 9 Hindsight / Qwen3 | PHASE9_RESULTS_AND_DECISION.md, PHASE9_HINDSIGHT_SOURCE_AUDIT.md | 免费校验；原文/Gold受控；付费重跑不允许 |
| E20 | 11-04–11-04 M5 Level A/B 与关系审阅 | EXPERIMENT_RESULTS.md, BONUS_FEATURES.md | 免费校验；原文/Gold受控；付费重跑不允许 |
| E21 | 11-04–11-04 有效选择诊断 | DYNAMIC_TRUTH_PROTOCOL.md | 免费校验；原文/Gold受控；付费重跑不允许 |
| E22 | 11-04–11-04 Level C v1 | LEVEL_C_RESULTS.md | 免费校验；原文/Gold受控；付费重跑不允许 |
| E23 | 11-04–11-04 Level C input v2 | LEVEL_C_INPUT_V2_RESULTS.md | 免费校验；原文/Gold受控；付费重跑不允许 |
| E24 | 11-04–11-05 留出集构建与恢复 | CONV44_SIXTH_EXPORT_SUCCESSOR_V1_REVIEW.md, CONV44_RELATION_SUCCESSOR_V1_RESULTS.md, CONV44_SIXTH_EXPORT_REVIEW.md | 免费校验；原文/Gold受控；付费重跑不允许 |
| E25 | 11-05–11-05 Level E 独立留出评测 | LEVEL_E_RESULTS_V1.md, FINAL_DELIVERY_EVIDENCE_INDEX_V1.md | 免费校验；原文/Gold受控；付费重跑不允许 |

## 研究者与评审者入口

- `scripts/personal-release verify-public-evidence --manifest public-evidence-manifest.json --directory .`：包内逐文件SHA/JSON，无key/原文。
- `scripts/personal-release verify-private-archive --manifest <private-archive-manifest.json> --directory <archive-dir>`：合法本机受控成员SHA、安全路径/JSON/SQLite检查，不执行历史runner。
- `scripts/personal-release replay-offline-demo`：只读Synthetic文件，不能冒充真实答案分数。
- `scripts/personal-release run-tests`：当前工程离线全仓；公开包使用`--public`明确排controlled_data。

E12旧757与E22开发100/E23同100新配置/E25留出400分开。类别5字面拒答、Source Recall代理、AI标签/教师真值、费用预约/已报usage/实际账单分开。完整分母失败记零，不以成功子集替代。

E0–E14源为3e64811；E15–E19研究工作区97bfaaa及未提交文件，source_ref不存在时tracked_at_recorded_head=false，以本地SHA和归档为准。E2仅共享R15来源，精确独立raw身份partial。Hindsight外部完整后端未完成，不是App正式功能。

主档35,440成员/2,301,324,861bytes，SHA bfb7f58a42cf5f76e35db580f06e215a3bc15beb691892d781a02fa0251f5ddd；源码补档2,446成员/5,880,956bytes，SHA 546a29a16cf4a7cffd40200a7a82cdb03112eb43833f83320e676f2e77200eef。完整路径及恢复验证见LOCAL_ARCHIVE_AND_CLEANUP_PLAN。受保护日志/凭据/caches未复制，原位保留；既有Level E白名单原档也完整保留。
