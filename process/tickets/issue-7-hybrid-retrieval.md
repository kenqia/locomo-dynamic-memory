## Parent

https://github.com/kenqia/locomo-dynamic-memory/issues/4

## What to build

使用者输入英文问题，在页面看到 BM25、Dense 与 RRF 融合后的初始候选及原始证据，能检查查询分析及回退。该票交付候选检查能力，不提前宣称已完成有效证据问答。

父 spec 用户故事：US34、US35、US43、US48、US49、US50、US59。本票贯穿数据、公开 API、页面及行为测试；只替换 LLM/Embedding，未实现功能不得伪装已完成。

## Acceptance criteria

- [ ] 真实 rank_bm25、本地 all-MiniLM-L6-v2 与 NumPy 检索路径可用；Query Analysis 通过同一 Model Adapter，失败仍检索原始问题。
- [ ] 保留原问题与 Entity/Topic/Time/Keywords 分析；推断结构化条件不能直接硬过滤潜在历史证据。
- [ ] RRF 按排名融合并稳定去重，不直接相加不同量纲分数；BM25/Dense 默认各 20 条，融合初始 20 条。
- [ ] 候选数、RRF 参数、token 预算等读取配置并记录实际生效值；不能把测试中的 20 写成不可配置常量。
- [ ] Embedding 检查 revision、384 维输出与输入长度；超过默认 256 word pieces 的政策明确且测试，不静默截断。
- [ ] 候选记录构建版本、通道排名和来源；界面可核查，仅英文检索，不自动翻译中文问题。
- [ ] API 测试实际运行检索与融合，仅控制 LLM/Embedding 输出，覆盖分析失败、排序去重、预算变化、长度错误和来源；另标记真实本地模型检查。

## Blocked by

- https://github.com/kenqia/locomo-dynamic-memory/issues/6
