# M4 报告修订与证据索引

日期：2026-10-22（Asia/Shanghai）。对应[报告 v0.2](../../docs/design/m4-midterm-report.md)和[5 页 PDF](../../deliverables/m4/PROJECT-MILESTONE4-3-在阴雨天游泳-报告.pdf)。本文保存本轮文档工作，不代替成员非作者复核或课程验收。

## 用户要求与版本保存

用户明确要求：按 Team Workflow 建分支保存已有进度、获取最新主线、据最新进度修订 M4 文档，并将报告限制为小于等于 5 页。用户转述的助教说明为：

> Mid-term 主要展示需求规格说明书，以及系统设计、已实现的功能、初步测试结果。建议届时已有可以运行的核心功能，不只是计划或界面截图；尚未完成的部分如实说明即可。

本轮据此将需求规格摘要、架构及数据设计、可运行核心、真实测试结果和剩余问题作为五页正文，未替代或改写单独的 M3/M4 原始 spec。

- 原主线：`3d9d37cb9f35d4ea656a217a55e9a8dafa4ec5a3`。
- 文档分支：`docs/m4-midterm-report`。
- 旧稿保存提交：`7a1da75`，保存 README、报告 v0.1 和证据索引。
- 本轮已执行 `git fetch origin`，获取的主线为 `ffb2657741a535c27cc7d38d6f20d7aede94013a`，包含 PR #22。
- 合入文档分支的提交：`f466a9e`。README 自动合并，无冲突；原始初稿仍可从保存提交读取。
- 本地 main 分支不作阶段验收合并；文档在上述任务分支继续修订，不推送、不创建 PR、不加正式交付 tag。

## 本次内容修订

| 项目 | v0.1 | v0.2 |
| --- | --- | --- |
| 实现基准 | 10 月 19 日主线，实验分支尚未合入 | 10 月 21 日最新主线 ffb2657 |
| 需求与设计 | 功能和架构概述 | 明确 F01–F06 行为、验收依据、共同约束及可编辑架构图 |
| 关系与构建 | 早期失败构建未完成 | 复用已发布 conv-26 完整 Build，272 条 Memory、4,902 条关系 |
| 配置 | 全阶段关闭思考、4096 输出 | 当前默认输出 8192；关系 high、解析 low，其余关闭，历史配置不覆盖 |
| 对照与结果 | 无完整真实问答成绩 | 20 题五策略 100 项、40 题 Recall、10 个动态案例与来源审阅 |
| 阶段范围 | 计划继续原全量基线 | 原 757 题／3,028 项取消；当前展示完成，留出和隐藏评分未评 |
| 报告交付 | Markdown，未核页数 | Markdown、Word、PDF；PDF 含索引共 5 页，逐页预览检查 |

## 来源与统计口径

| 内容 | 依据 | 核对边界 |
| --- | --- | --- |
| 术语与需求 | [CONTEXT](../../CONTEXT.md)、[Issue #4 规格](../../docs/specs/issue-4-m3-m4-dynamic-memory.md)、[ADR 0001](../../docs/adr/0001-memory-architecture.md) | 源规格保留历史正文，当前阶段变更引用 ADR 及执行记录 |
| 数据、范围变更 | [原始数据](../../data/raw/locomo/README.md)、[ADR 0002](../../docs/adr/0002-real-model-baseline-protocol.md)、[范围结案](../../experiments/issue-15-closure/README.md) | 开发、留出、隐藏评分不同；取消原全量不等于完成原验收 |
| 当前功能与模型配置 | [配置代码](../../src/locomo_memory/config.py)、[构建](../../docs/app/building.md)、[问答](../../docs/app/querying.md)、[版本](../../docs/app/versions.md) | 在线两策略与实验五策略分开，原文补查不产生新 Memory |
| 五策略 F1 与 Recall | [分题报告](../../experiments/current-showcase/results/report.md)、[配对机器记录](../../experiments/current-showcase/results/paired-results.json)、[Recall 机器记录](../../experiments/current-showcase/results/recall-results.json) | F1 仅类别 1–4 的 16 题；类别 5 拒答另计；K 计 Memory、覆盖计去重 Source Turn |
| 结果局限与案例 | [展示分析](../../experiments/current-showcase/results/analysis.md)、[动态审阅](../../experiments/current-showcase/results/dynamic-review.md) | 同一开发对话单轮；作者审阅不是独立动态准确率；Dynamic 两题实际触发备用 |
| 构建与调用身份 | [固定计划](../../experiments/current-showcase/plan.json)、[审计](../../experiments/current-showcase/results/final-audit.json) | 本轮展示复用 Build，100 项合法结果不等于提供方每次调用均成功 |
| 测试与浏览器 | [合并前验证](../prs/issue-15-integration.md)、[原始检查 JSON](../prs/issue-15-checks.json)、[浏览器回放](../../experiments/current-showcase/web-recorded/results.json)、[受控浏览器](../../experiments/current-showcase/web-controlled/issue-12-result.json) | 405 passed／4 skipped 为既有回归，24 passed 为展示前相关检查，本轮文档修订未重跑 |
| 真实 MiniLM | [实现总记录](../../experiments/issue-4-implementation.md) | 早期独立 3 passed，不混作本轮生成模型质量结果 |

## 导出与验证

报告源文件使用四处明确分页标记，共五个正文单元，参考索引包含在第 5 页内，无额外封面或附录。A4、正文字号 10.5 pt；输出 PDF 使用嵌入的宋体／黑体，架构图由代码生成 PNG 和 SVG。已查看全部五页预览，未见溢出、乱码、截断或空白页。

[构建脚本](../../scripts/build_m4_report.py)从同一 Markdown 生成 PDF 和可编辑 Word，PDF 页数若不为 5 即报错，保存[机器检查结果](pdf-validation.json)、来源与 PDF SHA-256。Word 分页未独立渲染，用户修改 Word 后需重新导出并核页数；可提交页数依据为已验证 PDF。

文档工具依赖为 Pillow、python-docx、ReportLab 和 PyMuPDF；本机新增工具仅装入本轮临时目录，没有修改全局 Python、应用 pyproject.toml 或 uv.lock。可在独立文档环境安装后运行：

```sh
python scripts/build_m4_report.py --font C:/Windows/Fonts/simsun.ttc --bold-font C:/Windows/Fonts/simhei.ttf
```

其他系统可通过两个参数指定已安装的中文 TrueType 字体；需要支持相应字形。预览图与提取正文由本目录 .gitignore 忽略，可按脚本在本机重建；正式 PDF、Word、架构图及检查 JSON 留档。

本轮只检查文档、来源指标、导出与格式，不调用真实模型、不读取凭据、不重跑业务系统。现有实验结果均引用来源，不宣称在本机新执行。

已从 100 条已保存配对记录重新计算五策略类别 1–4 的均值，并从 40 条检索记录重算初始 RRF Recall，均与报告四舍五入值一致；85 个本地链接目标检查通过，正文含 2,731 个汉字，分为五个正文单元。详见[来源指标校验](source-validation.json)。该检查只读已有结果，不新增模型请求。

以最新主线为基准完成规范与需求双轴 AI 审查，均为 0 项实质发现，见[审查记录](code-review.md)。同时核对源稿和 PDF 的 SHA-256、Git 提交内的 PDF 原始字节与五页检查一致。成员非作者复核仍待进行。

## 复核与交付待办

- [ ] 文档负责人和相关模块负责人核对架构、需求对应和当前功能。
- [ ] 指定非作者成员，记录真实复核意见及修订。
- [ ] 展示环境实际复测，保存本次运行版本、数据和配置。
- [ ] 按最新课程通知准备独立演示文件与过程包；本轮仅完成报告文件。
- [ ] 经授权再推送、创建 PR、合并或正式提交；当前均未执行。

目前未识别明确关联本次 M4 文档的 Notion 记录，本轮没有创建、领取、送审或验收外部任务，不宣称更新了任务状态。若后续流转该任务，负责人应补齐 Notion 关联及 Issue/PR 链接；未标记“完成”。
