# 证据覆盖优化的真实实验 A/B

2026-10-21，Asia/Shanghai。实现基点 `b0a7d06`，源码身份在 `plan.json` 中冻结。
两组共 30 项，仅追加评测和查询，不重建 Memory、关系或索引，不读取本地测试集成绩。

## 事前选择

A 使用 QA 3、15、153 和 QA 0、53 两道已正确的时间问题，比较 `dynamic` 与
`dynamic_raw_fallback`，共 10 项。QA 53 保留 this week 的周范围防退化。

B 选 10 道没有出现在此前真实查询尝试或测试中的官方原题，比较 `dynamic_raw_fallback`
和上轮 F1 最好的 `hybrid_no_resolution`，共 20 项。两组策略不同，不以组间均值估计泛化差值。

| 用途 | B 的官方 QA index |
| --- | --- |
| 跨会话 | 18、55 |
| 时间 | 36、74 |
| 动态变化及状态相关活动 | 65、136 |
| 枚举 | 32、60 |
| 错误人物前提／拒答 | 178、191 |

选择只看问题、类别和标注会话结构，没有依据答案或本轮模型结果筛选。
`question-usage-audit.json` 记录已有查询、评测尝试和测试的排除核对。
类别仅用于覆盖选题；动态题没有独立动态真值，不新增动态准确率。

目前只有 conv-26 有可复用完整构建，因此 B 是同一对话内的新问题级留出，
不是跨新对话泛化。底层对话事实、关系及来源在开发中已有暴露，原件中的全部问题
也可能在计划预览时出现；“未用来调参”不等于底层事实未见或独立隐藏测试。
选题冻结后不再换题、不改写题目，也不根据输出改实现或切换证据配置。

## 预算和来源

用户本轮要求真实实验，沿用前轮已批准额度的剩余 **102 次**。
新账本串联前轮历史累计 1009 次及原账本 SHA256，保持累计上限 1111，
不增加预算、不清零历史。失败、重试、未知请求均占额度，达到上限或外部未知结果需先审查。
持有原 Campaign 独占锁；所有上一轮文件和原账本保持不变。

新目录：`/home/kenqia/my_folder/locomo-worktrees/real-baseline-issue15-evidence-coverage-ab`。
从前轮库创建 SQLite 快照，继续 pin 原完整 Build
`5c7699dd6543407697ae232633154036`，复用 272 条 Memory、4902 条模型关系和真实 MiniLM 索引。
构建生产者身份与新查询实现身份分别保留，旧 Run 不恢复或改写。

沿用 `expanded`、原阶段思考强度、模型、超时和有限重试。
QA gold 只写入独立评测输入，由既有评分器使用，不进入模型请求。
新增实验只复用现有 app、审计器和 Campaign，没有新增生产依赖或认证、生产配置修改。

## 执行与产物

准备前需保留问题使用审计文件；目录只能准备和执行一次，不自动覆盖或重发。
异常恢复先核对 outcome、Run 和账本，而非修改旧身份。

```sh
.venv/bin/python experiments/issue-15-evidence-coverage-live/run.py prepare \
  --directory /home/kenqia/my_folder/locomo-worktrees/real-baseline-issue15-evidence-coverage-ab \
  --question-audit /tmp/issue15-ab-question-usage-audit.json

HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 OMP_NUM_THREADS=2 \
  .venv/bin/python scripts/with_deepseek_env.py -- .venv/bin/python \
  experiments/issue-15-evidence-coverage-live/run.py execute \
  --directory /home/kenqia/my_folder/locomo-worktrees/real-baseline-issue15-evidence-coverage-ab

.venv/bin/python experiments/issue-15-evidence-coverage-live/report.py \
  --directory /home/kenqia/my_folder/locomo-worktrees/real-baseline-issue15-evidence-coverage-ab \
  --output experiments/issue-15-evidence-coverage-live/results
```

每组独立保存 Input 和 Run；报告分列执行率、可回答题 F1、拒答短语匹配、
实际送达的首次／联合解析来源和最终回答来源、引用与原文补查。
标注来源覆盖不等于答案完整或事实正确，尤其图片来源、枚举遗漏与人物错配需另做语义检查。
提供方响应仅在内存校验，诊断只保存固定安全原因；不保存 HTTP 正文、凭据或隐藏思考。

既有优化与受控验证见 [validation.md](../issue-15-evidence-coverage/validation.md)，
前轮真实实验见 [comparison.md](../issue-15-answer-output-live/results/comparison.md)。
