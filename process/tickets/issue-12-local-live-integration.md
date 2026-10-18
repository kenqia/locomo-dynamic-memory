## Parent

https://github.com/kenqia/locomo-dynamic-memory/issues/4

## What to build

项目成员从独立环境启动本地前后端，在明确的小型合成案例上跑通导入、构建、问答、证据、导出与评测页面，区分已通过的自动化测试和实际模型/浏览器验证。

父 spec 用户故事：US43、US44、US45、US48、US51、US60、US62。本票贯穿数据、公开 API、页面及行为测试；只替换 LLM/Embedding，未实现功能不得伪装已完成。

## Acceptance criteria

- [ ] 首次安装与两进程启动命令可实际执行，依赖版本与模型 revision 可核查，已有成熟入口优先复用；记录可复现步骤。
- [ ] 受保护地配置 DeepSeek 凭据，不在聊天、仓库、Trace、输出或日志读取/展示秘密值；没有可用凭据则真实调用明确标为未执行并报告外部前提。
- [ ] 单独验证真实 DeepSeek 适配和本地 Embedding 的加载、编码、结构化输出及长度处理，不把受控适配器通过当作模型质量通过。
- [ ] 浏览器通过 Streamlit→FastAPI 跑通当前、历史、冲突、证据不足、来源跳转、Trace、进度/失败、版本、JSON 下载与评测展示。
- [ ] 复核版本隔离、有限失败处理、配置生效与原文不变，最终验收提供实际命令、通过/失败/跳过/未执行以及风险。
- [ ] 不擅自运行正式测试集调参，不发布/部署/推送代码或关闭父 spec；非作者复核与合并验证完成前不标记项目整体完成。
- [ ] 不以本票取代之前每张票的行为测试，本票关注新环境启动和真实服务/浏览器集成。

## Blocked by

- https://github.com/kenqia/locomo-dynamic-memory/issues/10
- https://github.com/kenqia/locomo-dynamic-memory/issues/11
