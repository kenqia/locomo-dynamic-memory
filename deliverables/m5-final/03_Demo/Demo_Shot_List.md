# Demo Shot List r2（逐镜头操作清单）

1920×1080，30 fps；浏览器缩放 100%，隐藏书签栏；鼠标高亮开启。每镜头为**连续真实操作**，只在镜头之间切换，不用截图替代镜头。
修订 r2：主线 5 段；冲突 / 证据不足 / 预算失败不逐个载入（S11 一扫而过）。

| # | 时间 | 窗口 | 操作 | 必须可见 | 角标 |
|---|---|---|---|---|---|
| S01 | 00:00–00:06 | 标题卡 | — | 项目名、组名、M5 Final | — |
| S02 | 00:06–00:25 | 终端 | `git rev-parse --short HEAD` → `uv run --locked python tools/team_v2/demo.py replay` → 出现 URL | SHA 5519dd2、命令、URL；无 key / `.env` | OFFLINE SYNTHETIC REPLAY |
| S03 | 00:25–00:50 | Overview | 停在三标签 → 展开"数据与版本"→ 指向指纹 → 收起 | 合成回放、conv-a、版本 1·已完成 | 同上 |
| S04 | 00:50–01:15 | Memory | 点 Paris → 点 Rome → 滚到"这条记忆的关系与冲突 · 替代" | 两条住所、SUPERSEDE/替代 | 同上 |
| S05 | 01:15–01:30 | Memory | 回顶部 → 点 "Alex plans to visit Tokyo." | 陈述性质 = 计划 | 同上 |
| S06 | 01:30–02:00 | Memory · 来源 | 点 Rome → 指向 D2:1 原文 → 展开"核对来源身份"→ 点 Paris，原文切换为 D1:1 | 原文随选择切换；身份三元组 | 同上 |
| S07 | 02:00–02:14 | Query | 选"当前事实"→ 载入冻结案例 | "Alex lives in Rome."、D2:1 | 同上 |
| S08 | 02:14–02:28 | Query | 选"历史日期"→ 载入 | "Alex lives in Paris."、D1:1 | 同上 |
| S09 | 02:28–02:58 | Query · Trace | 视图设置→评审者 → 展开"评审详情 · 阶段 Trace"→ initial → expanded → effective/delivered → answer/citations | 四阶段切换，每阶段内容可读 | 同上 |
| S10 | 02:58–03:05 | Query | 视图设置→展示者 | — | 同上 |
| S11 | 03:05–03:15 | Demo | 鼠标扫过六个案例卡片，不展开 | 冲突 / 证据不足 / 预算失败等名称 | 同上 |
| S12 | 03:15–03:30 | Experiments | 指向 3028 → 成本策略 Hybrid→Dynamic | 成功子集 / 完整分母分列；"非账户实扣" | **HISTORICAL E12 RUN（757 题）** |
| S13 | 03:30–03:55 | 报告 PDF 或图片 | 打开 F5、F6 | 0.403/0.409、CI 跨零；7.9×、3.5× | **报告图表 · E25 留出实验 · 冻结运行记录** |
| S14 | 03:55–04:25 | Overview | 回到 Overview，缓慢移动 | — | OFFLINE SYNTHETIC REPLAY |
| S15 | 04:25–04:30 | 结尾卡 | — | GitHub、SHA、"演示 0 模型调用；E25 真实调用记录见 level-e-runtime-terminal-v1.json"、成员名单（团队确认版） | — |

参考截图（同一 Console 实际页面，供对照取景）：`deliverables/m5-final/screenshots/loaded/`。
