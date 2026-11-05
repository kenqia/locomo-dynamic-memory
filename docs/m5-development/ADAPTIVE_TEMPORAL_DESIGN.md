# 自适应优先级与时间增强

route(question, analysis) 只读问题与冻结 Query Analysis，不接收答案、证据标注或得分。规则识别 state、temporal、multi_hop、entity、general，返回理由、建议关系深度和版本。

实际范围是固定 Hybrid 候选的软排序，并按问题选择已存关系扩展。BM25、Dense、RRF 由原 RetrievalService 执行。没有按类别重新查询检索通道，channels 建议不等于额外召回。executed_channels 和 execution_scope 记录实际范围。人物优先不硬过滤其他人物、共同参与者或代词证据。

时间优先使用明确 valid interval，不把事件日期当状态有效期。query_interval 支持单一明确日期、相对对话截止日的 yesterday、上一完整日历周及 current/today。未知表达或多个明确日期不编造点日期；区间不伪装成 QueryRequest 的单日字段。

原 query_memory_times 按来源 session_time 解析 Memory 相对时间并保存 query-only 诊断，新模块不改写持久时间。计划、取消、否定、条件生效仍由生产 source-backed resolver 判断，排序不自动宣布有效或失效。

所有能力默认关闭。自适应初轮来源代理出现退化，不能默认启用或据此做组合调优。时间模块工程通过不证明复杂时间问答准确率提高。

显式QueryRequest.requested_date优先于问题内的now/current等截止日表达，同时用于优先排序和生产有效记忆解析。该修复有保存interval的回归检查，并在隔离源码副本禁用修复后确认测试失败。它不改变没有requested_date的757题历史回放；原工件保持不动。
