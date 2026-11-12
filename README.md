# LoCoMo Dynamic Memory

[![Checks](https://github.com/kenqia/locomo-dynamic-memory/actions/workflows/checks.yml/badge.svg?branch=main)](https://github.com/kenqia/locomo-dynamic-memory/actions/workflows/checks.yml)

面向长期对话的动态记忆系统。系统从对话中提取带时间与来源的 Memory，保留状态变化，并为问答结果提供可检查的引用和执行记录。

项目包含 FastAPI 后端、Streamlit Research Console，以及基于 LoCoMo 的检索与动态记忆对照实验。课程交付材料见 [M5 提交目录](deliverables/M5_Final_Submission/README.md)。

## 快速体验

推荐先运行 Research Console 的离线合成演示。环境为 Python 3.12 和 uv，以下命令可在 Windows、Linux 或 WSL 中执行：

```sh
git clone https://github.com/kenqia/locomo-dynamic-memory.git
cd locomo-dynamic-memory
uv sync --locked --python 3.12
uv run --locked python tools/team_v2/demo.py replay --ui-port 18501
```

打开 **http://127.0.0.1:18501**。首次安装依赖需要网络；依赖就绪后，演示读取本地冻结案例，模型调用次数为 0，启动时无需 API Key。

页面依次为 Overview、Memory、Query、Experiments 和 Demo。在 Memory 查看 Alex 从 Paris 搬到 Rome 的记录，点击来源核对 Source Turn；进入 Query 切换当前与历史问题，再展开 Trace 查看证据处理过程。六类合成案例还覆盖冲突、计划状态及失败情形。

Query 标注为 **OFFLINE SYNTHETIC REPLAY**，回答来自冻结案例。Experiments 展示早期 757 题实验，最终留出实验通过下方报告单独查阅。详细操作见 [Console 指南](docs/team-v2/README.md)。

## 系统功能

| 模块 | 主要能力 |
| --- | --- |
| Build 与 Memory | 导入对话并抽取结构化记忆，按完整构建版本保存来源、索引和状态投影。 |
| 时间与状态 | 记录 RETAIN、UPDATE、SUPERSEDE 和 CONFLICT 关系，分别处理当前状态与历史问题。 |
| Query 与 Evidence | 结合 BM25、Dense 和 RRF 召回候选，按所选策略生成回答及来源引用。 |
| Trace 与实验对照 | 检查召回、证据选择和回答记录，浏览冻结实验并导出 JSON。 |

公共问答默认使用 **Hybrid**（`hybrid_no_resolution`）。显式选择 `dynamic` 可执行有效证据解析，`dynamic_raw_fallback` 提供原文补充路径。默认选择和回滚方式见 [策略说明](docs/release/DEFAULTS_AND_ROLLBACK.md)。

Temporal/Event Sidecar 已作为独立离线诊断工具合入，开关默认关闭。它与生产问答路径分离，采用范围和限制见 [Sidecar 交付说明](docs/release/SIDECAR_FREEZE.md)。

## 启动正常应用

Linux 或 WSL 可使用统一启动器，同时启动后端与前端：

```sh
uv sync --locked --python 3.12
scripts/personal-release doctor
scripts/personal-release start
```

| 服务 | 地址 |
| --- | --- |
| Research Console | http://127.0.0.1:8501 |
| FastAPI 与接口文档 | http://127.0.0.1:8000/docs |

Console 读取已有 Build 和 Trace，顶部可切换到上传、构建、问答和评测的五阶段工作流。统一启动器使用独立的 `var/personal-app/memory.sqlite3`；自选配置和端口设置见 [运行手册](docs/release/RUNBOOK.md)。

也可在两个终端分别启动，适用于希望单独管理服务的场景；这组入口默认使用 `var/memory.sqlite3`：

```sh
uv run --locked uvicorn locomo_memory.api:create_app --factory --host 127.0.0.1 --port 8000
uv run --locked streamlit run src/locomo_memory/console_ui.py --server.address 127.0.0.1 --server.port 8501
```

真实构建需要本地 Embedding 依赖与模型缓存：

```sh
uv sync --locked --python 3.12 --extra embedding
```

项目固定使用 `sentence-transformers/all-MiniLM-L6-v2`，revision 为 `c9745ed1d9f207416be6d2e6f8de32d1f16199bf`。模型缓存和生成服务准备方式见 [应用配置](docs/app/running.md) 与 [凭据说明](docs/agents/local-credentials.md)。启动应用本身只启动服务；实际构建、生成问答或新增评测可能产生模型费用，应使用自己的配置并确认预算。

可用 [合成输入](tests/browser/sample.json) 检查导入格式。MemoryExport 是构建结果，其结构见 [导出 Schema](memory-export-schema.json)，应与原始对话导入文件区分使用。

## 实验结论

项目分别记录历史 757 题开发实验和最终 400 题留出实验。历史实验共计划 3,028 个题目与策略组合；Console 的 Experiments 页面展示这一阶段的冻结结果。

最终留出实验每个策略计划 400 题，其中事实类别 1–4 共 301 题。以下 token F1 按这 301 题的完整分母统计，运行失败记为 0：

| 策略 | 事实类别 token F1 | 400 题运行成功数 |
| --- | ---: | ---: |
| Hybrid | 0.402606 | 394 / 400 |
| Dynamic | 0.409151 | 389 / 400 |

Dynamic 相对 Hybrid 的配对差为 +0.006545，95% bootstrap 区间为 `[-0.020133, 0.034035]`。区间跨零，当前评测尚未观察到稳定的质量优势，公共问答因此沿用 Hybrid 默认策略。

实验配置、费用口径及失败分类见 [实验摘要](PERSONAL_EXPERIMENT_SUMMARY.md)；[完整实验索引](EXPERIMENT_ARCHIVE_INDEX.md)保留各阶段记录，后续边界回归与冻结留出成绩分别报告。

## 交付材料与文档

| 入口 | 内容 |
| --- | --- |
| [M5 提交目录](deliverables/M5_Final_Submission/README.md) | 5 页课程报告、10 页汇报、演示视频、过程材料和源码快照。 |
| [技术报告](deliverables/M5_Final_Submission/01_Report/Final_Technical_Report.pdf) | PDF 主报告，同目录提供 DOCX 与 Markdown；完整报告和研究附录位于 Full_Report。 |
| [汇报 PPTX](deliverables/M5_Final_Submission/02_Presentation/Final_Presentation.pptx) · [PDF](deliverables/M5_Final_Submission/02_Presentation/Final_Presentation.pdf) | 可编辑汇报、演讲备注和答辩 Q&A。 |
| [演示视频与字幕](deliverables/M5_Final_Submission/03_Demo/) | 4 分 51 秒 Web UI 操作演示、中文配音、字幕及脚本。 |
| [完整提交包](deliverables/m5-final/m5-final.zip) · [SHA-256](deliverables/m5-final/m5-final.zip.sha256) | 解压后顶层目录为 M5_Final_Submission，包内清单用于逐项校验。 |
| [复现指南](deliverables/M5_Final_Submission/05_Reproduction/REPRODUCE.md) | 源码快照、环境准备与验证步骤。 |
| [运行手册](docs/release/RUNBOOK.md) · [应用文档](docs/app/running.md) | 启动、数据导入、接口与故障恢复。 |
| [研究附录](docs/supplement/supplement.pdf) · [重建源码](docs/supplement/supplement.md) | 实验过程、失败分析及补充研究。 |
| [周会摘要](process/meetings/weekly-summary-index.md) · [架构决策](docs/adr/) | 阶段安排、讨论记录及技术取舍。 |
| [Product 冻结记录](docs/release/PRODUCT_FREEZE.md) · [发布清单](RELEASE_MANIFEST.md) | 产品复核与版本身份；M5 交付文件以本节提交目录为入口。 |

## 开发验证与数据范围

Linux 或 WSL 中可运行公开离线回归：

```sh
uv sync --locked --python 3.12
scripts/personal-release run-tests --public
```

该入口排除需要受控数据、真实模型或本地 Embedding 的测试。验证范围及完整工作树的检查方式见 [运行手册](docs/release/RUNBOOK.md)。

离线演示使用合成数据。公开交付包按清单分发，六份真实 MemoryExport 通过获准的受控渠道另行交接；密钥、活动数据库和受控原文应保留在公开仓库之外。交接及课程提交状态集中记录在 [Delivery 任务](https://github.com/kenqia/locomo-dynamic-memory/issues/25)。
