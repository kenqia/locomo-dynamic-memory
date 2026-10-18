## Parent

https://github.com/kenqia/locomo-dynamic-memory/issues/4

## What to build

使用者对选定对话提出英文当前或历史问题，得到依据有效 Memory 的答案、引用及解析说明，能够区分相关历史与最终采用证据。证据不足或冲突时明确显示不确定性。

父 spec 用户故事：US18、US19、US27、US40、US41、US42、US47、US50、US51、US58、US59。本票贯穿数据、公开 API、页面及行为测试；只替换 LLM/Embedding，未实现功能不得伪装已完成。

## Acceptance criteria

- [ ] 公开 API 串联查询分析、真实混合检索、历史扩展、有效证据解析及答案生成，页面展示完整 Trace。
- [ ] 默认现在锚定对话最后一次会话并显示截止时间；历史日期使用相应旧证据，不能固定以 Current State 代答。
- [ ] 查询补判只保存在本次 Trace，查询前后全局关系与 Current State 不变；不在线回原文补抽或修改 Memory。
- [ ] 分别展示初始、扩展和有效集合、理由、引用、截断与配置；答案引用必须来自正确对话和固定构建版本。
- [ ] 覆盖当前、历史、冲突、证据不足、计划未实现和未知关系；不能仅因记录较新就选其为真。
- [ ] API 测试用真实存储及检索、受控 LLM/Embedding；交叉提问验证全局不被改写，失败与无证据不是同一状态。
- [ ] 生成模型调用、耗时和 token 用量可记录但不泄漏凭据；保留可核查理由，不要求展示模型隐含推理。

## Blocked by

- https://github.com/kenqia/locomo-dynamic-memory/issues/8
