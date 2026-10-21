# 答案优化后的 conv-26 真实复验

2026-10-21，Asia/Shanghai。在 `codex/issue-15-integration` 上复验三项答案与原文兜底优化，
并检查策略切换及来源展示。主实验固定为上一轮同样 10 道原题、四策略、40 项，
不依据本轮答案换题或调整参数。结果生成后见 `results/comparison.md`。

## 固定条件与历史保留

- 源实验目录：`/home/kenqia/my_folder/locomo-worktrees/real-baseline-issue15-thinking-conv26-v3`。
- 完整 Build：`5c7699dd6543407697ae232633154036`。复用 272 条 Memory、4902 条模型关系及原索引。
- 创建独立 SQLite 快照，只在新库追加查询和评测记录；不修改原库、旧 Run 或生产配置。
- 新查询使用当前实现身份，构建保留原来的生产者身份和配置，二者分开保存。
  新 Prompt、schema 不回填旧构建，也不重新声明旧抽取已接受新协议检验。
- 四策略为 `dynamic`、`dynamic_raw_fallback`、`hybrid_no_resolution`、`full_text`。
  原文证据模式继续为 `expanded`，模型和阶段强度保持前轮设置。
- 原始题目、原件 SHA、源码身份、实际配置和固定产物摘要记录在本轮 `plan.json`。
  QA gold 只用于评分，不进入任何生成输入。本地测试集未运行。

用户明确同意追加最多 200 次真实请求。续接账本将原累计 911 次作为历史，
保存旧账本 SHA256，而不是清空旧计数。新硬上限为 `911 + 200 = 1111`，
严于用户同时允许的累计 1200；失败、重试、未知调用全部占额度。
本轮持有原 Campaign 锁，旧 1000 次账本保持原样，后续若要调用须沿用本轮续接历史。
达到上限、未知调用或提供方异常必须审查，不能新建账本自动继续。

回滚本地实验只需停止该有限进程并将应用指向原库；保留快照、历史和诊断用于核对。
不涉及认证、全局配置、远端写入、新依赖或真实数据迁移。

## 执行

以下目录只准备一次，重复执行拒绝覆盖。启动前确认原件、独立库、无未知调用和剩余额度。
恢复执行必须先审查已有 outcome、Run 及账本，不直接更改身份或重发未知调用。

```sh
.venv/bin/python experiments/issue-15-answer-output-live/run.py prepare \
  --directory /home/kenqia/my_folder/locomo-worktrees/real-baseline-issue15-answer-output-conv26

HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 OMP_NUM_THREADS=2 \
  .venv/bin/python scripts/with_deepseek_env.py -- .venv/bin/python \
  experiments/issue-15-answer-output-live/run.py execute \
  --directory /home/kenqia/my_folder/locomo-worktrees/real-baseline-issue15-answer-output-conv26
```

提供方响应只在内存校验。`validation-causes.json` 只保存 schema 路径、错误类型和
源码中固定白名单原因，不保存响应正文、秘密或隐藏思考。此观察器不增加模型请求，
不替换模型结果，不修复非法引用，也不修改原有限重试。

完成后，用只读脚本生成原始得分和前后对照：

```sh
.venv/bin/python experiments/issue-15-answer-output-live/report.py \
  --directory /home/kenqia/my_folder/locomo-worktrees/real-baseline-issue15-answer-output-conv26 \
  --output experiments/issue-15-answer-output-live/results
```

固定样本及旧实验详情引用 [上一轮实验](../issue-15-thinking-qa/README.md)，
本地优化验证引用 [受控验证记录](../issue-15-answer-output/validation.md)。

## 目标判断

执行率使用所有计划项；可回答 8 题 F1 中已知执行失败记 0，同时保留成功样本分数。
两道拒答题仍用原有官方短语规则，另查真实答复和人物归属；不为提高分数改写评分器。
QA 53 对照原始 `this week` 的会话锚点做人工语义核查，不以 F1 非零认定时间正确。
Full Text 核查完整 419 轮是否送达、HTTP 200、证据截断和答案校验。
主答案词数、解释字段和原文兜底的前后证据保留分别记录。

三项优化同时变化，单次 10 题对照不能分离独立贡献，也不证明对隐藏评分集或全部时间表达的泛化。
动态关系与有效证据准确率缺少独立真值，继续未评。

UI 问答页可选择两种线上问答策略；评测页可切换同题四策略的已保存结果，按需读取引用原文。
切换与读取不调用模型，原有执行/恢复按钮仍是显式操作。`tests/test_strategy_ui.py`
用 Streamlit AppTest 验证真实控件行为，包括失败项和原文来源引用；这不等同于浏览器端到端检查。
