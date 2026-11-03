# 六天冲刺入口

周期：2026-11-03–2026-11-08，Asia/Shanghai。当前交付的是可开发基线与任务入口；最终系统、Sidecar、正式媒体和人工验收仍待各 Owner 完成。

| 主线 | Owner | 父 Issue | 工作分支 | PR 目标分支 |
| --- | --- | --- | --- | --- |
| A Product Console | @Thorns-06 | [#23](https://github.com/kenqia/locomo-dynamic-memory/issues/23) | `team/product-console-v2-6d` | `codex/v2-6d-production-safe` |
| B Temporal/Event Sidecar | @xiaozhuozi39 | [#24](https://github.com/kenqia/locomo-dynamic-memory/issues/24) | `team/temporal-event-sidecar-v0-6d` | `codex/v2-6d-research-safe` |
| C Research Delivery | @VanadisssSSS | [#25](https://github.com/kenqia/locomo-dynamic-memory/issues/25) | `team/research-delivery-v2-6d` | `codex/v2-6d-production-safe` |

负责人保留 Core/Research、付费预算、事实结论、集成和发布决策。Owner 为负责人明确指派，成员本人响应、非作者 Reviewer 和成果 PR 尚待记录。不要把 AI 检查填写为人工复核。

## 今天开始

需要 Git、Python >=3.11、uv 和仓库写权限。每人在自己的机器克隆；不要共用负责人的研究目录。以 A 为例，B/C 替换 `--branch` 后的分支名：

```sh
git clone --single-branch --branch team/product-console-v2-6d https://github.com/kenqia/locomo-dynamic-memory.git locomo-v2-product
cd locomo-v2-product
uv sync --locked
uv run --locked python tools/team_v2/check.py -q --tb=short
uv run --locked python tools/team_v2/demo.py prepare
```

`prepare` 创建本 clone 的 `var/team-v2-demo/`，用合成数据和受控适配器生成 Build 与四种 Query Trace，不下载 embedding，不访问真实模型。重复执行会拒绝覆盖；需要新实例时使用新的 `--output var/<new-name>`，后续启动用相同 output。

在两个终端启动：

```sh
uv run --locked python tools/team_v2/demo.py api
uv run --locked python tools/team_v2/demo.py ui
```

打开 [离线 UI](http://127.0.0.1:18501)，后端[健康检查](http://127.0.0.1:18000/health)。屏幕必须显示 `OFFLINE SYNTHETIC DEMO`；它证明应用链路可运行，不证明真实模型质量。启动器仅允许本 clone 的 `var/` 子目录，清除常用模型凭据变量，阻断非本机网络。通过 Ctrl+C 停止自己启动的服务。

界面选择 `OFFLINE-SYNTHETIC-v2-kickoff` / `conv-a` 及完整 Build，查看 Memory/关系/历史版本，再查询：

- `Where does Alex live?`：当前 Rome。
- `Where did Alex live?`，日期 `2023-05-01`：历史 Paris。
- `What is Sam's birth year?`：保留 1990/1992 冲突。
- `What is Alex's passport number?`：证据不足。

当前 Replay 是确定性的合成应用 fixture。真实实验比较的冻结聚合见 [research-evidence.json](research-evidence.json)，Product 需在 #28 接入比较页；不要把 fixture 变成真实成绩。

## 领取首项并提交 PR

在自己的父 Issue 回复环境检查和今日产物，开始第一个子 Issue。分工已经确定，无需再次自由认领。代码只写所属范围；跨范围先提交接口需求。

```sh
git status --short
git add <逐个检查过的文件>
git diff --cached --name-only
git diff --cached --check
git commit -m "feat: describe your actual increment"
git push origin HEAD
```

push 前核对无敏感内容且符合负责人授权；不要使用 `git add .`。D3 之前通过 GitHub 创建 draft PR，目标按上表，不指向旧 `main`，也不把原研究分支合并过来。PR 填写基准 SHA、运行命令、测试/截图/文件、费用与回滚；不要为了凑 PR 创建空成果。

## 冻结与验收

- **11/06（D4）18:00 功能冻结**：只修阻断，新增功能进后续 backlog。
- **11/07（D5）18:00 内容与数据冻结**：正式 PPTX/PDF/MP4、报告和 SHA 清单齐备。
- **11/08（D6）**：只修 P0，完成彩排、非作者人工复核、可恢复 RC 和验收记录。课程正式提交仍需负责人最终授权。

唯一日程：[06 六天冲刺看板](task-package/06_SIX_DAY_SPRINT_BOARD.md)。任务状态以 [GitHub milestone](https://github.com/kenqia/locomo-dynamic-memory/milestone/1) 为准；[每日记录](sprint-status.md)仅记录证据和阻塞。

继续阅读：[任务书及执行覆盖](task-package/README.md)、[接口与改动边界](contracts.md)、[事实台账](claims.md)、[同步审查](github-sync-report.md)、[最终验收](acceptance.md)。

机器可读任务分配及真实链接：[issue-map.json](issue-map.json)。已验证启动版本与 CI：[remote-verification.json](remote-verification.json)。
