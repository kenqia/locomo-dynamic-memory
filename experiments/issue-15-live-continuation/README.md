# 修复后继续真实 conv-26 实验

2026-10-20，Asia/Shanghai。用户明确授权：验证通过后新建并运行完整 `conv-26`，本轮最多 1,000 次真实调用。v5 独立验证通过后启动新构建，抽取和索引完成，关系阶段因 `provider_http / model_http_error` 停止。本轮已用 313 次调用，Build 已通过无凭据的正常启动恢复为 `interrupted`，未发布、未运行 QA smoke。此前各轮的调用与结果保留，不重置历史计数。

本轮从 `7893f04` 的 integration 工作区开始。最初 91 项针对性受控回归通过。原数据库保持只读，SHA-256 为 `13497e43f418275585532d7d8a3a2bb326035662ed6eef67f41a05b6e8f46116`。原始 29 项的具体根因仍未知，下面的独立调用不回填原始失败。

## 新增真实观察

每次保持原输入候选、顺序、生成模型、温度及输出上限。独立验证 `retries=0`，每个任务每轮只调用一次。完整构建使用正常配置的 `retries=2` 并分别计数。

| 版本 | 任务 | 结果 | 安全诊断 | 结束原因 |
| --- | --- | --- | --- | --- |
| `relations-v3` | `relation:2` | 通过，覆盖 1/1 | 无 | `stop` |
| `relations-v3` | `relation:4` | 通过，覆盖 3/3 | 无 | `stop` |
| `relations-v3` | `relation:112` | 失败 | `domain_validation / factual_resolution_required / judgments[17]` | `stop` |
| `relations-v4` | `relation:2` | 通过，覆盖 1/1 | 无 | `stop` |
| `relations-v4` | `relation:4` | 通过，覆盖 3/3 | 无 | `stop` |
| `relations-v4` | `relation:112` | 失败 | `domain_validation / factual_resolution_required / judgments[17]` | `stop` |
| `relations-v5` | `relation:2` | 通过，覆盖 1/1 | 无 | `stop` |
| `relations-v5` | `relation:4` | 通过，覆盖 3/3 | 无 | `stop` |
| `relations-v5` | `relation:112` | 通过，覆盖 20/20 | 无 | `stop` |

安全逐次记录分别位于 [v3 验证](../issue-15-relation-evidence-followup/round-2/results.json)、[v4 验证](../issue-15-relation-evidence-followup/round-3/results.json) 和 [v5 验证](../issue-15-relation-evidence-followup/round-4/results.json)。三轮各 3 次，共 9 次。成功批次的标签均为 `undetermined`，不据此断言语义正确。失败路径是输出位置，不能将 `[17]` 当作第 17 个输入候选。

`relations-v4` 补充了旧 fact 与新非 fact 的标签前提。请求指导回归先失败、修改后通过，另验证 15 种标签与陈述性质组合，相关受控测试 73 passed。真实观察说明仅增加这段文字仍未消除所选失败。

`relations-v5` 将现有三个标签前提提取为 `relation_label_error()`，由领域校验与请求中的 `allowed_labels_by_old_memory` 共用。每个旧 Memory 的可用标签作为输入提示；所有候选仍保留，模型输出仍经完整校验，不替模型改标签或放宽规则。Schema JSON 和版本不变，提示版本升为 v5。26 项请求与规则一致性回归先失败、实现后通过，四个相关测试文件最终 121 passed。

v5 的三项真实复验均通过后，冻结实现 SHA-256 为 `897f17a3f62022945e855773203cffebfa28183e13cf07cf132ab714359a98c0`，在 `/home/kenqia/my_folder/locomo-worktrees/real-baseline-issue15-relations-v5` 新建完整实验。它会重新抽取 Memory，不把旧版本的抽取或关系记录改写为新版结果；因此完整构建前后不是仅关系模块变化的配对因果比较。配对输入观察以上面的三轮为准。

## 完整实验的调用边界

[运行脚本](run.py) 复用现有 `Experiment` 和公开 FastAPI 路由，在进程内通过 ASGI `TestClient` 调用应用。生成仍使用真实 `DeepSeekModel` 的正常 HTTP transport，Embedding 仍使用真实本地 MiniLM。脚本不改请求、响应或校验结果，不提供模型模拟数据。

脚本通过既有 `on_call` 观察接口在每次 provider 请求发送前提交 SQLite 额度预留，所有失败、内部重试和未知结果都计入 1,000 次上限。此前本轮独立验证的调用数作为已用额度计入 header。检查点只复制白名单诊断字段，不写入请求正文、响应正文、凭据或任意异常字符串。检查点失败和超限停止本次生成，不触发额外 provider 重试；网络、HTTP、超时或上下文拒绝会停止后续生成，等待复核。

启动前还要求最新验证的全部任务通过，且每次调用的实现、Prompt、Schema 身份与当前版本一致。新实验必须使用不存在的新目录。旧 Build、旧数据库和旧 ledger 不修改；完整实验不能将不同 Prompt 的结果原地拼接为一个构建。

预算受控自检使用临时 SQLite 和合成 MockTransport，覆盖上限、持久预留、重启、未知槽位、字段白名单和内部重试。已验证满额时发送 0 次请求；只剩 1 个额度时，即使配置允许两次内部重试，也仅发送 1 次请求。自检真实模型调用为 0。

```sh
cd /home/kenqia/my_folder/locomo-worktrees/issue15
.venv/bin/python experiments/issue-15-live-continuation/run.py --self-check
```

完整实验使用以下命令，凭据只由既有 launcher 载入子进程环境。两个离线环境标志只限制当前进程的模型权重网络获取，不修改用户设置：

```sh
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 .venv/bin/python scripts/with_deepseek_env.py -- \
  .venv/bin/python -u experiments/issue-15-live-continuation/run.py \
  --directory /home/kenqia/my_folder/locomo-worktrees/real-baseline-issue15-relations-v5 \
  --verification experiments/issue-15-relation-evidence-followup/round-2 \
                 experiments/issue-15-relation-evidence-followup/round-3 \
                 experiments/issue-15-relation-evidence-followup/round-4
```

独立复核未发现标签前提弱化或预算超额路径。启动前已修正复核发现的两项问题：每次内部重试也核对实现身份，以及保留 `completed_with_errors` 的实际 smoke 终态。完整实验的实际停止结果见下文。没有 push、PR、Issue 或 Notion 状态写入；未生成本地测试集模型成绩。

## 首次完整抽取与显式恢复

新 Build 为 `23f0459c5b3b47269dc1497cfc066810`。首次抽取 20/21 个片段成功，序号 3
在三次 provider 尝试后失败，三次结束原因均为 `stop`，安全诊断均为
`domain_validation / domain_constraint_failed`，位置依次为 `memories[5]`、`memories[4]`、
`memories[6]`。目前不能从这个通用错误 code 确定具体领域规则。

首次流程主动返回 `build_failed_explicit_resume_required`，没有改配置或直接绕过失败。
26 次 provider 调用包含 1 次小型探针、20 个成功片段，以及失败片段与成功重试中的调用。
在同一授权额度内，通过 [显式恢复脚本](resume.py) 只恢复失败抽取一次，未重复已成功片段；
该片段用 1 次调用成功，抽取达到 21/21，得到 313 条 Memory，真实 MiniLM 索引通过。
之后建立 311 个关系任务。恢复过程复用原预算库，拒绝文件丢失或计数回退，不重置额度。

该次首次流程的 manifest 保留在新实验目录的 `continuation.json`。其中早期 usage 汇总
误把嵌套对象传给 `provider_usage`，已按同一 ledger 的原始 26 条调用重新计算到
`initial-phase-summary.json`；原始调用诊断、实际预留次数与调用额度不受该汇总错误影响。
初次片段导出随后被正常快照覆盖，原失败调用及字段路径仍保留在预算 ledger，补充记录明确
区分重建的关联说明与原始调用。显式恢复过程与最终状态另存为 `explicit-phase-retry.json`。

非真实模型全套测试为 252 passed、4 deselected，耗时 196.40 秒。预算自检与缺失、回退 ledger
拒绝检查通过，没有新增真实调用。真实模型与 Embedding 的实际运行单独按本报告记录。

读取安全进度只访问 SQLite，不发模型或应用请求：

```sh
.venv/bin/python experiments/issue-15-live-continuation/status.py \
  --directory /home/kenqia/my_folder/locomo-worktrees/real-baseline-issue15-relations-v5 --compact
```

## 关系阶段停止结果

最后一次 provider 请求在 `2026-10-20T09:02:39Z` 附近返回安全分类
`provider_http / model_http_error`。运行器随即停止，未发送后续请求。它记录停止报告后正常退出，
所以进程 exit 0 不能作为实验成功证据。最后一次调用属于 `relation:241` 的第 2 次 provider
尝试；该任务第 1 次尝试为 `length`，不能将两次失败混为同一根因。

确认运行器退出后，仅使用无凭据的正常应用 startup 恢复遗留状态，并通过公开 GET 路由重新
导出快照。恢复和收集均新增 0 次模型调用。只读 watcher 已结束，没有遗留后台监控。

| 项目 | 实际结果 |
| --- | --- |
| Build | `23f0459c5b3b47269dc1497cfc066810`，`interrupted`，阶段 `relations` |
| 抽取、Memory、索引 | 21/21 个片段成功，313 条 Memory，本地 MiniLM 索引通过 |
| 关系任务 | 总计 311；225 成功、14 失败、1 中断、71 待处理 |
| 已持久化判断 | RETAIN 13、UPDATE 22、undetermined 4,085；未经独立语义核查 |
| 发布和 QA | 均未执行，`query_ready=false` |
| 真实调用 | 前置验证 9 + 新实验 304 = 313/1,000 |
| 新实验调用组成 | extract 27、relate 277，含内部重试 |
| 本轮已报告 tokens | prompt 2,679,819、completion 1,041,509、total 3,721,328 |
| 未知用量 | HTTP 错误的 1 次调用没有报告 usage；上述数值不是完整账单 |

以下统计只针对新 Build 的已持久化诊断。失败任务的每次尝试均有记录，分类仍只是校验器
当时发现的首个错误，不能证明输出中不存在其他错误。

| 错误类别 | 当前确认数量 | 对应处理方向 |
| --- | --- | --- |
| 跨状态维度关系不合法 | 本次未记录该错误；不能据此宣称全部候选语义正确 | 保留共享标签前提与完整校验 |
| JSON/schema 字段错误、非法枚举 | 本次未记录这些错误；截断输出未进入后续完整校验 | 按具体诊断检查契约，不能把截断归成 JSON 错误 |
| 输出截断 | 12 个失败任务、36 次尝试；关系阶段合计 41 次 | 检查 20 候选批次的输出长度与 4096 上限，先用固定输入验证输出策略 |
| 引用证据未逐字匹配 | 2 个失败任务、6 次尝试 | 检查证据引用的输出指导和纠错反馈，保留逐字校验 |
| 来源 ID 不合法 | 3 次关系尝试，所在任务后来成功 | 检查来源 ID 指导及失败后反馈 |
| 重复证据 | 1 次关系尝试，所在任务后来成功 | 保留唯一性约束并检查输出指导 |
| 其他抽取领域约束 | 5 次抽取尝试，所在片段后来成功；仅通用 code 可用 | 现有诊断不足以进一步确定规则 |
| provider HTTP 错误 | 1 次，所在任务中断，usage 未知 | 现有记录无 HTTP 状态码，先补充安全分型再决定恢复策略 |

12 个截断失败任务序号为 `73,91,110,111,117,122,125,131,177,178,208,232`。
每项的 3 次尝试均为 `finish_reason=length`、`completion_tokens=4096`。
证据匹配失败任务为 `148,172`，各 3 次均为 `stop`、`verbatim_support_required`，
字段路径 `judgments[19]`。路径属于输出位置，不能用来指定第 19 个输入候选。

其余 5 次截断分别出现在后来成功任务的 4 次尝试和中断任务 241 的首次尝试。
因此，41 次截断不能解释为 41 个失败任务。原始旧 Build 的 29 个失败任务仍保留其未知
根因，不把这些新观察回填到旧统计。

现有证据表明，标签前提修复让所选固定输入验证通过，但完整构建仍受到输出长度、证据引用
和 provider 请求失败影响。继续修一个关系标签接口不足以解决已观察到的全部问题。
本次没有改变上限、候选数、校验器或冻结实现后继续同一 Build，也没有绕过 `resume.py`
对 provider 错误的保护。剩余预算 687 次是上限余量，不代表已授权的实验必须耗尽额度。

## 诊断产物与复核

[安全汇总 JSON](results/final-summary.json) 包含停止状态、全轮用量、每个失败或中断任务的
新旧 Memory 描述与逐次错误。表格可分别查看 [任务](results/failed-and-interrupted-tasks.csv)、
[provider 尝试](results/provider-attempts.csv) 和 [候选 Memory](results/candidate-memories.csv)。
记录包含 `entity_id`、`state_key`、`state_dimension`、`memory_type`、`statement_type` 和
片段序号；现有模型没有单独的 `event_type` 字段，不能臆造事件子类型。

[离线收集脚本](collect.py) 以只读、immutable 模式访问已停止数据库，持有共享运行锁，
拒绝非空 WAL。它检查 311 项数据库任务与公开导出一致、277 次关系调用的 ledger 与领域
诊断一致、源文件哈希在读取期间不变。旧数据库 SHA-256 仍为本页记录的原值，冻结实现
SHA-256 仍为 `897f17a3f62022945e855773203cffebfa28183e13cf07cf132ab714359a98c0`。
产物不包含请求正文、响应正文、凭据或任意异常字符串。

```sh
.venv/bin/python experiments/issue-15-live-continuation/collect.py \
  --directory /home/kenqia/my_folder/locomo-worktrees/real-baseline-issue15-relations-v5 \
  --output experiments/issue-15-live-continuation/results
```

原始运行 manifest、预算库与重新导出的完整 Build 快照仍保留在外部实验目录。
本报告记录一次未完成的真实构建，不能据此关闭 Issue #15 或验收完整基线。
