# conv-44 关系阶段 v1 真实结果

2026-11-05（Asia/Shanghai）。原授权关系阶段已终结为 `relations_failed`：384 个任务中 374 成功、10 失败，保存 6,973 条关系。根代理与非作者终态完整性审计均通过；这表示失败终态及其历史可核查，不表示关系构建成功。Build 仍非 complete，第六份严格 JSON 尚未生成。

## 任务、关系与来源

Build 为 `d9fb61417bb740e4b8eb34acb8652a46`。392 条 Memory、34 个成功片段、281 个引用 Source 和 392×384 维有限归一化索引均保持不变；原抽取继承血缘、其他 Build、成功任务和调用历史保留。全部已保存关系通过严格 schema、SQL 身份列、双方端点及来源证据校验，且与成功任务的完整 history 覆盖相符。这些检查不提供关系标签的语义准确率。

关系标签为 undetermined 6,769、UPDATE 91、RETAIN 106、SUPERSEDE 5、CONFLICT 2。失败阶段没有 CurrentState projection，未将部分关系冒充完整投影。

10 个失败任务各用尽原计划内 3 次物理尝试：8 个 `known_source_required`，2 个 `same_state_dimension_required`。对应安全错误路径为 `judgments[0]`、`judgments[1]` 或 `judgments[3]`；这些尝试均为 HTTP200 / stop。未读取原始 Provider 响应，因此不推断具体错误文本、缩写方式或语义原因。严格失败校验保持原样。

## 请求和费用

原阶段获批硬限为 1,152 次物理请求 / USD100.5944832；实际 417 次，全部 `response_received`、usage 已知，Unknown0。预约合计 USD20.5545036；已报告输入 4,154,084、输出 945,401 tokens，按峰价折算上界 USD2.3807064。预约与 usage 上界均不是实际账单；账户账单未读取。

全部新请求为 `deepseek-flash`，thinking disabled，无 reasoning_effort。响应返回 alias，不证明不可变服务端版本 pin。前五份 JSON 的历史 relation high 保留原记录。

原额度不继续使用或转移。若恢复这 10 个失败任务，须先完成独立工具、免费实际准备及非作者复核，再申请新的 30 次 / USD2.619648 硬限；这只是按当前峰价计算的待批准恢复范围。不得重跑其余 374 个成功任务。

## 证据与后续

根代理[终态审计](../../experiments/m5-development/conv44-relations-terminal-v1.json)和[独立终态审计](../../experiments/m5-development/conv44-relations-independent-terminal-v1.json)均绑定原 plan、授权、outcome 与最终 DB/ledger 逻辑摘要。重复原 execute 入口经 MockTransport 验证为零请求拒绝，DB、ledger 和历史不变。

恢复成功后仍需独立终态审计，再在新本地副本完整化和严格导出。六份 JSON 齐备后才锁最终系统配置，随后为一次独立 Level E 准备精确计划和新授权。目前留出 QA、evidence、answers 未读，未发布或查询留出 Build。没有远端写入，未识别关联 Notion，未标记总任务完成。
