# conv-44 独立恢复 v2 终态复核

结论：**独立终态与费用审计通过；本次恢复未成功。** 获批的独立阶段已用完 3 次物理请求，三次均因 `extraction_time_expression_required` 被生产校验拒绝。conv-44 保持 33/34 片段成功、383 条 Memory；目标 ordinal 18 没有新增 Memory。原数据库、旧 ledger、其他 Build、成功片段及历史 metadata 保持不变，不得自动重试。

非作者复核者：`final_code_review_v6`。实际观察时间：2026-11-04 13:04:46 UTC（Asia/Shanghai 21:04:46）。工作树为 `/home/kenqia/my_folder/locomo-worktrees/m5-final-build-repair-20261104`，记录报告时 HEAD 为 `213a8ab3cf5272c5faf4c18a092b7526d20418b0`。报告遵循已读取的 `google-developer-docs` 技能。

## 范围与方法

只读访问 `var/m5-development/conv44-isolated-recovery-v2` 的 plan、settings、authorization、execution marker、outcome、数据库和独立预算 ledger。复核者没有执行 launcher、Provider、恢复、index、relation、publish 或 QA，也没有读取凭据、原始 Provider 输出、留出 QA/evidence/answers 或 raw 日志。

首先对原 source 与 target 分别调用 `require_conversation_only`。两次 SQL guard 均通过，随后才调用任何全库逻辑快照或保护摘要。数据库只包含冻结的 8 张 conversation/extraction 表；guard 允许生产导入契约中的 null annotation 字段，拒绝非 null annotation 内容。

实际审计使用项目既有解释器与 offline guard，未创建持久审计脚本或修改 stage。入口与核心保护检查如下；完整内联审计还检查下文列出的 schema、来源连接、metadata 和预算：

```sh
env PYTHONPATH=tools/integration/offline_guard:src:. \
  /home/kenqia/my_folder/locomo-dynamic-memory/.venv/bin/python - <<'PY'
import json
from pathlib import Path
from tools.m5 import isolated_extraction_recovery as r
stage = Path('var/m5-development/conv44-isolated-recovery-v2')
plan = json.loads((stage/'plan.json').read_text())
source = Path(plan['source_stage'])
r.require_conversation_only(source/'memory.sqlite3')
r.require_conversation_only(stage/'memory.sqlite3')
assert r.source_identity(source) == plan['source_identity']
assert r.protected_snapshot(stage/'memory.sqlite3', plan['initial_build_calls']) == plan['protected_snapshot']
assert json.loads((stage/'authorization.json').read_text()) == r.authorization(stage)
PY
```

审计输出仅包含状态、计数、摘要、费用、usage 和安全诊断类别/字段路径。21 项独立检查全部为 true；另一次只读 SQL 核对确认各 conversation 的 Memory 数量及累计 fragment attempts。

## 冻结身份与授权

| 工件或检查 | 独立实测结果 |
| --- | --- |
| plan SHA-256 | `ca0b07d1633a5fb178bb9cec7061fa9ae453b8428c184ae6a2754c7931cc7425` |
| 工具 SHA-256 | `9d53ab4837757bedc0b3258ec4ef1be841cc05fec74358b9559bb650ab055ea3` |
| authorization SHA-256 | `5b7696f081960eeec59a474e9cb85c755c2dde2ab765aa55303aa36605b75809` |
| outcome SHA-256 | `22b0871c0fc3885d5414659a245f327a891bbd506818a2b37feb0e56196409dd` |
| producer 与工具身份 | 79 项 producer SHA 全部匹配冻结 plan；工具自身 SHA 匹配 |
| 精确授权与门闩 | authorization 完全等于现有 `authorization(stage)`；marker 的 scope 与 plan SHA 精确匹配 |
| 配置与 fingerprint | settings SHA、完整 settings、原 `db_path`、build config/fingerprint/source SHA/prompt version/schema version 全部保持不变；extraction thinking 为 disabled |
| 保护摘要 | 独立重算等于冻结值 `8be3094b7c2920af8fd996ea79beffd23c75a2551f4cc209ccf8aacc4517971e` |
| 历史 metadata | 原 42 条 build calls 前缀精确相等；新增 3 条等于目标 fragment 当前 calls，最终共 45 条 |

独立重算 source identity 与冻结 plan 完全相同：

| 原 source 工件 | 逻辑快照或文件 SHA-256 |
| --- | --- |
| 数据库 | `9310cd06333a4358ea688e752310c0616105e16c04dff7ab6c39686e92e7692c` |
| 原 ledger | `319c8025674ac9a3d25116b33f3459887da5d0f4dc411b677f7b40b4d89fc038` |
| 原 plan | `8363cb625599cd2650a89ee41c2b1773ad3528444d42d26a5ebfc254d9553c69` |
| 原 settings | `830bb4879747d32c16df0fc59a4cd87641c29a96c295f1eaec911a8ebd7146e7` |

上述不变性指逻辑内容及列出的文件身份，不声称 SQLite 辅助文件或时间戳逐字节不变。

## Build、Memory 与 Source

| 检查 | 独立实测结果 |
| --- | --- |
| conv-44 Build | `failed` / `extraction`，33 succeeded、1 failed，无额外 pending/running 片段 |
| 目标片段 | ordinal 18、20 个 source turns、`failed`、`error_code=invalid_output`、0 条 Memory |
| fragment attempts | target 累计值为 3，原 source 为 2；该列统计 fragment 执行批次，当前批次内部另有 3 条模型 calls |
| 另一 Build | conv-43 保持 `extracted` / `extraction`，402 条 Memory |
| 已保存 Memory | conv-44 为 383 条，合计 785 条，与 source 完全相同 |
| Source 与连接 | 1,355 个 SourceTurn、808 个 memory_sources，source/target 计数完全相同 |
| 生产契约复验 | 全部 1,355 个 SourceTurn、785 条 Memory 与 808 个来源连接通过，失败数 0 |
| 外键 | `PRAGMA foreign_key_check` 无违规，孤立来源连接数为 0 |

Memory 复验使用该 Memory 所属 fragment 的完整 sources context，检查生产 schema、时间原文约束、来源属于同 dataset/conversation/fragment、JSON 与存储身份列一致、state key/session times，以及 source links 与 `source_ids` 精确相等。复核没有输出任何来源原文或 Memory 内容。未通过模型校验的三个新候选没有落库。

## 三次调用的安全诊断

当前 fragment 的 3 条 calls 与独立 ledger 的 3 条 usage 按顺序逐项相等；build metadata 新增后缀也与这 3 条 calls 完全相等。

| 当前模型 attempt | HTTP / finish | 状态与 failure stage | 安全 error code | field path |
| --- | --- | --- | --- | --- |
| 1 | 200 / stop | `invalid_output` / `domain_validation` | `extraction_time_expression_required` | `memories[12]` |
| 2 | 200 / stop | `invalid_output` / `domain_validation` | `extraction_time_expression_required` | `memories[9]` |
| 3 | 200 / stop | `invalid_output` / `domain_validation` | `extraction_time_expression_required` | `memories[9]` |

三次均请求并返回 alias `deepseek-flash`，`thinking={"type":"disabled"}`、`reasoning_effort=null`、`max_tokens=32768`。返回 alias 不证明服务端不可变版本已锁定。

上述诊断只证明候选没有通过时间表达的生产校验；由于本次未读取原始输出，不能判定候选具体改写了哪段内容，或是否选择了错误 anchor。没有放宽生产契约。

## 独立费用重算

ledger policy 完整匹配冻结 plan，硬上限为 3 请求 / USD 0.2619648。金额使用 Decimal 从 ledger 与 usage 独立重算，并与 outcome 比较，全部一致。

| 请求 | 预约 USD | prompt tokens | completion tokens | total tokens |
| --- | ---: | ---: | ---: | ---: |
| 1 | 0.044322 | 4,794 | 1,921 | 6,715 |
| 2 | 0.0446235 | 5,019 | 1,318 | 6,337 |
| 3 | 0.0446232 | 5,019 | 1,467 | 6,486 |
| 合计 | **0.1335687** | **14,832** | **4,706** | **19,538** |

3 条 ledger 状态全部为 `response_received`。Unknown 用量请求为 0、Unknown 预约为 USD 0；每条 total tokens 等于 prompt 与 completion 之和。按 input USD 0.30 / output USD 1.20 每百万 tokens 重算已知 usage 峰价为 **USD 0.0100968**。该数值不是实际账单，复核者没有访问账单。

金额上限尚余 USD 0.1283961，物理请求额度已用完。余额不授权新增尝试，不释放一次性门闩，也不转移至旧 ledger 或后续阶段。

## 后续边界

target 只含 `datasets`、`import_artifacts`、`conversations`、`source_turns`、`build_versions`、`build_fragments`、`memories`、`memory_sources`；没有 index、relation、publish、query 或 evaluation 表。保护摘要与 source identity 匹配，outcome 的 `holdout_qa_read=false`、`complete_build=false`、`automatic_recovery=false` 与实际终态一致。

本阶段没有完成 conv-44 extraction，也没有推进关系构建、完整 Build、严格导出或 Level E。任何后继模型修复、数据处理或付费重试均需另行确定方案与授权；本报告不授予这些权限。复核没有重跑全仓测试，也不将其他代理的测试运行视为本次独立终态验证结果。
