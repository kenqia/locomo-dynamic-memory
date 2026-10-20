# locomo-dynamic-memory

软件需求工程课程项目仓库。

## 代码实现准备

- [核心课程课件](docs/sources/0%20-%20Project%20%282026%29.pdf)
- [M3/M4 实现决策与待定项](docs/adr/0001-memory-architecture.md)
- [M3/M4 代码实现 spec](docs/specs/issue-4-m3-m4-dynamic-memory.md)，已发布为 [GitHub Issue #4](https://github.com/kenqia/locomo-dynamic-memory/issues/4)，标签为 `ready-for-agent`
- [真实 DeepSeek 开发集基线评测 spec](docs/specs/issue-15-real-deepseek-baseline.md)，已发布为 [GitHub Issue #15](https://github.com/kenqia/locomo-dynamic-memory/issues/15)，标签为 `ready-for-agent`；开发集计划、完整全文、可恢复评测与失败报告已实现并完成离线验证，真实模型运行待执行
- [真实基线 tickets 与依赖](docs/decisions/real-deepseek-evaluation-interview.md#实现-tickets-发布记录)，对应 GitHub Issues #16–#21；原 T2、T3 已合并为 #17，正文副本位于 `process/tickets/`
- [实现 tickets 原样副本](process/tickets/)，对应 GitHub Issues #5–#12；每张票声明阻塞关系，并建立 GitHub 原生阻塞链接
- [本地 LoCoMo 原始数据与版本校验](data/raw/locomo/README.md)

本地 FastAPI、Streamlit、SQLite 应用已支持来源导入、原子 Memory 抽取、混合检索、历史关系和完整版本问答。启动见 [本地应用运行指南](docs/app/running.md)，抽取、失败重试与来源检查见 [构建指南](docs/app/building.md)。初始混合检索已提供 [候选检查](docs/app/retrieval.md)，[历史关系、状态、扩展与完整版本发布](docs/app/relations.md) 已接入；[有效证据问答](docs/app/querying.md)、[完整版本与导出](docs/app/versions.md) 和 [独立评测与基线比较](docs/app/evaluation.md) 已接入。根据用户转述的教师新说明，开发集为 `conv-26`、`conv-30`、`conv-41`、`conv-42`，最终评分集不公开；本组预先固定本地测试集为 `conv-43`、`conv-44`，系统冻结后再查看其模型成绩。公开 API 与页面可预览开发集全量和五题 smoke 计划，无需完整构建或模型调用。隔离准备、真实预检和全量入口见[真实基线运行指南](docs/app/real-baseline.md)。真实运行仍待落实，见[本次访谈](docs/decisions/real-deepseek-evaluation-interview.md)。spec 的准备标签不代表实现或验收完成。

## 本地启动与验证

在仓库根目录创建独立环境，再分别在两个终端启动后端与页面：

```sh
uv sync --locked
uv run --locked uvicorn locomo_memory.api:create_app --factory --host 127.0.0.1 --port 8000
uv run --locked streamlit run src/locomo_memory/ui.py --server.address 127.0.0.1
```

`uv sync --locked` 不包含本地 Embedding 模型运行依赖。构建索引前，运行
`uv sync --locked --extra embedding` 并准备固定 revision 的 MiniLM 本地缓存；
真实生成还需要进程环境中的 `DEEPSEEK_API_KEY`。配置文件不接受凭据。
详细步骤见[运行指南](docs/app/running.md)。
CI、夹具回归、独立浏览器环境和失败诊断见[检查指南](docs/app/checking.md)。

生成输出上限 `model_max_tokens` 默认 8192 tokens；可用 `relation_max_tokens` 单独覆盖关系阶段。
默认关系判断使用 `high` 思考、有效证据解析使用 `low`，抽取、查询分析和答案生成关闭思考。
字段、回滚和版本规则见[分阶段配置](docs/app/building.md#分阶段思考配置)；已有构建保留原配置快照。

```sh
uv run --locked pytest -q
LOCOMO_LOCAL_EMBEDDING=1 HF_HUB_OFFLINE=1 uv run --locked --extra embedding pytest -m local_embedding -q
```

默认测试不调用付费服务。`local_embedding` 检查真实缓存模型；`live_model`
需要显式设置 `LOCOMO_LIVE_MODEL=1` 和受保护凭据，才运行真实 DeepSeek 调用。
真实浏览器、受控外部适配器和未执行项分别记录在
[本地集成验证](experiments/issue-12-integration-validation.md)。

## 目录

| 目录 | 预计内容 |
| --- | --- |
| `docs/sources/` | 经确认可共享的课程原始材料、来源说明 |
| `docs/requirements/` | 审阅后的 Team Workflow、Vision & Scope，后续需求规格 |
| `docs/specs/` | skills 生成并成功发布到 GitHub Issues 的 spec 正文副本 |
| `docs/design/` | 后续模块设计、接口约定、数据结构和实现方案 |
| `docs/decisions/` | 团队协作、工作流程和项目范围等决定的背景、理由及待确认项 |
| `docs/agents/` | Agent 的项目约定，包括 Issue tracker、标签、领域文档和本地 skills 使用说明 |
| `.agents/` | 仓库内置的 Agent 资源；`skills/` 保存 workflow skills 及其依赖 |
| `process/tickets/` | skills 生成并成功发布到 GitHub Issues 的 ticket 正文副本，每个 ticket 单独保存 |
| `process/meetings/` | 会议纪要模板、真实会议记录及经检查的截图 |
| `process/snapshots/` | Notion 阶段任务快照、阶段复盘和提交记录 |
| `presentations/` | 审阅后的汇报源文件与导出 PDF |
| `src/` | FastAPI、Streamlit 与记忆构建、检索、问答、评测模块 |
| `tests/` | 公开 API 行为测试与本地浏览器 smoke |
| `experiments/` | 分票实验记录、集成验证与非敏感截图 |

`docs/decisions/` 记录为什么作出某项决定，`docs/design/` 说明具体如何设计。两者可以通过链接关联，同一份决策正文只保留在一个位置。架构与领域决策按现有 Agent 约定存入 `docs/adr/`，在首次需要时创建。

空目录用 `.gitkeep` 保留。spec 和 ticket 正文副本原样复制，不做润色。

## 材料

预计材料见 `docs/upload-plan.md`。

- Notion 保存实时任务状态；仓库只保存注明导出时间的阶段快照。

## M1 Team Workflow

- [Markdown 源稿](docs/requirements/team-workflow.md)
- [可编辑 Word](docs/requirements/team-workflow.docx)
- [PDF](docs/requirements/team-workflow.pdf)

M1 源稿修改后运行 `python scripts/build_m1_report.py` 重建 Word，PDF 使用 LibreOffice 导出。

## M2 项目提案

本轮制作中文报告和过程材料，暂不制作汇报文件。宏观方案由组长确认全组接受；当前文件属于本地制作版本，成员非作者复核、远端同步与正式提交按真实进度另行完成。

- [Markdown 源稿](docs/requirements/vision-and-scope.md)
- [可编辑 Word](docs/requirements/vision-and-scope.docx)
- [报告 PDF](docs/requirements/vision-and-scope.pdf)
- [方案确认记录](docs/decisions/m2-proposal-interview.md)
- [过程材料说明](process/m2-process-index.md)
- [过程材料离线阅读页](process/m2/index.html)
- [仓库与 ZIP 文件清单](process/m2/file-manifest.csv)
- [本地制作与打包验证](process/m2/validation-record.md)
- [报告与图示制作脚本](scripts/build_m2_report.py)

报告内两张简化图的 PNG 与可编辑 SVG 位于 `docs/requirements/assets/m2/`。过程材料、阅读页、文件清单与校验值全部在仓库留档，再通过 `python scripts/package_m2_materials.py` 整合为 ZIP；包内保留仓库路径和原始内容。报告 Word/PDF 独立提供，交付文件存放于 `deliverables/m2/`。

修改源稿后可运行 `python scripts/build_m2_report.py` 重建 Word 和图示，所需环境及 PDF 渲染方式见验证记录。当前分支 `codex/m2-proposal-materials` 用于本轮留档，正式合并、推送和提交仍按复核及授权执行。

M2 联网调研依据见 [现实系统与基准调研](docs/sources/m2-real-world-memory-research.md)。报告采用一手资料修订问题、可行性与评测边界；调研前快照保存在 `process/m2/iterations/vision-and-scope-before-research.md`。两者均进入过程 ZIP，不代表已运行系统实验。

## 过程材料同步与打包

修改任务快照或成员反馈后，运行 `python scripts/build_process_documents.py` 重建对应 Word，再使用 LibreOffice 导出同名 PDF。执行 `python scripts/package_m1_materials.py` 与 `python scripts/package_m2_materials.py` 重建两个过程包。

包内包含检查结果、文件清单和 SHA-256。版本记录仅保存演进，当前哈希由脚本生成；M1 另附独立报告校验。新任务快照不覆盖历史 CSV，成员反馈表只记录真实结果。
