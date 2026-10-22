# conv-26 分阶段思考与 10 题配对实验

2026-10-20 至 2026-10-21，Asia/Shanghai。用户授权在 `codex/issue-15-integration` 调整思考强度，
创建真实 `conv-26` 实验构建，并用 10 道原始开发集 QA 比较四种策略。
完整构建已完成，40 项 QA 全部执行，24 项成功、16 项输出校验失败，Run 状态为
`completed_with_errors`。见[得分与逐题回答](results/report.md)、[诊断与解释](results/analysis.md)
及[完整产物路径和哈希](results/artifacts.json)。

## 配置与样本

抽取、查询分析及答案生成关闭思考；历史关系判断为 `high`；有效证据解析为 `low`，
包括原文兜底。抽取与查询输出上限为 8192，关系阶段单独为 16384，有限重试仍为 2，MiniLM 使用原本地缓存版本。
本轮请求超时为 120 秒。原文兜底使用默认 `expanded` 输入，四策略共享一个完整构建，未运行全关闭思考的对照。

| 用途 | 官方 conv-26 QA index | 问题内容 |
| --- | --- | --- |
| 事实 | 3、4 | 研究对象、Caroline 身份 |
| 跨会话 | 13、15 | 职业选择、多种活动 |
| 时间 | 0、16 | 支持小组日期、陶艺课报名日期 |
| 状态进程 | 53、79 | 提交领养申请、通过领养面试 |
| 证据不足 | 153、157 | 将 Caroline 的领养及项链信息错配给 Melanie |

题目在模型回答前固定，不改写原始问题。状态题考查过程中的两个阶段，
不将它们声称为新增的当前状态或反事实题。QA 答案及证据标注仅用于评测，
构建和查询仍读取隔离的 `SourceTurn`。本地测试集未运行。

## 初次构建与必要修复

首个 Build `3d3204d2588042e2b97f03b035f4ad4e` 使用 `extract-v2-examples`，
21 个片段中 19 个通过。一次仅针对失败片段的恢复后仍有 2 个失败，累计 33 次调用。
固定类别诊断确认第 3 片段的时间锚点不在该条 Memory 的引用中；第 17 片段的
`entity_id`、`state_dimension` 不符合既有格式。返回均为 `stop`，不归因为截断。

抽取提示更新为 `extract-v3-output-constraints`，明确上述原有规则；有限重试增加
安全错误字段反馈。校验器、思考开关及输出上限保持相同。新 Prompt 使用独立目录和新 Build，
旧失败库及调用账本保留。受控回归先红后绿，修复后定向 129 项通过。
抽取修复时全量回归 340 passed、4 deselected，240.66 秒；另有离线真实 MiniLM 编码和
报告失败记零分母检查通过。旧的抽取重试请求不变测试按新增反馈行为调整，并保留
查询分析请求不变的检查。完整验证范围见 [verification.json](verification.json)。

## 本地复现与记录

`v2` Build `eca7ec7974d4492eb0a4047be6fe2906` 在 8192 共用上限下完成 21 个抽取片段、
270 条 Memory 和索引。关系阶段 52/264 个任务通过，两个任务连续三次 `length`，
无法形成完整版本。为更改上限而停止时，源码身份门禁阻止后续请求，调用账本全部已结束，
正常重启将剩余运行项标为中断。该轮使用 82 次调用，累计达到 479/1000，未执行 QA。
`v2-*` 文件保留快照；`DiagnosticPersistenceFailure` 来自有意触发的源码身份停止门禁，
不能据此归因为数据库损坏。

`v3` 新增可选 `relation_max_tokens`，仅本轮显式设为 16384，其他操作仍为 8192；
请求超时从 60 调为 120 秒。关系覆盖、来源及语义校验保持原约束，不从旧库复制 Memory 或关系。
新字段进入配置指纹，每次调用保存实际输出上限。恢复默认只需移除覆盖项并新建版本。
DeepSeek [Chat API 文档](https://api-docs.deepseek.com/api/create-chat-completion/)
允许该输出范围，2026-10-20 已重新核对；不把服务默认预算当作本次实际预算。

`v3` 在执行环境中断时保留 17 个成功片段、1 个运行片段和 3 个待处理片段，
账本累计 497/1000 次。恢复前确认旧进程不存在，取得 Campaign 和后端独占锁，
备份数据库，并通过正常启动将运行片段标为中断。序号 184 的提供方结果无法确认，
记为 `interrupted_unknown` 并继续占用额度；其 `completed_at` 表示审查关闭，
不代表收到提供方结果。审查保存在实验目录的 `interruption-review.json`。
随后只补做剩余 4 个片段，21/21 完成，共得到 272 条 Memory；没有重抽成功片段。
增加关系上限覆盖后的新鲜回归为 349 passed、4 deselected，242.59 秒。
关系完成 112/266 项后，执行进程以 143 退出，具体外部终止原因未确定。
再次备份并审查后，序号 302 记为 `interrupted_unknown`，成功任务保留，
恢复剩余任务。第二次审查保存为 `second-interruption-review.json`，累计调用仍为 615/1000。

最终 266/266 个关系任务成功，完整版本保存 4902 条模型判断。发布校验发现一条
`UPDATE` 引用了端点以外的来源，原始结果与数据库先备份、隔离，再只重试第 132 号任务，
随后正常发布及导出。见 [诊断](v3-endpoint-evidence-diagnosis.json)与
[原任务保留记录](v3-endpoint-evidence-repair.json)。全部付费调用结束后才补齐入口校验，
使其与导出已有的端点来源约束一致；受控回归先红后绿，最终全量非 live 回归
350 passed、4 deselected，238.24 秒。原实验实现身份与修复后身份分别记录，未改写原 Run。

初次创建 QA 时，脚本误用了禁止生成的 `official_structure_only`，系统拒绝请求，未发生模型调用。
脚本改用项目已有 `COURSE_SPLIT` 和 `kind=course, partition=dev`，只选本轮 10 题，
通过新增 `evaluate` 入口复用已完整构建。运行 40 项 QA 后累计 907/1000；
另一次独立答案诊断使用 4 次，最终累计 911/1000。诊断结果未替换原配对结果。

[运行脚本](run.py) 使用已有服务和持久预算账本，发送前预留额度，沿用历史 1,000 次总上限。
本次开始时累计 364 次。失败、重试和用量未知调用均占用额度。没有新生产依赖或凭据变更。
本地实验目录中的 `publish` 只把该库的完整 Build 标为可查询；没有远端发布。

```sh
.venv/bin/python experiments/issue-15-thinking-qa/run.py prepare --relation-max-tokens 16384 --model-timeout-seconds 120 \
  --directory /home/kenqia/my_folder/locomo-worktrees/real-baseline-issue15-thinking-conv26-v3

HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 OMP_NUM_THREADS=2 \
  .venv/bin/python scripts/with_deepseek_env.py -- .venv/bin/python \
  experiments/issue-15-thinking-qa/run.py execute \
  --directory /home/kenqia/my_folder/locomo-worktrees/real-baseline-issue15-thinking-conv26-v3
```

以上目录已存在时，`prepare` 和重复 `execute` 会拒绝覆盖；选择新目录进行新实验。
已知抽取或关系失败时，可显式使用 `resume`，只重试失败任务，保留原账本及成功项。
未知外部结果和达到上限的调用不自动重发。运行时持有原 Campaign 锁及独立数据库所有权锁。
`evaluate` 仅用于已完整构建、尚未创建任何 Run 且上次状态为 `experiment_stopped` 的显式恢复。
本轮完成后的目录保留为只读实验记录；后续入口校验修复改变了实现身份，不能直接恢复旧计划。

完整产物位于上述目录，包含 `plan.json`、`outcome.json`、`memory-export.json`、
`evaluation-input.json` 和 `evaluation-run.json`。只有完成相应阶段才会生成对应文件。
调用记录保存实际思考开关和强度，不保存 `reasoning_content`、凭据或 HTTP 正文日志。

完成后用[只读报告脚本](report.py)导出同题得分、回答和查询开销：

```sh
.venv/bin/python experiments/issue-15-thinking-qa/report.py \
  --directory /home/kenqia/my_folder/locomo-worktrees/real-baseline-issue15-thinking-conv26-v3 \
  --output experiments/issue-15-thinking-qa/results
```

QA 分数采用既有官方类别 F1 和短语拒答规则。另列 8 道可回答题和 2 道对抗题；
保留实际回答供检查拒答短语规则的漏计。Full Text 核查全部轮次实际交付与截断状态，
全文来源覆盖不能当作检索成绩。没有独立动态真值，关系和有效证据准确率保持未评。
10 题单次配对是定向诊断，不能代表全开发集、教师隐藏评分或思考强度的独立因果效应。
