# 项目过程（精简版）

我们按软件工程项目流程完成 M1–M5，提交材料只保留助教快速了解项目所需的过程证据。

## 1. 需求与范围

- 用户流程：导入对话 → 构建记忆 → 检查记忆 → 问答 → 评测。
- 核心质量要求：答案可追溯、构建版本一致、失败状态可见。
- 需求基线：`docs/requirements/team-workflow.md` 与 `docs/requirements/software-requirements-specification.md`。

## 2. 设计与决策

- 系统架构和运行方式：`docs/release/ARCHITECTURE.md`、`docs/release/RUNBOOK.md`。
- 记忆模型与时间语义：技术报告第 3 节。
- 主要技术决策：`docs/adr/`。
- Sidecar 的最终采用边界：`docs/release/SIDECAR_FREEZE.md`。

## 3. 开发与协作

- 源码、Issue、PR 与版本历史均保留在 Git 仓库。
- Product Console 通过 PR #41 合入 main。
- Temporal/Event Sidecar 通过 PR #42 合入 main，采用默认关闭、显式 opt-in 的离线诊断，不接入生产问答路径。
- 四位成员职责见技术报告「团队分工」。

## 4. 测试与验收

- 主分支离线公开回归：1,018 项通过（对应 Product 基准提交）。
- Sidecar 专项离线测试：183 项通过，另有 1 条依赖弃用 warning；已知时间修饰 P2 作为限制保留。
- Console 有真实浏览器操作截图和非作者复核记录。
- E25 留出实验的成绩、费用、延迟与失败统计见报告第 6–8 节。

## 5. 保留原则

提交包只保留需求、架构、决策、测试结果和版本记录的入口，不附内部质量评语、Notion 私有快照、原始对话或全部开发中间文件。
