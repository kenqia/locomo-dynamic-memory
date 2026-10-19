# 检查初始混合检索候选

你可以为已抽取的 Memory 建立本地索引，输入英文问题，并检查 BM25、Dense 和 RRF 融合后的初始候选及来源。[关系与历史扩展](relations.md) 已作为独立阶段接入。候选检查不解析有效证据，也不生成最终答案；`indexed` 版本的 `query_ready` 仍为 `false`。

## 安装与启动

先按 [构建指南](building.md) 导入并抽取对话。普通来源管理和受控测试无需安装模型依赖。实际 Dense 编码需要可选的 CPU 环境：

```sh
uv sync --locked --extra embedding
uv run --locked --extra embedding uvicorn locomo_memory.api:create_app --factory --host 127.0.0.1 --port 8000
```

Streamlit 的启动命令保持不变。后端及真实模型检查命令保留 `--extra embedding`，使首次创建环境和后续运行都包含所需模型依赖。

基础依赖新增 NumPy 和 `rank-bm25==0.2.2`。可选 extra 固定 `sentence-transformers==6.1.0` 和 `torch==2.14.1+cpu`；torch 使用显式的官方 CPU wheel 索引，不安装 CUDA 依赖。安装范围为项目 `.venv`，不修改全局 Python。

模型固定为 `sentence-transformers/all-MiniLM-L6-v2`，revision 为 `c9745ed1d9f207416be6d2e6f8de32d1f16199bf`。默认 `embedding_local_files_only=true`，只读取本地公开模型缓存。若未缓存，API 返回 `embedding_model_unavailable`，不会用伪向量替代。

需要首次下载时，可在项目环境中显式运行下面的公开模型预加载命令。它下载指定 revision 的权重与 tokenizer，不使用认证，也不执行远程模型代码：

```sh
uv run --locked --extra embedding python -c 'from sentence_transformers import SentenceTransformer; SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2", revision="c9745ed1d9f207416be6d2e6f8de32d1f16199bf", device="cpu", local_files_only=False, trust_remote_code=False, token=False)'
```

模型是惰性加载的，启动后端或导入来源不会加载权重。只有显式建立索引或检索时才需要编码器。

## 从页面检查

1. 选择已抽取的构建版本。
2. 点击 **建立或重试混合检索索引**。索引过程占用单活动构建名额；成功后状态为 `indexed`，失败为 `index_failed`，已抽取的 Memory 保留。
3. 展开 **索引版本、模型与长度政策**，核查 revision、384 维输出、CPU、归一化和拒绝超长策略。
4. 在 **英文问题（候选检查）** 输入问题，点击 **检查 BM25 / Dense / RRF 候选**。
5. 查看原问题、分析结果或失败回退、每个通道的原始分数与排名，以及 RRF 融合结果。展开候选来源核查英文原文。

页面拒绝中文等不支持的文字脚本，不自动翻译。当前脚本检查不能识别所有使用拉丁字母的非英语表达；使用者仍需提供英文问题。

## 检索与版本契约

建立索引要求当前完整配置与抽取版本保存的配置相同；不一致返回 `build_configuration_changed`，需要创建新构建。索引指纹包含构建指纹、模型 identity、实际索引文本与文本 schema 版本。向量及文本保存在 SQLite，查询在同一读取快照中固定索引身份和索引条目。

索引文本为实体、状态维度、独立状态值与 Memory 英文内容的组合。MiniLM 对**实际组合文本**及原问题检查 tokenizer 长度，包含 special tokens，最大不超过模型的 256 word pieces。超长返回 `embedding_input_too_long`，不会静默截断；超长问题在可选模型分析请求之前被拒绝。输出必须是有限、非零的 384 维向量，并一致归一化后用 NumPy 点积计算余弦相似度。

BM25 使用真实 `rank_bm25.BM25Okapi`，对原问题与文档采用相同的英文小写正则分词，不做词干化。问题分析通过同一个 DeepSeek 适配器提取 entity/topic/time/keywords；关键词可扩展 BM25 查询，但原问题始终保留并作为 Dense 输入。分析失败时记录安全错误与有限调用记录，仍检索原问题。推断的实体、主题和时间不作为硬过滤条件。

默认 BM25 和 Dense 各取前 20 条，RRF 融合后取初始前 20 条。融合使用 `sum(1/(rrf_constant+rank))`，不把 BM25 分数与 cosine 分数相加。按 RRF 分数降序、Memory ID 升序稳定排序并去重；原始通道分数只用于各自通道排序。空库和单 Memory 库不伪造候选。

`bm25_k`、`dense_k`、`initial_k`、`rrf_constant`、`candidate_token_budget` 全部读取 Settings。查询时改变检索预算允许复用同一索引，实际配置保存进该次结果；改变模型 identity 则拒绝旧索引。候选预算采用明确记录的 `regex-word-punctuation-v1` 计数单位，它是可复核的文本预算近似，**不是** MiniLM word-piece 数或 DeepSeek 实际账单 token。按融合顺序遇到超预算项即停止；初始数量或文本预算截断均显式记录，不宣称证据完整。

## API 参考

| 方法与资源 | 用途 |
| --- | --- |
| `POST /builds/{build_id}/index` | 建立或显式重试索引；成功返回 201 |
| `GET /builds/{build_id}/index` | 检查指纹、模型 identity、条目数与失败码 |
| `POST /candidate-queries` | JSON `{build_id,question}`；返回原问题、分析、各通道排名、初始候选及预算 |
| `GET /candidate-queries/{query_id}` | 读取固定的候选检查记录，不重新运行模型或检索 |

初始候选包含统一 Memory、通道排名、RRF 分数及来源 ID。结果保存构建 ID、索引指纹、时间、实际配置、Prompt 版本和分析模型调用元数据。它属于候选检查记录，不是最终答案 Trace。

## 验证

普通行为检查不加载模型或付费调用：

```sh
uv run --locked pytest -q
```

实际本地模型检查单独运行：

```sh
LOCOMO_LOCAL_EMBEDDING=1 HF_HUB_OFFLINE=1 uv run --locked --extra embedding pytest -m local_embedding -q
```

该检查加载真实固定 revision，检查 384 维归一化向量、组合文本越界拒绝，并通过实际 MiniLM、SQLite、BM25/cosine/RRF API 路径检索；只替换外部生成模型。独立 DeepSeek 付费检查仍默认跳过。实验结果见 `experiments/issue-7-retrieval-validation.md`。

实现依据：[MiniLM 模型卡](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2)、[SentenceTransformer API](https://sbert.net/docs/package_reference/sentence_transformer/model.html)、[rank_bm25 上游](https://github.com/dorianbrown/rank_bm25)。模型缓存与 revision 的核查不代表正式课程检索效果已达标。
