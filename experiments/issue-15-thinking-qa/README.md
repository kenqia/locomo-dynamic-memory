# conv-26 分阶段思考与 10 题配对实验

2026-10-20，Asia/Shanghai。用户授权在 `codex/issue-15-integration` 调整思考强度，
创建真实 `conv-26` 实验构建，并用 10 道原始开发集 QA 比较四种策略。
实验尚在执行；最终状态和结果以保存的 outcome、Run JSON 及报告为准。

## 配置与样本

抽取、查询分析及答案生成关闭思考；历史关系判断为 `high`；有效证据解析为 `low`，
包括原文兜底。共用输出上限仍为 8192，有限重试仍为 2，MiniLM 使用原本地缓存版本。
原文兜底使用默认 `expanded` 输入，四策略共享一个完整构建，未运行全关闭思考的对照。

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
最终全量回归 340 passed、4 deselected，240.66 秒；另有离线真实 MiniLM 编码和
报告失败记零分母检查通过。旧的抽取重试请求不变测试按新增反馈行为调整，并保留
查询分析请求不变的检查。完整验证范围见 [verification.json](verification.json)。

## 本地复现与记录

[运行脚本](run.py) 使用已有服务和持久预算账本，发送前预留额度，沿用历史 1,000 次总上限。
本次开始时累计 364 次。失败、重试和用量未知调用均占用额度。没有新生产依赖或凭据变更。
本地实验目录中的 `publish` 只把该库的完整 Build 标为可查询；没有远端发布。

```sh
.venv/bin/python experiments/issue-15-thinking-qa/run.py prepare \
  --directory /home/kenqia/my_folder/locomo-worktrees/real-baseline-issue15-thinking-conv26-v2

HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 OMP_NUM_THREADS=2 \
  .venv/bin/python scripts/with_deepseek_env.py -- .venv/bin/python \
  experiments/issue-15-thinking-qa/run.py execute \
  --directory /home/kenqia/my_folder/locomo-worktrees/real-baseline-issue15-thinking-conv26-v2
```

以上目录已存在时，`prepare` 和重复 `execute` 会拒绝覆盖；选择新目录进行新实验。
已知抽取或关系失败时，可显式使用 `resume`，只重试失败任务，保留原账本及成功项。
未知外部结果和达到上限的调用不自动重发。运行时持有原 Campaign 锁及独立数据库所有权锁。

完整产物位于上述目录，包含 `plan.json`、`outcome.json`、`memory-export.json`、
`evaluation-input.json` 和 `evaluation-run.json`。只有完成相应阶段才会生成对应文件。
调用记录保存实际思考开关和强度，不保存 `reasoning_content`、凭据或 HTTP 正文日志。

完成后用[只读报告脚本](report.py)导出同题得分、回答和查询开销：

```sh
.venv/bin/python experiments/issue-15-thinking-qa/report.py \
  --directory /home/kenqia/my_folder/locomo-worktrees/real-baseline-issue15-thinking-conv26-v2 \
  --output experiments/issue-15-thinking-qa/results
```

QA 分数采用既有官方类别 F1 和短语拒答规则。另列 8 道可回答题和 2 道对抗题；
保留实际回答供检查拒答短语规则的漏计。Full Text 核查全部轮次实际交付与截断状态，
全文来源覆盖不能当作检索成绩。没有独立动态真值，关系和有效证据准确率保持未评。
10 题单次配对是定向诊断，不能代表全开发集、教师隐藏评分或思考强度的独立因果效应。
