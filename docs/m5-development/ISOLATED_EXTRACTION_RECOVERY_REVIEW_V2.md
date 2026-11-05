# Isolated extraction recovery v2 独立复核

复核日期：2026-11-04。复核者未编写本次工具和测试。结论：在本报告限定的输入契约和执行范围内，未发现已证实的 P0、P1 或 P2 问题。独立运行的 13 项合成测试全部通过。本结论不代表真实抽取已经成功，也不构成真实请求授权。

## 复核范围

本次复核针对工作树 `/home/kenqia/my_folder/locomo-worktrees/m5-final-build-repair-20261104` 中的两个新增文件：

| 文件 | SHA-256 |
| --- | --- |
| `tools/m5/isolated_extraction_recovery.py` | `9d53ab4837757bedc0b3258ec4ef1be841cc05fec74358b9559bb650ab055ea3` |
| `tests/test_m5_isolated_extraction_recovery.py` | `2a45286d2f8d8cbd92bfe35300f401bc4abd4840c359b389a513cebf18a0595a` |

记录报告时的工作树 HEAD 为 `bcbf479d3a24f79a87695a3d3bbbacd86974e184`；上述新增文件当时尚未提交。复核同时追踪了现有 `BuildService`、`Database`、`backend_ownership`、`BudgetTransport`、`DeepSeekModel`、旧 recovery 的只读检查、排他写文件函数及导入 schema。

目标限定为：在新独立副本上重试 conv-44 的失败 extraction fragment ordinal 18；保持原 settings/config/fingerprint；最多发出 3 次请求，新增预约上限为 USD 0.2619648；原 source stage 和原 ledger 只读；不进行 index、relation、publish 或 QA。

## Standards 结论

已确认的 P0–P2 finding：0。

- 工具复用现有生产抽取、schema 校验、预算传输层及存储接口，没有新增抽取规则、时间表达降级、截断策略或请求重试层。
- 保留旧 `settings.db_path`，通过显式 `Database(target)` 路由所有 build 存储操作。现有 `BuildService` 使用该 database 实例；配置与 fingerprint 不需要重写。
- source 数据库和 ledger 的读取使用 SQLite 只读连接。保护摘要包含逻辑行、schema、plan 和 settings；结论是逻辑内容保持不变，不声称 SQLite 辅助文件或文件时间戳逐字节不变。
- `execution-started.json` 使用现有排他创建函数写入。target 的 backend lock 与持久门闩共同约束并发及重复执行；失败后没有自动重启路径。

## Spec 结论

已确认的 P0–P2 finding：0。

| 要求 | 复核结论 |
| --- | --- |
| 独立副本、新空 ledger | `prepare` 通过 SQLite backup 生成 target，创建独立预算 ledger，不转移旧预约。 |
| 先检查 annotations，再读取全表快照 | `prepare` 首先调用 SQL guard；`execute` 对 source 和 target 调用 guard 后才计算全表摘要。非空 annotations 的合成测试在 `source_identity` 前拒绝。 |
| 精确授权 | 授权必须与包含 scope、build、ordinal、policy 及 plan SHA 的预期对象完全相等；缺失、拒绝和变异均在请求及 marker 前停止。 |
| 冻结实现与输入 | plan 校验 producer hashes、工具自身 SHA、settings SHA、source identity、target 初始快照和空 ledger 快照。 |
| 只重试失败片段 | 旧 stage 检查要求唯一失败片段为目标 ordinal；生产 `retry` 和 `run` 只处理该 build 的待执行片段。 |
| 已成功内容保持不变 | 保护摘要覆盖 schema、所有非目标行和历史 build calls 前缀；仅允许目标片段、该片段新 memories/source links，以及相关 build 状态和追加 metadata 改变。 |
| metadata 历史保留 | 历史 calls 前缀逐项参与摘要；删减前缀会拒绝。`returned_models` 按历史前缀派生，与生产 metadata 追加规则一致。 |
| 完整生产校验 | 保留完整 fragment 输入、thinking disabled、原时间表达约束和生产 Memory 校验；执行后再次校验目标 Memory 与外键。 |
| 新预算硬上限 | 独立 `BudgetTransport` 在请求前预约，最多 3 次；按 160000 input bytes 与 32768 output tokens 的最坏情况，单次预约 USD 0.0873216，三次为 USD 0.2619648。 |
| Unknown 不退款 | 传输 Unknown 保留全部预约；合成测试验证连续三次 ReadTimeout 后停止，Unknown 预约等于总预约。 |
| 不扩大后续范围 | outcome 保持 `complete_build=false`、`automatic_recovery=false`；非 extracted 终态抛出异常，门闩阻止重复执行。 |

SQL guard 以现有 `import_dataset` 的生产契约为前提：`annotations_json` 为 sample 对象列表，`sample_id` 为 `StrictStr`，其余 annotation 字段由固定字段集生成。允许字段值为 JSON null，拒绝其余非 null 内容。任意手工构造的其他 JSON 形状不属于本次已验证的导入契约。

## 独立验证

在上述工作树执行现有离线检查入口：

```sh
./tools/integration/check.sh tests/test_m5_isolated_extraction_recovery.py -q
```

结果为 `13 passed, 1 warning in 10.25s`。warning 是既有 `StarletteDeprecationWarning`，提示 `starlette.testclient` 的 httpx 兼容路径将弃用，没有测试失败。入口使用项目已有环境与 offline guard；所有请求来自 synthetic fixture 和 `httpx.MockTransport`。

测试覆盖成功及失败路径、3 次有限尝试、源与好片段不变、授权缺失、source/copy/ledger/settings/plan/approval 变异拒绝、重复执行拒绝、原时间表达持续拒绝、历史 metadata 变异检测和 Unknown 全额预约。合成 fixture 的 output cap 为 8192，测试显式沿用该值；真实 stage 的 32768 上限另做 metadata 核对，未发出真实请求。

## 真实 prepared stage 的只读核对

仅核对新 stage `/home/kenqia/my_folder/locomo-worktrees/m5-final-build-repair-20261104/var/m5-development/conv44-isolated-recovery-v2` 的 plan、settings、ledger 计数及授权/marker 文件存在性；未读取真实 conversation、QA、evidence、answers 或 raw Provider 日志。

核对结果：

- status 为 `prepared_not_authorized`；build 为 `bef9f685957843698b3083ff4cbc79a4`，ordinal 为 18，初始 build calls 为 42。
- policy 为 deepseek-flash、最多 3 请求、USD 0.2619648、input cap 160000 bytes、output cap 32768 tokens；extraction thinking 为 disabled。
- 新 physical request ledger 行数为 0；`authorization.json` 与 `execution-started.json` 均不存在；authorization template 的 `approved` 为 false。
- settings 的 `db_path` 仍指向原 source，target 数据库为独立路径；plan 的 script SHA 与被审工具一致。
- plan SHA-256 为 `ca0b07d1633a5fb178bb9cec7061fa9ae453b8428c184ae6a2754c7931cc7425`。

## 操作文档与公开证据追加复核

只读追加复核了 `ISOLATED_EXTRACTION_RECOVERY_V2.md` 与三份 `conv44-isolated-recovery-v2` 公开 JSON。最终版本未留下已证实的 P0–P2 问题。

| 文件 | SHA-256 |
| --- | --- |
| `docs/m5-development/ISOLATED_EXTRACTION_RECOVERY_V2.md` | `d325d0f184811d9e77dbaa3701620536827fc2eeab1e8a74e875dddd1ee111a0` |
| `experiments/m5-development/conv44-isolated-recovery-v2-prepared.json` | `445674bd03add8cdc1ba6d3a074c2f11fdfcf67a1d24ae88416efc4e4ca09e51` |
| `experiments/m5-development/conv44-isolated-recovery-v2-pricing.json` | `ae1cb4884b36d241d8fc04704c0a7785a4eb78212770fb9b5846ab2d6f3a5d0e` |
| `experiments/m5-development/conv44-isolated-recovery-v2-authorization-gate.json` | `001e076e2ccccdaf11d15d85dffd972a19559ba3e40874c5d75708bd46ccceb3` |

公开 prepared JSON 与真实 plan 的全部共同字段一致，prepared 和 authorization-gate 的 plan SHA 与真实 plan 一致，公开 pricing 文件 SHA 与 prepared 引用一致。79 项 producer 文件的 SHA 均与当前工作树匹配，工具自身另有独立 SHA；文档已采用相同计数。使用 Decimal 独立重算新增预约上限，结果为 USD 0.2619648。scope、Unknown 全额预约、未授权及 0 请求的表述相互一致。

追加复核发现并向作者报告了一项 P2 文档命令问题：缺少 `PYTHONPATH` 时，所列共享 venv 导入原开发树，运行 `--help` 即报 `ModuleNotFoundError: locomo_memory.m5_budget`，且没有保证导入冻结的工作树代码。作者已仅修改操作文档，显式设置 `PYTHONPATH=src:.`，不改变冻结工具、plan 或 stage。

修正后的执行命令为：

```sh
cd /home/kenqia/my_folder/locomo-worktrees/m5-final-build-repair-20261104
PYTHONPATH=src:. python3 scripts/with_deepseek_env.py -- \
  /home/kenqia/my_folder/locomo-dynamic-memory/.venv/bin/python \
  -m tools.m5.isolated_extraction_recovery \
  --output var/m5-development/conv44-isolated-recovery-v2 --execute-authorized
```

该命令仍以用户明确批准和精确授权文件为前提。复核者没有执行 launcher，而是独立运行以下无凭据、无 Provider 请求的模块导入检查，结果 exit 0：

```sh
env PYTHONPATH=src:. \
  /home/kenqia/my_folder/locomo-dynamic-memory/.venv/bin/python \
  -m tools.m5.isolated_extraction_recovery --help
```

公开授权门证据记录缺少授权时 0 请求拒绝、原 source/新数据库/ledger 不变、没有 execution marker，并与 plan SHA 绑定。本次追加复核只校对该公开结果与计划的一致性，没有重新执行真实 stage。全仓测试仍由执行者运行，本报告不声明其通过。

## 验证边界

本复核未运行真实 `prepare` 或 `execute`，未访问凭据，也未调用真实 Provider。真实 stage 已由执行者准备，本复核只读取上述 metadata。未验证真实模型能否在相同生产契约下通过第 18 片段；该工具提供的是另一次有限尝试，不是已经证实的模型修复。

本报告不授权额外请求，不将预算余量视为自动授权，也不改变后续 index、relation、验证或发布的门槛。
