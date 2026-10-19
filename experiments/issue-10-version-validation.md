# Issue #10 恢复、固定版本与导出验证

日期：2026-10-19。实现基于 `81d2ecf` 的 Issue #8 完整版本契约。使用独立 worktree `/tmp/locomo-issue10`，运行 `uv sync --frozen --group dev` 创建该 worktree 的 `.venv`，未新增生产依赖。

## 已执行

测试边界为用户已确认的 FastAPI 公开 API，使用真实 SQLite、抽取持久化、BM25/NumPy 排序、关系及投影、发布与版本选择。只控制外部 LLM 与 Embedding。LLM 使用 `httpx.MockTransport`；使用虚构测试凭据，不调用真实 DeepSeek。

- 导出切片先得到 HTTP 404 的失败，再实现完整 JSON schema/API 后通过。
- 旧编码器切片先得到 `index_fingerprint_mismatch`，再按持久化 identity 选择 encoder 后通过。查询预算仍记录当前设置，旧构建配置不变。
- 真实子进程分别在抽取第二片段、索引编码、关系第二比较边界退出。新后端启动后显示 `interrupted`；显式 `/retry-phase` 保留先前成功片段/比较 attempts，最后得到 3 条 Memory、3 条关系，无重复。
- 分别在三个阶段暂停外部调用，第二个全局构建均返回 409；旧完整版本继续候选检索与导出。
- 候选编码期间发布新版本，并发请求导出旧版本。候选的全部 Memory 与索引 fingerprint 固定旧版本，导出集合保持不变。
- 三个阶段分别返回可见失败，拒绝发布部分结果，显式重试后可发布新版本。
- 导出验证跨 session 多来源、多个 Memory 共用来源、关系/投影/index/build 一致、部分版本拒绝、旧版可下载、没有 QA 标注或测试凭据。

`tests/test_versions.py` 默认运行结果为 12 passed、1 skipped。跳过项为显式 opt-in 的真实 MiniLM 验证。出现现有 Starlette/httpx TestClient 弃用提醒，不影响断言。

## 未执行与限制

未执行真实 DeepSeek 调用或付费调用。未在此 worktree 安装 optional Embedding 依赖，未声称真实模型结果。

已提供 `LOCOMO_LOCAL_EMBEDDING=1 .venv/bin/pytest -q tests/test_versions.py -m local_embedding`，需要先有 optional Embedding 环境和缓存。该用例使用真实 `c9745ed1d9f207416be6d2e6f8de32d1f16199bf` 建立完整版本，重启到不存在的本地 `000...` revision，验证旧版本仍可查询、新版本索引明确失败。

Streamlit 已接入分阶段恢复与后端完整 JSON 下载按钮；本票没有运行浏览器冒烟，下载交互留待 Issue #12 验证。接口测试不能代替浏览器下载验证。未修改 GitHub 或 Notion，未标记远端任务完成。
