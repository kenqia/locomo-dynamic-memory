# Product Console 本轮复核

Owner：Thorns-06；非作者 Reviewer：xiaozhuozi39。关联 #23、#26–#29，沿用 PR #39 和分支 `team/product-console-v2-6d`，目标仍为 `codex/v2-6d-production-safe`。

用户已确认暂按当前效果送审，撤销此前“仅本地、暂不推送”的等待。送审不代表真人验收、合并或任务完成；历史反馈不代替本轮实际 SHA 的复核。

## 版本与改动

- 远端对照基准：`43b6c6e05a9a10f1ae4c3ec0aed42dcf912bbcda`；本地起点 `1fff3a3` 另包含上轮未推送的 JSON 换行校验修正，本轮一并提交。
- 运行代码提交：`60f14bf5f8bf44086dd96907ac23f6e394255c57`。浏览器环境与 16 份材料校验见本轮 [证据清单](assets/product-review/manifest.json)；后续证据/说明提交不改写运行代码 SHA。
- 主要变化：导航四周留白和响应式排列；统一浅蓝状态标签；页内宽版数据/对话/版本面板；两种角色横向选择，摘要与评审详情分离。
- Memory：分页显示范围/总数、前后页与页码跳转，单页说明“已全部显示”；翻页后选中项与详情同步。
- 来源：选中即显示完整原文，删除查看按钮和临时说明。来源 1→2→1 反复切换始终按当前 ID 读取，保留作用域和完整身份校验；失败不显示旧原文。
- Query：详情随整页滚动，取消 Query JSON 的内部纵向高度上限；“本阶段已记录字段”默认关闭，其他原始字段仍可展开核对。
- 目录整理：六份历史文档归入 [product-history](product-history/README.md)，保留原版本、失败和素材；当前入口为本文、[模块/API 映射](product-console.md)和[真人空模板](product-human-review-template.md)。两份重复浏览器脚本已删除，其实际导出、完整分母与成本检查并入六案例脚本；布局/滚动分别保留独立检查。临时本地说明已合并到本文。

生产 Build/Query、Prompt、模型/检索默认、数据库与公开固定快照不变。合成案例演示应用链路，与独立历史真实报告分开；失败、unknown 和缺测不补造，不新增付费调用。

## 独立运行

在 Reviewer 自己的 clone 中切换对应分支并记录 `git rev-parse HEAD`，安装与启动：

```powershell
uv sync --locked
uv run --locked python tools/team_v2/demo.py replay
```

打开 `http://127.0.0.1:18501`。已有锁定环境可使用 `.\.venv\Scripts\python.exe tools/team_v2/demo.py replay`。安装依赖需联网，Replay 运行读取本地快照，无需 API、模型凭据或活动数据库。原五阶段入口按 [模块说明](product-console.md) 中的独立合成 prepare/api/ui 方式检查。

## 建议复核顺序

1. Overview：核对合成标识与独立真实报告；展开“数据与版本”，切换两版本再返回，确认摘要与内容一致。
2. Memory：选择记忆，原文应立即显示；核对计划、否定、事件/报告/有效时间及 unknown。单页总数明确；多页翻页/跳转由离线检查补充覆盖。
3. Query：依次载入当前事实（Rome）、历史日期（2023-05-01 / Paris）、冲突（1990/1992）、证据不足、引用异常和预算失败。失败必须保留原阶段/代码，不当成证据不足。
4. 冲突案例展开阶段 Trace，切换四阶段；来源 1→2→1→2→1 应直接显示对应原文。字段区初次关闭，展开后鼠标在原始字段上也能滚动整页；切换案例后仍可操作。
5. 手输不存在 ID 和 `../health`，应显示可恢复提示；重新载入当前事实可恢复，来源与 Build 身份不混用。
6. Experiments：核对 3028 计划组合 / 2969 成功 / 56 失败 / 3 unknown，705 成功配对子集与全量边界。切换策略/对话/题型，Full Text 完整分母保持 unknown，成本为历史估算；下载 JSON 保留原精度。补充 Run 明确未提供。
7. 将窗口缩窄，核对导航、面板和卡片重排；切换展示者/评审者，检查无重叠。最后按 Demo 的约 4 分钟路线连续操作。

填写 [真人独立记录](product-human-review-template.md)，回复实际 SHA、环境、命令、逐项结果、截图和未执行项。自动化记录不作为人工签字。

## 验证与边界

固定送审代码已通过：26 项 Console/实验/Replay/Evidence 定向检查（1 条既有依赖弃用 warning）、六案例与实际无损导出、30 个布局场景、来源自动显示/字段折叠及 11 个滚轮操作场景。新合成 API/UI 的四案例、原五阶段往返与启动端口错误透传也通过，真实模型调用 0。具体结果、环境与 SHA 见证据清单；GitHub CI 以 PR 当前 HEAD 的实际 checks 为准，不借用旧提交的通过结果。

主要材料：[桌面 Overview](assets/product-review/presenter-overview-1280.png) · [版本面板](assets/product-review/version-panel-1280.png) · [手机评审视图](assets/product-review/reviewer-overview-390.png) · [来源 1](assets/product-review/auto-source-1-1.png) / [来源 2](assets/product-review/auto-source-2-2.png) · [六案例/导出结果](assets/product-review/replay-result.json) · [滚轮记录](assets/product-review/scroll-result.json)。来源切换截图中原始字段已由测试手动展开，默认关闭由浏览器及单元检查分别验证。

```powershell
.\.venv\Scripts\python.exe tools/team_v2/check.py -q --tb=short tests/test_console_ui.py tests/test_console_experiments_ui.py tests/test_console_replay.py tests/test_console_evidence_ui.py
```

浏览器与 main 增量候选检查入口见 [工具索引](../../tools/team_v2/README.md)。浏览器环境独立，不增加项目模型依赖。

本轮核对的最新 main 为 `f18d76dc3227f0fd5b22be8bb6d7c28b516b812a`，与分配的安全分支没有共同历史。[增量候选检查](assets/product-review/main-compatibility.json)通过：只向独立 main 导出添加六个 Product 模块和公开 fixture，保留其 Hybrid 默认与五个核心文件字节；不代表合并、生产验证或 main 全量回归，不能整分支覆盖 main。

正式 PPTX/PDF、MP4、技术报告和统一 RC 按 Delivery/负责人分工；短浏览器 WebM 仅为素材。本轮不代替 Thorns-06 执行另项 Sidecar 真人复核。

Notion 已有关联任务，但本会话没有可用连接工具，送审状态、摘要及链接未同步，需负责人补录。当前仍是待非作者复核，未批准、合并或关闭任务。

## 回滚

停止自己的 Demo，在独立 checkout 使用对照基准 `43b6c6e` 可恢复上次远端页面。共享分支需要回退时按提交普通 revert，不 reset 历史；本轮无数据库迁移。目录归档的文件可从 Git 历史恢复，旧版本证据没有删除。
