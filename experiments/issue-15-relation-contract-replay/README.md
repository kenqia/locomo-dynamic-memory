# Issue #15 第二阶段：真实关系输出定位与最小修复

2026-10-20，Asia/Shanghai。用户已批准最多 6 次真实调用，并授权使用既有本地凭据。
修改前后各 3 次已完成，预算已耗尽，停止调用。结果为部分改善，两个多候选批次仍失败。
安全诊断见 [before.json](before.json) 和 [完整前后比较](comparison.json)。

第一阶段提交为 `9d36f76`，本轮重新运行两个诊断测试文件：34 passed。
原始失败基线及证据边界见 [旧离线报告](../issue-15-offline-relation-diagnosis/README.md)。
原始 87 次失败细节依然未知，已有独立回放不计入本次调用。

## 固定输入

[plan.json](plan.json) 记录完整任务和候选 ID、输入顺序、输入/request hash、配置和实现身份。
源 Build 为 `91f1f50938064972820e3ab7b390d9dd`，源数据库 hash 为
`13497e43f418275585532d7d8a3a2bb326035662ed6eef67f41a05b6e8f46116`，
与此前离线审计一致。读取前后 hash 一致；没有启动旧后端或更改源库。

| 来源任务 | 完整历史候选数 | 修改前输入估计 | 选择理由 |
| --- | --- | --- | --- |
| `relation:2` | 1 | 2,318 | 单候选，另一次独立回放有同维度约束线索 |
| `relation:44` | 20 | 9,308 | 多候选，旧记录一次输出达到上限 |
| `relation:90` | 20 | 9,948 | 多候选，旧记录两次输出达到上限 |

输入估计使用 `regex-word-punctuation-v1`，包含 Prompt、JSON Schema 和 payload，
不是 provider 的 token 计数。达到输出上限只是选例线索，不是已确认的截断。
每个任务保持原 batch 和候选顺序，不拆成单对。

## 已批准预算

总上限 **6 次真实 provider 调用**，包括所有探针、内部重试、失败、网络重发和纠错调用。
本计划不发探针，不增加反馈调用；修改前每项 1 次，取得证据并完成最小修复后每项最多 1 次。
执行修改前组不会自动执行修改后组。

| 项目 | 两组约定 |
| --- | --- |
| 模型 | `deepseek-flash`，官方直连 |
| temperature / thinking / response_format | `0` / disabled / `json_object` |
| 每次 max_tokens | 4,096，请求输出上限 |
| HTTP timeout | 60 秒，沿用源配置，不代表整轮墙钟上限 |
| 内部重试 | `0`，区别于旧 Build 的 `2`，两组保持一致 |
| 修改前请求输出上限合计 | 12,288 tokens |
| 两组合计请求输出上限 | 24,576 tokens |
| 金额 | 未估算；未取得可信的当前价格，调用次数上限不等于金额上限 |

修改前输入估计合计 21,574 个 regex 计数单位。修复后若 Prompt/Schema 改变，重新记录
实际请求 hash 和输入量；不宣称两组输入 token 绝对相等。

调用预算首次执行时冻结，发送前先提交调用预留。中断或用量未知的槽位仍占上限，
不自动返还、不自动重发。传输失败、HTTP/超时/上下文拒绝停止实验；普通输出失败
保存具体诊断后继续下一固定候选。全部候选成功时停止，不强行进入修复后组。
受控 CLI 和读取方式见 [操作说明](../../docs/app/relation-replay.md)。

凭据仅在执行进程内从已有受保护文件加载，不输出或持久化，不修改凭据文件和应用配置。
冻结的 `plan.json` 保留准备时的 `awaiting_budget_approval` 状态；实际授权和调用次数
以本文及独立 `calls.sqlite3` 为准。SQLite ledger 保留在本地，本目录忽略该库及运行锁；
可审阅安全导出保存为 JSON。

## 修改前证据与修复范围

实验 ID 为 `ec886d1d99c142ab9efb3cc944e6cb16`。三次调用的 `finish_reason`
均为提供方实际返回的 `stop`，没有据输出 token 数推断结束原因。

| 任务 | 错误代码 | 字段路径 | prompt / completion / total tokens |
| --- | --- | --- | --- |
| `relation:2` | `same_state_dimension_required` | `judgments[0]` | 1782 / 272 / 2054 |
| `relation:44` | `reason_and_unique_evidence_required` | `judgments[18]`、`judgments[19]` | 8393 / 3625 / 12018 |
| `relation:90` | `same_state_dimension_required` | `judgments[19]` | 9074 / 3895 / 12969 |

三次均为 `invalid_output` / `domain_validation`，没有取得通过完整校验的关系集合，
标签分布和有效候选覆盖未知，不填零。联合规则错误无法区分空白理由与重复证据 ID，
不根据它进一步猜测原文或回填旧失败。

原 Prompt 只对 SUPERSEDE 明确同维度前提，校验器还对 RETAIN 和 CONFLICT 执行
严格 `state_key` 相等要求。本次只把这项已有领域规则补入模型可见指令，版本升为
`relations-v2`，保留跨维度 UPDATE 的同过程证据条件以及 undetermined；不改变 Schema、
候选或生成参数，不增加纠错重试。`relation:44` 的联合规则问题不在本次修改范围内。

## 修改后比较与停止原因

修改后实现 SHA 为 `f22b45e588cbcb2ee481b0a2bffef2270e264db89f3ca5a2126738099660e3b2`，
Prompt 为 `relations-v2`，Schema 保持 `relation-v1`。两组保留相同输入及候选顺序，
`after-inputs.json` 记录新增指令后的请求 hash 和离线输入估计，实际输入 tokens 以提供方为准。

| 任务 | 修改前 → 修改后 | 修改后路径 | 修改后 prompt / completion / total tokens |
| --- | --- | --- | --- |
| `relation:2` | 同维度约束失败 → 通过 | 无错误 | 1849 / 239 / 2088 |
| `relation:44` | 联合规则失败 → 同一联合规则失败 | `judgments[18]`、`judgments[19]` | 8460 / 3729 / 12189 |
| `relation:90` | 同维度约束失败 → 联合规则失败 | `judgments[19]` | 9141 / 4016 / 13157 |

修改后 `relation:2` 的候选覆盖为 1/1，标签为 undetermined 1 项、确定关系 0 项。
其他失败批次没有通过完整校验的关系集合，覆盖和标签分布仍未知。所有六次实际结束原因
均为 `stop`，不能把 `relation:90` 的 4016 输出 tokens 当作截断。

本轮共 6 次实际调用，无内部重试、无网络重发，用量全部已报告：输入 38,699、输出
15,776、合计 54,475 tokens。没有可信的当前计价，金额未计算。剩余调用为 0，
停止原因为已批准预算耗尽，没有新增探针、修改第三版 Prompt 或恢复完整关系构建。

单候选案例观察到改善，多候选批次尚未修复。联合错误仍不能细分为空白理由还是重复 ID；
后续可先通过受控测试细化安全错误代码，再另行制定真实验证计划。本轮不为这条线索
追加契约修改或调用，不宣称原始 29 项或 Issue #15 已解决。

## 验证与复核

验证结果：

- `.venv/bin/python -m pytest tests/test_relation_replay.py tests/test_model_diagnostics.py tests/test_relation_diagnostics.py -q`：46 passed。
- `.venv/bin/python -m pytest -m 'not live_model and not local_embedding' -q`：190 passed，4 deselected。
- 新模块和测试的 `compileall`、`git diff --cached --check` 通过。
- Standards、Spec 两个独立复核均无 findings；各自独立运行回放测试，12 passed。

仅出现已有的 Starlette/httpx 弃用警告。没有独立静态 typecheck 入口；
只使用已有 Python/pytest/httpx/SQLite，不增加依赖。以上均为离线或受控测试，未产生真实模型调用。

本轮最小契约修复在同一公开适配器边界验证：先运行定向文件得到 1 failed、29 passed，
失败是请求尚无明确状态键前提；新增指令后，诊断、关系语义与独立回放四个测试文件
共 74 passed。测试还验证去掉唯一新增指令后请求 hash 恢复到修复前，其他协议字段未变；
跨维度 UPDATE、undetermined 保持可用，RETAIN、SUPERSEDE、CONFLICT 仍拒绝。
最终验证：

- `.venv/bin/python -m pytest -m 'not live_model and not local_embedding' -q`：195 passed，4 deselected，198.31 秒。
- `.venv/bin/python -m compileall -q src/locomo_memory/model.py tests/test_model_diagnostics.py` 与 staged diff 格式检查通过。
- Standards、Spec 两项独立复核均无 findings；各自独立运行诊断测试文件，30 passed。
- 本地 ledger 与安全导出一致，修改后请求 hash 与离线捕获一致，当前实现身份一致，
  调用数为 6/6，提供方用量完整；未发现响应原文、Memory 文本或任意异常字符串字段。
- 原数据库 SHA 仍为 `13497e43f418275585532d7d8a3a2bb326035662ed6eef67f41a05b6e8f46116`。

只有既有 Starlette/httpx 弃用警告。四项排除的测试没有运行；本轮真实关系回放的结果
与离线回归分别记录，不把离线测试通过视为两个失败批次已修复。

本轮不修改原有未提交离线成果、不 push、不发 PR、不关闭 Issue，也不更新外部任务状态。
本次有预算的真实定位、单项最小修复与前后对照已执行；剩余失败尚未解决，完整基线未恢复。
