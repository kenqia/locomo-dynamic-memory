# 独立 Level E 最终配置

2026-11-05（Asia/Shanghai）。六份完整JSON经实际严格解析、SHA和非作者复核通过后，最终系统配置已在读取留出问题正文前锁定。原参考库只通过SQL返回唯一dataset/artifact/sample、QA array长度和连续ordinal：conv-43为242题，conv-44为158题，共400题；没有取得question、category、answer或evidence值。

锁文件为 `var/m5-development/level-e-final-lock-v1/final-system-lock.json`，公共内容副本为[最终配置锁](../../experiments/m5-development/level-e-final-system-lock-v1.json)，SHA-256 `3b6e3fbcad1670226f1f9d8e1c9fa96436b104893a875527d078dc4948671ac6`。实现commit为 `0dbd98e7b296ef29d9998fa55d88d512f8ec85f1`；82个运行及评分producer逐个核对该commit的Git blob字节，全部匹配。配置锁不等于Release、生产默认切换或付费授权。

## 候选与参数

| 项目 | 冻结选择 |
| --- | --- |
| 两臂 | `hybrid_no_resolution`、`dynamic` |
| 默认候选建议 | Hybrid；Dynamic显式可选。本轮不改生产默认。 |
| Bonus | 全关，原必做的来源/关系/版本能力保留 |
| 模型 | 请求 `deepseek-flash`，官方当时对应DeepSeek-V4.1-Flash-1017；alias不是不可变权重pin |
| 新生成 | extraction/relation/query analysis/resolution/answer均disabled，无reasoning_effort |
| 输入 | 每次640,000 UTF-8字节；完整resolve 192,000代理tokens |
| 输出及重试 | 每次最多32,768 tokens，最多2次重试；transport隐式重试0 |
| 完整Settings | 精确复用已评估input v2快照；执行时仅把db_path指向各自独立副本 |
| Build | 六份complete严格JSON冻结；两留出执行源均为无标注本地complete副本 |

选择只依据开发证据：input v2普通80题F1为Hybrid0.401172、Dynamic0.444702，配对区间跨零，Dynamic成本约10.10倍。没有据留出成绩挑选策略。历史Build的relation high等原记录如实保留，不宣称所有历史调用均disabled；本轮全部新生成禁止thinking。

## 一次性评测与费用政策

完整保留两段全部400个原始ordinal，包含类别5，不筛题。两臂共800项回答。全部计划项先生成并冻结成功、失败、Unknown和输出身份，绑定授权、marker、ledger main/WAL、成本、producer及参考源身份；满足冻结门禁后才精确读取Gold评分。中断不自动重新启动，查看留出答案后不调参并继续称独立测试。

类别1–4 token F1与类别5 literal refusal分开报告；混合总体不称事实正确率。可评分失败保留完整分母并记零，成功子集另列。Source Recall为分阶段来源代理，缺独立真值的关系/有效选择/原子事实准确率保持not_measured。配对bootstrap按这两段所选题目重采样，不支持对话级泛化。

按峰价input USD0.30/M、output USD1.20/M，每次满640,000输入字节、32,768输出tokens，所有操作和重试计入，最多 `15×400=6,000` 次物理请求，独立硬封顶 **USD1,387.9296**。这是最坏预约上界，不是预计消费或账单。旧阶段余额不转移；缺usage保留Unknown并保守保留预约。价格源见[执行前官方复核](../../experiments/m5-development/conv44-relation-successor-execution-pricing-v1.json)，付费执行前必须再次核对。

## 准备与回滚

独立复核实际锁后，才运行现有入口的questions-only准备：

```sh
env -u DEEPSEEK_API_KEY -u OPENAI_API_KEY -u CODEX_ACCESS_TOKEN \
  HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
  PYTHONPATH=tools/integration/offline_guard:src:. \
  /home/kenqia/my_folder/locomo-dynamic-memory/.venv/bin/python -m tools.m5.level_e prepare \
  --final-lock var/m5-development/level-e-final-lock-v1/final-system-lock.json \
  --output var/m5-development/level-e-preparation-v1
```

准备只在两个独立执行库写入查询/评测schema并保存400个问题，不读取类别/答案/证据或调用模型。原参考库不backup、不做全表逻辑快照；只锁main/WAL字节身份。完成后须核空ledger、无授权/marker、800项精确计划与源不变，再申请新的明确费用授权。

停止使用新锁和副本即可回滚本轮准备；原Build、历史账本、参考库和生产配置保留。任何后续变更必须记录新身份，不能覆盖本次独立评测。生成后的分臂费用、延迟、资源、token效率和来源事实/拒答审阅仍需免费补齐；本配置文件不宣称实验已完成。
