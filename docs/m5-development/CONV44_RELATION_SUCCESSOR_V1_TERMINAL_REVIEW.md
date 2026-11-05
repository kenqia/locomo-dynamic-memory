# conv-44 单任务关系successor v1 实际终态独立复核

2026-11-05。**结论：6组独立终态检查全部通过；logical3首请求成功，384个任务全部succeeded，7134条关系完整，源Build为related/relations。** 此终态允许另新副本complete/pin/export；它不代表源已complete、最终配置已锁或Level E已启动。

复核者为非作者代理 `/root/final_actual_review`，工作树为 `/home/kenqia/my_folder/locomo-worktrees/m5-final-conv44-relations-20261104`，实现本地提交为 `1f79524`。根代理明确通知真实进程exit 0、公共终态就绪后才读取stage。复核者没有新增live、改代码、改stage、重跑合成测试、读取凭据/raw响应/私有stdout或留出QA/evidence/answers。

[独立终态JSON](../../experiments/m5-development/conv44-relation-successor-independent-terminal-v1.json) SHA-256为 `7b805b55d80548c539d6d263067ed32ba6abea5b1ee3cff303df88ce7b3e2c87`。一次性脚本 `/tmp/conv44_relation_successor_independent_terminal_audit.py` 最终SHA为 `d09d8994b9d717086ecbfa3222ac7f31ab3c79e1ec72f73ced0cf9db3944b6c0`。执行环境撤销DEEPSEEK_API_KEY、OPENAI_API_KEY、CODEX_ACCESS_TOKEN，启用HF/Transformers离线及项目offline_guard；命令为项目venv Python执行该脚本，参数 `--root-confirmed-process-terminated --output experiments/m5-development/conv44-relation-successor-independent-terminal-v1.json`。

| 独立检查组 | 结果 |
| --- | --- |
| 1. 授权与冻结身份 | 精确plan、3请求/USD0.2619648授权、marker、88 producer、settings/inheritance匹配。新stage、原恢复源、原关系祖先先通过无QA SQL gate，再核对各自冻结身份。 |
| 2. 全部历史保护 | 原383成功task、394旧attempt（384 logical1+10 logical2）、429旧provider、7114旧关系及430条calls前缀保持逐行和rowid身份；schema、Memory/Source/片段/索引及其他Build保留。 |
| 3. 新logical3闭环 | 恰好一个新logical3，唯一task attempts=3。新provider身份、时间、状态、metadata、新Build calls后缀及独立ledger逐项一致，1次成功调用。无额外task或logical attempt。 |
| 4. 全部关系与投影 | 7134条关系均通过严格上下文schema、端点、来源和确定ID检查，384成功task均完整覆盖history。新增20条：19 undetermined、1 RETAIN。392条Memory投影精确重算相等：current_states 200、historical_states 0、events 108、nonfactual 84、conflicts 0、conditional_relations 100。 |
| 5. 新ledger及outcome | 实际1请求，完整32768输出预约反推输入字节为合法整数，预约USD0.0537564，已知usage峰价上界USD0.0072651，Unknown0。prompt 14745、completion 2368、total 17113 tokens。独立计算的完整outcome等于保存值及production audit。 |
| 6. 公共终态与重复入口 | 根公共终态身份、status与outcome相等。真实execute重复入口以successor_already_started拒绝，Mock dispatch0；前后DB/ledger、授权/marker/outcome及全部源、祖先身份未变。 |

独立SQLite连接使用mode=ro、query_only和读事务；快照包括已提交WAL。严格来源子串校验不等于人工事实或关系语义审阅。新请求显式thinking disabled、无reasoning_effort；请求/返回deepseek-flash仍是可变alias。未重编码向量或重拼wire，未访问实际账单。

首跑的一次性审计脚本仍断言旧logical2输入契约，停在首组且未生成公共结果；仅修正脚本为logical3的relation-endpoint-label-prerequisites-v1后重新执行，全部6组通过。该残留属于审计脚本，不是产品发现；实现和冻结stage未修改。

| 冻结身份 | SHA-256 |
| --- | --- |
| plan | `699934d373556a353f837322322931cd8aec3adc76b87feada2c97a5fb9bd8a4` |
| database逻辑快照 | `e44a48d165665d5965b7ccc0af0d2558a98f9387c9cf2573d3653802175e60d3` |
| ledger逻辑快照 | `ab8fad0598948514b226fff8cb0b366efcf472e8730e4836d15083a1a1668398` |
| projection fingerprint | `6fe8d3db8ecf077bacca3a5bacdbc24ccb9ea5301dd3a85eac85ebd89e5ee465` |
| 根公共终态 | `24e09a0f75418be112a23d042c13cbfd1e42fed2338db1bb67a08951e78f030f` |

实际新副本导出和六份JSON由另一独立工件记录；本报告只冻结上述related终态。历史预算不转移，成功恢复授权不覆盖Level E或留出QA读取。
