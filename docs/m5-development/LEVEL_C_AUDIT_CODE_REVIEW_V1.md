# Level C 运行审计器独立代码复核 v1

初审结论：发现 **1 项 P2**，涉及 frozen Trace 的问题和策略归属未核对。两个独立 synthetic 复现均被初版审计器接受；现有离线测试新鲜运行 `11 passed`。该发现不代表真实冻结结果存在上述问题，也不影响独立物理账本的请求和金额封顶。

2026-11-04。非作者审查者 `final_code_review_v6`，未参与审计器实现。工作树 `/home/kenqia/my_folder/locomo-worktrees/m5-final-development-20261104`，初审 HEAD `c8e5c09456c8bfc3f2ad56701a0bfb56928c12b1`。报告遵循此前读取的 `google-developer-docs` 技能。实际读取新增审计器、测试及必要的 `level_c.py`、`QueryService`、`EvaluationService`、`provider_usage`、`BudgetTransport` 和逻辑 snapshot 实现。

| 文件 | 初审 SHA256 |
| --- | --- |
| `tools/m5/level_c_audit.py` | `c3debdd6a0f259eab274ff7ea620673a5d5ed9ab6486ffef53b5ffa57074fbfd` |
| `tests/test_m5_level_c_audit.py` | `016ac618518a8c06c3f3750669aa3f2405738d497c0d742a42a9c1b0b865215b` |

## [P2] Trace 的问题和策略归属尚未绑定固定输入

`scope_check` 遍历 Trace 内的 `build_id` 和 `sample_id`，但不比较 Trace 的问题与该 `question_id` 对应的固定输入，也不拒绝当前两臂不可达的 `m5_variant` 或 raw 策略标记。`frozen_items` 仅核对 item 外层问题身份，不能替代 Trace 内容归属检查；数据库 candidate/trace JSON 与 item 相等同样不能证明其回答了预定问题或未开启 Bonus。

独立 synthetic 复现使用已有 `proposal` fixture 和 `fake_frozen`，每次在新的 TemporaryDirectory 创建数据，仅修改一份 synthetic item 并更新其 synthetic freeze SHA，不修改 plan 或生产代码：

- 加入 `trace.m5_variant={adaptive:true,compression:true}` 后，`audit` 通过并输出 `bonus_enabled=false`。
- 将 `trace.question` 改为 `DIFFERENT_SYNTHETIC_QUESTION` 后，`audit` 通过，仍声称初始逻辑快照重建成功。

建议使用无 Gold 的 `inputs.json` 绑定实际存在的 Trace/candidate 问题，拒绝 Bonus 标记和当前 arm 不可达的 raw 策略/恢复标记；合法的无 Trace 失败项应保留为缺测，避免伪造时间或调用。若字段缺失仅能报告未核验，应明确区分这一状态。已将复现发给作者 `level_c_prepare` 与父任务。

private 证据：`var/m5-development/level-c-audit-review-reproduction-v1.json`。该文件只含 synthetic 变更说明、受控输出和验证结果，不含真实预测、原文或 Gold。

## 已核对通过的控制

- 终态 `audit` 首先调用 `frozen_items`，完整200项路径、哈希、外层身份和结果状态校验通过后才访问阶段数据库；进度入口只读取现有 item，不访问数据库、不要求完整 freeze。
- 初始数据库 snapshot 重建只将3张允许新增的查询表视为空，其他初始表均参与摘要；3张执行 evaluation 表必须为空，未知表直接拒绝。该比较不打开带 Gold 的原始来源数据库。
- 检查数据库仅四个开发 Build 和开发对话。保护 snapshot 包含 Memory、来源、抽取片段、关系、投影、索引和冻结 Build 状态；相关表任意单独变化由现有 mutation 测试拒绝。
- 查询 checkpoint 按 item 内的 candidate/expansion ID 查询并比较完整 JSON，额外未归属记录被计数拒绝；Dynamic Trace 与保存的 query_traces 逐条核对。源码已包括作者补强的 candidate checkpoint 关联。
- 物理请求/预约仅以 ledger 为依据，不把 `started` 检查点或本地拒绝当作发送。完成 adapter record 只作诊断；账本比已完成 adapter record 多出的部分单列，不用诊断记录虚构物理请求。
- ledger policy完整绑定冻结 plan；预约金额用 Decimal，未知/部分 usage 分开报告。未知用量预约不退款，不虚构账单；部分已报告字段进入 token 总量，同时保留 unknown 标记与预约金额。
- ordinary/diagnostic 与两臂分别报告 planned/completed/pending/succeeded/failed，失败保留在成功率分母。本地policy/budget拒绝单列；item/stage/adapter时间分别汇总，缺失值有明确 observed/missing，未把缺测填零或混称查询端到端时间。
- 正常输出为数字、固定字典键和受控状态，不返回预测、来源或 Gold；质量指标明确标记不由该审计器测量。

## 新鲜验证

实际执行：

```sh
./tools/integration/check.sh tests/test_m5_level_c_audit.py -q
```

结果：`11 passed, 1 warning in 57.77s`。warning 为既有 Starlette/TestClient 的 `httpx` 弃用提示。现有测试覆盖 synthetic 完整流水线500次 MockTransport 请求与200项结果，以及独立保存元数据fixture中的本地拒绝、unknown/partial用量、保护表变化、禁止表、无数据库进度和checkpoint变化检测。上述11项为本审查者实际复跑结果；额外实际运行了两项private复现。

## 边界

所有检查只使用 synthetic 临时数据库和受控 MockTransport；真实 provider 请求为0。没有读取或写入真实 stage 数据库、Gold、holdout、真实 items，未干预会话89061或85918，未重启任务。没有修改作者代码、冻结 producer、真实计划或数据库，只创建本报告及上述private证据。

此复核不裁决真实模型结果、关系或问答语义，不代表真实终态审计通过，也不批准发布或总目标验收。初审finding需在修复后追加独立复核记录。

## 修复后独立复核：P2 已关闭

2026-11-04，仍由非作者审查者 `final_code_review_v6` 复核；HEAD 未变。初审记录与 synthetic 证据保留。此次读取修复后的完整审计器及新增测试，没有修改作者代码。

| 文件 | 复核 SHA256 |
| --- | --- |
| `tools/m5/level_c_audit.py` | `5492cc710e6fb8967a281f0b0d42f8c2cc16b318d13edb34b7b3b62c02794cd9` |
| `tests/test_m5_level_c_audit.py` | `05057f59a613ad8433a0d732405809d114a8fc151d29a793b2acd0815148664b` |

`scope_check` 现在使用无 Gold 的固定 inputs 绑定 question、sample 和 stratum，并在实际查询容器内核对问题，避免误把来源 caption 中的 `question` 当成查询。它核对存在的 strategy，拒绝 Bonus `m5_*` 元数据及当前两臂不可达的 raw/recovery 标记。合法 Hybrid 空 raw_context 和无 Trace 失败仍可审计；成功项缺失 Trace 被拒绝。新增测试覆盖初审的两类篡改、operation 内嵌 Bonus、raw 标记及合法反例，原 P2 已关闭。

另外核对了模型身份汇总：完成调用的 requested_model 必须匹配冻结 plan；effort 与操作角色一致，max_tokens 处于冻结策略范围，returned_model 仅允许受控标识字符。缺失返回模型单列，未推定实际服务模型身份。未发现新的 P0/P1/P2。

独立新鲜运行相同命令，结果为 `24 passed, 1 warning in 63.40s`。warning 仍为既有 Starlette/TestClient 的 `httpx` 弃用提示。此次仍只使用 synthetic 临时 fixture 和 MockTransport，真实 provider 请求为0；没有访问真实 stage、Gold、holdout 或真实 item，也未干预执行会话。该结论仅关闭代码发现，不代替真实终态审计或总目标验收。
