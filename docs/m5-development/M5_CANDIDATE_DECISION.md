# M5 候选采用决策

2026-11-05 最新终态：conv-44 与六份严格 JSON 均已完成独立复核。锁定的独立 Level E 已单次冻结 800 项，根代理与非作者终态审计通过后才读取 Gold 评分。H/D 成功 394/389（每臂400）；类别1–4完整分母 F1 为 0.402606/0.409151，差值区间跨零；类别5字面拒答单列。本阶段 2,112 请求、预约 USD105.4516575，末段 HTTP402 及18次未知 usage 预约保留；没有重跑。800项来源盲审、条件语义汇总与私有白名单归档已完成；来源支持297可判定对净增10对，区间仍跨零。独立复核和14项底稿见[最终交付索引](FINAL_DELIVERY_EVIDENCE_INDEX_V1.md)。当前结果与测量边界见 [Level E 结果](LEVEL_E_RESULTS_V1.md)。下文历史检查点保留各自时点，不代表本次终态。

本分支是开发候选，不是Release冻结分支。建议最终M5保留现有生产动态关系/多版本、完整JSON导出，以及可关闭的Graph浏览和状态来源面板。压缩、自适应、Graph检索和时间优先保留为实验模块，默认关闭；五种采用状态见BONUS_FEATURES.md。

2026-11-05 当前检查点：后续全disabled input v2开发结果已完成，普通80题完整分母F1为Hybrid0.401172、Dynamic0.444702，配对区间跨零，Dynamic成本约10.10倍。最终Level E建议固定两臂、Bonus全关，Hybrid作为默认候选、Dynamic作为显式可选候选；这不是生产默认切换或最终配置锁。旧Level C下方负结果继续保留。五份严格JSON已完成；conv-44抽取34/34、392 Memory，关系恢复后383/384任务成功，仍有1失败，第六份JSON尚缺。见[input v2结果](LEVEL_C_INPUT_V2_RESULTS.md)及[恢复结果](CONV44_RELATION_RECOVERY_V1_RESULTS.md)。当前没有读取留出QA/evidence/answers，未锁配置或启动Level E。下方构建进度与费用属于早期决策时点。

没有发现经本轮真实答案验证的总体质量突破。Level B中Graph仅改善扩展候选来源代理，最终Answer包无增益；Adaptive差−0.029349，拒绝默认采用；Compression含解码提示仅节省0.02925%代理tokens；Temporal无总体代理变化。B5/B6和Bonus的Level C/D不晋级。

固定开发Level C真实H/D两臂200项已全部冻结后评分：普通80题完整分母F1为H0.399883、D0.228329，D−H为−0.171553；诊断20题为0.456503/0.293302。Dynamic49项输入限制失败不被删除或补跑。独立AI来源审阅200项、461条逐字引文通过；来源支持105/141，另10不确定、49失败。共同成功子集的正差值存在选择偏差，不能作为整体收益。完整结果、成本和模型alias限制见LEVEL_C_RESULTS.md；这些不是新的757题成绩或人工/教师真值。

PropMem直接上游配置REJECT，保留固定来源和合成方法探针；未运行真实抽取Canary，不外推整个方法家族无效。Hindsight保持Phase9结果，不作为新默认候选。

四开发Build冻结并严格导出。conv-43抽取完整且独立真实MiniLM索引已完成，获批关系阶段400/400任务终结为related，7,620条标签，根代理终态保护/来源/投影审计通过，未发布/查询/QA，非作者已独立重跑并核对完整审计对象一致，见[独立终态复核](RELATION_TERMINAL_REVIEW_V1.md)；见[关系终态](../../experiments/m5-development/conv43-relations-terminal-v1.json)。related仍非complete，标签数量不证明语义准确率。conv-44仍有1失败片段，唯一获批恢复三次仍命中时间原文契约，不再自动尝试。六份完整Build/导出与Level E仍缺；留出QA/evidence/answers未读。

60单位关系AI审阅50/60、Macro-F1 .766513，但无SUPERSEDE/CONFLICT参考覆盖；40题历史query-specific诊断25可判断、18/25集合完全一致，均不能当作新模型总体语义准确率。代码非作者范围复核已交付，P2修复后通过独立验证；尚未完成整个Release验收。

关系阶段已终结并通过根代理审计，接下来处理其余完整构建和验收。新付费阶段须有具体预算并获明确批准；各阶段余量不可自动转移；三阶段终态907请求、预约USD42.9743136及已知usage峰价上界USD5.3163252见[终态费用](../../experiments/m5-development/cost-ledger-terminal-v1.json)，实际账单未读取。最终少数策略、实现、模型、Prompt、参数、评分脚本和预算锁定后才做一次独立留出评价，查看答案后不再调参并称独立测试。Release冻结、生产整合、报告/展示/ZIP属于下一轮，不自动执行远端写入。

未识别关联Notion记录，未同步或标记完成。当前状态和全部提交入口见HANDOFF.md。

用户随后确认最终评测使用DeepSeek-V4.1-Flash-1017并禁止thinking，见[模型要求](MODEL_REQUIREMENTS.md)。本次resolution low和原关系high保留真实配置与结果，不作为全链disabled的最终成绩；后续新阶段须独立准备和获得所需预算授权。
