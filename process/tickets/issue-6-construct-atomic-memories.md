## Parent

https://github.com/kenqia/locomo-dynamic-memory/issues/4

## What to build

使用者在页面选择已导入对话并发起记忆构建，能看到进度、抽取的原子 Memory 与一条或多条原始证据。使用真正的 DeepSeek 适配路径，自动化测试仅替换模型调用。

父 spec 用户故事：US7、US8、US9、US10、US11、US12、US16、US17、US28、US29、US30、US33、US45、US46、US47、US49、US50、US51、US59。本票贯穿数据、公开 API、页面及行为测试；只替换 LLM/Embedding，未实现功能不得伪装已完成。

## Acceptance criteria

- [ ] 统一 Memory 与 BuildVersion 最小 schema，保存构建身份、片段进度、成功结果、失败状态；本阶段结果标明是可检查产物，不冒充全系统已完整。
- [ ] 每条 Memory 为独立陈述，多来源与一轮多事实均可表达；Event/State、事实/计划或意愿/不确定陈述、否定信息均保留。
- [ ] state_key 使用对话、实体与状态维度，公司等具体值分开保存；同键不自动认为事实互斥。
- [ ] 会话时间、原始时间表达、推导事件时间或范围及依据分开；未知不伪精确化，计划不当成既成事实。
- [ ] DeepSeek 官方 Chat Completions 使用 spec 指定模型、显式关闭思考、JSON 输出加 Pydantic 校验；有限超时及重试集中配置。
- [ ] 拒绝模型编造的来源、错误对话引用、无效 schema；空内容、截断或重试耗尽显示失败，不当成有效空记忆。最多一个构建任务同时执行。
- [ ] 页面经 API 显示 Memory、来源及失败；配置快照记录模型、Prompt/schema 与数据指纹，排除凭据。
- [ ] API 行为测试使用真实持久化及受控 LLM，覆盖多事实、多来源、计划、否定、模糊时间和失败；真实调用单独标记，凭据不在正文或日志出现。

## Blocked by

- https://github.com/kenqia/locomo-dynamic-memory/issues/5
