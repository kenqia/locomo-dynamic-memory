# conv-44 独立副本恢复 v2 提案

2026-11-04。本提案已获用户明确批准并执行终结：新增三次请求均因严格时间来源校验失败，未增加 Memory。当前结果见[终态报告](ISOLATED_EXTRACTION_RECOVERY_V2_RESULTS.md)。下文保留执行前准备与授权协议；其中空 ledger、授权不存在和 prepared_not_authorized 是准备时点记录，不代表当前状态。禁止重复执行，不复用旧余额。

## 诊断与范围

conv-44 原 Build `bef9f685957843698b3083ff4cbc79a4` 仍有 ordinal 18 未通过抽取，33/34 片段成功、383 条 Memory。上一次恢复的三个安全诊断均为 `domain_validation / extraction_time_expression_required`，位置分别为 `memories[7]`、`memories[8]`、`memories[6]`。规则要求 `time.original_expression` 逐字出现在所引 anchor 原文中。没有保留被拒的原始输出，不能确定是改写时间还是引用了错误 anchor。

合成复现将 source `I painted yesterday.` 与模型输出时间 `the previous day` 配对，连续三次触发同一错误；合法原文、anchor 和 retry feedback 的既有四项测试通过。没有证据支持放宽时间契约或修改生产 Prompt。本提案只提供相同 producer、相同完整 20 轮片段的另一次有限尝试；它不是已证实的模型修复，三次可能仍全部失败。

仅在新副本上执行一次现有 `BuildService.retry/run`，内部最多三次请求。范围不含 index、relation、publish、QA 或留出答案读取。原 DB、旧 ledger、历史 metadata、其他 Build 和已成功片段受摘要保护。保留原 settings、config 与 fingerprint，通过显式 `Database(target)` 路由新副本存储。

## 新预算与冻结身份

| 项目 | 值 |
| --- | --- |
| 请求 alias / 官方版本 | `deepseek-flash` / `DeepSeek-V4.1-Flash-1017` |
| 新生成 thinking | `disabled`，不发送 `reasoning_effort` |
| 物理请求硬上限 | 3，含 schema 和 transport 尝试 |
| 完整 messages UTF-8 输入硬上限 | 160,000 bytes |
| 单次输出上限 | 32,768 tokens |
| 当日峰价 input / output | USD 0.30 / 1.20 每百万 tokens |
| 新增预约硬上限 | USD 0.2619648 |
| prepared stage | `var/m5-development/conv44-isolated-recovery-v2` |
| plan SHA-256 | `ca0b07d1633a5fb178bb9cec7061fa9ae453b8428c184ae6a2754c7931cc7425` |

费用上界为 `3 × (160000 × 0.30 + 32768 × 1.20) / 1000000`。输入按 UTF-8 bytes 预约，费用与请求数均在物理请求前检查。缺失 usage 或 transport Unknown 保留完整预约，余额不授权重复运行。实际费用须以账单为准，本项目未访问账单。

[价格核查](../../experiments/m5-development/conv44-isolated-recovery-v2-pricing.json)记录 2026-11-04 官方页面的新鲜读取与原件 SHA。alias 与公告版本对应，不声称服务端不可变版本已锁定。执行前若价格变化，应停止并重新核算。

[准备摘要](../../experiments/m5-development/conv44-isolated-recovery-v2-prepared.json)绑定源码、79 个 producer 文件及工具自身、settings、原库与原 ledger 身份。`authorization-template.json` 的 `approved` 为 false，`authorization.json` 不存在。改变工具或配置后须创建新 stage，不能覆盖本计划。

## 验证与执行

已完成以下离线验证：

- 新工具合成测试 13 项通过；非作者独立重跑亦为 13 项通过，见[独立复核](ISOLATED_EXTRACTION_RECOVERY_REVIEW_V2.md)。
- 恢复、预算、Build 与 feedback 针对性回归 60 项通过，1 个既有 Starlette warning。
- 整合全仓 `./tools/integration/check.sh tests -q`：802 passed、1 skipped、4 deselected、1 个既有 warning，489.70 秒。入口排除 live_model/local_embedding，见[验证记录](../../experiments/m5-development/build-repair-verification-v1.json)。
- 实际 prepared stage 缺少授权时拒绝执行；MockTransport 请求数为 0，原库、新库和 ledger 内容保持不变，且未创建 execution marker，见[授权门验证](../../experiments/m5-development/conv44-isolated-recovery-v2-authorization-gate.json)。

仅在用户明确批准本提案后，才能根据精确 plan SHA 创建授权文件，并通过凭据 launcher 执行：

```sh
cd /home/kenqia/my_folder/locomo-worktrees/m5-final-build-repair-20261104
PYTHONPATH=src:. python3 scripts/with_deepseek_env.py -- \
  /home/kenqia/my_folder/locomo-dynamic-memory/.venv/bin/python \
  -m tools.m5.isolated_extraction_recovery \
  --output var/m5-development/conv44-isolated-recovery-v2 --execute-authorized
```

执行需要项目模块可导入的既有环境；不得带 offline guard 启动 live。授权内容必须与 `authorization(stage)` 完全相等。一次性门闩创建后，无论成功、失败或中断，均不得自动重新执行。失败保留 outcome 和完整预约，成功也仅达到 extracted。

后续 conv-44 关系构建尚未准备或授权。旧配置保留历史 relation high / resolution low；未来新生成必须 disabled，需要显式且可核查的后继 Build 契约，不能只替换模型设置而保留错误 fingerprint。本恢复不解决或隐含授权该后续阶段。

任务书第 10 节要求：“预算未明确获批时，只暂停付费子任务，继续其他开发、测试和文档，不要停止整个项目。”因此完成免费准备与复核后，仍须单独申请本次 3 请求 / USD 0.2619648。
