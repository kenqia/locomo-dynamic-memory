# Issue #5 来源导入验证

日期：2026-10-19。范围：`process/tickets/issue-5-import-source-turns.md`。测试边界沿用父 spec 已确认的 FastAPI 公开业务 API，使用临时目录中的真实 SQLite，不连接真实模型。

## 实施与依赖

- 独立 `.venv`，Python 3.12.12；依赖固定于 `uv.lock`。安装原因是仓库此前没有应用依赖或入口，范围仅为项目虚拟环境。
- Settings、Pydantic 契约、SQLite、导入业务、FastAPI、Streamlit 分文件，供后续构建/查询票复用。
- `create_app(settings=..., model=None, embedder=None)` 注入后续外部适配器；本票不调用模型或伪造 Memory。
- 未修改官方数据、许可证原件或历史交付物；不执行远端写入。

## TDD 与结果

执行 `uv run pytest -q --tb=short`。

1. 首条导入行为测试因缺少 API 模块失败；实现后发现 SQL 列数错误并修复。
2. 未知会话筛选返回 200，新增行为测试失败；修复后返回统一 404。
3. 原始文件校验测试因缺少文件导入端点返回 404；实现 multipart 导入后通过。
4. 官方数据导入测试发现 `conv-26` 有未对应文本会话的时间戳；放宽为保留 provenance 元数据，实际会话仍严格校验。
5. 最终 **11 passed**。依赖带一个 Starlette 对 httpx 测试客户端的弃用提示；不影响当前锁定版本的测试。

覆盖导入原文、说话人/会话时间、跨对话身份、重启持久化、稳定分页、重复导入、附加标注隔离、非法结构/缺字段/重复轮次的原子拒绝、统一安全错误，以及原始文件字节校验。官方数据检查确认 10 段对话、5,882 轮、上游 commit 与数据/许可证 SHA-256，并通过 API 定位 `conv-26 / D1:1` 原文。

## 验证边界

主集成工作通过独立 Playwright 实际启动浏览器验证 Streamlit → FastAPI：官方导入显示 10 段/5,882 轮，`D1:1` 定位显示 `source_id`，页面 `pageerror=[]`。截图存于工作区外 `/tmp/locomo-issue4-context/issue5-source-browser.png`，未加入仓库。本记录不宣称真实模型通过。未执行检索质量、动态标注或正式课程评测。没有课程指定六段对话与 4/2 划分，也没有独立动态标注，不构造替代分数。

Notion：本票未提供已关联 M3/M4 任务记录，本实现未做 Notion 状态写入或宣称同步。独立复核、最终合并及远端 Issue 关闭由父集成流程处理。
