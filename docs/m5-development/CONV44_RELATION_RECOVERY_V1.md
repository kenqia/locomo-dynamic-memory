# conv-44 失败关系任务的独立恢复

2026-11-05（Asia/Shanghai）。本工具仅为已结束的 conv-44 关系阶段准备一次独立恢复，不重建 Memory，也不重跑已成功任务。原关系阶段已审计终结：374成功、10失败；新恢复计划和账本现已实际准备、根代理与非作者复核通过，尚未获付费批准；详见[实际准备](CONV44_RELATION_RECOVERY_V1_PREPARATION.md)。代码和合成验证不能证明真实恢复成功。

## 输入与不变性

`tools/m5/conv44_relation_recovery.py` 接受原关系 stage 及其终态审计。必须先有 `relations_failed_not_complete`、完整关闭的任务和调用记录，以及绑定计划、授权、设置、继承血缘、outcome、DB 与 ledger 的终态摘要。原阶段还须通过非作者独立审计。中断中的任务不纳入失败恢复范围。

免费 `prepare` 在新 scratch 中只将原来失败的 F 个任务设为 pending，复用已有成功任务和关系。原成功任务整行、Memory、Source、片段、索引、其他 Build、旧 logical attempt 1、旧 provider 记录和 Build calls 前缀均保持不变。新调用记为 logical attempt 2，独立账本从零开始。旧任务的最新 metadata 可被核心服务覆盖，旧历史仍保存在原 stage、attempt/provider 表和 calls 前缀中。

输入包装器根据上下文提供每个端点的完整 `source_ids` 映射，并加入旧失败的安全 code/path 和复制指导。不截短、猜测或修复 ID，不放宽生产校验。每次新调用记录 `input_contract_version` 与包装器 SHA。原核心 Prompt、schema、配置和 Build fingerprint 保持原样；新输入契约由独立 sidecar 记录，不声称 fingerprint 已包含包装器。

## 准备、授权和执行

在隔离工作树 `/home/kenqia/my_folder/locomo-worktrees/m5-final-conv44-relations-20261104` 中运行。以下命令已在原阶段终结和双终态审计通过后实际执行，当前stage不得重复创建。

```sh
umask 077
env -u DEEPSEEK_API_KEY -u OPENAI_API_KEY -u CODEX_ACCESS_TOKEN \
  HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
  PYTHONPATH=tools/integration/offline_guard:src:. \
  /home/kenqia/my_folder/locomo-dynamic-memory/.venv/bin/python \
  -m tools.m5.conv44_relation_recovery prepare \
  --source var/m5-development/conv44-relations-v1 \
  --source-terminal experiments/m5-development/conv44-relations-terminal-v1.json \
  --output var/m5-development/conv44-relation-recovery-v1
```

实际准备后，逐项复核 F、任务身份、旧记录保护、完整来源映射、输入字节、设置及 producer SHA、零请求账本和缺少授权拒绝。不得覆盖已有输出目录。

每个失败任务最多 3 次物理请求；单请求最多 160,000 UTF-8 字节、32,768 输出 tokens。按峰价 input USD0.30/M、output USD1.20/M 计算：新请求硬上限为 `3F`，新费用硬上限为 `USD0.2619648 × F`。schema/transport 重试均计入，Unknown 保留全部预约；原额度余量不转移。执行前重新核对官方价格和 alias 映射。

取得匹配实际 plan SHA 的独立用户授权后，才能通过 `scripts/with_deepseek_env.py` 调用 `execute-authorized --output <stage>`。该模式要求精确批准文件、未使用的一次启动 marker 和数据库锁；所有新调用均为 `deepseek-flash`、thinking disabled，不发送 reasoning_effort。失败或中断后不自动追加尝试。授权仅覆盖恢复关系，不覆盖 Level E、远端发布或生产切换。

## 终态与第六份导出

恢复终态需独立核对新 logical attempt 2 与物理账本、全部原记录、完整新增关系覆盖和严格来源校验。成功时重算 CurrentState projection 并逐字段比对。原尝试失败记录与 Unknown 不删除、不重编号。

独立审计通过并保存 `m5-conv44-relation-recovery-terminal-v1` / `related_not_complete` 后，使用 `complete-export --source <recovery-stage> --source-terminal <terminal> --output <fresh-copy>`。该模式只在新本地副本完整化、pin 并严格 roundtrip `memory-export-v2`，原恢复库保持 related。导出 sidecar 同时绑定抽取继承血缘、原关系阶段和新恢复阶段的终态、plan 与两份 ledger，以及混合关系输入 producer。复制前后再次核对终态五文件绑定和源摘要；完整 JSON 不能提前生成。

原始 related 库和新 complete 副本都不属于生产发布。六份严格 JSON 齐备后，才锁定最终系统配置并准备独立 Level E。当前 conv-43/44 的 QA、evidence 和 answers 仍未读。

## 验证与回滚

最终代码由根代理运行 `./tools/integration/check.sh tests/test_m5_conv44_relation_recovery.py -q`，39 passed，56.19 秒，仅既有 Starlette warning。非作者对最终指导与账本测试基准修复验证8项通过，0.87秒；此前独立完整35项加终态链故障复现共36项通过，55.39秒。两轴复核见[最终复核](CONV44_RELATION_RECOVERY_V1_REVIEW.md)。

工具 SHA 为 `77cc554f9ebc94c70cb2f0f1e4674aeffdd3b659efaf997dcc5740371ac5120a`，测试 SHA 为 `18c803c1441a9be2bd3df58c76fb29eedd37e0e9d5d8d4f2f44f0825fa01412d`。本阶段不新增依赖或修改核心 producer。回滚时停止引用新 scratch 与导出，保留原库、所有失败证据、计划和账本；不清理或覆盖历史成果。
