# 五段 Build 的副本完整化与严格导出

2026-11-04。已在全新私有 scratch 中将 conv-43 从 `related` 完整化为 `complete`，并实际取得 conv-26、conv-30、conv-41、conv-42、conv-43 的五份 `memory-export-v2` 严格导出。脚本完整运行退出码为 0；原关系阶段仍为 `related`、未 publish，原关系库、账本和四开发源库逻辑快照前后不变。

这项操作属于用户“继续推进总任务”及六段完整 Build 验收范围内的本地可逆 scratch 工作，不扩展原付费关系阶段的授权。只有新副本执行 `VersionsService.publish`；没有写生产或原数据库、远端发布、查询、评测、模型请求或凭据访问。conv-44 在副本中整行保持原样，仍为 `failed`，因此尚未完成六段完整 Build 验收，也没有执行 Level E 或证明 QA、关系语义质量及 Release 就绪。

## 实际输入与输出

执行工作树为 `/home/kenqia/my_folder/locomo-worktrees/m5-final-build-repair-20261104`。

| 用途 | 路径 |
| --- | --- |
| 原 conv-43 关系终态 stage | `/home/kenqia/my_folder/locomo-worktrees/m5-final-development-20261104/var/m5-development/conv43-relation-proposal-v1` |
| 四开发冻结源 | `/home/kenqia/my_folder/locomo-worktrees/m5-final-input-v2-20261104/var/m5-development/level-c-input-v2-preparation-v1` |
| 本次全新私有输出 | `var/m5-development/five-build-export-v1` |
| 副本数据库 | `var/m5-development/five-build-export-v1/memory.sqlite3` |
| 五份原文 JSON | `var/m5-development/five-build-export-v1/exports/conv-*.json` |
| 公共身份与验收摘要 | `experiments/m5-development/five-build-export-v1.json` |
| 实现脚本 | `tools/m5/complete_export_copy.py` |

私有输出根和 `exports` 目录权限为 `0700`；数据库、SQLite sidecar、settings、审计、摘要和所有原文 JSON 均为 `0600`。公共摘要只保存身份、计数、指纹、模型血缘摘要和哈希，不包含 Source、Memory、关系理由或评测答案原文。私有目录受 Git 忽略，clone 不会自动取得它。

两份数据库主文件的执行时 SHA 如下。由于 SQLite 可能有已提交 WAL，完整状态依据逻辑快照和 SQLite backup，不把主文件 SHA 单独当作完整状态证明。

| 源 | 主文件 SHA-256 |
| --- | --- |
| 四开发冻结源 | `1b62ea21c13d65b4f4192f58d9c1786ffc38eb064d458bb2ea142aabb31699cf` |
| 原 conv-43 关系库 | `f4958a75ed33080804ae7126481adc27f450f5722c47768be542558c122dd3ae` |

## 已完成的严格导出

“来源并集”仅指被导出 Memory 引用到的 Source Turn；不把它冒称为整段 conversation 的全部轮次。

| 对话 | Build ID | Memory | 来源并集 / 整段轮次 | 关系 | 成功片段 |
| --- | --- | ---: | ---: | ---: | ---: |
| conv-26 | `367c901b300440649bdc0bfba2af8010` | 259 | 190 / 419 | 4,740 | 21 |
| conv-30 | `b8f34a05c8ef4585a1fc3c917745aa53` | 244 | 154 / 369 | 4,460 | 19 |
| conv-41 | `8d459492549b4a3e88005211f036addf` | 321 | 243 / 663 | 5,767 | 34 |
| conv-42 | `c892596ac8884f43b4cf2098349a7fa5` | 413 | 297 / 629 | 7,724 | 32 |
| conv-43 | `b19ae777b6e642c9855ea278ebd4cd81` | 402 | 300 / 680 | 7,620 | 34 |

五份导出都通过 `MemoryExport.model_validate_json`，与原 `MemoryExport` 对象和 JSON 字典严格 roundtrip 相等；自查还重新读取文件并再次序列化、解析、比较对象。schema 为 `memory-export-v2`，关系契约为 `relation-v2-stage-evidence`，索引均为 ready，投影版本均为 `current-state-v1`。各 Build、索引和投影的完整指纹见公共摘要。

所有索引沿用 `sentence-transformers/all-MiniLM-L6-v2`，revision `c9745ed1d9f207416be6d2e6f8de32d1f16199bf`，384 维、256 token 上限、`length_policy=reject`、normalized true、CPU，文本 schema 为 `entity-dimension-value-content-v1`。本次没有加载模型或重新生成 embedding。

最终导出文件身份如下：

| 对话 | 导出 SHA-256 |
| --- | --- |
| conv-26 | `08f4624a39c98793e0ad288e6de6c4ba058e0f30fa27f49569de0bdec0f1be78` |
| conv-30 | `efb5c9cdfea490358982f1c2b82818759aa46aad83d6f0d3f459415c268ec1ae` |
| conv-41 | `e15b30e89de463cca4ff9fcd347b332a72525f0fbfb8506a5476df120fd4b488` |
| conv-42 | `89d6bdf02e7eca10014688e0a7946fd536b846c4ff6c8b09a84bb8671680e3fd` |
| conv-43 | `2ae95deb13dcf22e1bb91cff44db88feba7c3bcf1b753e907ba121f4ac972f17` |

## 审计与变更边界

脚本在复制前实际调用 `relation_audit.audit`，要求结果与原 `terminal-audit-v1.json` 完整对象相等，且状态为 related、published false。结束时再次重跑并比较完整对象。原 audit 文件 SHA 为 `93ba6dd8a92e2f95985d3eb2aa00928e0e9ed507314f2458c1e56970e86ce793`；本地保存的复跑对象为 `source-relation-audit.json`。

复制使用源连接 `mode=ro`、`query_only=ON` 和 SQLite backup，纳入已提交 WAL；备份后的 schema 和逐表逻辑摘要先与源完整比较。settings 字节 SHA 保持 `830bb4879747d32c16df0fc59a4cd87641c29a96c295f1eaec911a8ebd7146e7`，包括历史 `db_path` 在内的生产者配置不改写，实际 storage 仅通过 `Database(target)` 指向新副本。`BuildService.require_current_contract` 检查原 fingerprint 和 settings。

执行 `VersionsService.publish` 后，差异检查只接受：

- conv-43 Build 的 `status`、`phase` 变为 complete，`updated_at` 更新。
- `active_versions` 新增该 dataset 下 conv-43 的唯一 pin。

conv-44 Build 整行与其余 Build 字段完全相等；schema 不变，除 `build_versions`、`active_versions` 外逐表摘要均相等。这覆盖 Memory、Source、Index、关系、投影、任务、尝试记录及 provider 元数据。没有初始化源库的 `Database` 或 service。四开发导出按 input-v2 plan 的四个明确 pin，在只读事务中直接 `read_bundle`。

原关系库、四开发源库和原 ledger 的 schema 与逐表逻辑摘要在操作前后相等；摘要保存于公共结果。副本的 query/evaluation 相关表存在时必须为空，没有构造 QueryService 或 EvaluationService。NoProvider 的 `generate` 入口直接抛错，成功退出说明没有通过该入口发起模型调用；实际命令还启用已有离线网络守卫。

源 relation、其冻结 index 源及四开发源都先在 SQL 内检查 QA、answer、evidence 和辅助 annotation 字段非 null 数量为 0，只返回计数，不返回标注值；不存在可读的留出 QA payload。随后逻辑摘要只产生哈希，不输出表内原文。本次未读取 conv-43/44 的 QA、evidence 或 answers。

## 历史模型血缘

本次没有新增模型请求，不能将历史 Build 描述为全链 thinking disabled。五段原 extraction 调用记录均为 disabled，关系调用记录均为 high：

| 对话 | 已保存 extraction 尝试 | 已保存 relation 尝试 | 关系记录来源 |
| --- | ---: | ---: | --- |
| conv-26 | 21 | 256 | 旧 `relation_tasks.metadata_json.calls` |
| conv-30 | 19 | 247 | 旧 `relation_tasks.metadata_json.calls` |
| conv-41 | 35 | 318 | 旧 `relation_tasks.metadata_json.calls` |
| conv-42 | 34 | 415 | 旧 `relation_tasks.metadata_json.calls` |
| conv-43 | 36 | 408 | `relation_provider_calls.metadata_json` |

这些是历史 metadata 中保存的尝试记录数，不是本次费用或新请求。conv-43 408 条中返回 model 为 `deepseek-flash` 的 401 条，另 7 条未报告返回 model，与历史 transport Unknown 一致；原账本风险预约不变。本次不据此重新结算历史费用。

五段原 build settings 保留 `relation_thinking_effort=high` 和 `resolution_thinking_effort=low`；后者是冻结配置，不表示本次运行了 resolution。model metadata 的 requested/returned alias 为 `deepseek-flash`，历史文档版本为 `DeepSeek-V4.1-Flash-1017`，可变服务 alias 不等于不可变模型 pin。input-v2 新 QA 的 thinking disabled 不会覆盖这些历史构建血缘。

## 实际命令、第一次结果保留与验证

本次未安装依赖、修改配置或 hooks。使用项目已有 Python 环境及离线守卫，实际命令如下：

```sh
env -u DEEPSEEK_API_KEY -u OPENAI_API_KEY -u CODEX_ACCESS_TOKEN \
  HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
  PYTHONPATH=tools/integration/offline_guard:src:. \
  /home/kenqia/my_folder/locomo-dynamic-memory/.venv/bin/python \
  -m tools.m5.complete_export_copy
```

脚本拒绝覆盖现有输出或公共报告。首次运行也通过完整化、严格导出与所有数据库不变检查，但 lineage 初版只计 `relation_provider_calls`，遗漏四开发旧 task metadata 中的历史关系调用。该问题只影响元数据汇总。修复后，将首次输出目录可逆移动至 `var/m5-development/five-build-export-v1-first-pass`，将首次公共报告和脚本副本也存入其中，再向规定的全新 `five-build-export-v1` 完整重跑；没有删除或覆盖首次结果。

| 证据 | SHA-256 |
| --- | --- |
| 当前脚本 | `4dc064e11d4d174fd21f7037379a3382b10d85b6a218e58afd0c7c0445a8a071` |
| 当前公共结果 | `ba90a8cb4d5389fd18367da245b573d1876c101dac58ad04ce84603b9c284bd9` |
| 首次脚本 `script-first-pass.py` | `342e49a6017ae50909daab896f9b8fac8cb42e55a3857fdf279449662908e1b6` |
| 首次报告 `public-summary-first-pass.json` | `4d03b17dfa5aaea09237bfcf25a2a6efef0a15b0b6d1604d10a1436371e0e7ba` |

当前脚本实际退出码为 0，输出 5 份 strict export、Provider 请求 0。另执行只读逐文件 SHA、大小、Memory/Source/Relation 计数及严格 roundtrip 复查，并核对全部私有目录与文件权限；证据保存在 `var/m5-development/five-build-export-v1/independent-export-reparse-check.json`，SHA 为 `0032a22fd9a25425ab3c8bb77b0375aac225827b2d47d506a1cf06b4b9bc8353`。代码已通过 `ast.parse` 与 `git diff --check`。

根代理随后完成非作者独立复核，退出码为 0；[独立核验证据](../../experiments/m5-development/five-build-export-v1-independent-check.json)确认最终脚本及报告 SHA、五份 roundtrip/SHA、历史 lineage、source/dev/ledger/copy 逻辑摘要，以及原关系 audit 完整对象相等。该复核只读检查产物，没有再次 publish 原库或副本。

本次未新增测试脚手架，真实 scratch 的严格导出与变更白名单断言是本任务的实际验收入口。根代理另报告新树全仓检查实际完成：802 passed、1 skipped、4 deselected、1 项既有 warning，489.70 秒；本脚本作者没有重复运行这项全仓检查。本脚本作者交接时未 commit；根代理后续本地提交以 Git 历史为准。没有 push、PR 或 main 合并。未发现关联 Notion 记录，本次没有同步或标记总任务完成。

恢复不需要修改原源：首次和最终 scratch 均可保留检查。任何后续清理、生产迁移、conv-44 修复、留出评测或 Level E 都不是本脚本动作；本报告没有把五段导出冒称为六段已验收。
