# Demo Shot List（逐镜头操作清单）

分辨率 1920×1080，30 fps；浏览器缩放 100%，隐藏书签栏；系统鼠标高亮/放大开启（OBS 插件或系统设置）。
每镜头保留**连续操作**，只允许在镜头之间切换；不得用静态截图替代镜头。

| # | 时间 | 画面 / 窗口 | 操作（逐步） | 必须可见 | 角标 |
|---|---|---|---|---|---|
| S01 | 00:00–00:05 | 标题卡 | — | 项目名、组名、M5 Final、日期 | — |
| S02 | 00:05–00:25 | 终端 | 1. `git rev-parse --short HEAD`（显示 5519dd2）2. 输入 `uv run --locked python tools/team_v2/demo.py replay` 3. 等出现 URL | SHA、命令、URL；**不出现** key、`.env`、家目录用户名以外的隐私 | OFFLINE SYNTHETIC REPLAY |
| S03 | 00:25–00:40 | 浏览器 | 1. 打开 `127.0.0.1:18501` 2. Overview 加载完 3. 鼠标依次停在三个状态标签 | "合成回放"、对话、当前版本 | 同上 |
| S04 | 00:40–00:55 | 浏览器 | 1. 展开"数据与版本 · 更换所选记录" 2. 展开"版本身份"JSON 3. 收起 | build_id、fingerprint、status=complete | 同上 |
| S05 | 00:55–01:15 | Memory 页 | 1. 点顶部 Memory 2. 点 "Alex lives in Paris." 3. 点 "Alex lives in Rome." 4. 停在"这条记忆的关系与冲突"（SUPERSEDE） | 两条住所记忆、SUPERSEDE 关系 | 同上 |
| S06 | 01:15–01:35 | Memory 页 | 1. 点 "Alex plans to visit Tokyo." 2. 点 "Alex does not own a car." 3. 展开"评审详情 · Memory 原始字段"，指向时间字段 | 计划 / 否定标注；时间字段 | 同上 |
| S07 | 01:35–02:05 | Memory 页 · 来源 | 1. 点来源 1 → 原文出现 2. 点来源 2 3. 切回来源 1 4. 展开"核对来源身份" | 原文随选择切换；dataset/sample/dia_id | 同上 |
| S08 | 02:05–02:20 | Query 页 | 1. 点 Query 2. 选"当前事实" 3. 点"载入冻结案例" | "Alex lives in Rome."；引用 D2:1 | 同上 |
| S09 | 02:20–02:35 | Query 页 | 选"历史日期" → 载入 | "Alex lives in Paris."；引用 D1:1 | 同上 |
| S10 | 02:35–02:50 | Query 页 | 选"证据冲突" → 载入 | 1990 与 1992 双来源；冲突状态 | 同上 |
| S11 | 02:50–03:00 | Query 页 | 选"证据不足" → 载入 | "Insufficient evidence…"；无引用 | 同上 |
| S12 | 03:00–03:10 | Query 页 · Trace | 1. 视图设置→评审者 2. 展开"评审详情 · 阶段 Trace" 3. 依次点 initial / expanded / effective/delivered / answer/citations | 四阶段切换 | 同上 |
| S13 | 03:10–03:15 | Query 页 | 选"预算失败" → 载入 → 展开"阶段错误、耗时与预算" | 错误被保留 | 同上 |
| S14 | 03:15–03:35 | Experiments 页 | 1. 视图设置→展示者 2. 点 Experiments 3. 指向"原 Run 计划组合 3028" 4. 成本策略切 Hybrid→Dynamic | 3028；成功子集与完整分母分列；"非账户实扣" | **HISTORICAL E12 RUN (757 题)** |
| S15 | 03:35–03:50 | 报告图 F7 / F8 | 打开报告 PDF 对应页（或图片查看器），停 10 s | 0.403 / 0.409、CI 跨零；7.9× / 3.5× | **报告图表 · E25 留出实验** |
| S16 | 03:50–04:25 | Overview | 回到 Overview，静止或缓慢移动 | — | OFFLINE SYNTHETIC REPLAY |
| S17 | 04:25–04:30 | 结尾卡 | — | GitHub、SHA、"无模型调用"、成员名单（负责人确认版） | — |

若加入经授权的 LIVE 片段：插在 S13 之后，单独镜头 S13L，角标改为 **LIVE MODEL CALL · deepseek-flash · <时间>**，并在检查表记录 Trace ID；总时长控制在 5:00 以内。
