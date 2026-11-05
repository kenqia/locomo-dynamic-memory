# Level E reporting 独立代码复核 v2

## 结论

针对新增的候选风险，源码核查和完整合成执行均未复现 `query_analysis` 失败产生 `retrieval` operation 的情况。当前锁定 producer 会捕获 analysis 的模型失败并 fallback，将其调用记录保存在 `query_analysis` 下。工具无需扩大 operation 白名单。

最终独立合成测试结果为 **21 passed, 1 warning in 14.72s**。结合 v1 复核，本次没有发现遗留的、已证实的 P0–P2 问题。候选风险未被确认为 P2；v1 已修复的 operation 顺序问题仍保留在历史记录中。

## 身份与历史证据

- 日期：2026-11-05。
- 作者：`/root/level_e_spec`；独立复核者：`/root/final_code_review_v6`。
- 工作树：`/home/kenqia/my_folder/locomo-worktrees/m5-final-conv44-relations-20261104`。
- 本次增量：新增一项真实 producer 合成回归，工具实现和冻结 producer 保持原身份。

| 文件 | SHA-256 |
| --- | --- |
| `tools/m5/level_e_reporting.py` | `50687231bd01a603a0bd6872b07a8c64c27b89abacc7b7b41591df0f7ab6fb89` |
| `tests/test_m5_level_e_reporting.py` | `7f9a6fdf9a3ada047db01d6693513af7ca8feca3534ab641f15ca925b1a1c707` |
| `docs/m5-development/LEVEL_E_REPORTING_REVIEW_V1.md` | `a8959aab7b28ec33689338f52b609e7e697f5b1b9e75c4e79d90fe6216fb81ba` |

v1 文件和其 20 项测试证据保留不变。v1 的冻结门禁、费用归属条件、source-only review、资源口径与分母边界复核继续适用；本文件补充 analysis 失败路径的可达性验证。

## 候选风险核查

候选风险来自 `QueryService.query()` 的通用失败处理：若一个 `ModelFailure` 在 active stage 为 `retrieval` 时向外传播，`queries.py:240` 会将 metadata 写到 `operations[stage]`，而 reporting 的白名单不含 `retrieval`。仅查看这段外层处理，不能证明锁定 producer 的 query-analysis 失败会触发它。

实际调用链中，`RetrievalService.query()` 在 `retrieval.py:139` 的 try 内发起 `query_analysis`；`retrieval.py:143` 捕获 `Exception`，并在 `retrieval.py:146` 保存 `ModelFailure.metadata`。随后检索使用原问题继续 fallback。动态查询在 `queries.py:167` 将返回的 metadata 写入 `operations['query_analysis']`；hybrid baseline 也使用相同检索服务并保存为 `query_analysis`。锁定的两臂为 `hybrid_no_resolution` 和 `dynamic`。

因此，本次没有为手工构造的 `retrieval` trace 扩大白名单，也没有修改 producer。结论范围是当前锁定实现及本次验证的模型输出失败路径，不推断其他实现或未来策略。

## 新增回归与独立验证

新增测试 `test_query_analysis_failure_is_frozen_as_analysis_and_fallback_keeps_all_costs` 使用现有合成准备流程、真实 `e.execute()`、ControlledEmbedder 和 MockTransport。它向每次 query-analysis 请求返回不符合 schema 的 JSON，触发真实的三次 invalid-output 尝试，然后让后续 resolve/answer 正常返回。

测试要求：

- 8 个 planned items 全部完成 fallback 并成功冻结。
- 每个 item 的三个 analysis 调用均为 `invalid_output`，operation 名为 `query_analysis`，不存在 `retrieval` key。
- physical ledger 与 completed adapter records 均为 36，且与 freeze 中的请求数一致。
- 分臂费用归属完整，重试请求共 16 次，失败尝试共 24 次。
- reporting 不打开 reference database，合成 reference 文件身份保持一致。

独立运行命令：

```sh
./tools/integration/check.sh tests/test_m5_level_e_reporting.py -q --maxfail=1
```

结果：`21 passed, 1 warning in 14.72s`。唯一 warning 是既有 FastAPI/Starlette TestClient 的 httpx deprecation。运行后重新核对工具、测试和 v1 报告 SHA，与上表一致。

## 验证边界

本次只读查看相关源码并运行合成测试，唯一新增复核文件为本 v2 报告。未读取真实 stage、items、执行库、QA、Gold 或私密/raw 日志，未运行 live 模型请求，未修改冻结 producer，未执行 add 或 commit。

本报告不表示真实 Level E 运行、真实答案 source-only review 或 Gold 评测已经完成。费用归属仍依赖 v1 中说明的冻结 producer 串行执行约定，ledger 本身不提供 item 外键。
