# Issue #7 初始混合检索验证

日期：2026-10-19。范围：`process/tickets/issue-7-hybrid-retrieval.md`。继续使用已确认 FastAPI 公开 API 主测试边界，实际 SQLite、BM25、cosine 和 RRF，只控制 LLM/Embedding 外部输出。

## 实施与隔离环境

- 基础依赖增加 NumPy、rank-bm25；实际 MiniLM 使用可选 `embedding` extra，固定 sentence-transformers 6.1.0、torch 2.14.1+cpu，通过官方显式 CPU index 获取。`uv sync --extra embedding --locked --quiet` 成功；无 CUDA 依赖、无全局安装。
- 默认只读已缓存的公开模型 revision `c9745ed1d9f207416be6d2e6f8de32d1f16199bf`，不读取认证 token，不执行远程模型代码。
- 显式索引阶段与候选检查 API/UI 已接入；`indexed` 仍 `query_ready=false`。未提前发布完整版本或生成答案。

## TDD 与回归

- 首条候选检查 tracer 因索引端点不存在返回 404；实现真实索引与混合候选路径后通过。
- 发现抽取配置改变后索引仍成功 201；公开 API 红绿测试修复为 409，写入前拒绝，保留原版本配置与状态。
- 超长问题原先先调用可选问题分析再失败；红绿测试将长度拒绝前移，避免无用的模型请求。
- API 覆盖排名融合、稳定去重、各通道预算、小文本预算截断、分析失败保留原问题、推断条件不硬过滤、来源、持久化、空库、无效向量/维度/NaN/零向量、错误模型 identity、未索引/非英文输入以及索引重试不丢 Memory。

普通全套新鲜验证：`uv run --locked pytest -q --tb=short` → **39 passed，3 skipped**。跳过项为 1 项真实 DeepSeek 检查与 2 项显式本地模型检查；后两项已在下面的独立命令实际通过。仍有一个上游 Starlette/httpx 弃用提示。

## 真实本地模型检查

先在父任务提供的独立 `/tmp/locomo-model-env` 中安装应用检查所需的小型依赖，使用 `PYTHONPATH=src` 执行实际适配器检查。初始边界样例恰好 256 tokens，没有超限；修正为原文 251、实际组合 257 tokens 的样例后通过，未改变截断策略。

随后在本票自身 `.venv` 使用正式 optional-extra 路径执行：

```sh
LOCOMO_LOCAL_EMBEDDING=1 HF_HUB_OFFLINE=1 uv run --extra embedding --locked pytest tests/test_local_embedding.py -q --tb=short
```

结果 **2 passed**：实际固定 CPU MiniLM 输出有限、单位归一化 `(2,384)`；短内容可编码，但加上真实索引前缀后的 257-token 文本被拒绝；302-token 输入被拒绝；实际适配器经 SQLite 索引、真实 BM25/cosine/RRF API 返回 Paris 来源候选。仅外部生成模型响应受控，没有付费调用。

## 边界

- 本票未单独运行浏览器，累计 UI 冒烟由后续集成完成。
- 真正 DeepSeek 集成保持单独标记、默认跳过；本票没有读取真实凭据或发送模型付费请求。
- 候选文本预算的 regex 计数是明确记录的近似单位，不声称它等于模型 tokenizer 或账单 token。
- 尚无关系扩展、有效证据解析、完整版本发布或正式课程分数。没有 Notion 关联记录，未进行 Notion 或其他远端状态写入。
