## Parent

https://github.com/kenqia/locomo-dynamic-memory/issues/4

## What to build

从中文界面导入或选择本地 LoCoMo 数据，经 FastAPI 校验并保存原始对话，再按对话、会话和轮次浏览英文来源。建立能运行的最小应用及公开 API 测试入口，后续票复用它。

父 spec 用户故事：US1、US2、US3、US4、US5、US6、US13、US43、US44、US49、US51、US59、US62。本票贯穿数据、公开 API、页面及行为测试；只替换 LLM/Embedding，未实现功能不得伪装已完成。

## Acceptance criteria

- [ ] 独立环境可启动 FastAPI 与 Streamlit；配置统一读取，界面通过后端访问数据，列表分页，错误格式一致。
- [ ] 保留官方 sample_id、会话、dia_id、说话人、会话时间和原文；轮次身份包含对话，跨对话同名人物不自动合并。
- [ ] 原始数据校验值、版本和许可证可核查；不改写下载原件，重复导入不制造无法区分的重复来源。
- [ ] QA、event_summary、observation、session_summary 与 conversation 隔离；改变附加标注不改变构建使用的原始对话视图。
- [ ] 页面可查看导入结果及定位来源；非法结构、缺失字段或重复轮次通过明确错误呈现，不泄漏凭据。
- [ ] 通过公开 API、真实 SQLite 和小型合成 LoCoMo 样例验证导入、持久化、分页、错误及隔离；真实数据只做结构与来源验证。
- [ ] 本票不伪造 Memory 构建、检索或回答能力，不需要新增预重构票。

## Blocked by

None (can start immediately).
