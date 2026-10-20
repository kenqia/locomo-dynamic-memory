# Issue #15：重复证据 ID 的独立定位与最小修复

2026-10-20，Asia/Shanghai。用户在上一轮 6 次结束后明确批准**新增最多 16 次**真实调用。
上一轮记录见 [状态键前提实验](../issue-15-relation-contract-replay/README.md)，不重置或修改旧 ledger。
本轮先分配 4 次给 `round-1`，定位与修复后比较 `relation:44`、`relation:90`。
修改前后各 2 次已完成，两个修复后批次均通过完整校验。本轮用 4/16 次，剩余 12 次；
停止原因为所选案例通过，不再发请求。用量与停止状态见 [outcome.json](outcome.json)。

## 预算与固定输入

[budget-plan.json](budget-plan.json) 限定最多四个独立轮次，每轮最多 4 次，合计不超过新增
16 次。每个轮次冻结单独的输入计划及 SQLite 调用计数，使用既有回放工具的硬上限，
发送前提交预算槽位。后续轮次只在新证据支持时准备；不使用其他目录绕过预算，不重置旧库，
不用满额度为目的追加调用。执行期间还持有 campaign 锁，核对所有轮次计数之和。

原 Build `91f1f50938064972820e3ab7b390d9dd` 与原数据库 hash 保持不变：
`13497e43f418275585532d7d8a3a2bb326035662ed6eef67f41a05b6e8f46116`。
`relation:44` 和 `relation:90` 均保留完整 20 个候选及原输入顺序。各次请求仍为
`deepseek-flash`、temperature 0、thinking disabled、`json_object`、max_tokens 4096、
timeout 60 秒、retries 0。每轮四次请求的输出上限合计 16,384 tokens。
若全部四轮均按该上限执行，输出上限为 65,536 tokens；后续若改变输出上限须更新计划。
当前没有可信金额估计，次数上限不代表金额上限。

`round-1/plan.json` 记录完整任务、候选 ID、请求 hash、输入估计与实现身份；
`round-1/after-inputs.json` 记录修复后的请求身份。输入估计不是提供方 token 计数。
传输失败、中断未知结果、HTTP/超时/上下文拒绝时停止，未知槽位继续占用额度；
不自动重发或增加纠错调用。全部候选通过时结束，不为了剩余预算继续改契约。

凭据只在进程内使用既有受保护文件，不输出或持久化，不修改凭据或应用配置。
SQLite ledger 和运行锁保留在本地并忽略提交，安全结果导出为 JSON。

## 先细化诊断，再定位

上一轮的 `reason_and_unique_evidence_required` 同时代表空白理由或重复证据 ID，
无法据此确定修复方向。本轮把已有两个校验谓词分别报告为：

- `nonblank_reason_required`：理由为空白。
- `unique_evidence_required`：证据 ID 列表有重复。

保留旧联合代码的诊断白名单和旧记录，不回填历史结果。接受或拒绝的关系集合不变，
JSON Schema 与模型请求均不变；修改前两个请求 hash 与上一轮修复后逐项一致。
受控测试先得到 2 failed、29 passed，细分后诊断和持久化测试 40 passed。
补充的两项持久化测试验证新代码经公开 API 读取、重启后仍完整保留。

## 本轮修改前真实证据

实验 ID `62c3c90019884561b9268701386a4a25`，完整安全记录见 [before.json](round-1/before.json)。

| 任务 | 错误代码与路径 | 实际结束原因 | prompt / completion / total tokens |
| --- | --- | --- | --- |
| `relation:44` | `unique_evidence_required`，`judgments[18]` 和 `[19]` | `stop` | 8460 / 3741 / 12201 |
| `relation:90` | `unique_evidence_required`，`judgments[19]` | `stop` | 9141 / 3652 / 12793 |

两次均为 `invalid_output` / `domain_validation`。本轮取得的错误可归因为重复证据 ID，
不将它回填上一轮联合错误或原始 87 次失败。不保留模型响应原文，也不根据索引假定
对应哪一候选。失败批次的有效候选覆盖与标签分布未知。

## 最小修复与受控回归

只为 Prompt 增加 `source_ids` 去重列表指令：两端引用同一来源时，若其支持两端，
该 ID 列一次，并继续覆盖双方证据。Prompt 升为 `relations-v3`；其余指导、Schema、
候选、输出上限和重试次数保持不变。不在解析后替模型去重，不放宽证据约束。

请求测试先得到 1 failed、34 passed，失败原因为缺少新增指导。新增测试还验证单个共享
来源可支持 UPDATE 或 undetermined 的两端，而重复 ID 仍被严格拒绝；原有跨维度标签
前提继续保留。修复后诊断、持久化、关系语义与回放四个文件共 81 passed。

## 修复后比较与限制

完整前后有序调用见 [comparison.json](round-1/comparison.json)。修复后实现为
`b6d38a90328a403651da8582a078d1015f9a2ead7ac4db42adaa56d9416bfcd0`，
Prompt 为 `relations-v3`、Schema 仍为 `relation-v1`。两组只在新增证据唯一性指令上有
请求差异；JSON Schema、payload、候选顺序、输出上限和重试次数均相同。

| 任务 | 修改前 → 修改后 | 修改后候选覆盖 | 修改后标签 | prompt / completion / total tokens |
| --- | --- | --- | --- | --- |
| `relation:44` | 重复证据 ID 失败 → 通过 | 20/20 | undetermined 20 项，确定关系 0 项 | 8512 / 3635 / 12147 |
| `relation:90` | 重复证据 ID 失败 → 通过 | 20/20 | undetermined 20 项，确定关系 0 项 | 9193 / 3734 / 12927 |

四次实际 `finish_reason` 均为 `stop`，本轮没有截断证据。实际输入 tokens 分别增加 52，
离线输入估计和请求 hash 见 `after-inputs.json`，不把估计当成实际提供方计数。
本轮 4 次调用输入 35,306、输出 14,762、合计 50,068 tokens，用量全部已报告，内部重试 0。
与上一轮分开计数；两轮共 10 次，不把更早的独立回放纳入本次授权统计。

修改前两个批次的标签分布未知，不能声称与修改后比例相同，也不能算作确定关系变少。
两个成功批次均为关系未确定，没有独立语义标签支持其正确性，不能仅凭可解析和领域校验
通过宣称语义改善。本次没有后处理强制改标签、过滤候选或放宽验证。单次对照与 temperature 0
不足以证明确定性、显著降低错误率或原始 29 项全部解决。`relation:2` 本轮未重新调用，
其上轮 `relations-v2` 的结果保留为原版本观察，不能宣称已验证本轮新 Prompt 下的结果。

## 最终验证

- `.venv/bin/python -m pytest -m 'not live_model and not local_embedding' -q`：202 passed，4 deselected，207.12 秒。
- `.venv/bin/python -m compileall -q src/locomo_memory/diagnostics.py src/locomo_memory/relation_schemas.py src/locomo_memory/model.py tests/test_model_diagnostics.py tests/test_relation_diagnostics.py` 和 staged diff 格式检查通过。
- Standards、Spec 两项独立复核均无 findings；分别独立验证诊断与持久化测试 46 passed、诊断测试 35 passed。
- ledger 与安全导出一致，修改后实际请求 hash 与离线捕获一致，实现身份匹配，
  提供方用量完整。安全字段检查未发现响应原文、Memory 文本或任意异常字符串字段。
- 原数据库 hash 仍为上述固定 SHA。只有既有 Starlette/httpx 弃用警告，
  没有独立静态 typecheck 入口；四项排除的测试没有运行。

原数据库、旧 Build、上一轮结果均保留；没有恢复完整关系构建，没有 push、PR、
关闭 Issue 或外部任务状态更新。
