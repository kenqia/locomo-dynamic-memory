# 集成候选的显式能力

本页描述 `production-integration-v1` 保留的研究接口。它们没有接入 FastAPI、Streamlit 或默认 Build/QueryService。调用者必须固定完整 Build 和来源快照、声明实际交付的原文引用权限、计量每次请求，并在另获付费授权后才能调用真实模型。离线验证请使用 MockTransport。

## 证据目录与实体标签

`EvidenceCatalog` 为已交付原文建立 E 片段和 T 时间地址，程序按 Unicode 位置读取原文并绑定持久来源。`labeled_fact` 将自然语言实体标签编码为带 hash 的 ID，保留原标签，不合并别名。

只在显式请求 `catalog_extract` 或 `catalog_extract_labeled` 时加载候选提示词，effort 沿用 `extraction_thinking_effort`。默认 `extract` 继续使用原结构化接口。目录拒绝未知地址、未包含于事实证据的时间锚点、重复引用和越界片段；不自动补来源。

地址存在仅证明原文定位，不证明事实、事件关联、模态或时间归属受到支持。新记录不得覆盖历史 Memory。新抽取默认关闭；完整语义和下游排序仍待验证。日期解析支持封闭语法，数字斜线歧义日期保持未知。

来源：`91786fb` 的纯契约/绑定、`19bdacf` 的目录与实体编码。本集成没有移植逐原子 judge、LayeredContractModel 或 Build 恢复挂钩。

## SourceAnswerReader

```python
from locomo_memory.source_answer_reader import SourceAnswerReader

# payload.sources 来自同一完整 Build 的实际交付快照。
# context.raw_sources 是调用方允许独立引用的子集；附件关系本身不产生权限。
# context.input_budget 必须是显式正整数，完整wire超限时不得发送。
result = SourceAnswerReader(metered_model).generate(
    payload, context=context, on_call=save_call_checkpoint,
)
```

该 reader 移除 QA 不接受的抽取 T 句柄，保留原文、人物和会话时间；只接受程序绑定的 E 引用。答案和必要解释都通过有来源的 claims 表达，禁止另加自由 explanation。非法引用仍拒绝，不修前缀、不补造来源、不删除错误断言来过关。调用者必须保存 `metadata` 和 `evidence_audit`；失败中的 metadata 也必须计量。

`source_statements` 沿用 `answer_thinking_effort`。默认 `answer`/`answer_raw`、API、UI 和 Build 指纹不因启用此模块而改变。四道已知题中的接口可靠性改进尚不足以证明泛化；QA51 偏好→已完成类型仍复发。来源为 `6db46ed` 和 `ce0e0c3`，去 T 实验验证的是 wire/schema/binder，不是整个服务的端到端验收。

## 单命题抽取

`PropositionFact` 只让模型生成一份 `content`，`bind_proposition` 将其逐字派生为 `state_value`，不再独立摘要。模型若返回非空 `state_value`，严格拒绝，不静默删改。生成时调用方必须将 `PropositionFact.model_json_schema()` 作为 `record_schema` 交付给 `catalog_extract_labeled`；所有记录通过绑定后才能接受整批，不能发布部分成功记录。

来源 `cde3250`。conv41 的局部改进不能说明完整抽取已修复；模态、极性和正文仍可能出错。`state_value` 参与既有关系与证据排序，不能迁移旧 Build 或默认替换现有抽取。

## 受限地址修复

`extraction_patch.apply_patches(catalog, records, patch_batch)` 是显式纯函数。它只接受原本失败的全部记录 index，锁定正文、实体、陈述性质、极性、状态维度、时间文字/锚点签名及合法 siblings。修复后仍需整批通过原 binder。它不发请求、不补来源、不发布部分批次，也不自动触发重试。

来源 `250795a`，本次只调整包内导入。历史 conv41 仅恢复技术交付，双方语义仍不确定；总体完整正确均为 2/12。因此没有接入 BuildService，也不能当成语义修复方案。

## 选择性前文与一次通用复核

调用方先用 `raw_retrieval.pinned_sources(database, build_id)` 取得完整 Build 的已验证快照，然后显式构造新交付范围：

```python
from locomo_memory.selective_context import predecessor_context
from locomo_memory.revised_source_reader import RevisedSourceReader, RevisionFailure

sources, context_audit = predecessor_context(original_sources, pinned_sources,
                                             max_turns=60, token_budget=12000)
payload = {**payload, 'sources': sources}
context = {**context, 'raw_sources': {s['source_id']: s for s in sources},
           'input_budget': 12000}
try:
    result = RevisedSourceReader(metered_model).generate(
        payload, context=context, on_call=save_call_checkpoint,
    )
except RevisionFailure as error:
    # 保留 error.initial_wire、error.metadata、error.usage 和失败阶段；不得当成功返回初答。
    raise
```

原始来源必须逐字匹配快照。词法规则只为包含固定英文指代词的来源补同会话前一位置，不递归扩张，不跨会话，不据邻近建立同事件关系。预算不足时仅省略新增前文并保存 `omitted`；原始来源本身超限则失败。没有指代词的语境依赖仍无法恢复。`source_context.source_window` 仅保留为显式对照，不自动启用完整窗口。

复核器复用来源 `384e068` 的原 REFINE 指令，两阶段各最多一次 HTTP，严格 binder 不变。每阶段都检查显式 `input_budget`，保留全部交付来源；初答、复核的成功和失败用量都通过 `result.metadata`/`error.metadata` 分阶段保留，`usage` 汇总这些物理请求一次。`reader_identity` 标记本集成代码身份，不能继承原实验的 8/8 成绩。调用前仍需冻结并授权独立的总调用/成本/截止账本，不能直接复用历史余额。

选择性规则来源 `250795a`；本集成新增交付预算与省略审计。旧四题中 28.3% 的 token 改善仅是历史局部结果；新 12 边界上的通用复核没有增加完整正确数，默认保持关闭。图片 caption 未导入、远距离前文和一般指代解析均未解决。

B01 `AblationService` 使用 `five-arm-paired-v2-complete-input-budget` 身份；C/D/E解析组复用普通Dynamic完整输入保护，超预算保存失败Trace且不发解析/回答请求，不裁掉事实。B03也强制显式正整数 `input_budget`；B05两阶段同样受预算约束。该请求上限不替代调用方持久化总调用/成本/截止账本。


## 最新采用边界

[统一采用矩阵](../integration/production-v1/adoption.json) 是当前决定。
RC2 保留 B03/B05 显式接口；通用复核在真实开发题上的完整正确数 17/24→17/24，
不足以推广默认复核（D08）。后续固定状态/日历指导 F02、指导与选择性前文复核组合 F03
均仅保留研究，F01 对象编码 v1 不采用；它们不在本分支的默认 Prompt、API、UI 或 Build 中。
F03 的 15.7594% 成本节省低于 20% 门槛，不能以局部正确数取代完整验收。
后续原件保留于 `codex/integration-followup-20261101@de3af73`，不复制其执行器到生产路径。

本分支没有启用这些接口的配置开关。仅导入模块不会使其生效；调用者必须显式执行上列入口。
`tests/test_production_paths.py` 在默认 Build/API/UI 成功及失败路径中将各研究边界替换为失败哨兵，
确认不会触发；显式模块自身的预算、来源和失败计量由各自测试保护。
