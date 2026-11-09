# Graph Memory 与只读多跳

从严格校验的 memory-export-v2 派生图。无需图数据库、SQLite schema 迁移或新 Python 依赖。Streamlit 现有 graphviz_chart 接受 DOT 字符串并在客户端渲染，不依赖 Python graphviz 包；实际安装版本记录在 environment-lock-application.json。

节点为 Entity、Memory、Source Turn。HAS_MEMORY 来自 entity_id，SUPPORTED_BY 来自 source_ids，均标注构造依据。MemoryRelation 边保留 relation ID、标签、适用时间/条件和来源。没有根据相似度创建事件同一性、因果或人物关系。

GET /builds/{build_id}/bonus/graph 先返回实体元数据。传 root=entity:Caroline 与 depth=1|2 后返回有界邻域。at=YYYY-MM-DD 只排除明确 valid interval 不适用的 Memory，未知日期保留。max_nodes 默认150，上限500，截断显式显示。灰色表示历史、红色表示冲突；节点详情保留原投影状态值。

图浏览与多跳检索分别验收。expand_relations 仅沿已存且非 undetermined 的 MemoryRelation 双向 BFS，深度默认0、上限3。新增 Memory 记录逐边路径和适用条件。图连通不意味着证据正确或满足当前问题。

研究入口 m5_queries.query(base, request, graph_depth=2) 复用生产 Hybrid、历史扩展、完整解析预算、回答与引用校验。只在显式调用时执行。最大候选默认60，完整 Memory JSON 的正则代理预算默认24,000；初始候选超限直接失败，不静默删除原证据。生产 Resolution 还会对包括来源、关系、提示和 schema 的完整请求做预算拒绝。

Graph API/UI 不调用模型，不修改 Memory/Relation/Projection，不跨对话或 Build。检索 Trace 写入调用者指定的独立实验数据库。关闭研究入口后走原 QueryService。

当前无 Chrome DevTools MCP，采用项目既有隔离 Playwright Chromium 完成真实 HTTP、DOM、截图和控制台检查。回滚只需关闭图浏览、停止调用研究入口，无需迁移数据或重建旧 Build。

真实开发图的密集边会阻塞浏览器布局。画布和边表限制为前300条，界面明确标注；完整有界邻域仍保留在JSON下载中。该展示限制不作用于Graph检索或关系存储。
