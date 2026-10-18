# Issue #6 原子 Memory 抽取验证

日期：2026-10-19。范围：`process/tickets/issue-6-construct-atomic-memories.md`。FastAPI 公开 API 为预先确认的主测试边界；真实 SQLite 与实际模型 HTTP 适配器协作，只有提供方 HTTP 响应被控制。

## 实施

- 复用既有 `httpx`、Pydantic、FastAPI、SQLite，无新增生产依赖；新工作树使用独立 `.venv` 与已有 uv 缓存。
- Memory 契约、DeepSeek 适配器、构建服务及 HTTP 路由分别保存；`create_app` 仍支持注入模型与 Embedding。
- `BuildVersion` 保存来源/实际配置/Prompt/schema 指纹、模型请求与返回标识、调用时间、usage、片段进度。凭据不在配置 schema 或导出字段中。
- SQLite 保证一个活动构建；每片段原子提交；失败仅保存安全分类；后端独占文件锁支撑明确的中断恢复。抽取结束是 `extracted`，不是全系统 `complete`。

## TDD 与新鲜检查

1. 首条多来源 Memory 构建测试因模型模块不存在失败；实现贯穿真实 SQLite 的生成/抽取/检查路径后通过。
2. 畸形提供方顶层 JSON 文档只尝试一次，有限重试测试失败；修复响应结构校验后按配置重试并记录全部尝试。
3. 空白 Memory 被错误标记为抽取成功；新增失败用例后补充非空陈述校验，并纳入有限重试。
4. 加入公开 API 场景覆盖：多事实共享来源、多来源事件、计划/否定/不确定性、模糊时间范围、跨对话真实来源拒绝、空/截断/无效 schema/无效 JSON/超时/HTTP 失败、显式空结果理由、单活动构建、失败片段重试保留成功 ID、重启持久化和缺凭据零调用。
5. 执行 `uv run pytest -q --tb=short`：**27 passed，1 skipped**。跳过项为 `live_model`；未设置真实调用开关，未使用真实凭据或发送付费请求。上游 Starlette/httpx 仍有一个弃用提示。

受控响应证明协议、校验、持久化与失败处理，不证明 DeepSeek 的事实原子性、关系或时间解释质量。官方协议文档已由父任务只读核查，摘要位于工作区外 `/tmp/locomo-issue4-context/research.md`。

## 未执行与边界

- 本票未单独运行浏览器；累计 UI 冒烟留给最终集成切片。Streamlit 当前通过 API 提供构建、刷新、失败重试、片段/Memory 检查及原文来源展示。
- 真实 DeepSeek 集成检查已单独标记且默认跳过；未宣称真实模型可用或达到质量要求。
- 本票不发布完整构建版本、不提供有效证据问答、不构造课程划分或动态评测分数。
- 没有已关联的 M3/M4 Notion 记录，本票未做 Notion 状态写入；远端 Issue 关闭与独立复核由集成流程处理。
