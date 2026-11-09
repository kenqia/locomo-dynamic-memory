# 真实模型时间与实体边界回归

2026-11-09。**本轮没有测到整体收益。** 12 道已曝光、预选时间题在固定检索后的配对回归中，10 道普通题 F1 从 **0.517381 降至 0.456314**；配对差 −0.061067，探索性 bootstrap 95% 区间 [−0.313876, +0.233333]。这个小样本不能证明总体提升或退化，更不能替代 E25 留出评测。原 E0–E25 分数及冻结身份不变。

本轮落实了上一轮免费[证据损失诊断](../evidence-flow-20261109/README.md)之后获授权的真实模型回归，保留执行失败、负面结果、AI 漏检与用户提交的有条件核查意见。没有全局放宽 Dynamic 筛选、增加默认 K 或启用实体别名合并。

## 方法和身份

[预先固定协议](PROTOCOL.md)规定最多 64 次实际请求、保守预约 USD15、重试为零。12 题两臂使用同一冻结 initial/expanded/relations/sources，分别执行真实 `QueryService.query` 的解析与回答；不重跑 Query Analysis 或 Dense。基线源码 `d3c4ae10fb73d70eabea42f5333e721168574190`，候选源码 `b3c9d0f4f4929de55df714523fff2edcd28f6548`，通过 Git archive 与隔离进程加载。模型均为 `deepseek-flash`、temperature 0、thinking disabled、输出上限 32768；这是服务别名，不能保证固定底层权重。

另有 conv-42 六组单目标轮次 vs 同会话 ±1 轮抽取探针。它没有评估默认 `fragment_turns=20` 全 Build，没有修改历史 Memory。四批 X/Y 身份盲化 AI 审阅只读给定来源，不读 QA Gold；生成和审阅全部终态冻结后才读 Gold 评分。

实际付费运行器是 **`3be7910`**；**`911ed2c` 仅离线修复后续审阅校验，未重跑、未重新认定失败审阅为成功**。[plan](plan.json)、[生成冻结](generation-freeze.json)、[审阅冻结](review-freeze.json)与[来源身份](provenance.json)分别保存身份与 SHA。

## 问答结果

| 指标 | 基线 | 候选 |
|---|---:|---:|
| 成功项 / 全部 12 题 | 11/12 | 11/12 |
| 普通题 F1，失败计零，10 题 | 0.517381 | 0.456314 |
| 普通题 EM，失败计零，10 题 | 0.100000 | 0.200000 |
| 共同成功普通题 F1，8 题 | 0.563393 | 0.445393 |
| 类别 5 字面拒答 | 2/2 | 2/2 |
| 送达 Source Turn Recall，12 题失败计零 | 0.750000 | 0.750000 |
| 成功 Query 耗时中位数，11 项，秒 | 8.739 | 10.071 |

送达 Recall 为标注来源覆盖代理，不是事实正确率；上述样本含两道无来源类别 5 题。耗时包括固定检索回放下的解析与回答，不含完整线上检索。全部逐题答案、引用、解释、耗时、失败及 Gold 在 [results.json](results.json)，完整已验证 Trace 在 [outputs.json](outputs.json)。

普通题改善 2、退化 3、持平 5。conv-44:qa:8 的改善来自基线 `invalid_output`；conv-43:qa:95 的退化来自候选 `model_http_error`（HTTP 状态为空、usage 未知）。失败没有补跑。其余分差不宜直接解释为事实变化：

- conv-44:qa:22 候选拒绝将原文 “are going camping” 断言成已经去过，F1 降 0.75；所给原文支持谨慎区分计划与完成。
- conv-44:qa:115 候选更长，短答 F1 降约 0.209；两臂解释却都把 Saturday **after** October 28, 2023 定位到 October 28 当天，严格之后应为 November 4。Gold 只有 “Go hiking”，测不出这个日期错误，AI 审阅也漏检。
- conv-44:qa:81 两臂把 Monday **before** July 24, 2023 解释为 July 24，当天本身周一，严格之前应为 July 17。原文 July 27 的 “on Monday” 又偏向 July 24，用户核查已指出该问题，题目/参考时间的不一致仍待裁定。
- conv-43:qa:24 的 “I was in Chicago” 是 August 11 报告的过去事件，不能据此确认 August 11 当天位置；候选仍有过度精确。

[作者 AI 逐案分析](author-audit.json)与模型审阅分开保存，不替换冻结标签。

## 实体和语义引用

六个新抽取对照没有重现 “Joanna owns turtles”。原文支持 Nate 饲养乌龟，Joanna 喜爱或希望饲养；这不证明历史错误已修复或总体实体准确率提高。[实体原文审计](entity-source-audit.json)保留逐字依据，不按 Jo/she/Joanna 的词形猜测身份归并。

e02/e05 基线空抽取，候选找回 Joanna 对 Nate 乌龟的态度/知识陈述；但候选都仅引用目标轮的 “your turtles”，没有引用识别 Nate 所需的相邻语境。**窗口联合证据支持，不等于实际单条 Memory 的引用充分。** 上下文选项保持默认关闭，不能据两条恢复推荐全量重建。

AI 审阅只有 2/4 批成功，覆盖 **9/18 对**（6 问答、3 抽取）；另外两批 `invalid_output` 原样保留。冻结 AI 包只隐藏臂标签，仍含可能提示变体身份的查询时间结构，不能保证身份盲化充分；人工可读版已去除此控制元数据。成功批原始支持计数为基线 supported 6 / unsupported 2 / not_executed 1，候选 supported 9；缺失一半且存在日期漏检，不能据此声称语义收益。旧审阅 schema 即使没有来源也要求引文，存在可复现门禁缺陷；`911ed2c` 已修复未来调用。没有读取无效原始响应来断言这就是两批失败的唯一原因。

已收到复核人**莫远序**于 **2026-11-09** 提交的全部 **18/18 对**文字核查，见[核查原文](human-review-submitted.txt)、[转录表](human-review.csv)和[待裁定说明](HUMAN_REVIEW_FOLLOWUP.md)。条件判断与不同意见保留，不将提交等同于全部通过或统一真值。提交过程独立性未另行核验；原 results/AI/provenance 的 pending_user 是生成时快照，当前状态及文件SHA见[核查增量身份](human-review-provenance.json)。

## 调用与费用

实际 **62 次请求**，其中两次解析失败跳过 Answer，未用剩余两次补跑。保守预约 **USD3.5863482**；已报告 prompt/completion tokens 为 1,150,920 / 51,849，对应峰价 cache-miss 上界 **USD0.4074948**。另 **1 次 usage 未知**，仍保留其完整预约；未访问账单，不能把已知用量估算称为总消费。generation 与 AI review 都计入，价格日期和官方链接见 [pricing.json](pricing.json)。

## 复现与验证

运行器入口为 `python -m tools.m5.live_boundary {prepare,execute,review,score}`。本次受保护运行目录 `var/live-boundary-20261109-v1` 不提交，包含独立预算账本；已冻结运行拒绝隐式恢复或覆盖。复查旧计划需使用实际运行器 `3be7910` 的隔离副本，当前代码哈希不同，不能改写旧计划后继续。

再次执行 execute/review 会产生新模型费用，需另行授权与独立新目录；本轮不再调用模型。公开记录不包含凭据、预算数据库、原始 HTTP 响应或敏感日志。代码审查、离线测试、工件核验和 PDF 身份见 [validation.md](validation.md) 与 [provenance.json](provenance.json)。
