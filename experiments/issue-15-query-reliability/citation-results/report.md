# 查询可靠性真实复验

使用既有评测 API 的类别 F1；失败记 0，未完成不算成功。固定开发题单轮复验，不能作为统计显著性或隐藏测试成绩。
逐题语义由作者核对原文并另记结论，不增加独立 LLM 评估器。历史对照不是同时运行的随机对照。

状态 `completed`，本轮调用 5/6。

| 组 | 成功 / 计划 | 失败项 | 成功可回答题 F1 | 全部可回答题 F1（失败记0） | 同题前后比较（失败记0） |
| --- | --- | --- | --- | --- | --- |
| primary | 1/1 | 0 | 0.75 | 0.75 | 1题：0 → 0.75 |

## QA 136 · dynamic_raw_fallback

What does Melanie do to keep herself busy during her pottery break?

状态 succeeded / sufficient，F1 0.75。

Reading the book Caroline recommended and painting.

解释：Melanie says she had to take a break from pottery after an injury and has been reading the recommended book and painting to keep busy. The pottery break is context; the busy activities are reading and painting.

前轮同题：None，F1 0。
