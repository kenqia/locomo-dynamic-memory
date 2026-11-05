# conv-44 独立恢复 v2 终态

2026-11-04。用户明确回复“是”批准本提案后，已按冻结计划执行一次，新增 3 次物理请求全部返回响应，但均未通过严格时间来源校验。conv-44 仍为 `failed / extraction`，33/34 片段成功、383 Memory；没有新增 Memory。进程以退出码 1 结束，这是有限恢复失败的预期停止路径，不是成功构建。

## 授权、实际执行与诊断

本阶段独立上限为 3 次物理请求 / USD 0.2619648，不转移旧预算。授权精确绑定 plan SHA `ca0b07d1633a5fb178bb9cec7061fa9ae453b8428c184ae6a2754c7931cc7425`，记录见[明确授权](../../experiments/m5-development/conv44-isolated-recovery-v2-authorization-v1.json)。79 个 producer 文件、工具自身 SHA、settings、原库和新副本初始快照均在启动前核对通过；使用当天已核查官方价格，未读取或打印凭据。

实际执行命令为：

```sh
cd /home/kenqia/my_folder/locomo-worktrees/m5-final-build-repair-20261104
umask 077
PYTHONPATH=src:. python3 scripts/with_deepseek_env.py -- \
  /home/kenqia/my_folder/locomo-dynamic-memory/.venv/bin/python \
  -m tools.m5.isolated_extraction_recovery \
  --output var/m5-development/conv44-isolated-recovery-v2 --execute-authorized \
  > var/m5-development/conv44-isolated-recovery-v2/live-process-output.txt 2>&1
```

仅 launcher 载入凭据；执行器使用新副本与独立 ledger。私有进程输出没有被读取或提交。终态判断来自结构化 outcome、SQL 安全 metadata 与独立复核。

| 尝试 | 结果 | failure stage | 安全错误码 | field path |
| --- | --- | --- | --- | --- |
| 1 | invalid_output | domain_validation | extraction_time_expression_required | memories[12] |
| 2 | invalid_output | domain_validation | extraction_time_expression_required | memories[9] |
| 3 | invalid_output | domain_validation | extraction_time_expression_required | memories[9] |

三次均为请求/返回 alias `deepseek-flash`，thinking disabled、reasoning_effort null，HTTP 200、finish_reason stop。没有截断错误或 transport Unknown。规则继续要求时间原表达出现在所引 anchor 原文中；没有放宽校验、清空时间、补写 Memory 或接受失败输出。

本次与前两组三次尝试一样命中时间原文契约，说明继续同配置追加尝试尚未解决问题。被拒输出未保存在本项目的结构化工件中，也未读取私有进程日志，不能据此判断具体是时间改写还是 anchor 选择错误。**没有证明有效的模型修复，不再自动申请或执行同配置重试。** 后续需要独立验证的恢复设计及明确 producer 血缘，不能用人工修补留出 Memory 伪装成功。

## 费用与数据保护

| 项目 | 实际记录 |
| --- | ---: |
| 新物理请求 | 3 |
| response_received | 3 |
| 预约费用 | USD 0.1335687 |
| 已报告 prompt / completion tokens | 14,832 / 4,706 |
| 按报告 usage 计算的峰价上界 | USD 0.0100968 |
| Unknown 请求 / 预约 | 0 / USD 0 |
| 剩余物理请求 | 0 |

费用不是实际账单。本阶段剩余金额 USD 0.1283961 不授权额外请求。五个已授权阶段累计 1,432 次请求、预约 USD 70.9142238、已报告 usage 峰价上界 USD 7.9126119；原关系 7 项 Unknown 的 USD 0.3500316 完整预约继续保留，不视为退款。

[根代理终态审计](../../experiments/m5-development/conv44-isolated-recovery-v2-terminal-v1.json)验证原库/原 ledger 身份及保护快照不变，源 Build fingerprint 保留，目标三次 metadata 与 ledger usage 逐项对应，外键完整。独立非作者另验证全库来源/Memory schema、片段归属、metadata 历史前缀、预算与未扩展范围，见[独立终态复核](ISOLATED_EXTRACTION_RECOVERY_V2_TERMINAL_REVIEW.md)。

一次性 marker 保留；实际以 MockTransport 再次调用入口已在请求前拒绝，终态库与 ledger 不变。没有 index、relation、publish、查询、评测或读取 conv-43/44 QA/evidence/answers，也没有远端或生产写入。

## 私有归档与剩余缺口

已创建 `var/m5-development/conv44-isolated-recovery-v2-terminal-v1.tar.gz`，权限 0600、350631 bytes、11 成员，SHA-256 为 `14725365ce411c488613fb6409befb369e3154284279c470e11bb23cf810b914`。成员回读 SHA 均通过；SQLite backup 与终态逻辑摘要一致，两个数据库主文件还通过 immutable 读取核对，完整行不依赖 sidecar。归档排除私有进程日志，见[归档清单](../../experiments/m5-development/conv44-isolated-recovery-v2-archive-v1.json)。

本次仅执行冻结工具，没有修改生产代码或 Prompt，因此不重复全仓测试；同源码上一轮全仓为 802 passed、1 skipped、4 deselected。此次新增的是实际终态核验、非作者数据契约检查及归档回读证据，不能替代真实恢复成功。

五段严格导出继续有效，conv-44 仍是第六段缺口。后续仍需解决抽取及全 disabled 后继 Build 契约，完成获批关系构建与六段导出，然后锁定最终候选再准备一次 Level E。Release、最终报告/展示/ZIP 和整体验收尚未完成。未识别关联 Notion 任务，本轮未同步或标记总任务完成。
