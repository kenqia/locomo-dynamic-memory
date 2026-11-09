# M5 最终交付证据清单

2026-11-05 最新终态：conv-44 与六份严格 JSON 均已完成独立复核。锁定的独立 Level E 已单次冻结 800 项，根代理与非作者终态审计通过后才读取 Gold 评分。H/D 成功 394/389（每臂400）；类别1–4完整分母 F1 为 0.402606/0.409151，差值区间跨零；类别5字面拒答单列。本阶段 2,112 请求、预约 USD105.4516575，末段 HTTP402 及18次未知 usage 预约保留；没有重跑。800项来源盲审、条件语义汇总与私有白名单归档已完成；来源支持297可判定对净增10对，区间仍跨零。独立复核和14项底稿见[最终交付索引](FINAL_DELIVERY_EVIDENCE_INDEX_V1.md)。当前结果与测量边界见 [Level E 结果](LEVEL_E_RESULTS_V1.md)。下文历史检查点保留各自时点，不代表本次终态。

2026-11-05。**总任务尚未完成，未冻结 Release。** 本页是作者维护的公共证据索引，不是独立验收报告。各项范围内已有的非作者复核不能替代最终整体验收。当前没有 push、PR、main 合并或部署；未识别关联 Notion 记录，未同步或标记完成。

最新检查点：conv-44抽取34/34、392 Memory；原关系374/384成功后，新增获批恢复修复9/10，目前383成功/1失败、7,114条关系。两轮失败终态与历史保护均通过根代理和非作者审计。第六份JSON、最终配置锁定和Level E仍缺；剩余单任务正在免费准备，未获新调用授权。八个获批阶段累计1,862请求/预约USD92.1054516/已知usage峰价上界USD10.3629372，历史7 Unknown预约USD0.3500316保留。见[恢复结果](CONV44_RELATION_RECOVERY_V1_RESULTS.md)与[累计费用](../../experiments/m5-development/cost-ledger-including-conv44-relation-recovery-terminal-v1.json)。下表和旧验证段落的准备/费用数值保留各自历史时点，以本检查点为当前状态。

下表对应最终交付的14项要求。既有六个付费阶段及本地构建补齐以[当前关系准备交接](../../M5_CONV44_RELATIONS_V1_HANDOFF.md)、[v2终态交接](../../M5_BUILD_REPAIR_HANDOFF.md)、[input v2 终态](LEVEL_C_INPUT_V2_RESULTS.md)和[五段导出](FIVE_BUILD_EXPORT_V1.md)为准。旧文档与旧 run-manifest 保留各自历史时点。recovery v2获批三次均失败；successor v3随后独立获批并首请求成功，新增9 Memory，现34/34片段、392 Memory，见[v3真实结果](CONV44_SUCCESSOR_V3_RESULTS.md)。

| # | 要求 | 公共证据 | 当前状态与缺口 |
| --- | --- | --- | --- |
| 1 | 开发分支每个 commit | [当前交接](../../M5_BUILD_REPAIR_HANDOFF.md)、Git 历史 | 本地整合 input v2 `aba95ca` 与原开发 `0aae59c`，合并提交 `bcbf479`；新补齐成果增量提交。未发布，原两工作树冻结；旧 commit-history.txt 只覆盖其生成时点。 |
| 2 | 新增和修改文件 | [input v2 冻结清单](../../experiments/m5-development/level-c-input-v2-terminal-manifest-v1.json)、[当前终态工件](../../experiments/m5-development/conv44-isolated-recovery-v2-terminal-manifest-v1.json)、[实现矩阵](IMPLEMENTATION_MATRIX.md) | 各阶段清单分别绑定 producer、公开/私有工件与源码；当前清单排除自身，Git 历史补充文件变更。私有原文、导出与答案不提交。 |
| 3 | 四类 Bonus 完成情况 | [五状态矩阵](BONUS_FEATURES.md)、[实现矩阵](IMPLEMENTATION_MATRIX.md) | A 状态/版本/来源、B Graph、C Compression、D Adaptive/Temporal 均列明实现、测试、实验收益、演示和生产资格。工程完成不等于质量收益或整体验收通过。 |
| 4 | 真实实验 | [input v2 结果](LEVEL_C_INPUT_V2_RESULTS.md)、[实验结果](EXPERIMENT_RESULTS.md)、[实验协议](EXPERIMENT_PROTOCOL.md) | 六臂各757题离线回放、60单位历史关系审阅、40题历史有效选择诊断完成；旧Level C与新input v2固定100题H/D各200项均已终结。Bonus真实QA与Level E未完成。 |
| 5 | 真实指标 | [input v2数值](../../experiments/m5-development/level-c-input-v2-results-v1/README.md)、[来源审阅](LEVEL_C_INPUT_V2_RESULTS.md)、[旧Level C](LEVEL_C_RESULTS.md) | 新普通80题完整分母F1 H 0.401172 / D 0.444702，诊断20题0.434314 / 0.473472；配对区间均跨零。H99/D100项成功，输入失败0；200项AI来源审阅，不是教师真值。旧49项输入失败保留，不改写旧分数。 |
| 6 | 未测项 | [交接缺口](HANDOFF.md)、[实验结果](EXPERIMENT_RESULTS.md)、[模型要求](MODEL_REQUIREMENTS.md) | 完整事实召回/保留、新模型有效选择准确率、Bonus真实QA、压缩模型解码质量、实际账单、本地硬件货币成本与独立留出泛化仍未测。 |
| 7 | 历史757题与新成绩分开 | [input v2结果](LEVEL_C_INPUT_V2_RESULTS.md)、[实验协议](EXPERIMENT_PROTOCOL.md) | 旧Run四策略F1为0.464869/0.519714/0.521886/0.515133；两轮Level C均固定100题。757题离线回放是来源代理，不能冒称新QA或直接相减宣称改进。 |
| 8 | 是否真正改善质量 | [input v2采用边界](LEVEL_C_INPUT_V2_RESULTS.md)、[采用决策](M5_CANDIDATE_DECISION.md) | 新普通题D−H为+0.043530、95%区间跨零；共同确定来源60对仅净改善1，引用支持61对差0。尚无稳定事实质量收益证据；旧输入限制下的负结果独立保留。 |
| 9 | 质量证据、成本、最大已观察收益与退化 | [input v2结果](LEVEL_C_INPUT_V2_RESULTS.md)、[实验结果](EXPERIMENT_RESULTS.md)、[费用分析](COST_ANALYSIS.md) | input v2 Dynamic usage峰价成本约Hybrid的10.10倍。Graph扩展来源代理改善未转成最终包收益；Compression完整请求代理节省0.02925%；Adaptive来源代理退化−0.029349；Temporal无总体代理增益。均不冒充Bonus QA收益。 |
| 10 | 推荐最终M5 | [采用决策](M5_CANDIDATE_DECISION.md)、[Bonus状态](BONUS_FEATURES.md) | 建议保留现有生产动态关系/多版本与完整JSON；Graph浏览和来源timeline作为可关闭展示候选。PropMem固定上游配置拒绝直接采用，Hindsight保留Phase9。尚未完成Release验收。 |
| 11 | 默认关闭 | [Bonus状态](BONUS_FEATURES.md)、[采用决策](M5_CANDIDATE_DECISION.md) | Graph检索、Compression、自适应和时间优先默认关闭；图浏览checkbox默认false，研究API须显式访问。问答默认仍为原Dynamic，不自动启用研究模块。 |
| 12 | 六段完整导出与独立测试 | [五段严格导出](FIVE_BUILD_EXPORT_V1.md)、[v3继承与恢复方案](CONV44_SUCCESSOR_V3.md)、[conv-44关系准备](CONV44_RELATIONS_V1.md) | 四开发Build只读导出；conv-43仅新scratch副本complete并严格导出，原库仍related、历史relation high保留。conv-44新successor已34/34抽取成功，新索引ready且384关系任务已准备，disabled关系执行及完整导出尚缺，六段完整导出和一次Level E仍缺；留出QA/evidence/answers未读。 |
| 13 | 付费与余额 | [当前交接](../../M5_BUILD_REPAIR_HANDOFF.md)、[input v2终态](LEVEL_C_INPUT_V2_RESULTS.md)、[v3继承与恢复方案](CONV44_SUCCESSOR_V3.md) | 六个已批阶段均终结，累计1433请求/预约USD70.9596105/已知usage峰价上界USD7.9158096；不是账单。关系7项Unknown保留USD0.3500316预约。新恢复3次均时间校验失败、预约USD0.1335687/usage峰价USD0.0100968/Unknown0，不再自动追加同配置尝试。 |
| 14 | 下一轮冻结、整合与验收 | [当前交接](../../M5_BUILD_REPAIR_HANDOFF.md)、[模型要求](MODEL_REQUIREMENTS.md)、[Level E准入](LEVEL_E_GATE.md) | disabled后继Build契约已离线准备并复核；conv-44抽取已获批成功，本地索引和关系任务准备已完成，接着批准并执行独立关系预算，再完整导出；锁定实现、策略、模型、Prompt、参数、评分和成本政策后才做一次Level E。Release冻结、生产整合、最终报告/展示/ZIP与整体验收尚未完成。 |

## 当前验证边界

本地五段导出只验证来源、schema、索引、投影与版本身份，不代表关系语义准确率或留出QA。历史recovery v2已获批执行且未通过时间校验；其独立终态复核与归档完成，一次性marker实际拒绝再次执行。任何新增付费阶段仍须按任务书第10节独立批准。v3新增指导、安全诊断与继承入口已通过[非作者代码复核](CONV44_SUCCESSOR_V3_REVIEW.md)；全仓842 passed，最终新增helper回归另在14项子集中通过。真实准备与零请求拒绝证据见[v3准备检查](../../experiments/m5-development/conv44-successor-v3-preparation-v1.json)。历史v2终态工件继续保留。当前conv-44新索引和384关系任务真实准备已完成，代码本地提交 `82a9d25`；最终针对性96 passed、非作者代码复核27 passed，根代理21项实际准备检查通过。新关系付费执行未获批，账本0请求；见[当前交接](../../M5_CONV44_RELATIONS_V1_HANDOFF.md)。未识别关联Notion任务，未同步或标记完成。
