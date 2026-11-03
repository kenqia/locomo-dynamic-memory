# 事实与内容台账

冻结依据：Research committed source `f41c94b79d0d59a81a1a26ac343ac82420560898`；原 Run `a2abe1fb49be45ccba291728e1f6b3c9`。可共享数据与原聚合 SHA256 在 [research-evidence.json](research-evidence.json)。这份导出没有读取活跃数据库、模型原始请求或封存映射。独立人工语义复核状态：未评。

| 可用论断 | 数字/边界 | JSON 证据指针 |
| --- | --- | --- |
| 原始运行未完整成功 | 757 QA ×4；2,969 success /56 failed /3 unknown | `original_baseline.aggregate` |
| Dynamic 的完整分母与成功子集不同 | 709/757 技术成功；成功子集 0.550008；完整分母 0.515133 | `paired.dynamic` |
| Hybrid 完成率更高 | 753 success /3 failed /1 unknown；完整分母仅报告上下界，不把 unknown 填零 | `paired.hybrid` |
| 可比成功子集有 Dynamic 优势 | 705 对；均差 +0.026074，不能外推完整运行 | `paired.comparable`、`paired.mean_paired_delta` |
| Dynamic 查询阶段峰值价估算较贵 | 98.930522 CNY vs Hybrid 9.597679；非账户实扣，Build 成本另列 | `provider_cost_estimates`、`shared_build_cost` |
| E1 负结果 | LOCO 757 项全部选 Dynamic，未执行新的付费 Screening | `e1` |
| E5 本地收益 | cold encoding CPU -64.22%，local retrieval CPU -57.36%；provider token/CNY 节省均 0 | `e5` |
| Sidecar 是候选 | 本次尚未实现/验收，无真实 QA 改善结论 | #24 与四个子任务 |
| 离线应用可运行 | 合成适配器，四案例，无真实生成 | 本次启动与验证记录，不是基线模型结果 |

四策略完整分母、对话/类别分组以 JSON 的 `original_baseline.groups` 为准。旧 M4 不是当前 v2 报告；补充/修复 Run 不能并入原 Run。证据支持、引用语义正确性、严重错误率、隐藏测试成绩未经独立评估，保持 null/未评。

Delivery 在每页图表标 Run、分母、统计口径、源文件哈希、reviewer type。课程最终格式、时长细则和媒体授权仍待负责人核实，默认按任务包 12–15 页 PPTX、3–5 分钟 MP4 制作，不假冒课程已确认。
