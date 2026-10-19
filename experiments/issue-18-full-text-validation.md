# Full Text 完整来源与上下文检查

2026-10-20。Issue #18 的离线工程验证，使用公开 FastAPI、真实 SQLite、BM25、Dense 排序、RRF、历史扩展和版本逻辑。仅控制模型 provider 与 Embedding，不代表真实 DeepSeek 的回答质量或课程评分。

## 改动

Full Text 送入按原始位置排列的全部 Source Turns，绕过 RAG 的最终证据预算。回答模型、生成参数、Prompt 和 schema 保持共享；原始来源引用使用空 `memory_id`。RAG 继续采用既有候选和证据预算。

Trace 分别保存完整应有来源、已尝试来源和已确认请求中的来源。provider 拒绝上下文时保存明确失败，不改用前缀、摘要或分块，也不重试相同超长请求。发送后未取得响应的情况保留送达未知状态。

模型调用记录增加完整 messages 的 regex 近似计数，包含 Prompt、schema 和 payload；provider 已报告的用量保持单列。Vector Trace 披露不影响 Dense 选择的问题分析、BM25 和 RRF 开销。结果页增加来源、上下文近似计数、截断、超限和用量核查表。

## 验证

在独立 worktree 中执行，复用原工作区解释器，通过 `PYTHONPATH=src` 加载当前源码：

```sh
PYTHONPATH=src /home/kenqia/my_folder/locomo-dynamic-memory/.venv/bin/python -m pytest tests/test_full_text.py tests/test_evaluation.py tests/test_queries.py tests/test_retrieval.py -q
```

结果为 30 passed，耗时 19.85 秒。现有 Starlette/httpx 弃用警告 1 条。

新增回归首先在旧实现失败，再实现通过。完整输入用 64 个有序轮次超过原 6,000 近似预算，最后一轮包含必要事实；受控 provider 直接检查全部轮次和末尾事实已进入请求，并返回可定位的原始来源引用。测试同时检查孤立会话时间未生成来源、QA 与辅助标注隔离、Full Text 与 Vector 的生成契约一致，以及 RAG 仍受原预算限制。

超限回归让 provider 明确返回 `context_length_exceeded`，核对失败持久化、完整来源审计、无截断回退、只尝试一次，以及 provider 私有错误详情和测试凭据不进入结果。

没有执行付费模型调用。页面展示改动未单独运行浏览器 smoke check，公开 API 结果及既有调用契约已通过上述回归。真实开发集运行和课程验收另行记录。
