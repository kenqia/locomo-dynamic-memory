# 检查历史关系、状态与相关历史扩展

本阶段保存有来源的历史判断，重算 Current State，并扩展真实初始检索候选。完成配置要求的抽取、索引、关系和投影后，可以显式发布一个完整构建版本供后续查询固定使用。最终有效证据解析与答案生成仍由后续票实现。

## 操作步骤

1. 按 [构建指南](building.md) 和 [检索指南](retrieval.md) 得到 `indexed` 版本。
2. 点击 **构建或重试历史关系**，再刷新进度。后端为每条新 Memory 比较同对话、同实体的有界历史，保存每个比较的判断；证据不足也必须明确返回 `undetermined`。
3. 检查关系任务的成功、失败和截断计数。失败或中断使用同一按钮显式重试；成功关系任务与抽取片段不重复调用模型。
4. 状态为 `related` 时，检查 Current State 的截止时间、当前候选、历史、事件、非事实陈述、条件及冲突。需要时点击 **从历史与关系重算投影**；它重算缓存，不编辑事实。
5. 选择一条关系，检查两端 Memory、适用条件、理由和双方原文。
6. 如需供后续完整库查询使用，点击 **校验并发布为完整构建版本**。发布原子地切换所选对话的活动版本；未通过或失败的新版本保留旧完整版本。
7. 运行初始候选检查，再点击 **扩展当前候选的相关历史**，对比初始、补充与合并集合，核查每条补充的入口及截断原因。

状态路径为 `extracted → indexed → related → complete`。只有 `complete` 的 `query_ready=true`。完整版本的索引、抽取重试、关系构建和投影重算接口都拒绝修改；更正事实或关系需创建新构建。

## 判断与来源约束

| 判断 | 含义与保留规则 |
| --- | --- |
| `RETAIN` | 新证据支持旧事实继续适用；没有新消息不能证明保留 |
| `UPDATE` | 同一过程推进，旧阶段仍可用于历史问题 |
| `SUPERSEDE` | 同一实体和状态维度的事实状态被明确替代；不抹除旧原文 |
| `CONFLICT` | 同一适用条件下的矛盾尚未消解；保留双方来源 |
| `undetermined` | 证据不足，不强迫归入其他标签，也不作为跨键扩展边 |

每条判断必须引用提供的历史端点及当前新 Memory，限定同一构建、数据集、对话和实体。来源必须真实存在并支持双方。确定判断还需要实际出现在来源中的 `support_quote`。替代只允许事实状态，事件、计划或不确定陈述不能替代已发生的事实状态；`RETAIN`、`SUPERSEDE` 和 `CONFLICT` 必须同一 `state_key`。跨维度 `UPDATE` 需要明确来源支持，不因同人而自动连通就业与商店经营。

有日期的关系适用区间必须保留原始时间表达、来源锚点和依据；倒置区间、伪造锚点或不存在的表达会拒绝。条件若未知就保持未知，声称条件满足必须引用证明来源。上述校验不等于验证模型的语义判断正确性。

`relation_history_limit` 默认 20，限制每个新 Memory 的同实体先前比较量。未比较的较早历史计入 `history_comparisons_truncated`，不声称已经穷尽所有可能关系。没有先前 Memory 时不调用关系模型，也不伪造 RETAIN。Prompt、schema、投影版本和相关配置在构建开始前进入指纹。

## 保守的 Current State

截止时间从所选对话的原始会话时间解析取最大值，不使用主机当前时间或字符串排序。支持 LoCoMo 原始英文时间格式和无时区 ISO 时间；无法解释的时间阻止投影/发布，不猜测日期或时区。

事实状态默认是带“未知有效期”提示的最后已知陈述。只有有依据的替代/推进日期在截止时间内且条件成立，才将旧状态标为 `superseded` 或 `advanced`。未知日期、未来变化或未满足的条件不会无条件抹去旧状态。冲突保留双方，兼容的同键工作可以共存。事件保留在历史，计划、意愿与不确定陈述单列；否定事实保留负向性质。

投影只引用原 Memory ID 与来源，是历史和关系的可重算缓存；没有手工状态编辑器。候选查询及历史扩展不会重算或改写全局关系与状态。

## 有界历史扩展

扩展固定初始候选记录所属的 `build_id`。`expansion_depth=1` 只沿**原始初始集合**的直接、已确定关系补充历史；`0` 关闭关系边扩展。同一初始 `state_key` 的历史补充独立保留，两种补充都不会将新增 Memory 变成下一轮种子。未知时间不会被推断查询日期硬过滤。

默认合并上限 `expansion_max_candidates=60`，总扫描上限 `expansion_scan_limit=200`；共用 `candidate_token_budget` 和检索指南中的明确 regex 计数单位。原始初始记录不改写；合并集合按初始顺序、种子顺序/稳定关系 ID、同键历史来源顺序稳定去重。初始项遇预算不足停止保留其后初始项；补充项超预算跳过并记录原因，后续较小项仍可进入。重复路径保留多个 origins，不重复占用候选预算。

只有发现潜在额外候选或额外扫描记录时才标记截断；恰好达到上限不自动代表存在遗漏。补充记录携带种子、关系 ID/标签或 `state_key`、理由和适用条件。扩展无法恢复从未抽取的 Memory。

## API 与后续查询契约

| 方法与资源 | 用途 |
| --- | --- |
| `POST /builds/{id}/relations` | 首次构建或显式重试关系阶段，返回 202 |
| `GET /builds/{id}/relation-progress` | 阶段进度、错误、Prompt/schema、历史比较截断 |
| `GET /builds/{id}/relation-tasks` | 分页任务、尝试次数及安全调用元数据 |
| `GET /builds/{id}/relations` | 分页历史判断，含未确定结果 |
| `GET /builds/{id}/current-state` | 读取固定投影及截止时间 |
| `POST /builds/{id}/current-state/rebuild` | 仅未发布的 `related` 版本可重算 |
| `POST /builds/{id}/publish` | 检查全部阶段并原子切换活动完整版本 |
| `GET /versions/pin?dataset_id=...&sample_id=...` | 固定该对话的活动完整构建 ID；可传 `build_id` 检查指定完整版本 |
| `POST /candidate-expansions` | JSON `{query_id}`，扩展既有初始候选记录 |
| `GET /candidate-expansions/{id}` | 读取已保存的扩展结果 |

后续业务模块可调用 `app.state.versions.pin(dataset_id,sample_id,build_id=None)` 得到固定 ID；之后全部 Memory、索引、关系和状态读取都必须使用该 ID。无匹配完整版本返回 `no_complete_version`。`app.state.relations.current_state(build_id)` 和 `app.state.expansion.expand(query_id)` 提供相应业务入口。此基础发布契约由后续恢复/导出票继续加固。

## 验证边界

执行 `uv run --locked pytest -q`。公开 API 使用实际 SQLite、BM25/cosine/RRF 和真实扩展，只控制模型/Embedding 输出。覆盖研究阶段实际未进入初始候选后的恢复、根本未抽取的反例、单跳/同键不再扩展、深度与数量/扫描/文本预算、条件替代、冲突/并存、任务重试和完整版本 pin。实际结果见 `experiments/issue-8-relations-validation.md`。

本票没有真实付费模型调用，也未单独运行浏览器；受控判断不能当作独立动态标注或模型质量证明。

## 安全失败诊断与调用历史

`GET /builds/{id}/relation-tasks` 的每个任务新增 `diagnostic_history`，按
`logical_attempt` 升序返回所有已记录的逻辑执行及其 `calls`。原有
`attempts`、`error_code` 和 `model_metadata` 保持兼容，其中 `model_metadata`
仍表示最近一次逻辑执行。读取完整历史时使用 `diagnostic_history`。
任务分页沿用 `limit` 和 `offset`，每个任务内的历史完整返回。

每个逻辑执行包含 `task_id`、`logical_attempt`、`status`、`started_at`、
`completed_at`、`error_code` 和 `calls`。状态为 `running`、`succeeded`、
`failed` 或 `interrupted`。每个 provider 调用包含以下诊断字段：

| 字段 | 约定 |
| --- | --- |
| `diagnostic_version` | 当前为 `1` |
| `build_id`、`task_id` | 构建和任务的实际标识；任务 ID 包含 Build 前缀 |
| `logical_attempt` | 显式逻辑执行序号，从 1 开始 |
| `provider_attempt`、`attempt` | 同一逻辑执行内的调用序号，从 1 开始；`attempt` 保留原接口 |
| `call_id` | 调用关联标识；检查点更新和 Build 用量按此标识去重 |
| `timestamp`、`completed_at` | UTC 开始时间与已观察到的结束时间；未观察到结束时没有 `completed_at` |
| `status` | `started`、`response_observed`、`succeeded`、粗错误类别或 `interrupted` |
| `outcome` | 结束时保留原粗类别，如 `invalid_output`、`model_timeout`；中断为 `interrupted` |
| `failure_stage`、`error_code` | 稳定失败阶段与安全错误代码；成功或结果未知时为 `null` |
| `field_path` | 仅含 Schema 已知字段和数组索引的路径；根级错误为 `null`，额外字段只保留已知父路径 |
| `validation_errors` | JSON/Pydantic 校验失败时的安全错误列表；每项仅含 `failure_stage`、`error_code` 和 `field_path`，顶层诊断取第一项 |
| `finish_reason` | 实际响应中的白名单值，未知值为 `null`；不从 token 数推断 |
| `finish_reason_status` | `reported`、`missing`、`unrecognized` 或 `not_observed` |
| `response_received`、`usage` | 是否收到 HTTP 响应及已报告的 token 字段；缺失用量保持 `{}`，不补零 |

失败阶段及常用代码如下：

| `failure_stage` | 例子 |
| --- | --- |
| `transport` | `model_timeout`、`model_http_error` |
| `provider_http` | `model_http_error`、`context_length_exceeded` |
| `provider_response` | `invalid_provider_document`、`invalid_provider_message` |
| `completion` | `non_stop_finish_reason`；包括 `length`、缺失或未知结束原因 |
| `content` | `empty_content` |
| `json_parsing` | `invalid_json` |
| `schema_validation` | `missing_field`、`extra_field`、`invalid_enum`、`schema_constraint_failed` |
| `domain_validation` | `same_state_dimension_required`、`every_candidate_required`、`verbatim_support_required` 等；完整静态规则代码见 `src/locomo_memory/diagnostics.py` |

例如，受控测试中的跨维度违规会记录
`failure_stage="domain_validation"`、`error_code="same_state_dimension_required"`、
`field_path="judgments[0]"`。数组下标指输出位置，不能据此猜测某个输入候选。
该示例不表示原始历史失败已获得具体归因。

`finish_reason` 只接受 `stop`、`length`、`content_filter`、`tool_calls`、
`function_call` 和 `insufficient_system_resource`。只有 `stop` 继续解析，
其余情况保持原有失败和有限重试行为。`stop` 也不保证 JSON、Schema 或领域校验通过。
诊断不保存响应原文、Memory/source 文本、异常字符串或 Pydantic 的 `input`、
`ctx`、`msg`。恶意额外字段名和未知结束原因不会原样透传。

### 持久化、中断和旧记录

新增 SQLite 表 `relation_attempts` 和 `relation_provider_calls`。逻辑执行开始、
调用发出前、响应用量读取后、结束原因读取后、最终成功或失败时分别提交检查点。
每个调用仅更新自己的检查点，下一次逻辑重试追加新记录。Build 调用聚合与调用
检查点在同一事务更新，不重复计数；失败检查点在异常向调用方传播之前保存。
无法保存检查点时停止执行，不把存储异常当作模型输出错误重新调用 provider。

进程退出可能发生在调用意图保存之后、请求实际发出之前，也可能发生在 provider
已经计费之后。重启将未结束调用和未提交的逻辑执行标为 `interrupted`，保留已知
用量与结束原因，未知值保持未知，不补写结束时间，不自动重放。调用记录数量表示
已记录的调用尝试，不能证明 provider 实际收到请求或未计费。即使 provider 调用
已成功，任务提交之前的中断也仍需显式重试，可能产生额外费用。

`diagnostic_history_status` 区分记录覆盖范围：

| 值 | 含义 |
| --- | --- |
| `not_started` | 任务尚未执行 |
| `recorded` | 从第 1 次逻辑执行起记录历史 |
| `legacy_not_recorded` | 旧任务已执行，但当时没有记录诊断历史 |
| `partial_legacy` | 旧任务后来显式重试，只有新版执行部分有历史 |

旧表和旧 `model_metadata` 不回填。原始 87 次 `invalid_output` 的具体错误、路径和
结束原因无法恢复。旧离线脚本 `scripts/diagnose_relation_failures.py` 继续只接受其
原始格式，不应用它强行解释新记录。新诊断通过上述 API 读取；
`Experiment.snapshot_build` 导出的 `builds/{id}/relation-tasks.json` 同样保留完整历史。
供检索使用的不可变 `MemoryExport` 仍沿用原有内容白名单，不包含运行时诊断。

此次只增加诊断和存储，不改变 Prompt、JSON Schema、关系标签约束、候选数、
输出上限、模型参数或重试规则。回退代码时旧程序会忽略新增诊断表；保留数据库，
不要为回退删除历史表，也不要对受保护的旧实验数据库启动新版后端。
