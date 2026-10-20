# 运行独立评测与基线比较

评测 API 单独保存 QA 与证据标注，不将其传给抽取、索引、问题分析、有效证据解析或回答。可先在页面 **独立评测与基线比较** 生成开发集计划预览；执行评测前，按[构建指南](building.md)发布所选对话的完整版本。也可上传独立评测 JSON、保存 Input ID，并选择对照策略。一次运行在任何模型调用前固定所有对话版本；读取已有 Run ID 不重新调用模型。

运行真实模型会产生与所选样本和策略对应的模型调用。默认验证只使用合成数据和受控模型。`official_structure_only` 输入只允许映射检查，运行生成时返回 422。开发集固定为 `conv-26`、`conv-30`、`conv-41`、`conv-42`；本地测试固定为 `conv-43`、`conv-44`，开发阶段不查看其模型成绩。教师隐藏评分集另行保密，本地测试不能代表最终评分。独立动态标注仍缺失，动态指标未评。

真实实验的隔离准备、预检、全量启动与显式恢复见[真实基线运行指南](real-baseline.md)。

## 预览固定开发集计划

预览不需要完整 BuildVersion，也不调用生成模型或加载 Embedding 模型。先调用 `POST /imports/official` 校验并导入仓库官方原件，保存返回的 `dataset_id` 和 `artifact_sha256`。导入完整原件只保存数据，不运行本地测试。

在页面 **开发集评测计划预览** 选择对应原件 SHA256 和范围，点击 **生成开发集计划预览**。页面显示固定划分、问题位置、四种策略、题目和组合数量，并提供 JSON 下载。读取已保存 Plan ID 也只读取记录。

公开 API 使用相同入口：

```bash
curl -X POST http://127.0.0.1:8000/evaluation-plans \
  -H 'Content-Type: application/json' \
  -d '{"dataset_id":"<导入返回的 dataset_id>","artifact_sha256":"<导入返回的 artifact_sha256>","scope":"development"}'
```

`scope` 为 `development` 时，只选择四个开发对话，按固定开发对话顺序和各自原始 QA 顺序保存 757 道题、四种策略、3,028 个组合。`scope: "smoke"` 只读取 `conv-26`，按原始 QA 顺序为类别 1–5 各取首题，再保留原始顺序，共五题、20 个组合。官方原件中的原始位置为 `0`、`2`、`3`、`82`、`152`；任何必要类别缺失时返回 422、`smoke_categories_missing`。不依据模型成绩选题。

返回 201 和 `status: "preview"`、`plan_id`、`input_id`、`course_split`、`partition: "dev"`、`strategies`、`questions`、`question_count` 和 `combination_count`。每个问题保存 `sample_id`、从零开始的 `qa_index` 及 `question_id`，例如 `conv-26:qa:0`。重复问题文本保留为不同位置，不去重。`GET /evaluation-plans/{plan_id}` 读取完整计划，可将响应保存为 JSON。

计划保留数据版本、许可证、`source_sha256`、原件 `artifact_sha256`、校验依据和 provenance。必须显式指定原件；同一来源对应多个 QA 原件时不自动猜选。固定输入与范围生成稳定 Plan ID，重复请求读取已有计划。对应的独立评测 Input 只包含所选开发问题，并保存原始问题身份和来源身份，答案、证据和辅助摘要不进入 Source Turn、构建或查询。

预览数量不代表模型已经运行或评测已经完成。计划不固定 BuildVersion；执行前由评测运行固定完整版本。此入口不提供本地测试计划，也不获取隐藏评分题目。

## 输入和公开 API

`POST /evaluation-inputs` 接收：

```json
{
  "dataset_id": "<已导入数据集 ID>",
  "kind": "synthetic",
  "samples": [{
    "sample_id": "conv-a",
    "question": "Where does Alex live?",
    "answer": "Rome",
    "category": 4,
    "evidence": ["D1:1 D2:1"]
  }]
}
```

返回 201、`input_id`、原始字段和逐样本映射诊断。`GET /evaluation-inputs/{input_id}` 读取记录。证据仅在该 `sample_id` 的对话内验证，重复来源去重；列表元素只有在整串均由合法 `D<number>:<number>` 组成时，才按空白、逗号或分号拆分。任何必要引用畸形或不存在，都将整条样本来源覆盖标为不可计分。原文保留，不猜测修正 ID；未提供人工修正映射功能。

`POST /evaluation-runs` 接收：

```json
{
  "input_id": "<评测输入 ID>",
  "strategies": ["full_text", "vector", "hybrid_no_resolution", "dynamic"],
  "build_ids": {"conv-a": "<完整构建 ID>"}
}
```

`build_ids` 可省略，后端在首次模型调用前固定所有所选对话的完整版本。固定开发计划可直接提交 `{"plan_id":"<Plan ID>"}`，后端采用计划的 Input、四种策略和 `dev` 划分；附带字段与计划不一致时返回 422。手工 Input 接口继续保留。

默认创建立即返回 201 和持久 `run_id`，无需等待全量生成。每项完成后独立事务保存结果或安全错误、Trace、耗时、已报告用量及尝试历史。后续失败保留此前已提交结果。HTTP 201 表示记录已创建，每项是否成功以状态为准。测试或短合成调用可显式提交 `"wait": true` 等待执行结束；长评测使用默认异步模式。

## 查看进度和显式恢复

页面启动后立即显示 Run ID。点击 **刷新评测进度** 或输入 Run ID 后点击 **读取评测记录**，查看已提交结果、计划项状态、尝试次数和部分汇总。运行未结束时 `completed_at` 为 null，界面显示尚未完成。

`GET /evaluation-runs/{run_id}` 返回完整记录，包括 `items`、已提交 `results` 和部分 `summary`。`items` 是固定的逻辑计划，每项只计一次；其 `attempts` 按顺序保留各次错误、结果、Trace、耗时及用量。`GET /evaluation-runs/{run_id}/progress` 只返回 `run_id`、`status`、`completed_at`、`elapsed_seconds` 和状态计数 `progress`，适合轮询，不返回输入或富 Trace。读取上述资源不会调用模型。

Run 状态为 `running`、`completed`、`completed_with_errors` 或 `interrupted`。计划项状态为 `pending`、`running`、`succeeded`、`failed`、`interrupted` 或 `unknown`。后端重启将未提交的执行中项标为 `unknown`，活动 Run 标为 `interrupted`；未执行项保留为可恢复的中断项。启动不会自动续跑。

显式恢复使用：

```bash
curl -X POST http://127.0.0.1:8000/evaluation-runs/<Run-ID>/resume \
  -H 'Content-Type: application/json' \
  -d '{"retry_failed":false,"retry_unknown":false}'
```

默认只继续待执行或尚未开始的中断项，跳过所有已提交成功项。`retry_failed: true` 明确重试已记录失败项；`retry_unknown: true` 明确重试外部结果未确认项。页面提供对应复选框和 **显式恢复此运行** 按钮。重试成功保留首次失败及全部历史尝试。恢复已完成且没有可重试项的 Run 只返回记录。

恢复前重新核对原始 Input、Plan、题目及顺序、数据及原件身份、划分、策略、固定完整构建、配置、Prompt/schema、计分版本、运行依赖和实现 SHA256。不一致时返回 409、`evaluation_identity_changed`，旧结果仍可读取，应创建新运行。新活动版本发布不会替换本 Run 固定的旧完整版本。

模型返回后、事务提交前退出时，供应商可能已经计费，但结果无法确认。`unknown` 不代表没有调用，显式重试可能再次计费，系统不保证供应商恰好一次计费。已报告的用量与未知账单分别解释，不把缺失用量当作零。

本地后端仍由 SQLite 所有权锁限制为单进程，同一时刻只执行一个评测 Run。重复启动或并发恢复返回 409、`evaluation_already_running`。正常关闭在当前有限超时、有限重试的调用结束后停止，不再启动下一项，并在释放后端所有权前等待工作线程退出。没有外部队列或自动恢复循环。历史整批运行记录保持可读，缺少逐项身份的旧记录不能恢复。

## 策略与比较口径

| 策略 | 实际上下文 | 状态解析与额外调用 |
| --- | --- | --- |
| `full_text` | 按原始位置排列的全部真实有文本 SourceTurn，不受 RAG 最终证据预算限制 | 不抽造 Memory，不检索或扩展；直接调用共享回答操作，引用 `memory_id: null` 与实际来源；孤立会话时间不制造来源 |
| `vector` | 原始问题的 Dense 排名，经 `initial_k` 和候选预算限制，再分配共享最终预算 | 不扩展、不解析；共用检索器仍执行 BM25 和一次问题分析，分析不影响 Dense 选择，额外调用保留在 Trace |
| `hybrid_no_resolution` | 真实 BM25/Dense/RRF 初始候选，加一跳及同键历史扩展 | 不调用有效证据解析，所有扩展候选进入共享最终预算 |
| `dynamic` | 初始检索、历史扩展、有效证据解析后的送达 Memory | 使用完整查询链路与持久 QueryTrace |

四种策略共享生成模型、温度、输出上限、回答 Prompt 和 schema。Full Text 的 `evidence_budget.budget` 为 null，`scope` 为 `complete_raw_sources`；RAG 保留配置中的候选预算和最终证据预算，后者默认 6,000。Full Text 上下文单位是 SourceTurn，其余排序单位是 Memory。不同策略的上下文长度不相同。

`evidence_budget.token_count` 使用 `regex-word-punctuation-v1` 近似计算实际回答证据的大小。每个模型操作还在 `model_metadata.request_context_estimate` 记录包含 system Prompt、JSON schema 和用户 payload 的完整 messages 近似计数，以及预留输出上限。这些计数都不是 provider tokenizer 结果或账单 token，也不用于猜测服务是否接受上下文。provider 已报告的 `prompt_tokens`、`completion_tokens` 和 `total_tokens` 单独保存在调用记录的 `usage` 中。

Full Text 的 `source_delivery` 保留有序的 `expected_source_ids`、`attempted_source_ids` 和 `delivered_source_ids`。成功响应标记为 `accepted`。请求收到 provider 响应时，送达列表表示该请求包含的来源；上下文被拒绝时 `provider_accepted` 为 false，不能据此称模型已使用这些来源。请求未收到响应时只记录尝试来源，送达列表保持空，状态为 `request_attempted`；未发起调用时为 `not_sent`。`raw_context` 与 `initial_source_ids` 保留完整应有输入，即使回答失败也可以核查末尾来源。

provider 明确拒绝上下文时，样本保存 `context_length_exceeded` 错误和 `evidence_budget.context_limit_exceeded: true`，不把运行失败当作证据不足。相同超长请求不再重试，也不会回退为前缀、摘要或分块后的“完整全文”；其他模型错误继续采用既有有限重试。regex 近似计数不能证明输入适合服务上下文，实际服务结果为准。

Vector 的 `retrieval.executed_components` 披露实际执行的问题分析、BM25、Dense 和 RRF。`selection.unused_components` 明确哪些步骤不影响 Dense 选择，`operations.query_analysis_unused_by_vector_selection.calls` 仍计入调用与 provider 用量。检索阶段耗时包含这些步骤，不将 Vector 冒称为只执行一次 Dense 的成本。

`memory_rankings` 保存真实 Memory 排名，`source_sets` 按阶段保存去重 SourceTurn；`source_coverage` 的分母是该样本所有可靠映射的独立 gold 来源。初始、扩展、动态有效集合和实际回答上下文分开统计。无状态解析的策略没有经验证的有效集合，其 `effective` 为 null。Full Text 和 Vector 未执行扩展，其扩展覆盖为 null。初始 K 指实际候选数，扩展集合与实际送达集合各自有独立数量，不将这三者统称 Recall@K。

## QA 计分与不可计分项

计分依据仓库保留的官方 `data/raw/locomo/upstream/task_eval/evaluation.py`（upstream commit `3eb6f2c585f5e1699204e3c3bdf7adc5c28cb376`），仅采用规范化、NLTK PorterStemmer 和类别分支，不导入重型 BERTScore。

规范化依次去逗号、小写、删除 ASCII 标点、删除整词 `a/an/the/and`、合并空白，再做词干化。类别 1 先按逗号拆分预测和 gold，为每个 gold 子答案取最高预测 F1 后平均；额外预测不一定扣分，该规则不对称。类别 2、4 使用普通词干 F1；类别 3 先截取 gold 第一个分号之前部分。类别 5 使用官方拒答子串规则：预测小写后包含 `no information available` 或 `not mentioned` 得 1，否则 0；即使缺 gold 也按该分支评分，同时标记 `missing_gold`。这不是普通 token F1 或 exact-match accuracy。

数值 gold 保留原类型，计分时按官方方式转为字符串。缺少其他类别 gold、空答案、未知类别均返回 null 和原因。来源无法可靠映射不妨碍适用 QA 计分。每个指标分别报告 `scored`、`unscored`、`coverage` 和仅针对可计分样本的 `mean`，不把不可计分项算作零或正确。逐样本存未四舍五入值；缺 gold、未知类别、坏证据另有计数。

## 接入正式课程划分与独立真值

固定开发计划已自动生成 `kind: "course"` 和上述划分。手工独立评测输入仍使用 `kind: "course"`，在输入提供 `course_split: {"dev": [四个 ID], "test": [两个 ID]}`，六个 ID 必须互异且属于所选数据集。执行时显式提供 `partition: "dev"` 或 `"test"`，仅运行对应样本。服务不挑选划分、不自动调参。

每个样本可提供 `dynamic_truth`，必须有非空 `provenance`，并提供 `effective_memory_ids` 或 `relation_labels`：

```json
{
  "provenance": "<独立人工或课程标注来源>",
  "effective_memory_ids": ["<固定构建 Memory ID>"],
  "relation_labels": [{
    "old_memory_id": "<旧 Memory ID>",
    "new_memory_id": "<新 Memory ID>",
    "label": "SUPERSEDE"
  }]
}
```

有效集合使用集合完全一致匹配；持久关系标签按标注的有向端点比较，缺关系算错误。端点必须属于固定构建，否则该指标不可计分。关系标签允许 RETAIN、UPDATE、SUPERSEDE、CONFLICT、undetermined。该接入点不产生真值；系统关系、LLM 自标和 gold 来源 ID 均不能替代独立语义标注。缺少课程划分或独立标签时显示未评；样本对应指标仍单独报告覆盖率。

页面并列显示策略汇总、逐样本 QA、各阶段覆盖、错误、调用及完整配置。上下文表显示全文应有来源数、已确认请求来源数、送达状态、证据及完整请求近似计数、截断或超限与已报告用量；展开逐项记录可核查有序来源 ID。失败分析只有在独立证据足够时才能归因；当前自动说明统一标为可能原因，不能从 gold 来源是否命中直接断言抽取或解析错误。

运行记录保存配置、完整构建元数据、Prompt/schema、Python/包版本、实现 SHA256、耗时、实际调用与 provider 已报告 token 用量。未报告用量单独计数，不将部分合计宣称为完整费用。

## 验证

```sh
uv run --locked pytest tests/test_full_text.py tests/test_evaluation_plans.py tests/test_evaluation.py tests/test_queries.py -q
```

测试通过 FastAPI、真实 SQLite、真实 BM25/cosine/RRF、关系与扩展，只控制 LLM 与 Embedding。计划预览实验记录见 [Issue #16 验证](../../experiments/issue-16-development-plan-validation.md)，既有评测记录见 `experiments/issue-11-evaluation-validation.md`。未进行正式测试集调参或付费模型质量评测。
