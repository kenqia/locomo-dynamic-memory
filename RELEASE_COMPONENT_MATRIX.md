# 组件、入口及采用矩阵

源码默认根为src/locomo_memory；逐文件来源commit/SHA见RELEASE_COMMIT_MAP.json。依赖来自uv.lock，未新增生产依赖。真实数据仅受控；Synthetic只验工程边界。新鲜测试结果见docs/release/ACCEPTANCE，不把历史664/198等计入本次。

| 组件/源码 | API/页面入口 | 输入→输出、依赖 | 默认/最终系统 | 验证、实验及局限 |
|---|---|---|---|---|
| 数据导入 imports.py、schemas.py | /imports、/imports/file；上传页 | LoCoMo conversation→SQLite SourceTurn；Pydantic/SQLite | 核心启用 | test_imports；QA/标注隔离；原文合法性由用户负责 |
| Source Turn | /datasets/{ds}/conversations/{sid}/turns/{dia} | ds/sample/dia→原轮次/报告时刻 | 核心启用 | 错ID404、跨对话隔离；不是事件时间 |
| Atomic Extraction builds.py、memory_schemas.py | POST /builds；构建页 | fragments→Memory原子事实/来源/时间；DeepSeek | 核心显式收费 | test_builds/extraction/contract；失败保留，不保证事实全覆盖 |
| Build/Index/Version builds.py、versions.py | /builds/{id}、/index、/publish；版本页 | 片段→完整Build/索引/原子切换；SQLite | 核心启用 | test_versions/build_progress/recovery；失败版本不可QA |
| BM25+Dense+RRF retrieval.py、embeddings.py | /candidate-queries；候选面板 | 英文Question→Memory排序；rank-bm25/固定MiniLM/NumPy | Hybrid及Dynamic默认基础 | test_retrieval/local_embedding；384维、固定revision、长输入拒绝；不等于事实Recall |
| Query Analysis retrieval_schemas.py | 随候选调用 | Question→实体/词/时间条件；可选DeepSeek | 核心启用，失败保留原问题 | test_retrieval；分析不硬过滤全部历史 |
| MemoryRelation relations.py、relation_schemas.py | /builds/{id}/relations | 新旧Memory+sources→RETAIN/UPDATE/SUPERSEDE/CONFLICT/undetermined | 核心显式构建 | test_relations/relation_selection；无SUPERSEDE/CONFLICT真值覆盖的60单位AI诊断不能外推四标签准确率 |
| CurrentState projection.py | /builds/{id}/current-state | 同Build历史/关系→当前/历史/事件/计划/冲突投影 | 核心启用 | test_relations/versions；可重算投影不是新事实来源 |
| 历史扩展 expansion.py | /expansions；候选扩展页 | initial Query ID+date→有界历史集合 | 核心一跳/同键启用 | test_relations/queries；总上限60，未抽取事实无法恢复 |
| Dynamic Resolution queries.py | POST /queries strategy=dynamic | 固定Build/问题/日期→有效集合/理由/补判 | 显式可选 | test_queries/dynamic_resolution_budget；长输入可明确失败；E未证稳定QA收益 |
| Answer+Citation queries.py、query_schemas.py | POST /queries；问答页 | 交付证据→answer/explanation/citations；DeepSeek | Hybrid默认，Dynamic可选 | answer contract/raw/focused tests；合法ID不等于语义支持 |
| Hybrid默认 release_queries.py、query_api.py | POST /queries省略strategy；问答页 | 复用Evaluation基线检索扩展→Answer，无resolve | Release默认 | tests/release：默认无resolve、日期优先、失败Trace；当前修复无新泛化分数 |
| QueryTrace queries.py、query_ui.py | GET /queries/{trace_id} | 成功/失败/配置/用量/证据→持久Trace | 核心启用 | 失败source、错误scope、budget审计；不得把失败当无证据 |
| Evaluation evaluation*.py | /evaluation-plans、/evaluation-runs；评测页 | 固定输入/策略→Run/逐题分母/指标/报告 | 读取启用，新生成显式收费 | test_evaluation/plans/reports；缺动态人工真值，类别5单列 |
| MemoryExport v2 exports.py、export_schemas.py | /builds/{id}/export | 同一complete Build→严格JSON | 核心启用 | schema/typed roundtrip/六导出SHA；不含Dense向量/完整conversation |
| FastAPI api.py | README uvicorn；/health、/docs | HTTP契约→隔离service/错误码 | 核心启用 | API tests/正常启动/合成Browser；启动lifespan可能恢复自选DB未完成任务，不可指向研究原库 |
| Streamlit ui.py、*_ui.py | README streamlit；8501 | HTTP-only→导入/Build/Memory/QA/Trace/Export/评测 | 核心启用 | AppTest/Chromium全流程；当前只支持英文检索 |
| Bonus A：冲突/多版本/时间线 m5_api.py、m5_ui.py | /bonus/timeline；版本/来源面板 | entity/dimension→历史、来源和适用关系 | 既有基础保留、只读展示可选 | test_m5_api/review+原关系测试；新面板QA收益未测 |
| Bonus B：Graph浏览 m5_graph.py | /bonus/graph；Graph checkbox | 固定Build/Memory→有界来源图 | 展示可选默认不打开 | API/Browser/release读取器；结构归属边不是语义推理 |
| Bonus B：两跳 m5_graph.py、m5_queries.py | /bonus/graph-expand、显式研究工具 | roots/budgets→depth2 paths/candidates→可接resolve | 默认关闭，不入默认QA | test_m5_graph_compression/queries；757回放444题有新增两跳，最终交付无增益；新QA未测 |
| Bonus C：可逆分组 m5_compression.py | /bonus/compression；Replay checkbox | 完整Memory→package→exact expand | 默认关闭、保留可逆展示 | roundtrip/API/replay；文件包4.1666%不是QA降本 |
| Bonus C：wire m5_wire_compression.py | tools/m5显式实验 | grouping payload→wire与budget记录 | 默认关闭 | test_m5_wire_compression；757完整messages省.02925%代理tokens；模型解码/账单收益未测 |
| Bonus D：Adaptive m5_adaptive.py | tools/m5显式研究 | Question+候选→可复现路由/扩展 | 默认关闭 | test_m5_adaptive；交付Source代理-.029349；拒绝默认采用 |
| Bonus D：Temporal soft priority m5_adaptive.py、temporal.py | 显式研究工具 | 单日/相对/未知区间→软优先 | 新机制默认关，原时间能力保留 | synthetic/时间回归；757总体无新增代理收益；复杂时间准确率未测 |
| 独立只读Viewer release_viewer.py、replay_ui.py | /replay挂载或独立18010/18510 | SHA清单+JSON→Memory/状态/Graph/Source/Replay/下载 | 免费演示入口 | tests/release/API/Chromium、六真导出同loader；无生成/SQLite/联网 |
| Hindsight/CE/PropMem | 历史研究档案与tools，EXPERIMENT_ARCHIVE_INDEX | 隔离合成/来源审计/离线重排 | 不进入App | Hindsight后端不完整；CE来源代理无显著提升；PropMem固定配置拒绝，无真实canary |

## 数据与实验采用说明

六真实Build：conv26/30/41/42来自完整四开发构建，conv43来自获批关系完成及完整发布副本，conv44来自successor/relation-successor完整副本；各SHA/指纹/数量见six-memory-exports-manifest.json。源码原件与身份沿Git祖先保留，不用Release修复伪装旧producer。

实验层级：A工程/合成、B757离线来源/packing（无新生成）、C两轮开发各100双臂、E留出400双臂；D、新Bonus QA、组合B5/B6未运行。Bonus“已实现/已测试/可演示/实验证明有益/可默认采用”是五个不同状态。当前可默认采用的结论不包含未测量语义收益。
