# Level E reporting 独立代码复核 v1

## 结论

本次复核在下列最终源码身份上，没有发现遗留的、已证实的 P0–P2 问题。独立运行合成测试得到 **20 passed, 1 warning in 8.92s**。

复核中曾发现一项 P2：失败 trace 经 canonical JSON 持久化后，operation 字典顺序不再等于请求顺序，可能将不同预约金额归给错误的重试或失败调用。作者已改为按冻结 producer 的固定 operation 顺序读取，并增加相同 usage、不同预约金额的回归。本结论包含该修复。

这份报告只评价后处理工具及其合成验证，不表示真实 Level E 运行已经完成、独立语义复核已经完成，或评测已经通过。

## 范围与源码身份

- 工作树：`/home/kenqia/my_folder/locomo-worktrees/m5-final-conv44-relations-20261104`。
- 作者：`/root/level_e_spec`；独立复核者：`/root/final_code_review_v6`。
- 工具：`tools/m5/level_e_reporting.py`。
- 测试：`tests/test_m5_level_e_reporting.py`。
- 复核日期：2026-11-05。

| 文件 | SHA-256 |
| --- | --- |
| `tools/m5/level_e_reporting.py` | `50687231bd01a603a0bd6872b07a8c64c27b89abacc7b7b41591df0f7ab6fb89` |
| `tests/test_m5_level_e_reporting.py` | `bfa9c050e6c7e7344e9de88c81b69fb63ee2a9ca2debc758f0e439175fbfcee9` |

测试完成后重新计算两文件 SHA，与作者冻结身份一致。工具将自身及 `level_c_audit.py`、`level_c_results.py`、`level_c_semantic_review.py` 的源码 SHA 写入 audit、review manifest 和语义汇总；验证旧 review 包时要求当前实现身份一致。

为核实调用约定，本次只读查看了复用 helper、Level E producer 和 query failure trace 的相关源码。未修改作者代码、冻结 producer 或任何真实执行产物；本复核者唯一新增文件为本报告，未执行 `git add` 或 commit。

## 检查证据

### 冻结门禁与读取范围

`checked()` 在读取 ledger 或 source evidence 前调用既有 `frozen_items()`，要求 item 数等于完整 plan，并检查 generation freeze 在读取前后保持一致。它复用既有 plan、lock、input、item、execution 和 ledger 身份门禁，不跳过冻结验证。

后处理不调用 Gold scorer。source-only review 通过只读 SQL 选择限定的 source columns 和 conversation turn count，不选择 reference answer 或 category。合成集成测试使用实际 Level E execute/freeze 路径、MockTransport 和 ControlledEmbedder，并拦截 reference database 打开；audit 和 prepare-review 均完成，未打开合成 Gold。

CLI 要求输出位于 stage 外；公共 review 汇总也不能写入私有 review 目录。数值 audit 和语义汇总不输出 question、answer、source text 或 review quotes。

### Adapter records、physical ledger 与费用

`records()` 统计已完成的 adapter records，不将其称为 physical sends。按 `query_analysis`、`resolve`、`answer`、`failed_operation` 顺序读取，修复了失败 trace 字典排序导致的费用错配。测试同时覆盖 dynamic 的 canonical failed trace 和 baseline 的 failed operation 顺序。

physical requests 数量和预约总额取自 ledger。已完成 adapter records 多于 physical ledger 时拒绝报告。仅在 records 与 ledger 行数相等、无 unknown item、逐行 usage 和 response/transport 状态一致且无未终态 reservation 时，才按顺序归属分臂预约。缺失、孤立、unknown 或不匹配记录保留全局 ledger，分臂预约和比例为 `not_measured`。

该归属仍依赖冻结 producer 串行执行 item 和 operation 的约定。ledger 没有 item 外键，工具没有声称提供请求 ID 绑定；仅靠相同 usage 也不能独立证明对应关系。

ledger 审计复用 Decimal、policy、budget 和 partial/unknown usage 检查。adapter 费用复用 `call_cost()`，缺失 usage 不补零；unknown usage 的预约不退款。分臂统计区分 all、retry、failed-attempt、failed-item 和 unknown-item，token efficiency 明确为已报告 tokens 除以成功 item 数，未将其解释为事实收益。

### 延迟、存储与资源口径

报告区分 item elapsed、stage latency 和 adapter attempt latency，提供覆盖数量和缺失信息。存储量明确为冻结后的文件大小，不解释为运行峰值或增长量。

CPU、RSS 和 GPU 默认 `not_measured`。可选资源 sidecar 必须绑定 plan 和 execution-started SHA、whole-launcher scope、成功退出状态及有限非负数值，并检查读取期间文件未变化。其口径为 launcher children 累计 CPU 和进程生命周期 peak RSS；per-arm CPU/RSS 与 GPU 仍为未测。此绑定不独立证明 sidecar 的采样来源。

### Source-only review 与指标分母

review packet 包含完整两段 source conversation、问题、最终预测/答案、execution outcome 和 opaque unit ID；不含 arm、question ID、QA index、category、Gold 或 score。arm mapping 单独保存，使用私有目录和文件权限。manifest 绑定 freeze、plan、packet、mapping 及后处理实现。

验证时重建 packet 和 mapping，要求单位唯一、完整且与冻结投影精确一致。复用的独立 review 合约检查 reviewer/provenance、独立性声明、同 conversation 的逐字 source quote、citation coverage，以及 false/correct abstention 所需证据。它记录独立复核者的判断与声明，不能自动证明其事实判断正确。

pending review 不能通过 complete gate。failed/unknown 保留在 planned 和 execution outcome 中；unknown 只在语义合约中使用 failed 的不适用规则。语义指标分母仅包含适用且已复核的记录，不能把 failed/unknown 计为语义成功。source support 不等于 Gold F1，字面拒答也不等于语义正确。

## 独立验证

在上述工作树运行：

```sh
./tools/integration/check.sh tests/test_m5_level_e_reporting.py -q --maxfail=1
```

结果：`20 passed, 1 warning in 8.92s`。唯一 warning 为既有 FastAPI/Starlette TestClient 的 httpx deprecation。

覆盖包括冻结门禁、串行费用归属、失败与重试、partial/unknown usage、孤立 ledger、资源身份、私有 review 输出、完整 review gate、quote/citation/abstention 合约、unknown 分母、真实合成 execute/freeze、reference SQL 拒绝访问，以及后处理 helper 身份变化后拒绝验证旧 review 包。

本次未运行 live 模型请求，未读取真实 stage、items、执行库、QA、Gold 或私密/raw 日志，未对真实运行产物执行 reporting，也未独立完成真实答案的 source-only review。真实运行数据及 review 结果仍须分别验收。
