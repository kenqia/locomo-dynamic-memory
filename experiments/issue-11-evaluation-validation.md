# Issue #11 评测与对照验证

2026-10-19。基于 #9 `59f7102`，合并含 #10 的 integration `9e4c302` 后验证。独立 worktree `/tmp/locomo-issue11`、分支 `codex/issue-11`。按已批准公开 FastAPI seam，使用真实 SQLite、BM25、cosine/RRF、关系、历史扩展及 QueryService，只控制外部 LLM/Embedding；没有付费调用、远端写入、认证读取或正式测试集调参。

## TDD 与集成覆盖

首个 `POST /evaluation-inputs` 测试在端点未实现时返回 404，随后实现输入隔离、映射、持久运行、分母与覆盖。后续逐步验证官方类别分支、严格证据、真实基线策略差异、未知会话/课程划分拒绝、失败调用与 Run 可重读、独立真值及固定构建边界。官方数据只读检查发现六个 numeric gold，公开 API 测试先因拒绝数字失败，再实现保留原类型、评分时依官方转字符串。

`uv run --locked pytest tests/test_evaluation.py -q`：6 passed。包含类别1不对称多答案、类别2词干、类别3gold分号、类别5缺gold拒答、未知类别、数字gold、复合/空/畸形/不存在来源、整样本不可计分、独立分母、gold不进入模型、Full Text真实轮次引用、Dense实际选取、消融扩展保留且无resolver、失败调用持久记录，以及课程4/2及独立标注接入。测试中的课程形状数据也是合成夹具，绝非已获得课程正式标签。

首次完整回归在合并 #10 前：`uv run --locked pytest -q`，76 passed、3 skipped。后续合并回归结果在下方追加。默认跳过真实/付费模型与本地模型标记测试；这里不重复父任务已完成的实际 MiniLM 检查。

## 官方规范只读交叉核对

从保留 upstream `evaluation.py` AST 仅选取 `normalize_answer`、`f1_score`、`f1` 函数，以同一个 NLTK PorterStemmer 对80组非空 gold 的合成预测、标注、类别组合进行独立比较，全部误差小于1e-12。没有整体导入 upstream，不安装或调用 BERTScore。

读取 `data/raw/locomo/locomo10.json`，仅验证结构与原始 dia_id 映射。1986个QA中1977可映射、4空证据、5异常样本、4个合法复合引用样本，与父任务独立 preflight 一致。空白分隔复合引用必须完整匹配合法ID序列。没有修正 `D30:05`、`D:11:26` 等异常，没有针对这些QA运行生成或调参。

## 页面冒烟

执行 `/tmp/issue11-ui-smoke.py`，启动真实本地 uvicorn/FastAPI，以真实HTTP完成合成导入、异步构建进度等待、索引、关系、发布与独立输入。Streamlit AppTest 调用页面 `render_evaluation`，点击运行四策略，验证一个结果表与四条成功结果，再输入Run ID并读取持久结果：`live_fastapi=true, real_sqlite=true, strategies=4, result_table=1, saved_run_read=true, exceptions=0`。

脚本只注入受控LLM/Embedding；不mock HTTP或存储。首次脚本尝试误用了 TestClient 的同步构建帮助函数，真实HTTP背景任务尚未结束导致索引断言失败；改为按公开构建状态轮询后通过。另一次脚本未在输入值变更后 rerun 就点击禁用按钮，AppTest正确拒绝；按浏览器交互规则 rerun 后通过。以上是验证脚本修正，不是被隐藏的产品通过状态。

没有运行真实浏览器视觉/网络审查、真实DeepSeek质量评测或正式课程指标。AppTest不代替真实浏览器检查。缺少课程六ID、正式划分及独立语义标签，不能宣称动态准确率或课程验收完成。

## 依赖和记录边界

项目独立 `.venv` 新增锁定 `nltk==3.10.3`，仅使用无需下载语料的 PorterStemmer，以复用官方计分依赖。没有新增生产服务或重型BERT模型。运行记录包含Python/包版本、实现源码SHA256、固定构建与配置、各Prompt/schema、真实上下文差异、截断、耗时、额外分析调用及provider已报告token。Embedding在成功检索中计实际一次或空索引零次；检索在返回前失败时次数不可确定，明确null并汇总未知样本数。未报告provider用量独立计数，不把部分用量当完整费用。

合并 #10 后首次完整回归：`uv run --locked pytest -q`，89 passed、4 skipped，93.62s。最后补入Embedding失败审计测试及独立关系真值验证后，`uv run --locked pytest tests/test_evaluation.py -q`，7 passed；失败Embedding不会被记作零次调用，Run持久可读。组合验证与最终全量结果随后追加。
