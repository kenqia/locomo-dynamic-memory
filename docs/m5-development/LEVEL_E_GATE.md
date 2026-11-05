# Level E 准入核查

2026-11-05（Asia/Shanghai）。当前状态为 `prepared_not_authorized`：六份完整严格 JSON、最终配置锁、questions-only 实际准备已完成。Level E 尚未获独立费用授权，未执行生成，也未读取留出类别、答案或证据。本页不是付费授权或 Release 批准。

| 准入条件 | 状态 | 实际证据 |
| --- | --- | --- |
| 全 disabled 开发评估 | complete | [input v2 结果](LEVEL_C_INPUT_V2_RESULTS.md)：200 项完成并冻结后评分；普通 80 题 H/D F1 为 0.401172/0.444702，配对区间跨零，Dynamic 成本约 10.10 倍。 |
| 六份 complete Build 与严格导出 | complete | [六份清单](../../experiments/m5-development/six-build-exports-v1.json)；conv-44 为 392 Memory、7,134 关系、384/384 任务成功，[非作者实际复核](CONV44_SIXTH_EXPORT_SUCCESSOR_V1_REVIEW.md)通过。 |
| 最终候选、实现和评分政策 | locked | [最终配置](LEVEL_E_FINAL_CONFIGURATION_V1.md)及[锁独立复核](LEVEL_E_FINAL_LOCK_REVIEW_V1.md)：18 组通过、0 发现；82 个 producer 匹配真实实现 commit。 |
| 模型与新生成参数 | locked | `deepseek-flash`，全部新生成 thinking disabled；640,000 UTF-8 字节、resolve 192,000 代理 tokens、输出 32,768 tokens、retries 2、transport retries 0。历史 Build 原设置如实保留；alias 不是不可变权重 pin。执行前须再次核对官方模型映射与价格。 |
| 完整问题身份与 Gold 隔离 | prepared | conv-43 的 242 题及 conv-44 的 158 题，完整原始 ordinal；两臂 800 项。配置先提交，再 SQL 仅投影问题；不读取 category/answer/evidence。全部生成冻结后才能评分。 |
| 独立执行库与账本 | prepared | [根代理实际审计](../../experiments/m5-development/level-e-preparation-root-v1.json)：25 项通过；两份数据库与冻结严格导出相等，新 ledger 0 请求；缺授权真实入口在 marker 前拒绝，Mock 0 dispatch，所有源保持不变。 |
| 非作者实际准备复核 | complete | [独立准备审计](../../experiments/m5-development/level-e-preparation-independent-v1.json)：6 组全部通过、0 项未决发现；完整 question-only SQL 比较、旧行/rowid 保留和所有源身份核对通过。 |
| 独立费用与执行授权 | awaiting_explicit_authorization | 最多 6,000 物理请求、独立 USD 1,387.9296 硬封顶；满输入/输出/重试的保守预约上界，不是预计消费。旧余额不转移。 |

## 执行门禁

1. 完成非作者实际准备复核，将计划、配置、审计和空账本身份绑定到准备 manifest 并本地提交。
2. 依据任务书第 10 节申请本次独立金额与请求授权。缺少明确批准时，继续免费工作，不启动 Provider。
3. 获批后复核当日官方价格、alias 和冻结身份，再写匹配本计划的授权文件。单次执行；中断不自动恢复。
4. 保留全部成功、失败、Unknown 和预约。800 项全部冻结并验证身份后，才读取 Gold；可评分失败保留完整分母并记零。
5. 分开报告类别 1–4 token F1 与类别 5 literal refusal，补充来源事实/拒答审阅、分臂费用、延迟、资源和 token 效率。缺独立真值的指标写 `not_measured`。题目 bootstrap 不支持对话级泛化。

查看留出答案后，不调参并继续称同一次独立测试。停止使用新副本即可回滚准备，源 Build、参考库、历史账本和生产默认保持原状。满足本 gate 或完成 Level E 均不自动批准 main 整合、发布或部署。总任务仍需完成[最终交付清单](FINAL_DELIVERY_CHECKLIST.md)。
