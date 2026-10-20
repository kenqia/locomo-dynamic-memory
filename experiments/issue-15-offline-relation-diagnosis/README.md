# conv-26 关系失败离线诊断

2026-10-20。原始 29 个失败任务的 87 次提供方调用均只能确认粗类别 `invalid_output`，现有持久记录无法确定其中任何一项的具体错误子类。既有独立回放确认了一个跨状态维度关系违规案例，但不能将它归入原始 29 项的根因统计。当前证据不足以断言只修改一个关系约束接口就能解决全部失败。

本次新增模型调用为 **0**。没有重放任务、启动后端、恢复构建、修改生产代码或更改模型配置。报告只读取现有数据库、任务导出、Build 信息和既有回放诊断，不读取凭据或敏感日志。

## 范围与统计口径

Build ID 为 `91f1f50938064972820e3ab7b390d9dd`。数据库共有 292 个关系任务，状态为成功 89、失败 29、中断 1、待执行 173。本报告逐项审计 29 个 `failed` 任务；中断任务 `relation:120` 的结果与未持久化用量仍未知，不计入这 29 项。

每个失败任务的逻辑执行次数 `attempts` 都为 1，该次逻辑执行内部各保存 3 次提供方调用，共 87 次。最后一次及前两次均为 `invalid_output`。这里的 87 次是原始失败调用；既有独立回放的 1 次调用单列，本次没有新增调用。

下表的“未知”表示没有足够证据判断发生数量，不能按 0 例或未发生理解。各错误子类也不能在缺少原始错误细节时互相排除。

| 错误类别 | 原始 29 项中的当前确认情况 | 对应处理 |
| --- | --- | --- |
| `invalid_output` 粗类别 | 29 个任务，87 次调用 | 只能确认输出处理或校验失败，不能确定具体层次 |
| 跨状态维度关系不合法 | 未知；既有独立回放另确认 1 例，不计入原始归因 | 对齐关系标签前置条件与纠错反馈，再验证具体规则 |
| JSON 语法、结构或 Schema 字段错误 | 未知 | 区分提供方文档解析、模型 JSON 解析与字段校验 |
| 枚举或取值非法 | 未知 | 记录稳定错误类型与字段路径，再检查枚举约束及输出指导 |
| 输出截断或不完整 | 未知；2 个任务的 3 次调用达到 4,096 tokens，仅为线索 | 保存 `finish_reason`，区分非正常结束、空输出和解析失败 |
| 其他领域约束 | 未知 | 按证据引用、端点范围、事实与计划限制、候选覆盖等具体规则分析 |

原始记录中，能够判定具体错误子类的任务为 **0/29**，仍未知为 **29/29**。87 次调用均未保存字段路径、具体校验规则、失败阶段或 `finish_reason`。无法据此判断每次是否存在 JSON 结构错误、领域约束错误或输出不完整。

## 逐项明细

以下表格中的任务序号 `N` 对应完整 ID `91f1f50938064972820e3ab7b390d9dd:relation:N`。片段与候选位置均从 0 开始。表中 `state_dimension` 是完整 `state_key` 的末段，完整值为 `conv-26:<实体>:<state_dimension>`。

所有行的历史错误依次为 `invalid_output / invalid_output / invalid_output`，最后一次仍为 `invalid_output`；字段路径和具体子类均为未知。`memory_type` 区分 `state` 与 `event`，`statement_type` 区分事实、意愿和计划。每个历史候选的两端属性与位置见候选 CSV 和 JSON。

| 任务序号 | 片段 | 实体 | `state_dimension` | `memory_type` | `statement_type` | 历史候选数 | 达上限的提供方尝试 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2 | 0 | Caroline | `emotional_response` | state | fact | 1 | 无 |
| 4 | 0 | Caroline | `sense_of_acceptance` | state | fact | 3 | 无 |
| 16 | 1 | Melanie | `self_care_belief` | state | fact | 7 | 无 |
| 17 | 1 | Melanie | `self_care_effect` | state | fact | 8 | 无 |
| 24 | 1 | Caroline | `family_goal` | state | intention | 11 | 无 |
| 25 | 1 | Caroline | `gratitude` | state | fact | 12 | 无 |
| 26 | 1 | Caroline | `emotional_state` | state | fact | 13 | 无 |
| 34 | 1 | Caroline | `school_event` | event | fact | 20 | 无 |
| 36 | 1 | Caroline | `support_experience` | state | fact | 20 | 无 |
| 38 | 2 | Caroline | `intention_to_advocate` | state | intention | 20 | 无 |
| 43 | 2 | Caroline | `relocation` | event | fact | 20 | 无 |
| 44 | 2 | Caroline | `support_after_breakup` | state | fact | 20 | 1 |
| 45 | 2 | Caroline | `romantic_breakup` | event | fact | 20 | 无 |
| 47 | 2 | Melanie | `marital_status` | state | fact | 15 | 无 |
| 60 | 3 | Caroline | `helping_goal` | state | intention | 20 | 无 |
| 61 | 3 | Caroline | `career_focus` | state | plan | 20 | 无 |
| 65 | 3 | Caroline | `passion` | state | fact | 20 | 无 |
| 69 | 3 | Caroline | `career_interest` | state | plan | 20 | 无 |
| 73 | 4 | Melanie | `interest` | state | fact | 20 | 无 |
| 82 | 4 | Caroline | `parenting_aspiration` | state | intention | 20 | 无 |
| 90 | 5 | Caroline | `conference_connections` | event | fact | 20 | 2,3 |
| 91 | 5 | Caroline | `conference_feeling` | state | fact | 20 | 无 |
| 96 | 5 | Caroline | `career_exploration` | event | fact | 20 | 无 |
| 100 | 5 | Caroline | `book_impact` | state | fact | 20 | 无 |
| 103 | 6 | Caroline | `belief` | state | fact | 20 | 无 |
| 106 | 6 | Melanie | `pet_name` | state | fact | 20 | 无 |
| 107 | 6 | Melanie | `pet_name` | state | fact | 20 | 无 |
| 108 | 6 | Melanie | `shoe_purchase` | event | fact | 20 | 无 |
| 112 | 6 | Melanie | `running_habit` | state | intention | 20 | 无 |

完整文件可按任务 ID 关联：

| 文件 | 内容 |
| --- | --- |
| [任务摘要](failed-tasks.csv) | 29 行，完整任务 ID、新 Memory 属性、片段、历史候选数、最后一次与历史错误类别 |
| [逐次尝试](provider-attempts.csv) | 87 行，每次提供方尝试、时间、最后一次标记、类别、未知字段路径、输出 tokens 和上限线索 |
| [候选 Memory](candidate-memories.csv) | 490 行，任务、输入候选位置、两端 Memory ID、实体、`state_key`、类型及片段 |
| [完整诊断](diagnosis.json) | 上述全部信息，另含每端 `source_ids`、原始轮次位置、`state_dimension`、逐类判定未知标记及独立回放 |

`history_candidate_index_zero_based` 是历史输入候选位置，不能当作原始输出的 `judgments` 位置。原始输出未保留，`original_output_judgment_index` 为未知。只有独立回放保存了它自己的 `judgments[0]` 错误位置。

## 可确认的线索及其边界

29 个失败任务共有 490 个输入候选对，其中 482 对两端的 `state_key` 不同。全部 29 个失败任务含跨维度候选；全部 89 个成功任务也含跨维度候选。因此跨维度输入本身不能判为模型输出违规，也不能用 482 对作为失败计数。

失败任务的新 Memory 包含 23 个 `state`、6 个 `event`；陈述性质为 22 个 `fact`、5 个 `intention`、2 个 `plan`；实体为 Caroline 21 个、Melanie 8 个。这些都是输入属性，不是根因分类。

87 次原始失败调用报告的输出量为 253 至 4,096 tokens。以下调用恰好达到配置上限：

| 任务 | 提供方尝试 | `completion_tokens` | 可确认范围 |
| --- | --- | --- | --- |
| `relation:44` | 1 | 4,096 | 达到上限；缺少 `finish_reason`，不能确认截断 |
| `relation:90` | 2、3 | 各 4,096 | 达到上限；缺少 `finish_reason`，不能确认截断 |

其他调用未达到上限也不能据此排除输出不完整。适配器将所有非 `stop` 结束、消息结构异常、空输出、JSON/Schema 错误及领域校验错误合并为 `invalid_output`。

## 既有独立回放

这里仅重新读取 [既有回放记录](../issue-15-relation-diagnostic-replay.json)，没有再次执行。该回放发生于 `2026-10-20T03:56:43.803844+00:00`，对象为原失败任务 `relation:2`，独立调用 1 次，原任务状态仍为 `failed`。

| 项目 | 已持久化证据 |
| --- | --- |
| 字段路径 | `judgments[0]` |
| 错误类型 | `value_error` |
| 规则 | `This judgment requires the same state dimension` |
| 旧 Memory | `fffe5349bcfeae710c3ac929`，Caroline，`conv-26:Caroline:support_group_attendance`，`event / fact`，片段 0，原始轮次位置 2 |
| 新 Memory | `0e45538fc6bcc18a98651192`，Caroline，`conv-26:Caroline:emotional_response`，`state / fact`，片段 0，原始轮次位置 4 |
| 候选位置 | 唯一历史候选，输入位置 0；该回放错误位于 `judgments[0]` |

该回放已进入领域校验，可确认这一次出现同状态维度约束违规。记录未保存实际关系标签，只能知道命中了 `RETAIN`、`SUPERSEDE`、`CONFLICT` 共用的规则，不能确定具体是哪一个。

该案例说明原失败任务的错误可以在独立回放中复现。它不能证明原始三次调用都违反同一规则，也不能证明原始任何一次一定违反该规则；原始三次仍只能判为 `invalid_output`。回放也未提供完整错误清单，不能据此排除其他问题。该案例不参与原始 29 项或 87 次的具体根因计数。

## 诊断缺口与后续判断

当前代码说明了为什么不能恢复更细的原始分类：

- [模型适配器](../../src/locomo_memory/model.py) 在第 169 行检查结束原因，第 176 行解析并校验 JSON，第 187 至 195 行统一异常类别并仅保存调用元数据。提供方 JSON、输出结构、字段及领域校验的失败细节已丢失。
- [任务执行器](../../src/locomo_memory/relations.py) 在第 129、135 行覆盖任务级调用元数据。本次所有失败任务只有一次逻辑执行，所以保留了该次的三次内部尝试；未来逻辑重试后的旧历史不能仅从任务最新元数据完整恢复。Build 总调用记录追加保存，但缺少稳定的任务与逻辑尝试关联字段。
- [关系校验器](../../src/locomo_memory/relation_schemas.py) 在第 66 至 67 行只对 `RETAIN`、`SUPERSEDE`、`CONFLICT` 强制同 `state_key`。不能由这一个回放推导出应无条件过滤所有跨维度候选。`UPDATE` 与 `undetermined` 不受该条款限制，仍需符合各自的其他约束。

现阶段可以确定诊断信息不足，尚不能确定修复范围。建议后续先补充安全的诊断持久化，再决定输出契约改进的范围：

1. 记录失败阶段、稳定错误 code/type、字段路径、`finish_reason`，以及可定位的候选端点 ID。不保存模型响应原文、输入值、任意异常字符串或凭据。
2. 明确关联 task ID、逻辑尝试和提供方尝试，保留所有尝试的诊断历史。反馈给后续尝试的纠错信息也需要可核对的安全记录。
3. 对照现有关系约束检查模型可见的前置条件、Schema 和 Prompt，再按确切违规补充纠错反馈。单个回放不足以证明需要全面重写契约，也不足以证明单点修改足够。

以上是建议，本次没有实施诊断接口或契约修复。新增记录能力也无法追溯恢复已丢失的原始 87 次错误细节。继续收集模型证据需要另行确定范围，本报告没有触发任何回放或完整构建。

## 复核方式

在 integration 工作区执行，只需 Python 标准库，不导入应用或模型模块：

```sh
cd /home/kenqia/my_folder/locomo-worktrees/issue15
.venv/bin/python -I -S scripts/diagnose_relation_failures.py \
  --directory /home/kenqia/my_folder/locomo-worktrees/real-baseline-issue15 \
  --build-id 91f1f50938064972820e3ab7b390d9dd \
  --output experiments/issue-15-offline-relation-diagnosis
```

脚本要求停止的后端和空 WAL，持有既有运行锁的共享非阻塞锁，以 SQLite `mode=ro&immutable=1` 和 `PRAGMA query_only=ON` 读取。输入读取前后的 SHA-256 一致。数据库全部 292 个任务与最新 `relation-tasks.json` 规范化后逐字段一致，87 次失败调用均可在 Build 总调用元数据找到。

| 输入 | SHA-256 |
| --- | --- |
| `memory.sqlite3` | `13497e43f418275585532d7d8a3a2bb326035662ed6eef67f41a05b6e8f46116` |
| `relation-tasks.json` | `b98124fb8f57a2d6056bb77e945f8fd7b58deef73aa1fab22402939d18c94fdb` |

其余输入路径和 hash 见 `diagnosis.json.verification.input_sha256`。机器明细中的 `null` 表示未知，不表示校验通过。脚本针对这份旧格式快照；遇到非空 WAL、多次逻辑尝试、数据库与导出不一致或更丰富的调用字段时拒绝沿用当前归因，需要重新审查。

验证覆盖脚本重跑、CSV 行数和 JSON 逐项一致性、回放证据分离、输入 hash 不变及 `git diff --check`。没有修改生产行为，未运行应用测试或真实模型 smoke。
