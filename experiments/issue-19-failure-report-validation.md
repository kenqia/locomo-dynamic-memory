# 失败分母、分组报告与尝试用量验证

2026-10-20。Issue #19 的离线工程验证，不代表真实 DeepSeek 的回答质量、课程评分或课程验收。

## 改动

保留官方 LoCoMo 类别 scorer。报告并列提供成功且可计分项 QA 均值、相对全部逻辑计划项的运行成功率，以及适用参考规则范围内将终态执行失败记零的基线运行得分。类别 5 缺普通 gold 仍适用拒答规则；其他类别缺 gold 或类别未知排除。坏 evidence 只影响来源覆盖计分。

任何计划项仍待执行、执行中、中断或结果未知时，最终基线运行得分为 null 并标记未完成。重试不增加分母，旧错误和用量保留。总体逐项汇总与分对话均值分别报告，另按策略、对话和 QA 类别提供分组和原始分母。

用量按全部已保存尝试汇总，逐 provider token 字段标明缺失、部分报告和已知合计。构建调用按唯一固定 BuildVersion 单列。历史构建未记录的 Embedding 调用数和实际运行耗时为 null，未保存的外部账单不能据此重建。页面提供分组、成本核查和完整 JSON 下载。

## 验证范围

沿用已确认的 FastAPI 公开 API、真实 SQLite、BM25/Dense/RRF、关系和版本逻辑，仅控制外部 provider 与 Embedding。每轮先观察公开行为失败，再补实现。

四个新增测试覆盖：

- 混合成功、执行失败、缺 gold、未知类别、坏 evidence 和类别 5。成功 QA 均值为 1，基线得分为 4/5；两对话得分均值另为 0.875，防止把宏平均冒充逐题汇总。
- 外部结果未知后保留待执行项，最终得分保持 null。默认恢复不重跑未知项，显式重试后只更新当前采用结果，保留未知尝试。
- 第一次失败仅报告 prompt tokens，恢复成功后保留此前已知用量，未报告 completion/total 不填零。零成功时 QA 均值为 null；重试不增加计分分母。构建调用与问题调用单列。
- 独立 QueryTrace 同样标记部分 provider 用量，读取保存 Trace 不改变结果。

运行环境曾在开发中重建，临时 worktree 的未提交内容从任务上下文恢复到持久 worktree。以下为恢复后的新鲜验证，早先环境中的测试结果不作为本记录依据。

```sh
PYTHONPATH=src /home/kenqia/my_folder/locomo-worktrees/issue15/.venv/bin/python -m pytest tests/test_evaluation_reports.py tests/test_queries.py -q
```

结果为 13 passed，耗时 27.14 秒，现有 Starlette/httpx 弃用警告 1 条。

未执行付费模型调用。页面改动未单独运行浏览器 smoke check，最终集成检查另行记录。没有新增依赖、配置、后台监控或外部写操作。
