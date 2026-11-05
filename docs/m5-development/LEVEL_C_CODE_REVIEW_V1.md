# Level C 独立代码复核 v1

结论：初审发现 **1 项 P2**：源 SQLite 身份仅覆盖主文件，遗漏已提交 WAL，可能在生成冻结后接受被变更的 Gold。已在独立 synthetic 数据库实际复现并通知作者。新鲜现有离线测试 `3 passed`。本报告不授权真实生成、QA 或发布，也不对正在运行的 conv-43 关系阶段作判断。

2026-11-04，审查者 `final_code_review_v6`，未参与实现。工作树 `/home/kenqia/my_folder/locomo-worktrees/m5-final-development-20261104`；初审 HEAD `fca2bf1dc8a2765ab95ead8e96afb0f9cb959e84`。报告沿用已读取的 `google-developer-docs` 技能。

## 范围与身份

实际深读三个新增文件及生产 `QueryService`、`EvaluationService.baseline`、QA 计分函数、BudgetTransport、版本 pin、导出契约、索引 encoder 选择等必要调用方。未打开真实留出 QA/evidence/answers 或密钥，未执行真实 generate、score、preflight 或读写真实准备数据库。

| 文件 | 初审 SHA256 |
| --- | --- |
| `tools/m5/level_c.py` | `3a60761e347f24512998e9b1ea648c577f912df6078b77e40738bbad19f4f2a3` |
| `tools/m5/level_c_embedding_preflight.py` | `638b39743803ecc2adbd212f9396e672be8b88424fc1e10cd0eddbbc2229db25` |
| `tests/test_m5_level_c.py` | `0e4714a76d607e62ad232995ff582c292d17eb2bf6649fd421ec8d376b1eab1e` |
| `src/locomo_memory/evaluation.py` | `bb692981de015522e9e9d0696072fd8e5bc5c1876b1323ab59be6fd61e6db813` |
| `src/locomo_memory/evaluation_metrics.py` | `dc73df532621309c97fcd4b142fb8f1170272a0f6b45894631c854a6f4497af6` |
| `src/locomo_memory/queries.py` | `201bfb8622889fd811b0355ad02f2764a76a9e3cc04344b699b5966f8feec0cc` |
| `src/locomo_memory/m5_budget.py` | `1734357d07b1fc932e078ca1f5a15cf3f08fddd02a588b2bf55d93d9ac13f0ee` |

## [P2] 参考源冻结身份遗漏 WAL 的已提交变更

位置：`tools/m5/level_c.py:135`、`:160`、`:307`。

准备阶段和评分阶段仅用 `sha(origin)` 计算 SQLite 主文件的 SHA。项目 Database 使用 WAL；尚未 checkpoint 的已提交更新位于 `-wal`，主文件 SHA 可以完全不变。评分的只读连接会正常看到 WAL 新值，因此 `reference_source_changed` 不能拒绝这类参考变更。类似地，准备前后主文件 SHA 不变也不能证明投影/复制期间没有 WAL 更新。

实际复现仅使用 `proposal.__wrapped__` 创建的独立 synthetic 四开发 Build：

1. 准备正常计划，在临时输出构造 200 份 synthetic 结果及完整 generation freeze，预测为 `MUTATED_SYNTHETIC_GOLD`，不发真实或 mock 生成请求。
2. 持有源库写连接，设置 `wal_autocheckpoint=0`，将 synthetic Run 的参考答案更新为该字符串并 commit，保持写连接打开。
3. 确认主文件 SHA 仍等于计划值，但 WAL 存在。调用 `score`。

实际结果：

```text
main_sha_unchanged_after_committed_gold_mutation=True
wal_exists=True
score_accepted_changed_reference=True
ordinary_hybrid_mean=1.0
```

这不是对真实 Gold 的修改或评分。它证明初版来源身份无法锚定冻结参考，而不表示当前真实计划的参考已变更。

建议：以主 SQLite 文件与 WAL 存在性/原始字节 SHA 组成保守存储身份，准备题目投影/副本复制前后核对，评分在完整 generation freeze 校验后再核对参考身份。不要在评分前调用逐行逻辑 snapshot 读取源库 Gold。文件身份可能因 checkpoint 而保守拒绝，可明确记录该限制。已通知 root 与作者 `level_c_prepare`；旧未授权计划应保留，新身份使用新计划。

## 其余重点核对

- 固定样本校验 80 ordinary、20 diagnostic、100 个不重复问题；每开发对话分别 20+5。只选固定题目身份，未按本次预测或成绩选题。
- 准备阶段 SQL 仅投影 Run config、pins、dataset 与问题字段到 Python。副本只复制 allowlisted Build/source/index/relation 表，不复制 evaluation Run、import annotations、Gold 或 evidence。仅四个开发 sample/pin；foreign key check、complete pin 和 `MemoryExport` 对四份 Build 的来源、Memory、关系、索引和投影身份继续进行生产校验。
- Hybrid 与 Dynamic 复用相同模型对象、冻结 Settings、四份 pinned Build 和 production retrieval。Hybrid 走既有 `hybrid_no_resolution` 基线（analysis+expansion+answer），Dynamic 走 `QueryService`（analysis+expansion+resolve+answer）。无 Bonus、策略替换或 holdout。
- 预算计算为 `100 × (2+3) × 3 = 1500` 次；每请求 160,000 输入消息 UTF-8 bytes、32,768 输出 tokens，Decimal 计算 USD130.9824000 保守预约上界。重试和所有两臂调用共用一份 BudgetTransport，delegate 重试禁用；原始请求费用上界仍取决于执行前核对的官方费率。
- 授权不自动创建；缺失授权在标记和 provider 之前拒绝。执行核对计划、生产模块代码 SHA、输入/样本/Build身份文件 SHA、准备数据库与 ledger 逻辑快照，再用后端锁与排他写入创建一次性标记。正常失败逐项保存 error/trace；进程级中断保留标记及已写结果，不能自动继续或打开 Gold。
- `frozen_items` 要求完整 200 项路径、SHA、问题/对话/分层/arm/outcome 匹配，并在打开参考库前执行。修改单项或不完整 manifest 被拒绝。Gold 按开发 scope 投影；每 arm 的 planned/scorable/succeeded、成功子集分数及全部可评分样本失败记零分数分别报告，ordinary/diagnostic 分开。缺失 Gold 单列，不静默计成正确或零。
- `review_units` 仅在生成冻结后输出开发原文证据与预测，标记独立审核待完成，不生成真值。`level_c_embedding_preflight` 明确要求 local-files-only，检查固定100个向量的384维、有限性及单位范数，不产生 provider 调用或 Gold。

## 新鲜验证

实际运行：

```sh
./tools/integration/check.sh tests/test_m5_level_c.py -q
```

结果：`3 passed, 1 warning in 36.51s`。warning 为既有 Starlette/TestClient 使用 `httpx` 的弃用提示。

端到端 synthetic 测试实际执行生产 Hybrid/Dynamic 链路，检查 Gold/evidence sentinel 未送入 HTTP、缺失授权拒绝、生成前禁止打开 Gold、完整200项冻结、失败保留、missing Gold 分母、重复执行及篡改单项后的评分拒绝。该测试发生 502 次 MockTransport 请求，包括有限失败重试，真实 provider 请求为0。额外独立运行了上述 WAL 复现。

## 边界

未复跑真实 MiniLM preflight，未访问真实 Gold，未执行真实 Level C 生成或评分，未触碰 conv-43 关系进程、真实计划或生产源码。只新增本报告。来源指纹校验不证明 Memory 抽取、关系或问答语义正确；synthetic 流程成功不代表课程或真实开发集分数达标。修复后须追加独立复核及定向测试，保留此初审发现。

## 增补：WAL 来源身份修复复核

2026-11-04，实际读取作者修复及两项新增 synthetic 回归后，独立重新运行完整文件测试。**初审 P2 已修复，本次明确审查范围内无剩余阻断 finding。** 初审发现、SHA 与漏检复现保留如上。

修复后的代码身份：

| 文件 | SHA256 |
| --- | --- |
| `tools/m5/level_c.py` | `3d8cb571f727099db8a0f171527052b2354449b9f9194e499e8c7e78f9d53ee0` |
| `tools/m5/level_c_embedding_preflight.py` | `638b39743803ecc2adbd212f9396e672be8b88424fc1e10cd0eddbbc2229db25` |
| `tests/test_m5_level_c.py` | `ff54d72aaa53c5f29e225b2824d27b74c383d742defc470d4a18d1619a2a1d54` |

核对结果：`source_storage_identity` 只记录主 SQLite 与 `-wal` 文件的存在性和原始字节 SHA，不打开 SQL Gold、不纳入易变共享内存文件。准备在投影/复制前后比较同一原始存储身份；评分先完成全部 generation freeze 核验，再在打开 Gold 前比较，读取参考后再次比较。只读连接采用明确 `BEGIN` 读取快照，并在 `finally` 关闭。该方案会因 checkpoint 等原始文件变化保守拒绝，即使逻辑内容等价；该限制不放宽冻结身份。

两项新增回归实际验证：

- 参考答案 commit 到 WAL、主文件 SHA 不变、写连接保持打开时，`score` 在参考 readonly 调用前以 `reference_source_changed` 拒绝，且不写 `scores.json`。
- 准备复制期间并发提交源库 WAL 元数据变化时，`prepare` 以 `source_changed_during_preparation` 拒绝，且不写 `plan.json`。

独立新鲜执行：

```sh
./tools/integration/check.sh tests/test_m5_level_c.py -q
```

结果：`5 passed, 1 warning in 36.60s`。warning 仍为已有 Starlette/TestClient 弃用提示。原有200项 synthetic 端到端流程、未授权拒绝、Gold隔离与完整分母测试同时通过。

作者告知将旧未授权计划保留，并用新唯一目录准备修复身份；本审查者未修改或读取真实计划数据库，未运行真实生成/评分/embedding preflight，也未触碰正在运行的关系阶段。此增补只对上述代码与离线机制提供独立复核，不能代替真实阶段的明确批准及终态验证。

## 增补：所有可达调用分支的理论请求上界

2026-11-04，在申请费用前按源码调用图再次只读核对。结论：**当前固定 Level C 两臂的 `100 × (2+3) × 3 = 1500` 次物理请求及 USD130.9824000 理论上界完整，不需要因证据缺口或解析重试增加。** 这是“最多”，不是每项恰好消耗上界。不能把此结论泛化为整个 QueryService 的所有可选策略均最多3次 generate。

源码依据：

| 路径 | generate 次数上界 | 源码依据 |
| --- | --- | --- |
| 共享 retrieval | 1 | `retrieval.py:140` 唯一 `query_analysis` 调用。analysis失败后仅回退原始检索词，不启动第二次 generate；embedding/SQL排序不调用生成模型。 |
| 普通 Dynamic | 共享 retrieval 1 + resolve 1 + answer 1 = 3 | `queries.py:164` retrieval；`:212` 唯一 `resolve`；`:228` 调用 `generate_answer`，其唯一模型调用为 `:112`。`:170` ExpansionService 全程仅SQLite及确定性排序，没有生成调用。 |
| Hybrid | 共享 retrieval 1 + answer 1 = 2 | `evaluation.py:199` retrieval；`:222`本地扩展；`:228`一次 `generate_answer`，没有调用 resolve。 |
| 显式 raw fallback，可选且当前不可达 | 共享 retrieval 1 + initial resolve_raw 1 + joint_resolve 1 + answer_raw 1 = 4 | `raw_queries.py:205` 初次 resolve，`:215` 在insufficient且有raw时最多再resolve一次，两次均经`:194`；`:277` answer_raw。不是循环重规划。 |

当前 Level C 的 `ARMS` 在 `level_c.py:38` 固定为 `hybrid_no_resolution/dynamic`；`:238` 构造 QueryRequest 没有传 raw strategy，`query_schemas.py:61` 默认 `strategy='dynamic'`；`:242` 每个arm仅调用一次。`queries.py:195` 仅在显式 `dynamic_raw_fallback` 时进入 raw 分支，没有根据 insufficient、证据缺口、冲突或异常隐式切换。普通 Dynamic 的解析失败在`:216`至`:219`重新抛出后终结该项；证据不足仍只调用一次answer；预算拒绝提前终结。`generate_answer` 证据预算/冲突处理同样没有增加generate调用。

`model.py:317`至`:323` 将单次 generate 内部物理尝试限制为 `model_retries+1`，当前冻结值为3；context的max_attempts只能通过min进一步减少。retry feedback在同一个有限循环内更新消息，不递归调用generate；每轮`:386`最多一次HTTP POST。`:428`的明确本地预算拒绝立即抛出，HTTP不可重试错误也提前停止。Level C 显式创建 `HTTPTransport(retries=0)`，因此没有额外隐藏的delegate重试。外层200项没有失败重跑循环；失败结果照常冻结。

若未来将 Dynamic 改为 `dynamic_raw_fallback`，理论上界应改为 `100 × (2+4) × 3 = 1800` 次；按当前相同单次预约上界将是 USD157.1788800。当前独立 ledger 即便策略代码被误改仍会硬封顶，但不能因此继续宣称旧的完整理论次数足够覆盖raw策略。当前计划不含此变更，本次未修改代码或计划。

本次没有运行任何真实或mock调用，仅静态读取调用方及全部相关分支。复核时 `level_c.py/model.py/queries.py/evaluation.py` SHA与上文保持相同；额外读取 `raw_queries.py` SHA为 `bd09a2e71c111b7a9df7e7baba822ceaf6455c53b47ffbdb4ddcbdcb34912e0e`。
