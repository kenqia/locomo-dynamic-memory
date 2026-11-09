# M5 总任务完成性审计

2026-11-05 最新终态：conv-44 与六份严格 JSON 均已完成独立复核。锁定的独立 Level E 已单次冻结 800 项，根代理与非作者终态审计通过后才读取 Gold 评分。H/D 成功 394/389（每臂400）；类别1–4完整分母 F1 为 0.402606/0.409151，差值区间跨零；类别5字面拒答单列。本阶段 2,112 请求、预约 USD105.4516575，末段 HTTP402 及18次未知 usage 预约保留；没有重跑。800项来源盲审、条件语义汇总与私有白名单归档已完成；来源支持297可判定对净增10对，区间仍跨零。独立复核和14项底稿见[最终交付索引](FINAL_DELIVERY_EVIDENCE_INDEX_V1.md)。当前结果与测量边界见 [Level E 结果](LEVEL_E_RESULTS_V1.md)。下文历史检查点保留各自时点，不代表本次终态。

## 当前执行状态（2026-11-04）

Level C 开发集真实实验已终结：固定80普通+20诊断、Hybrid/Dynamic共200项；151成功、49输入限制失败，421物理请求，Unknown用量0。已完成全部生成冻结后的开发Gold评分、四份Build与来源不变的终态审计，以及200项独立AI来源审阅。普通题完整分母F1为Hybrid 0.399883、Dynamic 0.228329；这是本轮小样本，不是新的757题成绩。来源支持105/141，另10项不确定、49运行失败；AI审阅不代表人工或教师真值。完整结果见 [Level C真实结果](LEVEL_C_RESULTS.md)。

本次QA独立封顶1,500请求/USD130.9824，终结预约USD19.3089549，reported usage峰价cache-miss上界USD1.1698209；实际账户账单未读取。剩余容量不自动授权补跑或其他阶段。已终结抽取/恢复另为78请求、预约USD3.4624767；加上关系终态408请求，三阶段共907请求、预约USD42.9743136、已知usage峰价上界USD5.3163252，7项终态transport_unknown预约USD0.3500316保留，见[终态费用](../../experiments/m5-development/cost-ledger-terminal-v1.json)。旧cost-ledger.json原样保留为历史快照。

conv-43关系阶段已终结为related：400/400任务成功、7,620条关系标签；408次物理请求（401 response_received、7 transport_unknown），保守预约USD20.2028820、已知usage峰价上界USD3.9199638，未知预约USD0.3500316保留。终态审计通过保护表、其他Build、来源/关系契约及投影核对，确认未publish、无query/evaluation。原relation thinking high如实保留，不代表全链disabled；conv-44仍failed，留出QA/evidence/answers未读，两份留出均非complete。公共结果见[关系终态审计](../../experiments/m5-development/conv43-relations-terminal-v1.json)，非作者已独立重跑并核对完整审计对象一致，见[独立终态复核](RELATION_TERMINAL_REVIEW_V1.md)，总任务保持开发候选。

2026-11-04，基于任务书、课程PDF第9–13页及当前代码/实验工件。结论：未完成总目标，保持开发候选。以下“通过”仅在明确证据范围内成立，不等于Release、课程验收或非作者批准。

| 任务书章节 | 当前证据 | 判定与仍需完成 |
| --- | --- | --- |
| 0 总目标 | 四类Bonus、两轮757回放、真实抽取、测试、工件 | 部分完成；Level C真实QA已完成，完整六Build和独立Level E仍缺 |
| 1 课程来源 | PDF重新读取，CONTEXT/ADR、实现矩阵 | 通过来源核查；用户已确认最终使用V4.1-Flash-1017、thinking disabled；既有low/high实验单列，不冒称最终符合配置 |
| 2 隔离开发 | codex/m5-final-development-20261104，独立SQLite、ledger；主仓HEAD仍f5a5dfd | 通过；无push/merge，历史DB SHA保持 |
| 3.1 六数据与JSON | six-conversation-import-corrected；四开发严格memory-export-v2；live-extraction-summary | 部分；conv-43原库extracted、独立副本索引及400/400关系任务related；conv-44 failed，两留出均非complete且无严格完整导出 |
| 3.2 状态与有效证据 | test_relations/test_queries/test_query_evidence_delivery，来源/条件/历史/冲突合成测试 | 机制通过；真实语义与所有课堂案例端到端未全部独立核验 |
| 3.3 动态准确率 | 60预测盲选单位，独立AI参考双方引文验证，50/60，Macro-F1 .766513 | 关系对测量完成；非人工/教师真值，SUPERSEDE/CONFLICT覆盖0；query-specific历史诊断25/40可评分、18/25严格集合；新模型有效选择未测 |
| 4 Bonus A | timeline API/UI；当前/历史/冲突/Unknown合成Browser，真实conv-26图来源 | 实现与局部演示通过；新增6项synthetic端到端API/Query测试覆盖取消计划和共同参与者；不是Browser或真实模型语义评价 |
| 5 Bonus B | graph_view/neighborhood/expand_relations；实际两跳测试；444题两跳路径 | 浏览/有界遍历通过；Graph与no-resolution真实QA机制消融未测 |
| 6 Bonus C | 精确字段/order/hash展开，wire解码，完整消息计数 | 可逆机制通过；事实/人物/事件正确率和模型解码QA未测，默认关闭 |
| 7 Bonus D | route/query_interval/prioritize；before/between保留；显式requested_date修复 | 局部机制通过；自适应来源退化，复杂时间语义未独立评价；默认关闭 |
| 8 PropMem | 固定官方commit/LICENSE/SHA、纯方法合成探针 | 条件候选已REJECT直接配置；未冒称完成抽取Canary或质量提升 |
| 9.1 历史基线 | 四策略757完整分母历史F1保留 | 通过冻结；Level C新100题另列，不替代历史757题 |
| 9.2/9.3 新策略/层级 | Level A/B，H/D/B1-B4六组每组757；B5/B6不晋级 | C已完成H/D两臂100题；D/E未运行，Bonus未取得晋级事实门槛 |
| 9.4 指标 | Recall@5/10/20、来源代理、tokens、资源、AI关系分数、真实抽取usage | Level C QA、延迟、错误人/事/时、拒答与支持率已有真实值及独立AI审阅；原子事实、新模型有效选择和账单仍未测 |
| 9.5 统计 | 每题/对话/类别差，2,000bootstrap、改善/退化ID | 来源代理与Level C QA分别配对统计；四暴露开发对话的探索性题目bootstrap，不外推跨对话泛化 |
| 10 费用 | BudgetTransport、并发单slot/金额/Unknown保留测试；抽取与恢复累计78请求 | 抽取/唯一恢复78次已终结；关系独立授权408次已终结；QA独立授权421次已终结，余量不可转移或自动补跑 |
| 11 自动化/Web | full-offline-final-v4 634/4；预算历史另3；最新16；受控全流程Browser、真实图Browser | 已有范围通过；新增6项合成端到端通过；最后一轮全仓v7：664 passed/4 deselected，325.80秒；无独立真实QA恢复成绩 |
| 12 交付 | 12份要求文档、环境/数据/Build/策略/逐题/成本/失败/测试/命令/SHA | 本地工件就绪；私有引用与原文留var、详细gzip忽略；克隆不自动带私有数据 |
| 13 并行实施 | 分工AI盲审产生真实A/B文件；已交付范围明确的非作者代码复核及真实AI盲审 | 不把协议确认算review；CODE_REVIEW_V6已实际交付、P2修复后37项复核通过；不等于整个Release批准 |
| 14 采用规则 | BONUS_FEATURES与CANDIDATE_DECISION分列五种状态 | 通过诚实分列；无实验收益的模块不默认采用 |
| 15 最终交付 | HANDOFF、changed-files、commit列表、成本/留出状态 | 开发候选已交接；不得据此标总任务完成；Release/报告/ZIP为下一轮 |

## 本轮发现和实际修复

可选时间排序此前忽略QueryRequest.requested_date，导致排序使用now的cutoff而解析使用明确日期。修复优先传入同一日期，保存m5_interval；新回归与isolated mutation验证。新增预算并发与金额先于次数耗尽的测试证明硬上限，不把测试分数当实际模型质量。

## 下一步边界

conv-43关系阶段已终结并通过根代理终态审计，非作者已独立重跑并核对完整审计对象一致，见[独立终态复核](RELATION_TERMINAL_REVIEW_V1.md)；保留原high与所有历史工件，不重启。conv-44唯一获批恢复已终结且仍failed，原67成功片段和785条已接受Memory不变；不放宽时间原文契约、不追加尝试。当前关系授权只到related，不publish/query/QA。

Level C已完成200项生成、完整冻结后Gold评分、终态审计及200项独立AI来源审阅，49项输入失败计入完整分母；不是新757题成绩或教师真值。普通题D−H为−0.171553，不晋级Bonus、Level D/E。三个新增工具的非作者新鲜验证分别24/36/7项通过，原P2均关闭；生产回归仍以full-offline-final-v7的664/4为准。

完整六份Build/导出、符合已确认全关闭thinking设置的最终评测、候选锁定后的独立Level E及最终Release验收仍缺。新的付费阶段必须先准备具体可审阅边界并取得明确授权。保留原始实验工件和历史提交，当前交接与成本文档不再把历史待授权描述当现状。
