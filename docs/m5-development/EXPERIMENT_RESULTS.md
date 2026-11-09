# 已执行实验与测量边界

2026-11-09 后续真实调用：[小规模时间/实体回归](../../experiments/live-boundary-20261109/README.md)完成 62 次请求。10 道普通题失败计零 F1 0.517381→0.456314，共同成功 8 题 0.563393→0.445393；没有总体收益证据。抽取窗口恢复两条但上下文引用不足，AI 仅 9/18 对有效且漏检日期。已收到莫远序（2026-11-09）提交的18对核查，条件判断待裁定；原 E25/Level C 冻结分数不变。

2026-11-09 增量记录：[证据损失诊断与边界回归](../../experiments/evidence-flow-20261109/README.md)只读回放既有 Level E，并验证查询时间和新 Build 的显式上下文契约；没有付费请求、没有新 QA 成绩。原 E25/Level C 的冻结结果保留。

2026-11-05 最新终态：conv-44 与六份严格 JSON 均已完成独立复核。锁定的独立 Level E 已单次冻结 800 项，根代理与非作者终态审计通过后才读取 Gold 评分。H/D 成功 394/389（每臂400）；类别1–4完整分母 F1 为 0.402606/0.409151，差值区间跨零；类别5字面拒答单列。本阶段 2,112 请求、预约 USD105.4516575，末段 HTTP402 及18次未知 usage 预约保留；没有重跑。800项来源盲审、条件语义汇总与私有白名单归档已完成；来源支持297可判定对净增10对，区间仍跨零。独立复核和14项底稿见[最终交付索引](FINAL_DELIVERY_EVIDENCE_INDEX_V1.md)。当前结果与测量边界见 [Level E 结果](LEVEL_E_RESULTS_V1.md)。下文历史检查点保留各自时点，不代表本次终态。

## 当前执行状态（2026-11-04）

Level C 开发集真实实验已终结：固定80普通+20诊断、Hybrid/Dynamic共200项；151成功、49输入限制失败，421物理请求，Unknown用量0。已完成全部生成冻结后的开发Gold评分、四份Build与来源不变的终态审计，以及200项独立AI来源审阅。普通题完整分母F1为Hybrid 0.399883、Dynamic 0.228329；这是本轮小样本，不是新的757题成绩。来源支持105/141，另10项不确定、49运行失败；AI审阅不代表人工或教师真值。完整结果见 [Level C真实结果](LEVEL_C_RESULTS.md)。

本次QA独立封顶1,500请求/USD130.9824，终结预约USD19.3089549，reported usage峰价cache-miss上界USD1.1698209；实际账户账单未读取。剩余容量不自动授权补跑或其他阶段。已终结抽取/恢复另为78请求、预约USD3.4624767；加上关系终态408请求，三阶段共907请求、预约USD42.9743136、已知usage峰价上界USD5.3163252，7项终态transport_unknown预约USD0.3500316保留，见[终态费用](../../experiments/m5-development/cost-ledger-terminal-v1.json)。旧cost-ledger.json原样保留为历史快照。

conv-43关系阶段已终结为related：400/400任务成功、7,620条关系标签；408次物理请求（401 response_received、7 transport_unknown），保守预约USD20.2028820、已知usage峰价上界USD3.9199638，未知预约USD0.3500316保留。终态审计通过保护表、其他Build、来源/关系契约及投影核对，确认未publish、无query/evaluation。原relation thinking high如实保留，不代表全链disabled；conv-44仍failed，留出QA/evidence/answers未读，两份留出均非complete。公共结果见[关系终态审计](../../experiments/m5-development/conv43-relations-terminal-v1.json)，非作者已独立重跑并核对完整审计对象一致，见[独立终态复核](RELATION_TERMINAL_REVIEW_V1.md)，总任务保持开发候选。

2026-11-04。本轮Level C真实QA已全部冻结、评分并完成独立AI来源审阅，新增100题结果见上文及Level C报告。授权后的留出抽取属于Build阶段，单独记录。历史757题 F1 为 Full Text 0.464869、Vector 0.519714、Hybrid 0.521886、Dynamic 0.515133；不可与下表来源代理混用。

## 开发集离线交付回放

delivery-v1 及修复后 delivery-final-v2 均为757题、六组每组757项完成。证据映射适用753题，4题不可评分。各组共享生产 Expansion/Answer packing，未执行 Resolution、Embedding、Provider 或新答案。D 表示冻结 Dynamic 初始检索后的候选流程，不能称新端到端 Dynamic 质量。

| 组 | 初始全量来源覆盖 | 扩展全量来源覆盖 | would-be Answer 来源覆盖 | 相对D最终差 |
| --- | ---: | ---: | ---: | ---: |
| H 冻结Hybrid输入 | 0.782566 | 0.819588 | 0.773801 | 0 |
| D 冻结Dynamic输入 | 0.782566 | 0.819920 | 0.773801 | 0 |
| B1 D+两跳Graph | 0.782566 | 0.823098 | 0.773801 | 0 |
| B2 D+可逆wire分组 | 0.782566 | 0.819920 | 0.773801 | 0 |
| B3 D+自适应 | 0.782566 | 0.820916 | 0.744452 | -0.029349 |
| B4 D+时间优先 | 0.782566 | 0.819920 | 0.773801 | 0 |

B3最终变化：5题改善、25题退化、723题不变；配对题bootstrap95%区间[-0.042629,-0.016730]。四对话最终差分别-0.040609/-0.019048/-0.040415/-0.016667。它们是已曝光开发样本的探索性来源代理，不是事实准确率或未见数据置信区间。

Graph在444题中实际存在长度2的新增遍历路径；expanded候选新增7,689个Memory题次，但最终来源覆盖没有增益。无路径、候选上限、完整Memory预算、循环和跨Build拒绝均有合成测试。浏览图完成不等于多跳问答改善。

完整Answer messages 原计5,558,932个正则代理token；加入解码提示并仅在变小时启用后为5,557,306，减少1,626，约0.02925%。757题仅30题启用分组，其余保持原请求。文件候选包的4.1666%节省不再作为查询节省引用。Provider账单和模型解码质量未测。

历史Hybrid四条失败/Unknown行没有delivered_memories但保存answer_context_items，首版parity因此出现4条差异。delivery-analysis-final-v2改按明确的would-be包身份检查，757/757初始候选、扩展和packet一致；没有把这四条改为历史成功或真实送达。

## 工程、资源与数据

早期全仓full-offline-final-v4为634 passed、4 deselected，336.64秒；新增“预算停止保留先前物理失败”回归在其后另行3项通过，另有159项模型/构建/关系定向验证通过。既有Starlette/httpx弃用警告保留。

Chromium156.0.8078.4完成上传、构建失败/恢复、索引、发布、当前/历史、冲突、Unknown、原文、JSON、评测失败及新Graph面板，pageerrors/console_errors均0。模型/embedding受控，不是新真实模型成绩。首次checkbox定位失败保留，第二轮通过。

最终交付回放wall436.60秒、CPU286.06秒、进程峰值RSS2,363,464KiB。B1变换p50/p95约0.125/0.191秒，D约0.081/0.123秒。包含SQLite、Expansion、packing和消息计数，排除完整问答延迟。共享机器测量不作吞吐承诺；GPU未用。

四个冻结Build共1,237条Memory、884个被引用来源、22,691个关系。独立导出严格通过memory-export-v2，身份和SHA可复核。六段原文格式已检查；conv-43/44未读QA；授权抽取结果见后文，未complete或评价。

## 未测量项

Level C的官方QA F1、Answer Source Support、人物/事件/时间错误、正确/错误拒答、真实item延迟及Query/retry已报告usage金额均已测量，完整分母和限制见LEVEL_C_RESULTS.md。新的757题QA、Bonus真实QA、新模型query-specific effective-selection accuracy、757题原子事实召回/保留和实际账户账单仍not_measured。动态关系参考与历史预测评分见下节。

## 独立 AI 动态关系审核

两个独立 AI 审阅者分审不重叠的30+30单位；60个单位身份、双方端点引文逐字匹配均通过。没有人工双审一致性或教师真值。冻结参考后才读取历史预测，50/60正确，Accuracy 0.833333，Macro-F1 0.766513。参考标签覆盖RETAIN33、UPDATE4、undetermined23，SUPERSEDE/CONFLICT均0；不能评价未覆盖标签。系统未判断率28/60，缺失预测0。每对话Accuracy为0.8/0.8/0.866667/0.866667。

pair-local有效Memory预测未运行。query-specific以40题历史预测和独立AI参考补充，见末节；新模型预测仍未运行。首版dynamic-review-v1错误将未执行有效选择写成0%；dynamic-review-final-v2已修正，保留旧件用于审计，不引用旧0%作为质量分数。动态关系数据为历史Build的状态对样本，不是新模型关系提升。

## 真实开发数据演示

real-demo-v4使用conv-26严格导出和历史SQLite只读连接，复用生产Bonus路由与面板。Chromium156.0.8078.4通过图、状态维度、Memory JSON及引用原文查看，页面/控制台错误0，源库SHA前后一致。真实原文截图保存在忽略的var目录，不提交Git。早期ASGI误识别和选择器失败记录保留；密集边渲染问题已以明确显示的300边展示上限修正，完整邻域JSON仍可下载。

最终757题回放相对delivery-v1逐题核对，除wall_seconds外的紧凑语义/来源/token指标完全相同。详见replay-final-parity.json。没有因修复重写历史结果。

## 历史阶段：初次授权抽取结果（恢复前）

用户明确批准18USD/204次的conv-43/44 conversation抽取阶段后执行。conv-43：Build b19ae777b6e642c9855ea278ebd4cd81，34/34片段成功、402 Memory、300个引用来源，状态extracted。conv-44：Build bef9f685957843698b3083ff4cbc79a4，33/34成功、1失败，保存383 Memory、274个引用来源，状态failed。均未index、relate、publish或QA，不是complete Build，不提供memory-export-v2冒充完整导出。

75次物理请求全部返回usage，67次有效输出、8次invalid_output。保守预约USD3.3289083，按报告usage峰时cache-miss计算上界USD0.2173917；实际账单未读取。Unknown用量0，剩余预约容量USD14.6710917/129次，不能解释为同一失败片段自动获得额外尝试。conv-44 ordinal18三次均extraction_time_expression_required，保留失败，不截断或放宽时间契约。这是初次抽取终结时的状态；之后唯一恢复和关系/QA已获各自明确授权，最新结果见文末与上文。详见experiments/m5-development/live-extraction-summary.json与live-extraction-failures.json。

两段共785条已接受Memory完成schema、来源身份、session time与Build归属检查；这是结构与定位校验，不是事实语义准确率。仍未读取留出QA/evidence，也未评价。开发四份冻结Build和757题历史分母保持原样。


## 2026-11-04 问题相关有效选择历史诊断

新增query-applicability-v1：按身份哈希固定每开发对话10题、共40题，不依赖预测、成功状态或QA成绩。两位独立AI分别审核20题，未读预测/存储关系/生成答案/QA标准标注；逐字来源与选中Memory范围验证通过，参考先冻结后评分。30条参考sufficient、9条insufficient、1条conflict；25可评分、15因参考歧义单列，参考覆盖率62.5%，不是双审一致性或人工/教师真值。

可评分25题中严格有效集合18/25=0.72、集合Macro-F1=0.8542857、状态23/25=0.92。差异为4题多选、1题少选、2题缺失预测；所有40题内原有5个缺失预测，其中3题参考不确定而不评分。每对话严格集合：conv-26 7/9、conv-30 1/6、conv-41 6/6、conv-42 4/4。不能忽略不确定分母或用成功题子集冒充40题总体准确率。

这是旧Run a2abe1fb49be45ccba291728e1f6b3c9的真实解析预测重新接受独立诊断，不是新M5回答、不是757题新成绩。只评价给定候选Memory及完整来源内的适用性；来源恢复细节不等于Memory文本事实保留；严格集合对等效证据选择敏感。该历史诊断没有测量QA F1或全局事实召回；另行Level C已得到新QA，未证明总体增益。紧凑指标、逐题集合差、参考SHA和不确定分母均保留；原文和参考文件在var，不提交。

非作者CODE_REVIEW_V6.md已实际交付，深读预算、日期、恢复、评分模块并运行50项定向测试，发现并修复关系本地拒绝留下未发送检查点的P2；修复后独立37项通过。报告是明确范围内的代码复核，不能外推为Release或全部项目验收。


## 2026-11-04 单片段恢复授权与实际结果

用户在本聊天明确回复“接受恢复授权申请”，批准只恢复conv-44 ordinal18，最多新增3请求、预约上限USD0.2619648，仍受原18USD/204次全局账本约束。已绑定原计划SHA并执行一次；未index/relate/publish/QA，未读取留出答案或证据。

实际新增3请求全部返回usage，三次均在domain_validation以extraction_time_expression_required失败（memories[7]、[8]、[6]）。该规则要求time.original_expression逐字出现在其anchor原文中；不能将归一化或改写后的时间当原文表达接纳。没有网络Unknown，也没有放宽契约。conv-44仍33/34成功、383 Memory；conv-43仍34/34、402 Memory。原67成功片段及785条已接纳Memory逐行摘要前后完全一致。恢复入口已终结并保留一次性标记，不自动追加尝试。

本次保守预约USD0.1335684，按usage峰时cache-miss上界USD0.0091488；不是账户账单。累计78物理请求、保守预约USD3.4624767、usage峰价上界USD0.2265405，Unknown用量0；全局剩余容量USD14.5375233/126次不自动授权更多片段尝试或关系/QA。原75次审计保留，新件为live-extraction-post-recovery-v1.json和extraction-recovery-outcome-v1.json。最新恢复结果优先于较早“待授权”段落，旧记录保留过程历史。
