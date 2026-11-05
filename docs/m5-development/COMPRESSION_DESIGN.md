# 可逆 Memory 分组与可选请求压缩

m5_compression.pack 按 Build、对话、人物和状态维度共享重复字段；原子成员保留独立 ID、内容、性质、否定、时间、session_times 和 source_ids。order 保存原顺序，SHA-256 检查完整展开字段。不删除、覆盖或摘要化原 Memory。

文件包用于可逆导出，包体 token 减少不等于 Provider 节省。expand 校验成员全集、无重复、共享字段不可覆盖、单 Build/对话身份及展开 SHA。当前协议只处理现有 Memory schema。

m5_wire_compression 在生产证据预算和作用域验证后，对实际 wire Memory 的 entity_id/state_dimension/state_key 分组。其他字段和 Source Turn 原文不变。解码指导加入系统消息；完整 messages 的原始与候选正则 token 都计量。候选请求没有变小时原样发送，记录 decoder_overhead_exceeds_savings。

m5_queries.query(..., compression=True) 显式调用适配器。输出仍由原 EffectiveResolution/EvidenceAnswer 与完整未压缩对象作 context 校验。原解析预算基于未压缩完整请求，不借压缩绕开来源预算。请求和重试继续走原 DeepSeek adapter，Trace 增加 m5_compression 审计。

Roundtrip 100% 只证明字段保留，不证明原抽取事实完整、模型正确解码或回答非劣。缺少真实答案和独立语义审阅时，Atomic Fact Retention、人物/事件/时间正确率、QA F1、实际账单节省均为 not_measured。不执行 LLM 摘要压缩。
