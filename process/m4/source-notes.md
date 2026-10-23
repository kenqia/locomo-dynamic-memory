# M4 来源与统计口径

本文只索引依据；版本变化见[修订记录](draft-evidence.md)，文件检查见[验证说明](validation-record.md)。来源优先采用已确认课程说明、现行 ADR、实际实现和保存的执行记录；历史 spec 保留当时范围。

| 内容 | 原始依据 | 使用口径 |
| --- | --- | --- |
| 需求与设计 | [需求文档](../../docs/requirements/software-requirements-specification.md)、[CONTEXT](../../CONTEXT.md)、[ADR 0001](../../docs/adr/0001-memory-architecture.md)、[Issue #4 规格](../../docs/specs/issue-4-m3-m4-dynamic-memory.md) | 引用需求与设计，不改写 M3 原件 |
| 数据、配置与版本 | [原始数据](../../data/raw/locomo/README.md)、[固定计划](../../experiments/current-showcase/plan.json)、[配置代码](../../src/locomo_memory/config.py)、[ADR 0002](../../docs/adr/0002-real-model-baseline-protocol.md) | 以固定 Build、题单、配置和实现指纹标识展示 |
| 问答成绩与查询用量 | [分题报告](../../experiments/current-showcase/results/report.md)、[配对机器记录](../../experiments/current-showcase/results/paired-results.json) | conv-26 开发对话，20 题五策略共 100 项；F1 汇总类别 1–4 的 16 题，类别 5 的 4 题拒答另列 |
| 证据检索 | [Recall 机器记录](../../experiments/current-showcase/results/recall-results.json) | 40 题；K 计初始 Memory 排名，覆盖计映射后去重 Source Turn，逐题计算后平均 |
| 动态案例与来源审阅 | [动态记录](../../experiments/current-showcase/results/dynamic-review.json)、[原文证据包](../../experiments/current-showcase/results/dynamic-packets.json)、[回答来源审阅](../../experiments/current-showcase/results/answer-source-review.json)、[展示分析](../../experiments/current-showcase/results/analysis.md) | 作者审阅保留失败及异议，尚未独立复核；真实 Build 无 SUPERSEDE／CONFLICT |
| 页面表现 | [真实 Trace 回放](../../experiments/current-showcase/web-recorded/results.json)、[受控浏览器](../../experiments/current-showcase/web-controlled/issue-12-result.json)、[案例原图](../../experiments/current-showcase/web-recorded/history-and-effective-memory.png) | 前者读取保存结果，后者使用受控模型检查边界；截图原件不改，文档仅裁切显示 |
| 工程与 MiniLM 检查 | [合并前验证](../prs/issue-15-integration.md)、[检查 JSON](../prs/issue-15-checks.json)、[早期实现记录](../../experiments/issue-4-implementation.md) | 405 passed／4 skipped、展示前 24 passed、早期 MiniLM 3 passed 均沿用原执行范围 |
| 调用身份及历史范围 | [最终审计](../../experiments/current-showcase/results/final-audit.json)、[范围结案](../../experiments/issue-15-closure/README.md) | 原始失败、重试和范围变化留档，不把旧计划当本轮成果 |
| 运行与接口 | [运行指南](../../docs/app/running.md)、[构建](../../docs/app/building.md)、[问答](../../docs/app/querying.md)、[版本](../../docs/app/versions.md) | 在线两策略与实验五策略分开；原文补查不产生新 Memory |

token 采用各策略 usage_summary 的全部已保存查询尝试，包含失败、重试和查询各阶段，不含复用 Build 的构建、额外 Recall 或动态案例调用。Dynamic 两题实际触发备用路径，按请求策略汇总并保留实际执行策略。

开发对话为 conv-26/30/41/42，本地留出为 conv-43/44；当前单轮展示仅用 conv-26，不能代表跨对话、留出集或教师隐藏评分。此轮过程整理不新增系统实验。
