# Issue #4 P2 review 修复验证

2026-10-19。在 `codex/issue-4-review-fixes` 独立 worktree 修复 review 中的三项 P2，基于 `409f0b9` 开始，验证前合并 `9b57a79` 的审查记录和 PR 草稿。原始发现见 [review 记录](issue-4-review.md)。

## 修复行为

- `Settings.api_url` 拒绝 URL 用户信息和查询参数。Pydantic 文本、JSON 及结构化错误均隐藏被拒绝的 URL，避免配置快照、Trace 和导出携带这些凭据。
- 历史扩展与有效证据解析共用日期解析。页面/API 的 `requested_date` 优先于问题中的明确日期；候选有上限时，同键历史按同一日期优先补入适用区间。
- 新建版本和阶段恢复共用同一构建指纹计算，覆盖来源、配置、抽取与关系 Prompt/schema 内容及版本、投影版本。契约变化返回 `409 build_contract_changed`，在模型调用或状态改写前拒绝恢复；创建新版本会获得新指纹。相同契约继续保留成功片段/关系，旧完整版本仍可读取和查询。索引与显式投影重建也使用该检查。

## TDD 记录

已确认的测试边界为 Settings 校验与公开 FastAPI 构建、关系和问答接口。测试使用临时 SQLite、真实 HTTP 模型适配器、BM25/cosine/RRF、来源校验及投影；外部模型使用 `httpx.MockTransport`，Embedding 使用现有受控适配器。所有测试凭据和 URL 均为合成字面量。

| 命令 | RED | GREEN |
| --- | --- | --- |
| `.venv/bin/python -m pytest -q tests/test_config.py` | 3 failed：原实现接受凭据 URL | 3 passed |
| `.venv/bin/python -m pytest -q tests/test_queries.py -k capped_history` | 1 failed：请求日期扩展出 Paris + London | 1 passed：请求日期、英文日期、ISO 日期均扩展 Paris + Rome，并回答 Rome |
| `.venv/bin/python -m pytest -q tests/test_contract_recovery.py` | 14 failed, 1 passed：变化后恢复仍返回 202 | 15 passed：抽取/关系恢复 × 7 类契约变化均拒绝，旧完整版本仍可查询 |

契约变化测试还检查拒绝后无新增模型调用、版本与 Memory 未改写，以及新建版本获得不同指纹。现有测试继续覆盖相同契约恢复不重抽成功片段、不重做成功关系比较。

## 环境与范围

使用 `uv sync --frozen --group dev` 创建 worktree 自有 `.venv`，依赖取自已有 `uv.lock`，不修改全局 Python、锁文件或认证配置。同步更新运行、版本恢复与问答指南。

本轮不执行真实付费模型调用，不读取真实凭据，不进行远端写入。真实浏览器回归由主任务在合并后统一执行，本记录不宣称该项通过。本轮没有执行可选的真实本地 Embedding 检查。

## 全套新鲜验证

合并 `9b57a79` 后运行一次 `.venv/bin/python -m pytest -q`：**109 passed, 4 skipped, 1 warning，187.63 秒**。跳过项为 1 个真实 DeepSeek 检查和 3 个需要明确选择的真实本地 MiniLM 检查。唯一 warning 来自现有 Starlette TestClient 对 `httpx` 的弃用提示；本轮未增加依赖或处理该上游迁移。

`git diff --check` 通过。独立 Standards 与 Spec 复核由主任务单独记录，本记录只报告本分支执行的验证。

## 浏览器受控夹具稳定性修复

后续浏览器回归在当前问答遇到 `resolve/invalid_output`，尚未完成该轮冒烟。诊断发现 `tests/browser/server.py` 复用的受控问题分析返回空关键词；四条 Memory 的 BM25 分数均为 0，RRF 平分时按随机生成的 Memory ID 排序，可能将 Sam 的出生年份选为 Alex 居住问题唯一初始候选。受控 resolver 预设居住证据存在，因而返回无效结果。该故障属于合成夹具不确定性，不能据此判定生产检索错误，也不能把失败浏览器运行记为通过。

仅在浏览器夹具中为问题分析明确返回区分性关键词：出生年份用 `1990`，本夹具其余居住、护照及故障检查问题用 `Rome`。生产实现、`initial_k=1`、真实 BM25/Dense/RRF 和关系扩展均未修改。

公开 API 临时探针在修改前已失败：出生年份问题没有得到预期 `conflict`。修改后在 6 个全新构建上重复当前、历史、冲突、护照证据不足问题，共 24 次查询全部返回 201：12 次 `sufficient`、6 次 `conflict`、6 次 `insufficient`。12 次居住问题均初始只召回 Rome，再真实扩展为 Rome + Paris；历史回答使用 Paris，当前回答使用 Rome。探针复用 `tests/browser/smoke.py` 的合成输入、浏览器受控模型/Embedding 和公开 API，临时 SQLite 与构建 ID 每次重新生成；未访问失败运行数据库或任何凭据。

探针命令：`PYTHONPATH=src:tests:tests/browser /home/kenqia/my_folder/locomo-dynamic-memory/.venv/bin/python /tmp/locomo-browser-ranking-check.py`。使用已有解释器与当前 worktree 源码，无环境同步或新依赖。`git diff --check` 通过。本次仅改测试夹具，因此未重复运行生产全套；浏览器完整回归由主任务合并后重新执行，本段不宣称浏览器已通过。
