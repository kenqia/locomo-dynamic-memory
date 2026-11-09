# Product Research Console

本版本将 [Thorns-06 的 Product PR #39](https://github.com/kenqia/locomo-dynamic-memory/pull/39) 接入 main 的个人核心。原始交付为 `0401155aa2c270c48b942e4b410a9f4b390156b3`，整合基准为 `ba349cf7a8b784ff6c739767ee392802055feff5`。

## 启动应用

在 Linux/WSL 中安装仓库锁定依赖后运行：

```sh
uv sync --locked --python 3.12
scripts/personal-release start
```

打开 `http://127.0.0.1:8501`。默认 Console 读取已有记录，五个页面分别用于选择工作、检查记忆与原文、追溯回答、比较实验和演示。顶部“五阶段工作流”保留原上传、构建和问答入口。

没有后端或已有 Build 时，页面明确显示空态或连接问题；冻结实验仍可查看。真实构建和问答的凭据、费用授权沿用 [Release 运行说明](../release/RUNBOOK.md)。

## 启动无凭据 Replay

```sh
uv run --locked python tools/team_v2/demo.py replay
```

打开 `http://127.0.0.1:18501`。此模式只读取 `demo_fixture/product-v1`，验证快照摘要后显示六类合成案例，不启动 API 或数据库。原始数据、合成记录和真实实验聚合分别标识。

Experiments 显示历史 757 QA / 3028 组合的冻结报告。705 双方成功配对与完整分母、失败、unknown 分开解释；下载 JSON 保留原精度。此页面没有重新运行评测，也不代表后续 M5 留出集或教师评分，后续研究见 [实验摘要](../../PERSONAL_EXPERIMENT_SUMMARY.md)。

## 验证整合

```sh
uv run --locked python tools/team_v2/check.py --tb=short
uv run --locked python tools/team_v2/verify_replay.py --browser-python /absolute/path/to/browser-env/bin/python --output var/new-replay-check
uv run --locked python tools/team_v2/verify_replay.py --browser-python /absolute/path/to/browser-env/bin/python --output var/new-layout-check --browser-script browser_console_controls.py
uv run --locked python tools/team_v2/verify_replay.py --browser-python /absolute/path/to/browser-env/bin/python --output var/new-scroll-check --browser-script browser_query_scroll.py
uv run --locked python tools/team_v2/verify_main.py --browser-python /absolute/path/to/browser-env/bin/python --output var/new-main-check
```

浏览器命令使用另一个已安装 Playwright 和浏览器的 Python 环境。Linux/WSL 使用 Playwright Chromium，Windows 使用已安装的 Edge。每次指定新的 `var/` 子目录；验证程序只停止自己创建的进程。`verify_main.py` 创建合成临时数据库，实际启动正常 Release 入口，核对 Console、已有 Trace 与五阶段入口。

`check.py` 复用 main 的公开回归入口，明确排除 live_model、local_embedding、controlled_data；排除项不计为通过。原作者浏览器记录位于 `assets/`，本轮记录见 [整合验收](../release/PRODUCT_INTEGRATION.md)。

## 整合范围与回滚

迁入六个产品模块、公开 fixture、测试、浏览器工具和原始证据。正常启动器改为 `console_ui.py`，原 `ui.py`、Query/API、Hybrid 默认、既有独立 Replay、M5/Bonus 实现保留。未迁入安全分支的旧 CI、配置或查询默认。

最新真人逐项复核绑定 `0401155`，见[完整记录](../release/product-integration-20261109/Product-Human-Review-PR39.md)及[原回执](https://github.com/kenqia/locomo-dynamic-memory/pull/39#issuecomment-6734327474)。此前真人复核依据为 xiaozhuozi39 的 [本地跑通反馈](https://github.com/kenqia/locomo-dynamic-memory/pull/39#issuecomment-6723185216)、[截图附件](https://github.com/kenqia/locomo-dynamic-memory/pull/39#issuecomment-6730042061)，以及负责人确认其已完整复核。原交接文档中的待验收描述是源分支历史记录，不表示该确认被撤回。

需要回滚时，可先直接运行原 `src/locomo_memory/ui.py` 恢复原入口；完整撤销采用本次 main 整合提交的 `git revert`。没有数据库迁移或新生产依赖。Sidecar、Delivery 正式媒体和课程提交分别验收。
