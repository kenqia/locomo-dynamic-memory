# Issue #15 第二阶段：固定候选与调用计划

2026-10-20，Asia/Shanghai。当前为**离线准备完成、等待预算确认与凭据注入**。
真实调用为 **0**，修改前结果尚未取得，模型输出契约未修改。

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

## 待确认预算

建议最多 **6 次真实 provider 调用**，包括所有探针、内部重试、失败、网络重发和纠错调用。
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

当前执行进程未注入 `DEEPSEEK_API_KEY`，本轮只检查是否存在，没有读取凭据值。
实际调用还需要通过既有本地安全方式注入；不要在聊天或仓库中提供密钥。

## 验证与复核

验证结果：

- `.venv/bin/python -m pytest tests/test_relation_replay.py tests/test_model_diagnostics.py tests/test_relation_diagnostics.py -q`：46 passed。
- `.venv/bin/python -m pytest -m 'not live_model and not local_embedding' -q`：190 passed，4 deselected。
- 新模块和测试的 `compileall`、`git diff --cached --check` 通过。
- Standards、Spec 两个独立复核均无 findings；各自独立运行回放测试，12 passed。

仅出现已有的 Starlette/httpx 弃用警告。没有独立静态 typecheck 入口；
只使用已有 Python/pytest/httpx/SQLite，不增加依赖。以上均为离线或受控测试，未产生真实模型调用。

本轮不修改原有未提交离线成果、不 push、不发 PR、不关闭 Issue，也不更新外部任务状态。
完整任务 B 的真实定位、最小修复和前后对照仍待执行，当前准备结果不表示任务 B 已完成。
