# Issues #20、#21 本地入口验证

2026-10-20。本记录说明入口实现与受控行为验证，未读取受保护凭据文件、发起付费请求或执行本地测试集模型评测。真实 DeepSeek 抽取、真实 `conv-26` smoke 和 757 题全量成绩仍待执行；#20、#21 不因代码实现而视为真实实验完成。

## 实现与边界

`python -m locomo_memory.experiment` 通过公开 HTTP API 使用独立数据库和产物目录。`prepare` 导入官方固定原件并生成五题和全量计划；`verify` 实际检查本地 Embedding；`probe` 使用三轮合成原文检查抽取与来源；`smoke`、`full` 有限推进已有构建阶段与持久评测；`status`、`export` 只读取；`resume` 仅显式重试指定阶段或结果状态。

`--allow-paid` 是每次可能生成操作的显式开关。真实全量门槛重新读取实际 smoke Run，要求 20 项成功、原始问题身份与四策略匹配、固定构建、完整全文全部来源送达以及来源、配置、实现身份匹配。受控 provider 或 Embedding 的成功只记为 `controlled_validation_only`，不能解锁全量。没有 QA 质量分数门槛。

创建 Build/Run 前先持久保存 pending initiation。HTTP 结果丢失时保留未知状态，拒绝重复创建；成功身份立即保存 receipt。此保护不能保证跨 provider 恰好一次计费，未知调用仍需公开记录检查与人工复核。

## TDD 与新鲜验证

在实现工作树根目录运行：

```sh
PYTHONPATH=src /home/kenqia/my_folder/locomo-worktrees/issue15/.venv/bin/python -m pytest tests/test_experiment.py -q
```

合入 #17、#18、#19 后结果为 14 passed，耗时 72.08 秒，仅有既有 Starlette/httpx 弃用警告。工作树 `git diff --check` 通过。测试使用公开 CLI/FastAPI、真实 SQLite 和官方原件，只控制外部生成与 Embedding，不通过私有 SQL 断言。

主要行为包括：

- 安全凭据存在性、未加载模型的只读 preflight，以及数据库路径不匹配时在导入前拒绝。
- 官方开发计划产物、缺凭据离线准备、重复准备复用同一计划，不建立付费构建。
- `--allow-paid`、公开服务契约、MiniLM 形状与超长拒绝等前提检查。
- 小型公开抽取检查保留原始来源与返回模型身份，并将受控检查单列。
- `conv-26` 五题、四策略完整受控运行得到 20 个持久项；重复运行、读取与导出不再调用提供方。
- 20 项失败后默认恢复不重试失败项；显式 `--retry-failed` 后成功，每项仍保留失败和成功两次尝试，错误正文不进入结果。
- 创建 Build 后丢失 HTTP 响应的基线先复现重复生成第二个构建；修复后重复命令只保留一个构建并返回 `initiation_outcome_unknown`。

阶段调用记录 HTTP 请求及响应观察时间，构建状态变化保留观察时间线。它们可能包含操作人员两次命令之间的空闲时间，不能作为纯构建计算耗时。provider 调用用量、各次尝试耗时和查询统计分别保留；未知值不冒称零。

## 待执行的真实检查

本票未安装新依赖；测试复用 root 已有独立环境。root 的受控回归、真实 MiniLM 和实际模型运行应各自留下最终记录。本入口测试中的 LengthCheckedEmbedder 仍是受控适配器，不能替代真实 MiniLM 验证。没有真实 smoke 通过记录时，全量入口保持阻塞。

使用、准备、启动、诊断、恢复、导出和回退步骤见[真实基线运行指南](../docs/app/real-baseline.md)。模型契约示例明确保留 2026-10-20 指南重新获取失败的限制。完整机器记录与短报告由实际命令写入所选隔离目录；没有用受控结果编造正式实验成绩。未执行 push、PR、部署、Issue 关闭、Notion 更新或课程提交。
