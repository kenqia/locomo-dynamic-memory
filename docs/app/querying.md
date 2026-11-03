# 使用有效证据回答问题

完整版本支持英文当前与历史问答。后端先固定一个完整 BuildVersion，再执行问题分析、真实 BM25/Dense/RRF 检索、相关历史扩展、有效证据解析与答案生成。查询只追加候选、扩展和 Trace 记录，不修改 Memory、全局关系或 Current State，也不在线补抽原文。

## 准备和操作

先按[运行指南](running.md)启动服务，按[构建指南](building.md)、[检索指南](retrieval.md)和[历史状态指南](relations.md)完成抽取、索引、关系及完整版本发布。问答需要本地 Embedding 和受保护环境提供的 DeepSeek 凭据；不要把凭据写入配置、请求正文或仓库。

1. 在页面选择完整构建版本。
2. 在 **问答策略** 选择 **Dynamic** 或 **Dynamic + 原文兜底**，再输入英文问题。默认是 **Dynamic**。切换不会调用模型；默认以对话最后一次会话为已知截止时间，需要历史或未来日期时，在 **指定日期，可留空** 输入 `YYYY-MM-DD`。
3. 点击 **分析证据并回答**，检查证据支持、证据冲突或证据不足状态。
4. 展开回答引用，查看实际来源英文原文。展开候选与有效集合，检查初始召回、历史扩展、选择和排除理由。
5. 展开完整 Trace，检查固定版本、时间条件、关系条件、补充判断、截断、配置、模型调用和已报告 token 用量。

失败响应显示错误及 Trace ID；页面同时读取失败 Trace。也可以在 **查看已有 Trace ID（含失败记录）** 输入 ID，重新读取持久记录。模型或检索执行失败与证据不足分别记录，不将失败当作有效的空证据。

在评测页面读取已保存 Run 后，使用 **同题策略切换与引用原文** 选择题目和策略。
已保存的 Dynamic、原文兜底、Hybrid 和 Full Text 答案可直接切换；不会新建或重试查询。
点击 **读取引用原文** 只读取该答案引用的来源，失败项显示错误记录。完整 Trace 仍可展开检查。

历史扩展使用与有效证据解析相同的查询日期：优先使用页面/API 的 `requested_date`，其次解析问题中唯一明确的 ISO 或英文日期。候选达到上限时，同一 `state_key` 下覆盖该日期的已知有效区间优先进入补充集合；未知时间的历史仍可候选，不因日期被过滤。

## API 参考

`POST /queries` 接收以下 JSON，成功返回 201 和完整 Trace：

```json
{
  "dataset_id": "<已导入的数据集 ID>",
  "sample_id": "conv-a",
  "build_id": "<完整构建 ID，可省略>",
  "question": "Where did Alex live on 2023-05-01?",
  "requested_date": "2023-05-01"
}
```

省略 `build_id` 时，服务在任何模型调用之前固定所选数据集与对话的活动完整版本。显式版本必须属于该对话并且已完整发布。首次构建未完成时返回 409 `no_complete_version`。新版本发布不会改变进行中的查询所用版本。

省略 `requested_date` 时，原问题中单个明确的 ISO 日期或英文年月日可作为显式日期；无法解析的表达或日期范围保留在原问题中交给解析模型，不擅自取范围端点；默认时间锚点仍使用原始会话的截止时间，不使用机器当前日期。Trace 区分 `explicit_request`、`explicit_question` 和 `conversation_cutoff`。问题分析推断的时间保留在分析结果中，不覆盖显式条件或默认截止时间，也不硬过滤历史。超出截止日期的回答强制保留 `insufficient` 状态，不能把未来计划视作未来已知现实。

`GET /queries/{trace_id}` 读取既有记录，不重新调用模型。执行失败返回安全错误码和 `trace_id`；通过此端点可检查失败阶段及有限调用记录。输入校验失败或无法固定完整版本发生在查询创建之前，不产生问答 Trace。

## 证据和预算

解析和回答是两个独立生成操作。解析必须对每条候选提供选择或排除理由；所有 Memory ID 必须来自所供固定版本候选。查询补充关系使用已有关系证据校验，仅保存在本次 Trace。历史查询可以使用已被替代的旧状态，不能总是从 Current State 选答案。计划、否定、事件、兼容状态与未知关系的语义由明确的操作提示词约束；受控测试不能证明真实模型的语义质量。

解析选择后，按扩展候选的稳定顺序分配 `evidence_token_budget`。预算统计实际传给回答的 Memory 字段及对应来源文本，使用 `regex-word-punctuation-v1` 近似计数，不等于模型实际计费 token。放不下的 Memory 不传给回答；Trace 分别保留解析选择、实际送达集合、遗漏 ID 和截断原因。截断只表示交付集合不完整，不自动表示问题无法回答。回答模型根据实际交付证据判断充分性，允许将 `sufficient` 降为 `insufficient`；控制器已知的证据缺口、冲突和未来日期约束不得升级。无证据时仍强制不足，冲突仍须引用双方；混合查询中支持某子问的证据组未交付时，该子问明确记录不足。

最终 RAG 回答预算使用 `unique-source-payload-v2`：按完整的 `memories` 与去重后的 `sources` 对象计量，包含 JSON 容器开销。同一原始轮次支持多条原子事实时，来源文本只计一次，事实仍分别交付。`evidence_budget.algorithm_version` 及查询指纹记录该策略。若 `conflict` 的选定证据无法全部放入，发送前返回 `conflict_evidence_budget_exceeded`，保存遗漏 ID、零次回答调用及预算诊断；不发送单边冲突，也不自动改变冲突状态。Full Text 继续完整交付原文，不受此 RAG 截断规则限制。

回答只能引用实际送达的有效 Memory 及该 Memory 的来源。跨版本、跨对话、候选外或被排除的引用触发有限重试，仍无效则失败。`sufficient` 需要来源，`conflict` 需要双方引用；`insufficient` 不允许提升为确定状态。部分不足时保留已支持的事实及其引用。

Trace 保存实际配置、查询提示词/schema 指纹、索引与投影身份、关系证据摘要指纹、阶段耗时、模型调用和 provider 已报告用量。缺少 provider 用量的调用单独计数，不能把已报告 token 合计当作完整费用。Trace 不保存凭据、原始 provider 响应或隐藏推理。

解析提示词版本 `resolve-v2-explicit-existing-contract` 明确列出现有输出要求：对每个候选恰好作一个决定，所选 ID 与决定一致；补充关系若提供 `from_date` 或 `to_date`，同时提供 `time_anchor_source_id`、原文中的 `original_time_expression` 及 `time_basis`。不能为通过校验清除有来源支持的日期，也不能用问题日期或会话时间擅自补出真实转变日期。该版本不放宽事实、来源、时间或候选范围约束，不改变检索和扩展规模。

解析候选遗漏、选择不一致、候选外端点、证据不足等失败现在分别记录固定的 `resolution_*_required` 诊断码，而非统一记为 `domain_constraint_failed`。诊断不包含未经验证的模型内容。历史通用错误缺少细节时仍保持未知，不能从新诊断追认旧失败的原因。独立两题可靠性验证见 [修复实验](../../experiments/resolution-contract-20261028/README.md)。

回答阶段保留相同拒绝条件，使用下列固定诊断码。查询级错误仍为 `invalid_output`；具体原因读取 Trace 的 `operations.answer.calls` 中 `error_code`。原文兜底的模型操作名为 `answer_raw`，Trace 仍使用 `operations.answer`。这些模型级校验的 `field_path` 仍为 null，不推造字段位置。

| 诊断码 | 含义 |
|---|---|
| `answer_nonblank_required` | 答案仅含空白 |
| `answer_evidence_status_required` | 回答状态违反输入证据的不确定性约束 |
| `answer_citations_required` | 充分或冲突回答缺少引用 |
| `answer_raw_citation_scope_required` | 原文引用含未交付或重复来源 |
| `answer_memory_citation_scope_required` | 引用了未交付 Memory、非该 Memory 来源或重复来源 |
| `answer_conflict_sides_required` | 冲突回答未引用两个不同证据端点 |

字段缺失、类型错误等继续记录 schema 诊断；其他未分类领域错误继续保留 `domain_constraint_failed`。诊断不保存无效答案正文、隐藏推理、Pydantic input/ctx 或异常文本；失败请求用量仍按原调用账本保留。JSON schema、Prompt、重试配置和证据规则未变；新增诊断不能反推历史通用错误的原因。离线验证与适用边界见[回答诊断记录](../../experiments/answer-diagnostics-20261029/README.md)。

当前候选采用 `safe-validation-feedback-v2-budget-aware`，复用已授权的 `model_retries`，向解析和回答重试附带已知领域错误的固定码、已净化字段位置及静态说明。首次请求和现有校验条件保持原样；控制器不修改模型状态、时间或引用。未知错误不猜测原因，重试为 0 时仍只发送一次。完整反馈超过显式 `input_budget` 时，只保留错误码和字段位置，所有证据、Prompt/schema 和校验上下文保持不变。每次实际发送前仍检查上限；简短诊断也超限时返回 `input_budget_exceeded`，保留此前请求的诊断和用量，不产生新的 HTTP 请求。调用记录中的 `retry_feedback_mode` 区分 `full` 和 `diagnostic_only`，反馈版本进入查询指纹。受控测试只能验证反馈和计量路径，不能证明真实失败率降低；相比 v1，原本因完整反馈超限而停止的请求可能使用已有重试名额，因此总费用也需要重新验证。

回答提示词 `evidence-answer-v8-event-boundaries`（混合原文路径为 `mixed-answer-v8-event-boundaries`）进一步要求：来源未证明同一具体过程时分别报告事件，不因人物、状态维度或职业相近而连接阶段；某日的报告不证明此后持续成立，未报告完成也不证明没有发生。约束同时适用于答案和解释。这是针对已复核越界的提示词候选，尚未通过新一轮真实输出盲审，不代表事件误连已经解决。

## 验证

```sh
uv run --locked pytest tests/test_queries.py -q
```

测试通过公开 API 使用真实 SQLite、BM25、cosine/RRF 和历史扩展，仅控制外部模型与 Embedding。覆盖当前/历史交叉提问、真实初始遗漏后的扩展、全局不改写、冲突、计划、未知关系、证据不足、未来、预算、非法引用和并发版本切换。执行记录见 `experiments/issue-9-query-validation.md`。真实模型与浏览器检查单独记录。

## 有界原文兜底

2026-10-21 的查询可靠性修复以回退后的 `5c1e23e` 为基线，保留原有实验数据。
当前采用核心 Memory 与来源优先交付，不恢复完整证据组排序或枚举题强制补查。
验证范围见[查询可靠性记录](../../experiments/issue-15-query-reliability/README.md)。

`POST /queries` 可显式设置 `strategy: "dynamic_raw_fallback"`。默认 `dynamic` 继续只使用 Memory。
新策略先解析 Memory 并列出每个子问的覆盖。整体或任一子问不足时，仅检索一次原文，
有命中时再联合解析一次；无缺口不增加操作。整体不足仍可有引用地回答已知部分。
联合解析保留前次 coverage 的问题标识和已支持引用，包括部分不足项中的已知事实。
更改已支持项时，必须填写 `revision_reason` 并在该项引用新增原文；未说明的撤回或整项遗漏
触发既有有限重试。耗尽后若首次解析已有支持，控制器恢复该次有效证据，
将覆盖标记不足，说明新原文未完成核查，并记录 `raw_fallback.recovery` 和失败操作用量。
没有首次支持时仍返回执行失败。恢复不接受非法引用，也不声称旧判断已通过新证据核查。
真实矛盾、人物错配及适用时间变化可以修正初判；新原文缺少细节本身不能推翻已有支持。
联合打包先预留首次 coverage 的全部支持，包括 `insufficient` 项中的部分证据，
再放入可选原文和其他候选。预留无法放入时停止联合请求，恢复首次支持并标明不确定性。
Trace 仍记录 `omitted_previous_evidence`。这些结构约束不能自动证明修订理由的语义正确性。

原文只来自已 pin 的完整 Build 的全部输入轮次，包括未抽出 Memory 的轮次。
查询在读取事务内核对来源清单及规范化正文摘要，不读取 QA、Observation 或 Session Summary。
BM25 最多取3个中心，同 session 前后各1轮，去重后最多9轮；超长中心跳过，继续尝试后续匹配。
完整原文及元信息受 `raw_token_budget=2000` 限制，并占共同 `evidence_token_budget=6000`。
解析和回答的完整 messages 受 `resolution_input_budget=24000` 限制，包含 Prompt、schema 和载荷。
这些是 `regex-word-punctuation-v1` 近似单位，输出 `model_max_tokens=8192` 另计。

Trace 分开记录首次解析、兜底触发理由、排名、窗口、省略、联合解析、有效来源、最终送达及引用。
基础交付单元为核心 Memory 与全部原始来源；原问题词干匹配优先，同名人物优先，
同分时沿用现有 Hybrid／扩展顺序，不增加模型排序。共享 `state_key` 不再强制合组。
CONFLICT、SUPERSEDE 双方一同交付；before／after 等演化问题同时保留 UPDATE 端点。
必要关系组仍放不下时记录省略，不拆开后假定无冲突。缺失端点保存在 `incomplete_relations`，
缺失冲突、替代或问题需要的 UPDATE 端点时，解析不得给相关事实确定的适用性结论。
普通事实查询可独立采用 UPDATE 之前的事实，但不能据缺失端点声称演化链完整。
回答阶段优先交付仍有效的首次支持；确因最终证据预算省略的覆盖项降为不足。
原文独立引用使用 `memory_id: null`，Memory 引用继续绑定其来源。
混合证据可以保留 Memory 与原文、两条原文之间的冲突。查询不写回 Memory、关系或状态投影。
原 Full Text 继续使用完整全文契约，不复用本策略的片段预算开关。

### 精简证据输入对照

仅在 `strategy: "dynamic_raw_fallback"` 下，可设置 `evidence_profile: "focused"`。
默认 `expanded` 保留 D 的候选输入，便于单独比较 P1。
精简使用原问题的词面匹配及英文词干，不把模型推断的人物、日期或主题作为排除条件。
仅在单一明确命名人物、单问且该人物有原问题词面命中时裁选。
保留此人物的全部候选，以及其他直接匹配证据的关系连通组，
包括 undetermined、未知时间、未满足条件、并存状态和冲突双方。
复合问题、间接人物引用、多人物或匹配只落在其他人物时保留全部候选。
原文窗口不再二次裁剪，避免丢掉否定或指代上下文。

`evidence_selection` 记录逐项保留和省略原因；实际预算交付沿用上述核心证据规则。
精简阶段保留的关系组在交付时仍按查询必要性处理。词面精简不等同于语义充分性保证，
当前采用显式对照，不改变旧 dynamic 或新策略的默认模式。

主答案 `answer.answer` 仅用于直接回答问题；依据、未覆盖部分和适用范围放在可选的
`answer.explanation`，引用保存在 `citations`。两个回答 Prompt 共享可回答性规则，
逐个子问核对人物、时间与所问事实。整个问题没有可回答信息时，提示模型将主答案完整写为
`No information available.`，原因及相关背景放在 explanation。仅主题相关的背景不算部分答案，
其他季节的意愿不能回答指定季节的计划。确有子问获得支持时，保留直接事实及引用并另述缺口，
不能按 `insufficient` 状态统一替换主答案。此规则由 Prompt 约束，没有新增语义判别器或改写评分规则；
受控回归不证明真实模型始终遵循。
查询页面和评测结果页面分别展示主答案、说明和截止时间，JSON 导出保留完整 Trace；评分只读取主答案。
新策略的当前问题及超出截止日期的问题，控制器在 `answer_boundary` 单独记录会话截止和“后续现实未知”。
`answer_boundary` 标明控制器补充及版本，不追加到主答案，也不把边界冒称模型输出。
这只限定已知证据时间，不证明模型的任职、替代或冲突判断正确。

相对时间以引用来源的会话时间为锚点。`this week` 指包含该来源日期的一周，
不是此前一周；不明确具体日时保留时间范围或带锚点的原始表达。抽取、解析及回答共享此提示约束，
原文、`original_expression` 和 `session_time` 高于派生 `time.basis`。
查询副本对来源可核对的 `this week`、`last week`、`yesterday`、`last <weekday>` 使用确定性规则。
周按周一至周日；`last Friday` 指来源日期之前最近的周五，当天为周五时指前一周的周五。
周表达保留区间；事件区间不作为状态有效期。其他表达保持已有精度，不猜日期。
`time_diagnostics` 保存派生时间和查询时间的差异，`time_authority_version` 进入查询身份。
该过程不改写持久化 Memory、来源、索引或构建契约。

Resolution 负责适用性、来源选择和各部分覆盖；Answer 按已解析的覆盖生成答案，
不重新做关系推断。两个阶段均要求多项目问题列出所有已交付证据支持的不同项目，
包括同一来源中的多个项目；保留人物归属、计划与事实、否定和部分答案约束。
这些 Prompt 要求及合成示例不能代替真实模型语义验证。

查询传输采用 `query-semantic-fields-v1`。控制器先固定 Build、对话和来源范围，保留完整对象供校验与 Trace 使用；发给解析及回答模型时，Memory 省略重复的 `build_id`、`dataset_id`、`sample_id`，来源省略 `dataset_id`、`sample_id`，关系省略 `build_id`。问题分析的调用账单元数据不作为模型证据发送。事实内容、所有来源 ID、原文、人物、会话位置与时间、极性、计划性质、状态维度和关系依据保留；未知扩展字段也保留。重试沿用同一精简规则。完整请求估算按实际传输对象计算，版本进入查询指纹及模型请求估算记录；该估算不等于 provider 计费 token。

`query-semantic-fields-v2` 进一步省略输入证据中已知可选时间、适用条件字段的 `null` 值，以及未提供的 `support_quote`、`update_evidence`。省略表示未知或没有提供支持，不能推断持续有效、条件满足或同一事件。显式 `false`、实际日期、原始时间表达、引用和阶段证据全部保留；控制器仍使用完整对象校验。来源原文不压缩或截断。

普通 Dynamic 解析使用 `complete-dynamic-input-v1-no-omission`，保留完整候选 Memory 和来源全文。默认 `resolution_input_budget=24000`（2026-11-01由12000提高一倍）；显式配置的旧值保持生效。完整 Prompt/schema/wire 超限时，在解析 HTTP 前返回422 `complete_resolution_input_budget_exceeded`，Trace保存全部候选ID、输入估算和未交付状态；此前分析阶段可能已经产生费用。解析不自动裁掉事实或扩充预算。重试逐次检查同一上限并保留失败用量。原文兜底继续使用独立的 `core-source-distinct-items-v4-raw-only` packing策略和省略审计，不能把它当成完整上下文。类型化引用、来源和时间校验保持严格。


## Production Integration v1 的失败边界

普通 `dynamic` 查询只执行问题分析、检索、历史扩展、完整输入解析和回答。
解析在配置的有限重试后仍无效时，返回 `502 invalid_output` 并保存失败 Trace；
不会自动切换 `dynamic_raw_fallback`、裁剪解析证据或启动研究 reader/复核。
该执行策略以 `dynamic-complete-input-no-implicit-fallback-v2` 纳入查询指纹。
完整输入超限仍返回 `422 complete_resolution_input_budget_exceeded`，不发送解析请求。

需要原文兜底时，必须在请求或 UI 显式选择 `dynamic_raw_fallback`。
该已有策略继续使用独立的 raw-only 预算和省略审计，不代表完整证据交付。
历史 `strategy_recovery` Trace 继续可读、可展示，新的默认请求不生成此字段。
研究接口、完整采用清单及运行回滚说明见
[Production Integration v1](../integration/production-v1/REPORT.md)。
