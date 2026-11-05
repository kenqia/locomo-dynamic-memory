# conv-44 关系恢复 v1 真实结果

2026-11-05（Asia/Shanghai）。已批准的 10 任务恢复阶段已终结：9 个恢复成功，1 个仍失败。当前共 383/384 个关系任务成功，保存 7,114 条合法关系。根代理与非作者终态审计均通过；这些审计确认失败终态及其历史完整，不代表关系构建完成。第六份严格 JSON 尚未生成。

## 保留结果与剩余失败

Build 为 `d9fb61417bb740e4b8eb34acb8652a46`。恢复阶段新增 141 条关系：137 条 undetermined、4 条 UPDATE。累计标签为 undetermined 6,906、UPDATE 95、RETAIN 106、SUPERSEDE 5、CONFLICT 2。全部已保存关系通过严格 schema、端点、来源及成功任务完整 history 覆盖检查；这不等于关系标签的语义准确率。

原 374 个成功任务、384 个 logical1、417 条原 Provider 记录、6,973 条原关系和 418 条 Build 调用前缀逐行保留。10 个新 logical2 与物理请求闭环一致。392 条 Memory、34 个片段、Source、索引、抽取继承和其他 Build 均保持不变。失败状态没有 CurrentState projection，未发布、未查询或完整化 Build。

剩余任务 ordinal163 包含 20 次比较；logical2 的 3 次尝试均为 HTTP200 / stop，安全错误为 `same_state_dimension_required`，路径为 `judgments[1]`。旧 logical1 的 3 次记录保留相同错误。未读取原始 Provider 响应，因此不能根据响应数组下标推断具体错误端点或输出标签。

仅检查端点结构得到：15 个跨状态维度的 fact 候选只允许 undetermined；4 个跨维度的 plan 候选允许 UPDATE 或 undetermined；1 个同维度 intention 候选允许 RETAIN、UPDATE、CONFLICT 或 undetermined。后续免费修复应按现有 `relation_label_error` 展示逐候选约束；不得改写旧响应、强制标签或放宽证据校验。

## 请求与费用

本阶段硬限为 30 次 / USD2.6196480。实际 12 次请求全部 `response_received`，usage 已知，Unknown0；预约 USD0.5913375。已报告输入 121,592、输出 24,953 tokens，按当时峰价折算上界 USD0.0664212。预约和 usage 上界均不是实际账单，账单未读取。

新请求全部为 `deepseek-flash`、thinking disabled，无 reasoning_effort；返回 alias 不提供不可变权重 pin。历史构建的其他思考配置按原记录保留。

截至本阶段，八个已批准阶段累计 1,862 次请求，预约 USD92.1054516，已知 usage 峰价上界 USD10.3629372；历史 7 个 Unknown 的 USD0.3500316 预约保留。各阶段额度独立，不转移余额或自动追加任务尝试。

## 审计与后续

根代理[终态审计](../../experiments/m5-development/conv44-relation-recovery-terminal-v1.json)、[独立终态审计](../../experiments/m5-development/conv44-relation-recovery-independent-terminal-v1.json)和[私有归档清单](../../experiments/m5-development/conv44-relation-recovery-terminal-archive-v1.json)绑定计划、授权、outcome、脚本及最终 DB/ledger。归档使用只读 SQLite backup 并验证逻辑身份，排除私有执行 stdout/stderr。重复 execute 已验证为零 Provider 请求拒绝，数据库与账本不变。

只为剩余单任务准备新的独立恢复入口、测试、账本和精确预算，经非作者复核后申请新的费用授权。成功后仍须终态审计，再在新副本完整化并严格导出。六份 JSON 齐备后才能锁定最终配置和准备一次独立 Level E。留出 QA、evidence、answers 尚未读取。

本阶段没有远端写入。未识别关联 Notion，未同步或标记总任务完成。
