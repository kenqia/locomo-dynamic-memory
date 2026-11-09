# 关系阶段审计器独立复核 v1

结论：发现 **3 项 P2**，均会使只读审计器漏报不符合阶段边界的状态。已有增量测试新鲜运行 `11 passed`；另用三个独立 synthetic fixture 实际复现以下漏报。发现针对审计器，不表明真实运行已出现这些状态，也不表明生产预算 guard 失效。

2026-11-04，非作者审查者 `final_code_review_v6`。工作树 `/home/kenqia/my_folder/locomo-worktrees/m5-final-development-20261104`；审查时 HEAD `08be26d1bf8a069191054464957a0ac6b950c8a7`。本报告遵循此前已读取的 `google-developer-docs` 技能。

## 范围与身份

实际深读 `tools/m5/relation_audit.py`、`tests/test_m5_holdout_relations.py` 新增审计测试，以及必要的 `QueryService` 表定义、`create_projection`、关系 schema、预算 ledger/plan 格式、只读逻辑快照与已有抽取审计实现。未运行真实阶段的审计或 execute，未读取真实留出 QA、evidence、answers、密钥或日志。

| 文件 | 初审 SHA256 |
| --- | --- |
| `tools/m5/relation_audit.py` | `4026b5425fed0c60163391cc868f4b77dfddc6d5dbd3e5efb908e27ddcf315ef` |
| `tests/test_m5_holdout_relations.py` | `f4e4e60d7bd6d007faae93ca0a691fc31bfdc9bb3000e721195b6ecee0ce74b6` |

## Findings

### [P2] 禁止查询检查遗漏真实持久表 query_traces

位置：`tools/m5/relation_audit.py:84`。

禁止表列表检查 `query_results`，而生产 `QueryService.__init__` 在 `src/locomo_memory/queries.py:39` 建立的表是 `query_traces`，`_save` 也写入该表。失败于候选落库前的查询可以留下 trace 而不留下 `candidate_queries`。此时审计器跳过实际 trace，仍输出 `query_or_evaluation_run=False`，误报阶段未发生查询。

实际复现：独立 synthetic 准备副本新增一行 `query_traces(trace_id,build_id,result_json)`，内容仅为 synthetic 空 JSON；未运行 query。`audit` 通过并返回 `query_or_evaluation_run=False`。

建议：按真实表名检查 `query_traces`，增加只有该表存在记录的独立回归。只查询计数，不读取问题或答案正文。

### [P2] 预算核验仅信任 ledger 当前 policy，没有绑定批准计划

位置：`tools/m5/relation_audit.py:47` 和 `:60`。

`audit` 从 ledger 读取 policy，再用相同 policy 核验次数和金额并输出剩余预算，没有与 `plan['policy']` 的批准上限、费率、模型及单次限制进行比较。账本 policy 一旦变更，审计器会把变更后的值当作批准上限，无法独立证明请求仍受原计划预算约束。

实际复现：synthetic 计划保持 `max_requests=6`、`max_usd=0.5239296` 不变，仅修改 ledger policy 为 `max_requests=6000`、`max_usd=1000`。`audit` 通过，并输出放大的 policy 和剩余容量。

建议：将 plan 的 `input_usd_per_million/output_usd_per_million` 与 ledger 的 `input_rate/output_rate` 规范化为同一结构，核对完整 policy。之后才依据已核对的批准上限汇总。增加 ledger policy 单独变化、plan 不变时拒绝的测试。此修改不需要重写已冻结 plan。

### [P2] 不变性基线没有绑定冻结的 source_index_snapshot

位置：`tools/m5/relation_audit.py:61` 至 `:65`。

保护表摘要只比较“当前阶段副本”和“当前源索引库”。`plan['source_index_snapshot']` 记录了已批准的原始逻辑快照，但审计器没有核验它。源库和阶段副本若发生相同变化，两者摘要相等，审计器仍声称来源、Memory、片段和索引不变；因此该比较没有锚定准备时的基线。

实际复现：在 synthetic 源索引库及副本中同时改写 `source_turns.text` 为相同 synthetic 字符串，冻结 plan 保持不变。`audit` 通过，并返回 `source_memory_fragments_indexes_unchanged=True`。

建议：先核对源索引库的逻辑快照等于 `plan['source_index_snapshot']`，再比较保护表与其他 Build。增加源库和副本同步变化的测试，避免仅验证副本单独变化。保持真实冻结 plan 不变。

## 已核对通过的实现

- `connect` 使用只读 SQLite URI、`query_only=ON` 与显式读事务，contextmanager 的 `finally` 关闭连接。未通过 Database 构造器初始化或迁移真实库。
- 保护表使用固定本地 allowlist，摘要不会输出对话或模型文本；直接比较其他 Build 的完整行，现有测试确认副本 source 或 conv-44 单独变化被拒绝。
- 逐条关系通过生产 `MemoryRelation` 来源/schema 校验，限制同一目标 Build 及 conv-43，不将来源/schema 通过称为独立语义真值。
- 成功 `related` 状态重算投影并与存储完整 JSON 比较；终态对齐物理 ledger 与 provider 诊断数量，检查计划任务数、无 pending/running。失败阶段保留独立错误与未完成状态。
- 用量和预约金额使用 Decimal 汇总；缺少 prompt/completion 用量单列 unknown。输出明确实际账单及语义准确率未测，attempt 延迟未冒称整段 Build 或 query 延迟。

## 新鲜验证与复现

实际执行：

```sh
./tools/integration/check.sh tests/test_m5_holdout_relations.py -q
```

结果：`11 passed, 1 warning in 8.71s`。warning 为已有 Starlette/TestClient 的 `httpx` 弃用提示。

另外使用现有 `prepared.__wrapped__`、synthetic `sample` 与临时目录，分别构造上述三个状态后调用只读 `audit`；各状态独立创建 fixture，未变更共享测试或源码，得到：

```text
query_trace: audit_accepted=True, query_or_evaluation_run=False
ledger_policy: audit_accepted=True, reported_max_requests=6000
both_source_and_copy: audit_accepted=True, protected_unchanged=True
```

所有模型调用由测试中的 MockTransport 提供 synthetic 响应，真实 provider 请求为 0。未改动已授权正在运行的工具入口、生产代码、计划或其副本；只新增本报告。

## 边界

本次只复核审计器与增量测试，不对当前真实进程状态、785 条 Memory 的真实不变性、实际账单或关系语义质量作结论。没有独立执行留出 QA、发布或总目标验收。修复后应追加复核与定向回归结果，保留上述初始发现。

## 增补：三项 P2 修复复核

2026-11-04，在相同 HEAD 上实际复核修复后的审计器及新增三项定向回归。**上述三项 P2 均已在所审范围修复，当前没有未处置 finding。** 保留初审发现与原始复现，不将其覆盖为“从未发现问题”。

修复后身份：

| 文件 | SHA256 |
| --- | --- |
| `tools/m5/relation_audit.py` | `039c02b6390eab5366745514524428f9b28a39f7e6962ed7f852da5ff4d25bc8` |
| `tests/test_m5_holdout_relations.py` | `a0cd41166103958f8f62a2c99ff9ef151077afc486400833ae559aad26a92cc6` |

实际读取并确认：

- 禁止表检查改为生产真实表名 `query_traces`。只有该表存在 synthetic 记录的新增测试拒绝审计。
- 从冻结 plan 构造与 `BudgetTransport` 存储格式一致的 policy，使用 Decimal 规范化金额/费率字符串，映射输入/输出费率字段，再精确比较完整 ledger policy。仅放大账本上限、plan 不变的新增测试拒绝审计。
- 开始审计时使用只读逻辑 `snapshot(source)` 核对冻结 `source_index_snapshot`，之后再比较保护表与其他 Build。源库与副本同步变化的新增测试拒绝审计。
- 既有成功/失败审计和副本单独变化检测保持覆盖。测试在预期拒绝后仍断言副本逻辑快照不变。

独立新鲜运行相同命令：

```sh
./tools/integration/check.sh tests/test_m5_holdout_relations.py -q
```

结果：`14 passed, 1 warning in 11.00s`。warning 仍为既有 Starlette/TestClient 弃用提示。新增三项测试实际覆盖上述三个已复现状态，均由修复后的审计器拒绝。

核对冻结工具代码身份未变：`holdout_relations.py=960de2683e341966e13217a1a07ef4ef5a1b1e0dada840822f0d32e2865ae5d7`，`holdout_index.py=344b320970bd947f217189820c9bd421999775618dc083daf42b53e339e3c9c2`。本审查者未修改其内容、冻结 plan 或运行进程，也未调用真实 execute。

修复复核仅确认审计代码及 synthetic 拒绝机制。真实终态还需要父任务在进程结束后实际运行审计；本报告不预先宣称真实阶段通过、账单已核实、QA 完成或关系语义正确。
