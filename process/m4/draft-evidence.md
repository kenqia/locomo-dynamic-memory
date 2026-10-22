# M4 报告初版编写与证据索引

日期：2026-10-21（Asia/Shanghai）。对应[报告 v0.1](../../docs/design/m4-midterm-report.md)。本记录保存编写依据和待核对项，不代表成员已复核或课程已验收。

## 版本范围

- 主线实现：`3d9d37cb9f35d4ea656a217a55e9a8dafa4ec5a3`，2026-10-19，当前工作区 `main`；其中包含 PR #13、#14 的合并提交。
- 实验分支快照：`7893f04d97a8deea6a9134c1a148aa5ea68a6b08`，2026-10-20，本地缓存的 `origin/codex/issue-15-integration`。仅通过 Git 读取，未切换分支、联网刷新或运行真实实验。
- 文稿不回写历史规格、ticket、M1/M2 包或旧验证记录。报告是本轮新编写文件，尚未分配正式交付 tag、作者签字或成员复核结论。

## 主线来源与核对内容

| 报告内容 | 来源 | 核对要点 |
| --- | --- | --- |
| F01–F06 和阶段范围 | [Vision & Scope](../../docs/requirements/vision-and-scope.md)、[Team Workflow](../../docs/requirements/team-workflow.md) | M4 核心链路，JSON 与评测为已接入进展 |
| 术语、状态与历史边界 | [CONTEXT](../../CONTEXT.md)、[ADR 0001](../../docs/adr/0001-memory-architecture.md) | 查询不回写状态；关系未确定与冲突分开 |
| 架构、数据对象、配置 | [配置](../../src/locomo_memory/config.py)、[Memory schema](../../src/locomo_memory/memory_schemas.py)、[关系 schema](../../src/locomo_memory/relation_schemas.py)、[数据库](../../src/locomo_memory/database.py) | 默认检索参数、来源、时间、版本、Linux 文件锁 |
| 接口与操作流程 | [运行](../../docs/app/running.md)、[构建](../../docs/app/building.md)、[问答](../../docs/app/querying.md)、[版本](../../docs/app/versions.md)及对应 API 路由 | 字段与端点存在；适用环境为 WSL Ubuntu |
| 默认回归 112 passed、4 skipped | [复盘验证](../../experiments/retro-validation-guardrails.md) | 2026-10-19 历史执行结果；编写本稿未重跑 |
| 真实 MiniLM 3 passed | [实现总记录末段](../../experiments/issue-4-implementation.md)、[集成验证](../../experiments/issue-12-integration-validation.md) | 独立 opt-in 运行，不能并入默认回归数量 |
| 当前、历史、冲突与不足案例 | [合成原件](../../tests/browser/sample.json)、[集成验证](../../experiments/issue-12-integration-validation.md)、[后续浏览器结果](../../experiments/retro-browser-result.json) | 真实页面与业务实现，生成模型及 Embedding 响应受控 |
| 修复与验证局限 | [修复记录](../../experiments/issue-4-review-fixes.md)、[评测说明](../../docs/app/evaluation.md) | 日期优先级、契约恢复；主线 Full Text 有共享预算；失败项不伪造分数 |

报告只链接已有截图，没有重新截图。`issue-4-final-history-trace.png` 是历史浏览器合成案例，不是官方数据上的真实模型成绩。

## 实验分支来源

以下文件不在当前主线目录中。固定提交为 `7893f04d97a8deea6a9134c1a148aa5ea68a6b08`，可在仓库根目录使用 `git show <commit>:<path>` 读取。没有将原始实验正文复制到本目录。

| 分支内路径 | 报告采用的信息 |
| --- | --- |
| `docs/adr/0002-real-model-baseline-protocol.md` | 固定开发／留出对话、隐藏评分集、完整全文基线协议 |
| `experiments/issue-15-live-outcome.json` | conv-26 抽取 21/21、295 条 Memory、真实索引通过；关系 89 成功、29 失败、1 中断、173 待执行；QA 预检与全量未执行 |
| `experiments/issue-15-live-validation.md` | 真实运行、停止与独立回放背景，不能把局部抽取通过扩展为问答通过 |
| `experiments/issue-15-relation-evidence-followup/README.md` | 去重证据指令修订；两个多候选批次通过但均为 undetermined；未恢复完整构建；202 passed、4 deselected |

例如：

```sh
git show 7893f04d97a8deea6a9134c1a148aa5ea68a6b08:experiments/issue-15-live-outcome.json
```

该分支的新数据划分、Full Text 策略和恢复机制属于后续版本，报告已与主线能力分开。最终采用哪个版本演示，需在定稿时统一，不能混用两个版本的测试数字、配置或实验结果。

## 定稿前待核对

- [ ] 文档负责人确认作者信息；各模块负责人核对模块、接口和实现状态。
- [ ] 明确拟演示的 commit、数据及配置；若改用实验分支，更新报告和对应证据。
- [ ] 在实际展示环境复测核心链路，保存本轮结果；已有记录不能代替本轮复测。
- [ ] 核对独立动态标注、真实构建及评测的最新状态，保留未执行和失败项。
- [ ] 根据最新课程通知确认报告、演示和过程包要求；课件总表列报告 PDF 不超过 5 页、演示 PDF 不超过 10 页，尚未检查本稿导出页数。
- [ ] 导出 PDF 后检查图、表、分页和链接；M4 演示及过程 ZIP 尚未由本轮生成。
- [ ] 完成真实非作者成员复核，记录意见和修订；AI 辅助起草不代替成员验收。
- [ ] 按团队授权补充关联任务、Issue/PR 和提交记录，再进行相应状态更新。

## 本轮验证范围

本轮仅编写 Markdown、检查相对链接和 Git 差异格式，未安装依赖、调用模型或重跑应用测试。没有发布、提交或合并代码，没有创建、领取或送审外部任务，也没有更改 Notion 状态。

报告、编写记录及 README 共 3 份 Markdown 的 69 个本地链接目标存在；逐行尾随空白和代码块闭合检查通过，`git diff --check` 通过。Mermaid 图保留可编辑源码，尚未做图形渲染或 PDF 排版检查。
