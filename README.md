> 此分支是从main导入公开allowlist tar的安全快照，未导入个人研究分支历史。新发布身份、当前验收及main保留材料边界见[安全快照发布记录](SAFE_PUBLIC_SNAPSHOT.md)。下述运行命令适用于本快照。

2026-11-09：[证据损失诊断与边界回归](experiments/evidence-flow-20261109/README.md)已增加 20 案冻结证据包、查询时间范围修复和默认关闭的新 Build 上下文窗口；[实验汇总 PDF](docs/supplement/supplement.pdf)同步更新。此前免费诊断没有新增模型调用；后续实测另列如下，Level E 原结论保持不变。

2026-11-09 后续[真实模型回归](experiments/live-boundary-20261109/README.md)完成：62 次请求，12 道已曝光题中普通题 F1 0.517381→0.456314，没有整体收益证据。六组实体探针有局部抽取恢复，但引用仍不完整；AI 审阅存在漏检，已收到莫远序（2026-11-09）提交的18对[人工核查意见](experiments/live-boundary-20261109/HUMAN_REVIEW.md)。E25 冻结成绩不变。


# LoCoMo Dynamic Memory

M5 个人核心与 Product Research Console 整合版。课程截止：2026-11-09 24:00（北京时间）。
当前冻结实验与工程验收分开记录，最新状态见 [Release清单](RELEASE_MANIFEST.md)。
这不是团队最终报告、PPTX、MP4或课程平台提交。

## 从零开始

需要 Linux/WSL、Python 3.12、uv。在仓库或公开代码包根目录执行：

```sh
uv sync --locked --python 3.12
scripts/personal-release doctor
scripts/personal-release replay-offline-demo
```

打开 `http://127.0.0.1:18510`；只读API为 `http://127.0.0.1:18010/docs`。
这条路径无须key、本地embedding、互联网或研究SQLite，不创建Build/Resolve/Answer。
页面明确区分 Synthetic / Offline Replay 和 Real Experimental Result。
按顺序选择Build、Memory、历史/关系、Graph、Source Turn、预录问题与引用、Trace、评测对照，再下载JSON。
Graph和分组checkbox默认关闭；失败Trace可直接选择演练。

`Ctrl+C` 或向启动器发送 SIGTERM 会停止两个自有进程组。端口占用/启动失败以非零退出，保留诊断目录；数据库不删除。
端口可用 `--api-port 18020 --ui-port 18520` 修改。UI、API均只绑定127.0.0.1。

## 正常应用

```sh
scripts/personal-release start
```

后端 `http://127.0.0.1:8000`，页面 `http://127.0.0.1:8501`。
正常启动默认进入 Research Console：Overview → Memory → Query/Evidence → Experiments → Demo。
Console 只读已有 Build、Memory、Trace 和冻结实验；切换顶部“五阶段工作流”可进入上传、构建、问答与评测。
公共问答及原工作流仍默认使用 Hybrid；Console 不会自动生成回答或修改 Build。
统一启动器默认使用新的 `var/personal-app/memory.sqlite3`，不会指向研究数据库。
`--config /absolute/path/to/local.toml` 读取自选配置，启动时仅新建快照，不改配置原件。
正常应用启动本身不调用模型；点击真实Build/问答/评测可能收费，需要用户自己的授权和Provider配置。本次Release验收未调用真实付费模型。

也保留原入口，分别在两个终端执行（此方式默认数据库是 `var/memory.sqlite3`）：

```sh
uv run --locked uvicorn locomo_memory.api:create_app --factory --host 127.0.0.1 --port 8000
uv run --locked streamlit run src/locomo_memory/ui.py --server.address 127.0.0.1
curl --fail http://127.0.0.1:8000/health
curl --fail http://127.0.0.1:8501/_stcore/health
```

本地Dense构建需额外安装锁定依赖 `uv sync --locked --extra embedding`，并事先合法取得固定MiniLM缓存。
模型 `sentence-transformers/all-MiniLM-L6-v2`，revision `c9745ed1d9f207416be6d2e6f8de32d1f16199bf`，384维、256tokens、local_files_only=true。
`doctor`报告包/缓存是否具备；不会下载模型或读取凭据。无缓存时使用只读Replay；不要把合成Embedding当真实索引。
DeepSeek官方Provider是可选项；认证发现遵循 [本地凭据说明](docs/agents/local-credentials.md)，不把key写进TOML或仓库。

页面流程：上传许可允许的LoCoMo格式数据 → 选择对话 → 抽取 → Index → 关系/Projection → 发布完整Build → Memory/Source检查 → 问答 → 引用Source Turn/Trace → JSON导出。
全流程见 [运行/数据入口](docs/release/RUNBOOK.md)，原有接口和数据模型见 [应用文档](docs/app/running.md) 与 [JSON Schema](memory-export-schema.json)。
公开包不附LoCoMo原文/QA/Gold；“导入官方”在缺原件时明确失败，可上传合成或合法受控文件。请勿把MemoryExport上传到LoCoMo原始conversation导入入口。

## Product 离线演示

下面的独立演示展示 Console 的六类合成案例、来源跳转、历史 Build、Trace 与真实冻结实验比较，不启动 API 或数据库：

```sh
uv run --locked python tools/team_v2/demo.py replay
```

打开 `http://127.0.0.1:18501`。合成 Replay 与真实冻结成绩分别标识；没有发布新的模型成绩。
原有 `scripts/personal-release replay-offline-demo` 继续提供独立 MemoryExport/Graph 查看器。
使用方法、来源版本与整合验证见 [Product 指南](docs/team-v2/README.md)。

## 默认策略与回滚

Release页面和公共 `POST /queries` 默认 **hybrid_no_resolution**；内部历史 `QueryRequest` 的Dynamic默认保持，用于旧工具复现。
Hybrid复用已有QA评测基线：BM25+Dense+RRF、历史扩展、Answer；它不执行Dynamic Resolution，也不把回答上下文称为有效Memory真值。
显式 `strategy=dynamic` 启用有效证据解析；`dynamic_raw_fallback` 是已有可选原文兜底。
Graph两跳检索、compression wire、adaptive、temporal soft priority均不进入默认路径；Graph浏览为只读显式入口。
[默认变更与回滚](docs/release/DEFAULTS_AND_ROLLBACK.md)记录实现、日期修复、测试和身份边界。

## 导出与免费验证

```sh
scripts/personal-release run-tests           # 合法含原件的工作树全仓
scripts/personal-release run-tests --public  # 无受控原文的公开包
scripts/personal-release validate-six-exports --directory /absolute/path/to/controlled/memory-exports
scripts/personal-release verify-public-evidence --manifest public-evidence-manifest.json --directory .
scripts/personal-release verify-private-archive --manifest /absolute/path/to/private-archive-manifest.json --directory /absolute/path/to/archive
```

六份真实JSON的 [清单](six-memory-exports-manifest.json) 公开；原件仅在本地受控区。
验真后可用同一只读页面查看，API与页面共用相同Catalog：

```sh
scripts/personal-release replay-offline-demo --manifest six-memory-exports-manifest.json --directory /absolute/path/to/controlled/memory-exports
```

该模式没有预录问答时只展示真实Memory/关系，不创建新答案。目录必须显式指定，SHA、Build、来源、时间、索引和Projection不一致即拒绝。
课程许可/受控渠道尚须负责人确认；不要把完整六份JSON或整个var上传公开仓库。

## 实验、交付与团队接入

- [个人实验摘要](PERSONAL_EXPERIMENT_SUMMARY.md)：历史757题、开发100题两版、留出400题严格分开；E类1–4 H=.402606/D=.409151，差值区间跨零。
- [37页研究附录](docs/supplement/supplement.pdf)、[重建源码](docs/supplement/supplement.md)、[勘误和构建验证](docs/release/SUPPLEMENT_ERRATA.md)。附录独立于团队总报告。
- [组件与Bonus矩阵](RELEASE_COMPONENT_MATRIX.md)、[完整实验索引](EXPERIMENT_ARCHIVE_INDEX.md)、[代码血缘](RELEASE_CODE_LINEAGE.md)。
- [个人交付staging](deliverables/m5-personal-candidate/README.md)、[新鲜验收](docs/release/ACCEPTANCE.md)、[对抗性审查](docs/release/ADVERSARIAL_REVIEW.md)。
- [团队接入契约](TEAM_INTEGRATION_HANDOFF.md)、[本地归档及仅拟删除清单](LOCAL_ARCHIVE_AND_CLEANUP_PLAN.md)。

公开包验收命令/受控数据测试排除边界见RUNBOOK。禁止重新执行历史一次性付费runner、复用旧预算、用已曝光E调参后再次声称独立验证。
