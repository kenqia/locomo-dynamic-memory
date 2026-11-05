# M5 开发候选验收矩阵

2026-11-05 最新执行状态：conv-44 已384/384任务成功，392 Memory、7,134关系；六份严格JSON独立复核齐备。最终配置先于问题正文锁定，完整400题/H-D共800项的独立Level E已明确获批（独立6,000请求/USD1,387.9296）并单次启动，当前生成中，尚无最终冻结或留出成绩，类别/答案/证据未读。准备、授权、当日价格和后处理门禁见[当前执行记录](LEVEL_E_EXECUTION_V1.md)。下文各历史检查点、费用与成绩保留各自时点，不代表本次运行终态。

2026-11-04（Asia/Shanghai）。基线为生产提交 915fac02f6b9296e331f913a1e78717cfa7e2df1，开发分支为 codex/m5-final-development-20261104。未发布、未合并 main。课程依据为 docs/sources/0 - Project (2026).pdf 第 9–13 页；课堂模型约束仍是转述。

| 要求 | 实现和证据 | 当前边界 |
| --- | --- | --- |
| 六段原始对话 | replay-v1/dataset-split.json，独立 conversation-only 文件 | 开发四段有完整Build；留出抽取1段extracted/1段failed，均未complete |
| 完整 Memory JSON | 复用四个冻结 Build，严格 MemoryExport 校验，记录 export/index/projection SHA | 原文和导出留在忽略的 var/m5-development/ |
| 动态状态与多版本 | 沿用生产关系/解析，增加只读 timeline API/UI | 合成机制与真实语义结果分列 |
| 动态独立参考 | 60对state关系及40题query-specific候选内适用性，独立AI盲审 | 非人工/教师金标；关系50/60；query可评分25/40、严格集合18/25，15歧义单列 |
| Graph 浏览 | m5_graph.py、m5_api.py、m5_ui.py | 默认关闭；只读派生；结构边不冒充语义关系 |
| Graph 多跳检索 | expand_relations、m5_queries.query(graph_depth=2) | 记录完整路径；深度/数量/token 预算；后续解析适用性 |
| Memory 压缩 | 可逆文件包和可选 CompressionModel wire 分组 | 全字段保持；解码提示计入完整请求，变大则原样发送 |
| 自适应/时间 | BonusRetrieval、BonusExpansion、m5_adaptive.py | 原 Hybrid 候选软排序与已有关系扩展，不声称额外通道召回 |
| 统一实验 | tools/m5/offline.py、delivery_replay.py | 757 题；候选回放与真实生产 packing 回放分别保存 |
| 物理请求预算 | BudgetTransport + SQLite 预约上限 | 抽取恢复78次、旧QA421次已终结；conv-43关系终结408次/预约USD20.2028820（原硬限1,200次/USD104.78592），400/400任务related、非complete；新v2独立1,500次/USD346.9824待批，各阶段余量不可转移 |
| PropMem | 固定 commit、源码 SHA、原方法合成探针 | 不满足来源/多人/更新契约，拒绝直接采用 |
| Browser | 原生产受控模型 smoke 加图开关/来源/timeline | 真 Chromium，模型为 stub |
| Level C/D/E | 固定 80 普通 +20 诊断身份；留出纪律 | 旧Level C两臂200项已冻结、评分并完成独立AI来源审阅，resolution low如实保留；全disabled新v2待批，D/E未运行 |

IMPLEMENTED、TESTED、EXPERIMENTALLY_BENEFICIAL、DEMO_READY、PRODUCTION_ELIGIBLE 必须分开记录。最终采用决策见 M5_CANDIDATE_DECISION.md。

## 2026-11-04 授权抽取实际结果

用户明确批准18USD/204次的conv-43/44 conversation抽取阶段后执行。conv-43：Build b19ae777b6e642c9855ea278ebd4cd81，34/34片段成功、402 Memory、300个引用来源，状态extracted。conv-44：Build bef9f685957843698b3083ff4cbc79a4，33/34成功、1失败，保存383 Memory、274个引用来源，状态failed。均未index、relate、publish或QA，不是complete Build，不提供memory-export-v2冒充完整导出。

75次物理请求全部返回usage，67次有效输出、8次invalid_output。保守预约USD3.3289083，按报告usage峰时cache-miss计算上界USD0.2173917；实际账单未读取。Unknown用量0，剩余预约容量USD14.6710917/129次，不能解释为同一失败片段自动获得额外尝试。conv-44 ordinal18三次均extraction_time_expression_required，保留失败，不截断或放宽时间契约。这是初次抽取快照；后续唯一恢复、独立关系与QA已各自获批并终结，见[当前终态费用](../../experiments/m5-development/cost-ledger-terminal-v1.json)。该历史抽取余量不授权额外操作。详见experiments/m5-development/live-extraction-summary.json与live-extraction-failures.json。

两段共785条已接受Memory完成schema、来源身份、session time与Build归属检查；这是结构与定位校验，不是事实语义准确率。仍未读取留出QA/evidence，也未评价。开发四份冻结Build和757题历史分母保持原样。


## 新增边界回归

`tests/test_m5_course_boundaries.py`的6项synthetic端到端测试已通过：计划取消保留正向plan与负向fact及各自来源；共同参与者即使analysis只返回Alex也保留Alex/Sam两条Memory及共享来源，不生成跨人物关系。分别运行默认、temporal、自适应加两跳图路径；保存查询回放与完整Build导出不变。受控模型只证明管线与契约，不作为语义质量分数，也未新增Browser验收。显式requested_date排序回归及预算并发/金额上限16项通过；日期修复在隔离副本中被mutation测试检出。


## 2026-11-04 单片段恢复授权与实际结果

用户在本聊天明确回复“接受恢复授权申请”，批准只恢复conv-44 ordinal18，最多新增3请求、预约上限USD0.2619648，仍受原18USD/204次全局账本约束。已绑定原计划SHA并执行一次；未index/relate/publish/QA，未读取留出答案或证据。

实际新增3请求全部返回usage，三次均在domain_validation以extraction_time_expression_required失败（memories[7]、[8]、[6]）。该规则要求time.original_expression逐字出现在其anchor原文中；不能将归一化或改写后的时间当原文表达接纳。没有网络Unknown，也没有放宽契约。conv-44仍33/34成功、383 Memory；conv-43仍34/34、402 Memory。原67成功片段及785条已接纳Memory逐行摘要前后完全一致。恢复入口已终结并保留一次性标记，不自动追加尝试。

本次保守预约USD0.1335684，按usage峰时cache-miss上界USD0.0091488；不是账户账单。累计78物理请求、保守预约USD3.4624767、usage峰价上界USD0.2265405，Unknown用量0；全局剩余容量USD14.5375233/126次不自动授权更多片段尝试或关系/QA。原75次审计保留，新件为live-extraction-post-recovery-v1.json和extraction-recovery-outcome-v1.json。最新恢复结果优先于较早“待授权”段落，旧记录保留过程历史。
