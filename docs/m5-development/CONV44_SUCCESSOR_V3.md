# conv-44 继承构建与抽取恢复 v3

2026-11-04。用户已另批并执行本阶段，首请求成功，新增9 Memory、conv-44现34/34片段与392 Memory；详见[真实终态](CONV44_SUCCESSOR_V3_RESULTS.md)。以下保留执行前方案，“未授权/未执行”仅表示准备时点，不代表当前状态。

v3 提供独立的新 Build，只重新生成失败的 ordinal 18。当前为离线准备阶段，尚未获得新增付费授权、尚未真实执行；conv-44 仍为 33/34 片段、383 条 Memory，第六份完整 JSON 尚未形成。

## 失败证据与修改

[恢复 v2](ISOLATED_EXTRACTION_RECOVERY_V2_RESULTS.md) 的三个真实请求都因 `extraction_time_expression_required` 被严格拒绝。历史被拒输出未保存，不能据此断言过去九次失败的具体原因。session timestamp 误用、错误 anchor、改写或归一化时间只是待验证假设。

`extract-v5-literal-time-grounding` 明确要求 `original_expression` 逐字来自所引 source 的 `text`。三个新增合成示例覆盖相对日期、仅有 session timestamp 和跨 source 的不同时间。推导日期单独记录，不能通过改写原表达、拼接时间或清空有依据时间绕过校验。原 `ExtractionBatch`、实体身份规则和严格时间 schema 保持原契约。

新增安全诊断仅在抽取发生既有时间表达校验错误时运行。诊断输出包含字段路径、固定枚举类别和布尔标志；类别区分其他已引 source、未引 source、anchor session time、空白差异、Unicode NFC 差异及未找到。诊断不保存原文、时间表达、source ID、其摘要或原始异常；诊断异常不改变重试和计费行为。未来真实诊断才能验证上述假设。

## 继承与来源记录

`tools/m5/conv44_successor.py` 先只读检查父库不含 QA、evidence 或 answers，再验证 recovery v2 终态、旧 producer、数据库和账本身份。脚本通过 SQLite backup 创建独立库，保留全部父记录，并用当前 producer 创建新 Build。新 Build 的全部 thinking 字段为 `disabled`。

脚本对 33 个成功片段的每条 Memory 重跑严格校验，仅改变 Build、Fragment 和 Memory 身份。内容、实体、状态、时间、source links 和 session times 必须保持相等。旧片段和旧调用 metadata 保存在私有 `inheritance.json` 与片段 `inherited_from` 中；新阶段的 `calls` 从空开始，不重复计费。新 Build 只有原完整 20 轮失败片段 pending。

新 Build 执行契约绑定当前 Prompt，但 33 个继承片段仍来自历史 producer，不能宣称其由 v5 生成。`inheritance.json` 保存完整身份映射、历史 producer 和混合来源声明。严格 `memory-export-v2` 禁止额外字段；未来第六份 JSON 必须另附绑定 JSON SHA 的 provenance sidecar。

准备和执行入口冻结核心 producer、当前恢复 helper、脚本、settings、继承 sidecar、父终态及原行/继承行摘要。执行前修改任一受保护对象必须拒绝。单次 marker 阻止重复执行；网络期间修改继承 Memory 会触发终态保护失败。

## 离线准备

在此独立工作树运行，保留已有输出，不覆盖它。命令不加载凭据，并通过项目离线守卫阻止网络：

```sh
umask 077
env -u DEEPSEEK_API_KEY -u OPENAI_API_KEY -u CODEX_ACCESS_TOKEN \
  HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
  PYTHONPATH=tools/integration/offline_guard:src:. \
  /home/kenqia/my_folder/locomo-dynamic-memory/.venv/bin/python \
  -m tools.m5.conv44_successor \
  --source /home/kenqia/my_folder/locomo-worktrees/m5-final-build-repair-20261104/var/m5-development/conv44-isolated-recovery-v2 \
  --source-terminal /home/kenqia/my_folder/locomo-worktrees/m5-final-build-repair-20261104/experiments/m5-development/conv44-isolated-recovery-v2-terminal-v1.json \
  --output var/m5-development/conv44-successor-v3
```

预期结果为继承 33 片段和 383 Memory、全新独立空 ledger、无 `authorization.json`、无执行 marker。实际结果与摘要在准备完成后另存公共检查记录。准备不会自动授权。

## 付费范围与后续顺序

本阶段仅申请最多 3 次物理请求、独立硬封顶 USD 0.2619648，`deepseek-flash`、thinking disabled、不发送 `reasoning_effort`。单请求最多 160,000 UTF-8 字节及 32,768 输出 tokens；按 2026-11-04 峰价 input USD 0.30/M、output USD 1.20/M，以每字节一个代理 token 的保守上界计算。独立 ledger 包含 schema/transport 重试，Unknown 保留完整预约。旧预算不转移。

只有用户明确批准精确 plan 后，才创建匹配授权并通过 `scripts/with_deepseek_env.py` 调用 `--execute-authorized`。本工具最多运行到 `extracted`，失败后不自动再试。合成验证不能保证真实恢复成功。

成功后依次完成新本地索引、单独获批的全 disabled 关系构建、完整化、严格第六份 JSON 及 provenance sidecar。旧索引、关系和投影不复制到新 Build。六份完整导出齐备后，再冻结最终策略、全部查询参数、评分与成本政策，并为一次独立 Level E 准备独立预算和授权。在此之前保持留出 QA、evidence 和 answers 未读。

回滚不需要修改父库：保留新 scratch 与账本供审计，后续不引用新 Build 即可。没有安装依赖、远端写入、主分支整合或发布。未识别关联 Notion 记录，本轮未同步，也未标记总任务完成。
