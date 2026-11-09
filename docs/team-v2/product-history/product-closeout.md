# Product 第一阶段返工收尾记录

> 历史记录：以下行为、命令、截图与结果仅对应文内注明的版本。复现历史命令请使用当时的 Git 提交；当前送审入口见 [Product 复核说明](../product-review.md)。

日期：2026-11-08（北京时间）。关联 #23、#26–#29、Draft PR #39。此记录不是任务关闭、第二阶段方向确认或非作者验收。

历史状态提示：负责人随后已在 #23 明确确认方向；本轮后续实现与 main 集成风险见 [最终候选交接](product-final-handoff.md)。下文保留第一阶段当时的记录。

## 已交付与版本

| 项目 | 实际版本与证据 | 状态 |
| --- | --- | --- |
| Memory / Query-Evidence 两页返工 | 运行代码 `e6dd29a`；截图文档提交 `91c407c`；[修改与操作记录](product-ui-rework.md) | 已提交并推送 |
| 专项回归 | `e6dd29a`，29 passed / 1 warning | 已执行 |
| 离线 Replay 浏览器 | `e6dd29a`，六类案例、版本/来源/阶段、无效 ID 恢复；真实模型请求 0 | 已执行 |
| 原合成 API/UI 和旧五阶段入口 | `37e9910` 浏览器回归，四例、入口与启动器退出码 | 已执行 |
| 同视口对照与文件完整性 | 8 张截图，7 张固定 1280×900、1 张扩展高度；[11 份材料校验清单](../assets/product-ui-rework/manifest.json) | 已核对 |
| 成员反馈 | [xiaozhuozi39 11 月 8 日 17:53 反馈](https://github.com/kenqia/locomo-dynamic-memory/issues/23#issuecomment-6720040739)：本地运行和新版呈现总体正面 | 未附实际 SHA、完整逐项结果，不作验收通过 |

## CI 环境阻塞与处理

`91c407c` 的 [PR 检查](https://github.com/kenqia/locomo-dynamic-memory/actions/runs/42464670736) 首次及第二次均在 `uv sync --locked` 下载 CPython 时遇到 HTTP 504；尚未开始编译或测试。
[push 检查](https://github.com/kenqia/locomo-dynamic-memory/actions/runs/42464667531) 也未通过。旧失败及重跑记录保留，不将它们当作测试通过或 UI 代码失败。

本次仅调整 CI 准备环境：

- runner 明确为 Ubuntu 24.04；GitHub 官方 Python manifest 提供匹配该系统的 3.12.12。
- 用固定提交的官方 `actions/setup-python` v6 安装 Python 3.12.12，与本地已验证 patch 版本一致。仓库 `.python-version` 仍为 `3.12`。
- uv 仍为 0.9.11，使用已准备的系统 Python，禁止其再次下载托管解释器；输出实际 Python 版本。
- 原锁定安装、编译、完整离线检查和 Demo prepare 步骤全部保留；不删除测试、不放宽排除、不修改依赖锁或生产默认。

最终结果以新提交对应的 GitHub Checks 和日志为准；本次环境调整不改变 `e6dd29a` 的 UI、合成快照与截图内容。

## 剩余门槛与分工

| 待办 | 所需证据 / 执行人 |
| --- | --- |
| 第一阶段方向确认 | kenqia 明确确认两页方向，才能开展 Overview / Experiments 等第二步返工 |
| Product 非作者独立实操 | xiaozhuozi39 补实际 SHA、环境、命令、六类案例、来源/Build/阶段、实验与旧入口检查、截图及逐项结论 |
| 最新完整 CI | 新提交环境准备成功后执行全部原有检查；失败则区分环境和代码原因 |
| 第二步 UI 与新版素材 | 方向确认后实施，保留原分母、失败、unknown、成本边界与旧功能 |
| 合并和集成 | 真实非作者复核通过、负责人批准及必要验证后进行；当前不合并、不关闭 |
| 正式媒体与统一版本 | 按团队分工完成正式 MP4、PPTX/PDF、报告、验收记录和统一 RC |
| Notion | 当前无可用连接或已关联记录；负责人补录摘要与 Issue/PR 链接，不能声称本次已同步 |

成员可使用 [真人操作记录空模板](../product-human-review-template.md) 补充证据；模板本身不表示已执行。

另外，[#24 的交叉复核指派](https://github.com/kenqia/locomo-dynamic-memory/issues/24#issuecomment-6703754063) 要求 Thorns-06 对 `codex/sidecar-research-20261107@2deefd54` 做真人非作者复核。
这属于独立任务，在另一目录执行；当前没有 Thorns-06 本人执行的证据。AI 可以辅助准备和检查，不能代替本人结论。
真实数据复验还依赖负责人合法提供受控导出与冻结参考，不读取活动数据库，不新增付费调用。

## 回滚

撤销本次 CI/收尾记录提交即可返回 `91c407c` 的工作流；UI 和既有截图不受影响。回滚第一阶段 UI 见 [原记录](product-ui-rework.md)。
