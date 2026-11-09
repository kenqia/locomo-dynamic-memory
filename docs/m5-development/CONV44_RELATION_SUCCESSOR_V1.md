# conv-44 单任务关系恢复

此入口在独立副本中重试已闭合的唯一 logical attempt 2 失败任务，生成 logical attempt 3。准备操作不授权付费调用。每个新阶段最多 3 次物理请求、预约总额最多 0.2619648 USD，使用 `deepseek-flash`、thinking disabled、160,000 UTF-8 输入字节和 32,768 输出 tokens 上限。旧额度不转移。

## 前提

源阶段必须保留原关系阶段与第一次恢复的数据库、独立账本、计划、授权、结果和已审计终态。第一次恢复终态必须为 `m5-conv44-relation-recovery-terminal-v1`、`relations_failed_not_complete`，所有检查严格为 `true`，且仅余一个执行过两次 logical attempt 的失败任务。该任务的最后三次安全诊断必须为 `same_state_dimension_required`、`judgments[1]`。此路径不表示返回判断与 history 顺序一致。

入口调用冻结的第一次恢复审计，递归验证原阶段。保留全部原成功任务、attempt、provider calls、Build calls 前缀与关系，不修改已冻结 producer、端点或校验器。新增输入契约 `relation-endpoint-label-prerequisites-v1` 独立记录，不属于原 Build fingerprint。

## 准备独立副本

在此工作树根目录运行以下命令。`<source>` 是已闭合的第一次恢复阶段目录，`<terminal>` 是独立审计后的终态 JSON；`<new-stage>` 必须不存在。

```sh
PYTHONPATH=src python -m tools.m5.conv44_relation_successor prepare \
  --source <source> --source-terminal <terminal> --output <new-stage>
```

核对 `plan.json`、空的新账本与 `authorization-template.json`。只有唯一失败任务进入 pending，旧两个 logical attempt 及其物理调用保留。未获本阶段明确授权时，不创建 `authorization.json`，不执行下一步。

## 执行已授权阶段

先由负责人核对预算、价格与计划 SHA，再按明确授权写入与模板对应、`approved=true` 的 `authorization.json`。使用现有凭证 launcher 执行：

```sh
PYTHONPATH=src python3 scripts/with_deepseek_env.py -- python -m tools.m5.conv44_relation_successor \
  execute-authorized --output <new-stage>
```

使用已配置的项目 Python 环境，并确保 `src` 在 `PYTHONPATH`。入口只允许启动一次。失败时仍保存结果与独立账本，不自动追加重试或沿用其他阶段余额。成功仅到 `related`，不自动完成或发布 Build。

每个候选的新增输入矩阵直接调用原 `relation_label_error`，列出维度是否相同、端点类型、允许标签及禁止标签的安全错误码。允许标签仍须满足证据与业务语义；`UPDATE` 仍要求同一过程的真实阶段推进与原文引文。入口不更改已有响应，不强制选定标签。

## 导出第六份完整 JSON

先独立核验新阶段并写入 `m5-conv44-relation-successor-terminal-v1`、`related_not_complete` 终态。`<export-copy>` 必须不存在。

```sh
PYTHONPATH=src python -m tools.m5.conv44_relation_successor complete-export \
  --source <new-stage> --source-terminal <new-terminal> --output <export-copy>
```

此操作不调用模型，在另一份独立副本中只完成并 pin 目标 Build，导出 `exports/conv-44.json`，严格执行 `MemoryExport` roundtrip。`conv-44.provenance.json` 绑定抽取继承、三个关系阶段的终态、计划与各自账本快照，并逐阶段记录三种 wire producer。导出结束前再次验证源终态、全部父血缘及源身份。

没有更新线上数据库或远端版本。回滚时保留源阶段与账本，只停止使用新增副本；清理文件由负责人按项目归档规则处理。此工具不读取留出 QA、evidence 或 answers，不执行 Level E。

## 合成验证

```sh
./tools/integration/check.sh tests/test_m5_conv44_relation_successor.py -q
```

测试使用独立合成历史和 `MockTransport`，覆盖 logical attempt 1–3 历史保留、独立预算、unknown usage、未授权与篡改拒绝、跨维度 fact→plan 标签限制、跨维度 UPDATE 证据要求、三阶段导出血缘和导出末尾终态复核。测试不打开真实实验阶段。
