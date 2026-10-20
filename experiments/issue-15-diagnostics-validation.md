# Issue #15 第一阶段：安全诊断与持久化验证

2026-10-20，Asia/Shanghai。范围为交接中的任务 A。任务 B 与真实模型定位未启动。
本记录不改变原始失败归因，原始 29 个失败任务、87 次 `invalid_output` 的细节仍未知。

## 实现与验证边界

实施起点为 `d65e380bc949497f8f095dfea1ed0062beacabd4`，工作区为
`/home/kenqia/my_folder/locomo-worktrees/issue15`，分支为 `codex/issue-15-integration`。
已有离线诊断报告、脚本和 `issue-15-live-validation.md` 的未提交改动保留，不混入本次提交。
旧实验数据库没有启动、迁移、重试或恢复。真实模型新增调用为 **0**。

诊断现在回答：某个逻辑执行内各调用在哪一阶段失败、真实结束原因是什么、此前调用
是否仍可读取，以及中断后哪些结果或用量未知。实现不增加生产依赖、监控平台或配置项。
字段、旧记录和中断语义见 [关系 API 说明](../docs/app/relations.md#安全失败诊断与调用历史)。

测试边界为 `DeepSeekModel.generate`、公开关系任务/构建 API、实验快照和独立临时数据库。
先用测试复现缺少分类字段与重试覆盖历史，再实现相应能力。受控 HTTP 使用
`httpx.MockTransport`；Embedding 使用既有 `ControlledEmbedder`。
中断测试在独立子进程中调用 `os._exit(23)`，不连接真实 provider。

## 模型行为等价对照

运行：

```sh
cd /home/kenqia/my_folder/locomo-worktrees/issue15
PYTHONPATH=src .venv/bin/python experiments/issue-15-diagnostics-contract-check.py
```

脚本从起点提交载入旧适配器与关系 Schema，在相同的 13 组受控响应中比较旧版和新版。
覆盖成功、JSON、Schema、枚举、领域规则、length、缺失 finish_reason、空内容、
畸形 provider 结构、HTTP 错误、超时、上下文拒绝和失败后成功。每版共 34 次 Mock
调用，请求字节、粗类别、重试次数和报告用量一致，JSON Schema 完全相等。
完整结果及请求 SHA-256 保存在 [机器记录](issue-15-diagnostics-contract-check.json)。
`tests/test_model_diagnostics.py` 同时固定了从旧版独立取得的请求 hash。
原设置没有等待退避，新增诊断也没有添加等待退避；检查点持久化会增加少量本地耗时，
不改变 HTTP timeout 设置。该对照证明受控场景行为相同，不代表真实模型质量改善。

## 回归与复核

已运行：

```sh
.venv/bin/python -m pytest tests/test_model_diagnostics.py tests/test_relation_diagnostics.py tests/test_relations.py -q
```

结果为 57 passed。此前包含构建和契约恢复的针对性测试同样通过，命令为：

```sh
.venv/bin/python -m pytest tests/test_relation_diagnostics.py tests/test_model_diagnostics.py tests/test_builds.py tests/test_relations.py tests/test_contract_recovery.py -q
```

该较早切片为 58 passed，后续新增测试另行运行，不将这两个数量相加。
最终全套非付费回归命令为：

```sh
.venv/bin/python -m pytest -m 'not live_model and not local_embedding' -q
```

结果为 **178 passed, 4 deselected**，耗时 191.83 秒。被排除的项目要求显式真实模型
或本地 Embedding 验证，不属于本阶段受控验收范围。

语法检查和 diff 格式检查通过：

```sh
.venv/bin/python -m compileall -q src/locomo_memory tests/test_model_diagnostics.py tests/test_relation_diagnostics.py experiments/issue-15-diagnostics-contract-check.py
git diff --cached --check
```

项目没有独立静态类型检查入口；语法检查不能替代 typechecking。未新增检查依赖或框架。
测试仅出现现有 Starlette/httpx 的弃用警告。

按仓库 `code-review` 技能，由两个非作者代理独立复核暂存 diff，固定起点为上述 SHA。
Standards 轴无 findings，Spec 轴无 findings。两个代理分别运行两个新增诊断测试文件，
各为 34 passed。复核未发现待修问题，不表示 Issue #15 已合并、验收或完整基线已通过。

本阶段完成后停止。任务 B 仍需单独冻结少量输入、确认硬调用预算，再取得新证据；
不得直接重试旧 Build 或自动恢复完整开发集实验。
