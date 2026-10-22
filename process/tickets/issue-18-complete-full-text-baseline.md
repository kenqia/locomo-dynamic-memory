## Parent

https://github.com/kenqia/locomo-dynamic-memory/issues/15

## What to build

使用者选择 Full Text 后，模型在上下文允许时实际收到完整、有序的原始对话，可以核查末尾来源是否送达；其他策略继续使用既有检索预算，并能检查不同策略的实际输入及额外调用。

父规格用户故事：US18、US19、US20、US21、US22、US23、US24、US25。

## Acceptance criteria

- [ ] Full Text 送入该对话全部真实有文本的 Source Turns，保持原始顺序，不受 RAG 最终证据预算截断；孤立会话时间不制造来源。
- [ ] Full Text 保持相同生成模型、温度、输出上限、回答 Prompt 和 schema，只用真实来源引用且 memory_id 为空，不伪造 Memory。
- [ ] 完整输入超出服务上下文时明确记录失败，不静默截成前缀、摘要或分块后仍称完整全文；记录全部应有来源与实际送达来源。
- [ ] RAG 保持原候选和证据预算；Vector 仍按原问题 Dense 排名、不扩展或解析，混合消融保留扩展但不解析，动态策略保持完整链路。
- [ ] API Trace 和现有结果页面可核查来源完整性、上下文近似计数、截断或超限、provider 已报告用量；regex 计数不冒称实际账单 token。
- [ ] 当前 Vector 的额外问题分析和 BM25 开销如实记录，不能隐藏调用或为美化成本另改检索语义；不把四种策略的上下文长度说成一致。
- [ ] 公开 API 回归使用超过旧短预算、末尾含必要事实的对话，在受控 provider 边界证明完整末尾已送达，并验证超限失败、引用、RAG 预算和 QA 隔离。
- [ ] 同步基线说明和已有预算断言；本票可在现有公开评测入口验证，不依赖进度与恢复改造先完成。

## Blocked by

- None (can start immediately).
