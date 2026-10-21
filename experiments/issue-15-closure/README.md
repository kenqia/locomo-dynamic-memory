# Issue #15–#21 范围结案与独立工程验收

2026-10-21，依据用户明确决定，停止扩展原 Issue #15，课程项目转向增量质量迭代。保留历史规格、代码、Build、实验、失败记录和报告，不追加模型调用。

| Issue | 决定 | 验收边界 |
| --- | --- | --- |
| [#15](https://github.com/kenqia/locomo-dynamic-memory/issues/15) | Superseded，以 not planned 关闭 | 原定四个开发对话、757道QA、四策略3,028项全量评测未执行；不宣称原验收条件全部完成 |
| [#16](https://github.com/kenqia/locomo-dynamic-memory/issues/16) | 独立工程验收后关闭 | 固定划分、官方数据身份、离线计划与预览 |
| [#17](https://github.com/kenqia/locomo-dynamic-memory/issues/17) | 独立工程验收后关闭 | 持久进度、版本身份、显式恢复、未知结果及尝试历史 |
| [#18](https://github.com/kenqia/locomo-dynamic-memory/issues/18) | 独立工程验收后关闭 | Full Text完整交付、超限失败、来源及RAG语义 |
| [#19](https://github.com/kenqia/locomo-dynamic-memory/issues/19) | 独立工程验收后关闭 | 类别计分、失败分母、未完成状态、分组与用量 |
| [#20](https://github.com/kenqia/locomo-dynamic-memory/issues/20) | 低优先级延期，保持开放 | 原定类别首题五题四策略20项固定预检仍有形式缺口，未认定完成；不补跑 |
| [#21](https://github.com/kenqia/locomo-dynamic-memory/issues/21) | 取消本轮实验，以 not planned 关闭 | 3,028项真实全量实验未执行；小样本结果不替代全量 |

这里的独立验收表示按每张工程票的交付范围分别检查，不依赖父票全量实验。它不新增成员非作者复核、合并或课程验收已经完成的声明。原验收清单作为历史定义保留，以状态注记和结案评论说明本次结论。

## 验证证据

- #16：[计划预览验证](../issue-16-development-plan-validation.md)。
- #17：[持久化与恢复验证](../issue-17-recovery-validation.md)、[既有复核记录](../issue-15-final-review.md)。
- #18：[完整全文验证](../issue-18-full-text-validation.md)。
- #19：[计分报告验证](../issue-19-failure-report-validation.md)。
- 后续质量迭代：[修复与定向真实复验](../issue-15-query-reliability/followup.md)。该记录保留原失败结果、后续修复及小样本限制。

在 `ff037d2` 上重新运行对应工程范围的离线回归：

```sh
LOCOMO_LIVE_MODEL=0 LOCOMO_LOCAL_EMBEDDING=0 .venv/bin/python -m pytest tests/test_evaluation_plans.py tests/test_evaluation_recovery.py tests/test_full_text.py tests/test_evaluation_reports.py -q --tb=short
```

结果为18 passed，22.97秒，1条既有Starlette/httpx弃用警告。此轮不修改生产代码，不追加付费调用。此前405 passed、4 skipped的全量非live回归及浏览器验证保留，未在本轮重新执行全量。

## 保留与恢复

`issues-before.json` 保存本次更新前的Issue正文、状态及标签；`issue-*-body.md` 和 `issue-*-comment.md` 保存提交到GitHub的确切文字。原规格与ticket副本不覆盖，历史实验结果不改写。恢复原计划需另行确认范围、策略、参数和预算，不能自动接续或把旧小样本拼为全量。

GitHub更新已执行并回读确认，状态与评论链接保存于 `github-update-results.json`。#15、#21关闭原因为 `not_planned`，#16–#19为 `completed`，#20保持开放。七票均移除 `ready-for-agent`。仓库不存在 `ready-for-human` 标签，因此#20使用正文和评论明确延期，不新建标签。

Notion未同步：未找到#15–#21明确关联的任务记录，当前无可用Notion工具。由负责人补录对应状态和Issue链接；不将Notion任务标为已完成。
