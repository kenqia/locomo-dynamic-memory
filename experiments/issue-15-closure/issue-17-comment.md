独立工程验收后关闭，本票不再等待父规格 #15 的全量实验。

已核对持久 Run ID、逐项结果保存、执行时版本固定、读取不触发模型、显式失败/未知重试、成功项不重跑、崩溃窗口与身份变化拒绝，以及尝试历史保留。未知供应商结果不宣称未计费。

逐项证据：experiments/issue-17-recovery-validation.md；experiments/issue-15-final-review.md；tests/test_evaluation_recovery.py；docs/app/evaluation.md。

2026-10-21 对 #16–#19 独立工程范围进行新鲜联合回归：LOCOMO_LIVE_MODEL=0 LOCOMO_LOCAL_EMBEDDING=0 .venv/bin/python -m pytest tests/test_evaluation_plans.py tests/test_evaluation_recovery.py tests/test_full_text.py tests/test_evaluation_reports.py -q --tb=short。结果18 passed，22.97秒，1条既有Starlette/httpx弃用警告；无付费调用。此前全量非live回归405 passed、4 skipped及浏览器检查记录另行保留。

本次依据用户于 2026-10-21 的明确范围与关票决定执行。不追加付费模型调用；保留原始规格、代码、Build、失败记录、实验及报告。本说明不新增非作者复核通过、合并完成或课程验收完成的声明。Notion 未同步：未找到这些 Issue 的明确任务关联，当前无可用 Notion 工具，由负责人补录状态及 Issue 链接。
