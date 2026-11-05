# conv-44 successor v3 独立终态复核

2026-11-04。**通过：8 组独立只读检查，未发现问题。** Build `d9fb61417bb740e4b8eb34acb8652a46` 已到 `extracted` / `extraction`，34/34 片段成功，共 392 条 Memory，其中继承 383 条、新增 9 条。该结果尚非 complete，第六份严格完整 JSON 尚未形成，Level E 未执行。

实际发生 1 次物理请求，状态为 `response_received`；保守预约 USD 0.0453867，报告 usage 的峰价上界 USD 0.0031977，Unknown 为 0。实际发票未访问。调用使用 `deepseek-flash`、thinking disabled；metadata 的 `reasoning_effort` 为 null，现行 adapter 在 disabled 分支不发送该字段。响应 metadata 报告 `deepseek-flash`、HTTP 200、`finish_reason=stop`、`status=succeeded`。mutable alias 不能证明不可变服务端版本 pin。

## 范围与安全边界

工作树为 `/home/kenqia/my_folder/locomo-worktrees/m5-final-conv44-recovery-v3-20261104`，阶段为 `var/m5-development/conv44-successor-v3`。本审计在 root 确认唯一 live 进程已 exit 0 后开始。

复核方通过项目离线守卫及已有 Python 环境读取安全 metadata；移除真实凭据变量，全部 SQLite 连接为 `mode=ro` / `query_only=ON`。Memory 和 Source Turn 只在内存中用于严格校验与等价比较，没有输出正文、表达式或 source ID。未读取私有 stdout、原始 provider 日志、留出 QA、evidence、answers 或凭据，未发起新 live 请求。

唯一主动行为是向已完成入口注入 `httpx.MockTransport`，验证单次执行门禁。入口在任何 provider、锁或数据库写入前抛出 `successor_already_started`；Mock provider 调用数为 0。

## 八组独立检查

| 组 | 核验内容 | 结果 |
| --- | --- | --- |
| 1. 范围与冻结身份 | 先以 SQL 检查 conversation-only 表集及空评测 annotations，再核父终态、源数据库、账本、plan、settings 与准备复核记录 | 全部匹配；源库和源账本保持冻结逻辑身份 |
| 2. 授权与 producer | 独立枚举 82 个 producer 文件并核摘要；私有精确授权与公共授权记录、plan、scope、policy 相等；marker 绑定同一 plan | 全部通过；用户“是”的公共授权记录对应最多 3 请求 / USD 0.2619648；旧预算未转移 |
| 3. 配置与当前契约 | 核 settings、sidecar、Build 不可变身份、fingerprint/config、v5 prompt、全部 thinking 字段 | 当前契约有效；全部新 thinking disabled；继承血缘摘要保持不变 |
| 4. 父记录与继承保护 | 比较全部原 rowid 行及 schema；重算父行/继承快照；逐项比较 33 片段和 383 Memory 的允许身份变换、关系列、links 与历史 metadata | 原记录完全保留；继承内容和 metadata 未变；历史调用未计入新账本 |
| 5. 完整失败片段与严格产物 | ordinal 18 与父失败片段 source 顺序完全相等，核完整 20 条 position 范围；对新 Build 全部 392 Memory 重跑 Memory/MemoryDraft 严格校验、身份列、source links、session times 及外键检查 | 34 片段全部 succeeded；ordinal 18 仅执行一次，产生 9 条新 Memory；全部校验通过 |
| 6. 调用、usage、费用与 outcome | 新片段 calls、新 Build calls、独立 ledger、outcome 的请求数与 usage 相等；按实际序列化输入重算预约和已报告用量峰价 | 1 次请求；prompt 5,679 / completion 1,245 / total 6,924；预约与费用计算一致；Unknown 0 |
| 7. 阶段边界与权限 | 核数据库表集、当前状态、私有工件权限和 outcome 边界 | 仅原 8 张数据表，无 index/relation/publish/query/evaluation 表；stage 0700，所核私有文件 0600；尚非 complete |
| 8. 重复拒绝与审计后身份 | 使用 MockTransport 重复调用执行入口，再比较新库、独立账本与父源身份 | 立即拒绝，Mock 调用 0；数据库与账本逻辑快照未变 |

继承等价与 schema 验证不替代独立事实准确率评价。383 条继承 Memory 仍来自历史 producer，只有本次新增片段由 v5 生成；混合来源已如实记录。此次成功也不能确诊此前九次失败的具体原因，历史被拒输出未保存。

## 费用核算

首请求序列化 messages 为 20,217 UTF-8 字节，输出上限 32,768 tokens；按已获授权当日峰价 input USD 0.30/M、output USD 1.20/M 核算：

```text
预约 = (20217 × 0.30 + 32768 × 1.20) / 1000000 = USD 0.0453867
报告用量峰价上界 = (5679 × 0.30 + 1245 × 1.20) / 1000000 = USD 0.0031977
```

该预约低于本阶段 USD 0.2619648 封顶。调用 metadata、账本 policy 与当日公共价格复查记录一致；未访问实际发票。已使用的单次 marker 关闭本入口，剩余容量不构成额外恢复、关系阶段或 Level E 的授权。

## 终态身份

[独立安全审计 JSON](../../experiments/m5-development/conv44-successor-v3-independent-terminal-v1.json) 保存全部安全计数、布尔值和摘要，SHA-256 为 `03ae0702fbec79fff228b3cbb2ec6ab7a655933077ff2baa7c417aea7504181e`。

| 工件 | SHA-256 / 逻辑摘要 |
| --- | --- |
| plan | `27fbb376bbd493c7911b55124c3a6e71930428fe86e10d65f1533af208114bbd` |
| settings | `3e2bd434a1c75f263a35dd5f28be50d858ff8047e0e540390a68b8fce0eafe28` |
| 继承 sidecar | `b5e312b5c54bde04f57c1d6961e6dd108a1c9594c6a6ffa8526b0ce2969cdf1e` |
| 入口脚本 | `8d2aba66c44c77844d7c597e11c3027f586b47a128d475ab25b2c2652b2b0c6a` |
| 精确私有授权 | `37f08da570dbd3577cc85bd8c64051b9b73f65e93fa0360b165e676e486ecb74` |
| 执行 marker | `c9cb08507253b9ce669abc6dd4f6bdb8363781b6d71c49d2637f09e6f68cc6bb` |
| outcome | `255bfd54b5f5fd49ca48c8dbfa6a67c15a5df203bac1a82282c7b1d0e24c4fce` |
| 新库终态逻辑摘要 | `07ce1ee6d2a32c9b4c310e520c328134fea00cb7fc041776425770e618034e79` |
| 新账本终态逻辑摘要 | `ece4a12e1128428da2aaee99fadf13272457fa1fb4e7df8c01a527b37bcfddf0` |

数据库身份按包含提交 WAL 的逻辑行冻结。本轮没有重新运行测试集，也没有修改源码、索引、关系或完整化。

## 下一阶段建议

在新的本地副本中，直接复用 `RetrievalService.create_index(新 Build ID)`，保留冻结 settings.db_path 并显式路由副本存储。旧 `holdout_index.py` 遍历所有 Build，会对保留的旧 v4 failed Build 触发契约不匹配，不适合作为本次直接入口。索引只允许修改新 Build 的 status/phase/updated_at 及其索引记录，Memory、片段、历史 Build 和来源保持不变。

disabled 关系阶段复用 `RelationService.start/run`，另行准备任务清单、保护摘要、独立账本与精确授权；不使用 conv-43/high 专用门禁。保留本次 extraction calls 为历史前缀，只将新关系调用计入新账本。若实际任务数为 T、保持每任务 3 次尝试、160,000 字节和 32,768 输出上限，则独立关系封顶为 3T 请求、USD 0.2619648T；T 必须在成功终态基础上重新计算，不能沿用失败前数量。

终态复核通过；本报告不授权后续付费关系构建、发布、留出 QA 读取或 Level E。
