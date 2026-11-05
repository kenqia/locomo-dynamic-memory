# conv-44 本地索引与 disabled 关系入口非作者代码复核

2026-11-04。最终 Standards 与 Spec 两轴均通过，未解决发现为 0。代码可进入新的免费本地索引、关系任务 prepare 与独立 metadata 复核；本报告不授权付费关系请求、完整化、publish、留出 QA 读取或 Level E，也不保证关系语义质量。

## 范围与方法

工作树为 `/home/kenqia/my_folder/locomo-worktrees/m5-final-conv44-relations-20261104`，固定基点和复核时 HEAD 均为 `aed4634deb6c873ef1620d0a80bd023e2541d1a2`。`git diff aed4634...HEAD` 与提交列表为空；按明确范围，实际审阅使用 `git diff aed4634` 加 `git ls-files --others --exclude-standard`，全文检查下表八个未跟踪工件。范围内没有生产 `src/locomo_memory` 改动。

使用仓库 `.agents/skills/code-review/SKILL.md`，Standards 与 Spec 两名独立子代理并行审阅，初始结论互不污染。主审另行追查现有服务调用链、审阅修复并运行新鲜合成测试。Standards 依据用户工作约定、`AGENTS.md`、`CONTEXT.md`、ADR 0001/0002、`docs/agents/local-skills.md` 和技能 smell baseline；Spec 依据本次明确需求及 `CONV44_RELATIONS_V1.md`。

本次需求限定：复用现有服务，仅处理明确 successor；原库只读 backup，保留 fingerprint、settings.db_path 和继承血缘；仅目标 Build 可进入索引和关系阶段；全部新 thinking disabled；来源、Memory、片段、索引、历史 Build 与 schema 受保护；无 query/QA；实际 T 决定独立 3T 请求和 USD 0.2619648T 上界；精确授权、锁、单次 marker、Unknown 全额预约；抽取 calls 保留为历史前缀，新关系调用独立计费；成功最多到 related。

复核没有读取真实 stage、留出 QA、evidence、answers、凭据、私有 stdout 或原始 provider 日志。没有执行真实 index、prepare 或 live，没有修改实现、测试或提交代码；唯一写入为本报告。三个公共 preflight 的内容和状态已静态核对，本轮未重新读取真实数据计算其数量。

## Standards

最终未解决发现：0。没有硬标准违反或值得报告的实质 smell。

实现复用现有 `BuildService`、`RetrievalService`、`MiniLMEmbedder`、`RelationService` 和 `BudgetTransport`。新阶段使用独立 scratch；文档同步提供命令、前置条件、预算、Unknown、血缘限制、未授权状态与回滚方式；没有新增依赖或生产 schema。公共预检没有冒称真实 index 或任务 DB 已准备。后续补充的终态对账 helper 与既有契约一致。最终文档新增的终态审计段落和交接文档均已只读核对，成功状态、全 disabled、尚未真实 prepare、独立费用与后续顺序均与当前实现及既有公共终态记录一致。

## Spec

最终未解决发现：0。初审 1 项 P2 已完整关闭。

**已关闭 P2：关系 attempts 与整体终态对账不完整。** 初版只比较 provider metadata、task/build calls 与 ledger，未核 `relation_attempts` 终态及 SQL/metadata 身份；保护摘要又将目标阶段行排除。独立 Spec 子代理通过合成注入把正常完成 attempt 改为 `running`、清空 completed_at，原成功 case 仍通过并返回 related。

首轮修复加入 `terminal_calls()` 后，主审与独立 Spec 子代理又分别复现：将 task 与 attempt 同时改为 failed，phase/build 仍保持 succeeded/related，成功 case 仍通过。该情况属于同一终态一致性缺口。

最终修复与复验已覆盖：

- task.attempts、logical_attempt 连续序列及首次运行的一次逻辑 attempt；task/attempt 终态、错误和完成时间一致。
- provider SQL 的 task_id、logical_attempt、provider_attempt 与 metadata 的 build_id、task_id、logical_attempt、provider_attempt、attempt、call_id 逐项相等；物理编号连续，单逻辑 attempt 最多三次物理调用。
- `related` 必须没有失败或 pending task；Build phase 为 relations，phase prompt/schema 与 prepared 值一致，成功状态没有残留 error。
- 抽取 calls 前缀、任务 calls、规范化 provider calls 与新账本 usage 保持一致。逻辑与物理 attempt 不强行一一计数。
- 本地 policy 拒绝允许 failed logical attempt 和零物理调用；投影失败而任务全部成功的失败路径仍保留。

独立 Spec 子代理对最终 SHA 再审确认问题关闭。新增回归涵盖 running attempt、provider SQL 身份、task/attempt 联合失败、Build phase、关系 prompt/schema 与成功残留 error，以及零物理调用的本地拒绝。

其余要求均已静态核对及合成覆盖：源八表与评测 annotations 在全文摘要前检查；只索引指定新 Build；schema、历史行、继承 metadata 和 index 保护；candidate_queries 必须为空；仅实际任务数决定预算；无授权、篡改配置/源/任务/ledger 时在 marker/provider 前拒绝；Unknown 保留全额预约；重复执行拒绝；成功停止于 related，不自动重试、publish 或进入 QA。

## 新鲜验证

主审在最终稳定代码上运行：

```sh
./tools/integration/check.sh tests/test_m5_conv44_relations.py -q
```

结果：**27 passed，35.72 秒**，1 条既有 `StarletteDeprecationWarning`。测试使用合成资料、ControlledEmbedder 和 MockTransport，入口移除真实凭据并启用离线守卫。最终两文件摘要在验证前后保持一致，`git diff --check` 通过。

修复前主审的 19 项、首轮修复后的 22 项，以及故障注入结果仅作为过程证据，不替代最终验证。`conv44-relations-verification-v1.json` 明确记录修复前作者 19 项与 root 88 项结果；其中旧全仓 842 项也注明不含本次新入口，本报告不冒称已重跑全仓。root 另行启动的修后广泛回归不计入此处独立结果。

公共只读预检给出 T=384、7,134 次比较、最多 38,182 输入字节、预计 1,152 请求/USD 100.5944832。这些仍是规划值；真实 prepare 完成后须独立核对任务身份、selection、计数、费用上界、空 ledger、未批准模板、来源/索引/继承保护和权限，才可申请精确付费授权。

## 最终审查身份

| 文件 | SHA-256 |
| --- | --- |
| `tools/m5/conv44_relations.py` | `d82f8fc0bd0bc0562700a37d1c168a3276b8762936ead2d188c888f79b7bde7a` |
| `tests/test_m5_conv44_relations.py` | `eef56ec88f6972a8239c5dfd18a6dbce292a58b580257641dd152ba9d8b7f4d6` |
| `M5_CONV44_RELATIONS_V1_HANDOFF.md` | `ebc0bfd5eb6c0c8e17555d9979aadcf7f3f49eb0031660fd67471a3e4624e8d0` |
| `docs/m5-development/CONV44_RELATIONS_V1.md` | `dd6b40a9ed4fc77353b51ba80bb65d369223228bdc207ca8271c75376b27b78e` |
| `experiments/m5-development/conv44-cached-embedding-preflight-v1.json` | `fa3b41815b29ca56d702e1ad93b2d14bd0b56b1cee4099e5b765b013986903c8` |
| `experiments/m5-development/conv44-embedding-input-preflight-v1.json` | `d254f7ecb550cf1b202e2a75d3ee4758a8b50481e6f52a0a2e03d8f9b3fe5af9` |
| `experiments/m5-development/conv44-relations-readonly-preflight-v1.json` | `4ebde8dce6023c51e812fdca3e0cbb979f9941fa388cf3712deb1b61eb6ef433` |
| `experiments/m5-development/conv44-relations-verification-v1.json` | `797a5c6462635a1e8b0050bf6921467b24c310e616d6d7b943721ade0daad004` |

Standards：0 未解决；Spec：0 未解决，1 项 P2 经故障注入、修复和最终独立验证后关闭。
