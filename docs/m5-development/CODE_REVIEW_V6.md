# M5 非作者代码复核 v6

审查日期：2026-11-04。审查者：`final_code_review_v6` 独立子代理；未参与被审源码的实现。

结论：发现 **1 项 P2 问题**，涉及预算本地拒绝后的持久调用诊断。针对所审范围，未发现突破请求次数或金额硬限制的问题。此次复核不批准真实 QA、Release、合并或总目标完成。

## 审查身份与范围

工作树：`/home/kenqia/my_folder/locomo-worktrees/m5-final-development-20261104`。

固定基点：`915fac0`；审查时 HEAD：`ed47868c83163485d1e276a6203bdffd871640cd`。检查 `git diff 915fac0...HEAD` 的文件清单及提交历史，实际深读下列源码及其调用方；未声称逐行审阅全部实验工件或全部生产改动。

- `src/locomo_memory/m5_queries.py`：显式日期优先级、时间运算符、变体 Trace、图扩展调用。
- `src/locomo_memory/m5_budget.py`：策略固定、SQLite 原子预约、嵌套预算、保守保留费用。
- `src/locomo_memory/model.py`：本地拒绝停止重试、保留先前物理调用、`on_call` 检查点。
- `tools/m5/extraction_recovery.py`：授权匹配、生产身份、逻辑快照、独占锁、独占执行标记、单片段恢复。
- 尚未提交的 `src/locomo_memory/m5_query_review.py`、`tools/m5/query_review.py` 及测试：独立参考校验、来源范围、冻结、缺失预测分母。
- 相关调用方：`queries.py`、`builds.py`、`database.py`、`relation_diagnostics.py`、`relations.py`、`relation_replay.py`、`m5_adaptive.py`、`m5_graph.py`、`tools/m5/offline.py`、`tools/m5/holdout_extraction.py`。

已阅读根 `AGENTS.md`、`CONTEXT.md`、ADR 0001/0002、恢复协议及动态审核协议。报告按 `google-developer-docs` 技能编写。

审查时源码 SHA256：

| 文件 | SHA256 |
| --- | --- |
| `m5_queries.py` | `d0aa18f0a2fb537902a2ebeddeb10f7c5195002aa4d1ece0e51cf96de17c4332` |
| `m5_budget.py` | `1734357d07b1fc932e078ca1f5a15cf3f08fddd02a588b2bf55d93d9ac13f0ee` |
| `model.py` | `394f1bb436620bf9e63311dca4d83f6dd6e33ee12f28d0e7caf084490c1818de` |
| `extraction_recovery.py` | `439ade803fc1894c6c48ae4b20df3032b2fa44a6e7c823dc950ec959a1641260` |
| `m5_query_review.py` | `4b94e966cfef8e7c5b6e78684655d69b6d19925e2a6dae9ac022c3c84940fde9` |
| `query_review.py` | `57e3b952ab94eed08e466426590ca2fa153789a72677019f7c571c20764e1a7d` |

## Standards

未发现需要单独列为阻断项的仓库标准违规或结构性代码异味。保持只读源码，未改动共享实现或测试；只新增本报告。未创建远端记录、执行付费请求、加载凭据或读取 holdout QA。

## Spec 与行为发现

### [P2] 本地预算拒绝留下未发送的持久 provider 调用

位置：`src/locomo_memory/model.py:425` 新增的 `except ModelFailure` 分支；相关前置检查点在 `model.py:382`，持久调用方在 `relation_diagnostics.py:33`。

触发条件：给 `DeepSeekModel.generate` 传入实际的 `RelationAttempts.observer`，并用 `BudgetTransport` 在 HTTP 发送前本地拒绝请求。适用于零预算，也适用于已有物理失败后下一次尝试耗尽预算。

`generate` 先通过 `observe_call(on_call, call)` 发出 `status='started'`。关系 observer 随即将该记录写入 `relation_provider_calls`，并追加到 Build 的 `model_metadata.calls`。预算拒绝后的新增分支直接抛出只包含先前物理调用的 `ModelFailure`，未终结或撤销这个已经持久化的检查点。`Relations._judge` 追加返回的空 `calls` 也不会移除它；随后 `RelationAttempts.recover` 会将该未发送调用改标为 `interrupted`。

影响：物理账本仍保持正确，请求和费用硬限制未失效；但关系任务历史、Build 调用计数和未知用量诊断会把已知未发送的尝试误记为未知物理调用。这与“本地拒绝不记为计费请求”的审计目标不一致。当前抽取恢复不传 `on_call`，因此该入口的已验证次数限制不受此问题影响。

实际离线复现使用独立临时 SQLite、真实 `RelationAttempts.observer`、`max_requests=0` / `max_usd='0'` 与禁止 provider 被调用的 `MockTransport`，得到：

```text
failure: physical_request_budget_exhausted
physical_reservations: 0
provider_sent: 0
returned_metadata_calls: 0
durable_provider_status: started
build_metadata_calls: 1
durable_status_after_recover: interrupted
```

建议：为已知本地拒绝增加显式的终态及 `physical_request_sent=false` 语义，并在持久调用统计中排除；或在安全保留“发送前崩溃未知”检查点的前提下撤销这类已知未发送记录。避免直接移除所有发送前检查点，否则会破坏现有崩溃审计。补充使用真实关系 observer 的零预算和“先物理失败、再本地拒绝”回归测试，同时断言原物理调用仍保留。

## 核对通过的行为

- 显式 `request.requested_date` 优先于问题中的“现在”和截止时间，传入 `BonusRetrieval` 后覆盖优先级区间；临时 `BonusQueryService` 仅在没有显式日期时设置相对日期或保留时间运算符。未修改存储时间。
- `BudgetTransport` 在 `BEGIN IMMEDIATE` 内检查已有预约次数和金额并插入预约，支持多 transport 并发争用同一槽位；未知传输结果保留完整预约。`DeepSeekModel` 本地拒绝不继续自动重试，异常元数据保留之前的物理失败记录。
- 恢复入口以本地 guard 包裹原全局 guard。两层均在 delegate 之前预约；原全局拒绝可留下本地保守预约，但不会新建全局物理请求。不能将两个账本相加。
- 恢复入口校验明确授权、原计划/配置及实现 SHA，限制两个原阶段 Build 状态、唯一失败片段及该片段无已存 Memory；重用生产 `BuildService.retry/run`，生产契约仍由 `require_current_contract` 检查。
- `snapshot` 在只读事务中对逻辑已提交行计算摘要，覆盖 WAL 的已提交数据。执行取得后端独占锁后再次核对数据库/账本快照；`write` 使用文件 `open('x')` 原子创建执行标记，崩溃和重复执行不会自动复用此次批准。
- query scorer 拒绝显式自标、非布尔不确定性、重复/越界身份、伪造引文及所选 Memory 缺少自身来源支持。它只声称给定候选证据包内的 applicability，不声称全局召回或 QA 质量。
- 当前 35 项已有解析预测、5 项缺失的计划中，缺失预测进入可评分分母计错；空预测集合可被计为实际预测，参考不确定项单列。全部没有实际预测时按当前协议返回 `not_measured`。
- 审核准备按题目身份确定样本，校验候选与导出一致，审核包不写入解析选择、存储关系、生成答案或 QA 标注。评分前要求完整参考并校验冻结工件 SHA。

## 新鲜验证

实际执行：

```sh
./tools/integration/check.sh tests/test_m5_extraction_recovery.py tests/test_m5_budget.py tests/test_m5_queries.py tests/test_m5_query_review.py tests/test_builds.py tests/test_m5_failure_audit.py tests/test_m5_adaptive.py -q
```

结果：`50 passed, 1 warning in 31.12s`。warning 为现有 Starlette/TestClient 的 `httpx` 弃用提示。该入口清除 live model 环境变量并启用离线 guard；所有新鲜验证均无真实 provider 请求。此外实际运行了上述两个独立临时数据库复现：先记录 observer 序列，再接入生产 `RelationAttempts` 持久化与恢复路径。

父任务已提供全仓 644 通过的历史结果；本报告未再次运行整仓，因此不将其作为本审查者独立复跑结果。

## 局限与验收边界

未执行原失败片段的真实恢复、真实模型 QA、独立测试集 QA、发布、远端写入或最终总验收。未审阅 holdout QA、凭据、敏感日志或私密 history。未验证独立参考标签本身的语义正确性；`reviewer`/`provenance` 的真实性依赖实际审核组织，字段校验无法证明独立性。未验证电源故障级别文件系统持久性；执行标记使用原子排他创建，并未实现跨磁盘事务。

本报告仅对以上明确身份与范围提供非作者代码复核。修复 P2 后需复核相应 diff 与新的针对测试，才能清除此 finding。

## 增补：P2 修复复核与参考状态校验

2026-11-04，在相同 HEAD 的未提交修复上完成第二次实际复核。保留上面的原始发现及其复现记录。**原 P2 在实际使用持久 observer 的 `RelationService` 路径上已修复，本次定向范围内没有剩余阻断 finding。** 此结论不扩展为全部自定义 `on_call` 调用方均已处理本地拒绝。

已深读 `relation_diagnostics.py`、`relations.py` 及 `test_relation_diagnostics.py` 的新增 diff：

- `RelationService._judge` 只在 `physical_request_budget_exhausted` 或 `physical_request_policy_rejected` 两个明确的发送前拒绝错误下清理预派发检查点。
- `discard_local_rejection` 仅查询当前任务、当前 logical attempt，删除 `status='started'` 且未收到响应的记录，并按 `call_id` 同步移除 Build 调用元数据。先前 `invalid_output` 等终态物理调用仍保留。
- 清理、保存具体预算失败错误、追加原物理元数据及标记 logical attempt 失败处于同一数据库事务。普通超时、崩溃及已观察响应的调用不经过该清理分支。
- 新测试分别覆盖实际请求 0 次，以及实际请求 1 次后再本地拒绝；两者均检查关系历史、Build 调用数、物理账本与重启前后完全相同。既有进程崩溃恢复测试继续保留未知调用。

修复身份：

| 文件 | SHA256 |
| --- | --- |
| `src/locomo_memory/relation_diagnostics.py` | `1778028ded92529eb6501e8ef49bd21aca6a99187097094f5d647f0e701bf4ea` |
| `src/locomo_memory/relations.py` | `7f909ce169756c70d9f4415811e1436518a5e6c61b4e47e4fe50f9b63b9ac7a6` |
| `tests/test_relation_diagnostics.py` | `ffe71de2454fa957282f00a191bc9711a9402643f2f23fe4d9fbfc121667c00a` |

重新计算确认 `model.py` 与 `extraction_recovery.py` 的 SHA256 和本报告初审记录相同；本修复未改变该抽取 producer 身份。

实际新鲜执行：

```sh
./tools/integration/check.sh tests/test_relation_diagnostics.py tests/test_m5_budget.py tests/test_m5_query_review.py tests/test_m5_extraction_recovery.py -q
```

结果：`37 passed, 1 warning in 33.22s`。warning 仍为既有 Starlette/TestClient 弃用提示。没有真实 provider 请求。

另外，实际以 `score_query_applicability(units, refs, [])` 校验两份独立参考及审核单位，**没有打开历史预测文件**。40 份参考身份完整且唯一，引用、所选 Memory 的来源及独立性字段结构均通过当前 scorer 校验；其中 `sufficient=30`、`insufficient=9`、`conflict=1`，25 份可评分，15 份 `uncertain/unresolvable`。直接比较 `set(STATUSES)` 与 `typing.get_args(query_schemas.EvidenceStatus)`，三种合法状态标签完全一致。

此项校验确认状态字符串及引用结构，未重新裁决参考语义，也未计算预测成绩。真实 QA、Release、远端写入与总目标验收的边界保持上文所述。

结构校验输入 SHA256：`review-units.json=e06ce7b3f9ccd6b34b89934e0dcb6ea037f546abecb3c3c70f000dde81540911`；`independent-a.json=45675cdfff88bd3d1afe85000ddc02fe80e0b1059d7f72a41c069e123fd4530c`；`independent-b.json=60eb34abd0a0faadf3faf226553bd8b86bea15ad3b8489de8bc64bb9f0cfdc96`。
