# 答案优化后的 conv-26 真实复验

新 Run `70f6545c0de94cdabf5507be050a26da`；前轮 `1e6e9dac610b4491b1362a151022af05`。
相同 10 道开发集原题、四策略，共 40 项；原 272 条 Memory、4902 条模型关系及索引均复用。
本轮只改变查询实现；不重新抽取或判断关系，未读取本地测试集成绩。

| 策略 | 执行成功：前 → 后 | 可回答 8 题 F1：前 → 后 | F1 变化 | 本轮两道拒答匹配 |
| --- | --- | --- | --- | --- |
| dynamic | 9/10 → 10/10 | 0.154 → 0.334 | +0.180 | 1/2 |
| dynamic_raw_fallback | 4/10 → 10/10 | 0.039 → 0.340 | +0.301 | 2/2 |
| hybrid_no_resolution | 3/10 → 10/10 | 0.020 → 0.388 | +0.368 | 1/2 |
| full_text | 8/10 → 10/10 | 0.179 → 0.376 | +0.197 | 2/2 |

已知执行失败在计划均值中记 0。F1 是原有类别词重叠评分，不能直接作为语义正确率；单次小样本不证明统计显著性。
主答案压缩、截断契约与原文修订约束同时变化，不能分别估计三项改动的独立效果。

## 主答案长度

| 策略 | 前轮平均词数 | 本轮平均词数 |
| --- | --- | --- |
| dynamic | 57.1 | 19.2 |
| dynamic_raw_fallback | 92.8 | 16.9 |
| hybrid_no_resolution | 72.0 | 19.1 |
| full_text | 82.0 | 23.3 |

只统计各轮成功产出主答案的样本。解释仍保存在 Trace 的 explanation，不参与 F1。

## QA 53 时间核对

原始会话于 2023-08-23 说 this week。正确语义为包含 8 月 23 日的一周，不能解释为此前一周。以下保留真实输出供核查：

- `dynamic`，succeeded：The week of 23 August 2023 (she said she applied "this week" as of 23 August 2023).
  解释：Caroline stated she applied to adoption agencies "this week" in a session on 23 August 2023, so the application falls in the week containing that date; the exact day is not specified.
- `dynamic_raw_fallback`，succeeded：During the week containing 23 August 2023 (she said on 23 August 2023 that she applied to adoption agencies "this week").
  解释：Caroline's own statement on 23 August 2023 says she applied to adoption agencies "this week," so the application occurred in the week containing that source date; the exact day is not stated.
- `hybrid_no_resolution`，succeeded：Caroline applied to adoption agencies "this week" as of her 23 August 2023 message, i.e., during the week containing 23 August 2023.
  解释：The source states she applied to adoption agencies 'this week' in a session dated 3:31 pm on 23 August 2023, so the application falls in that week; no exact day is given.
- `full_text`，succeeded：Caroline applied to adoption agencies this week, as of her 23 August 2023 conversation (the week containing 23 August 2023).
  解释：In the 23 August 2023 session, Caroline says she took the first step toward becoming a mom by applying to adoption agencies 'this week.' Resolving against that source date, the application occurred during the week containing 23 August 2023; the exact day is not stated.

## 来源与执行审计

构建及原库产物保持相同：`True`。本轮实际付费调用 98/200，历史累计 1009。
Full Text 完整 419 轮且 HTTP 200：10/10；通过答案校验：10/10。
初始与扩展候选的逐题比较保存在 results.json，失败原因仅依据本轮安全诊断，不假定与前轮全部同因。
跨轮候选集合核对见 comparison.json 的 cross_round_candidate_audit；不将候选变化隐去。
完整逐题答案、引用和用量见 [report.md](report.md)；结构化前后对比见 [comparison.json](comparison.json)。
UI 的策略切换与来源读取使用本地 Streamlit 交互测试验证，浏览器端到端情况另行记录。
