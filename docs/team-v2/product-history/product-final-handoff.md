# Product Console：职责说明与最终候选交接

> 历史记录：以下行为、命令、截图与结果仅对应文内注明的版本。复现历史命令请使用当时的 Git 提交；当前送审入口见 [Product 复核说明](../product-review.md)。

记录日期：2026-11-09（北京时间）。负责人 Thorns-06，父任务 #23、子任务 #26–#29，沿用 Draft PR #39。
依据 [11 月 8 日负责人放行](https://github.com/kenqia/locomo-dynamic-memory/issues/23#issuecomment-6721763944)，第一阶段方向已通过，本轮继续完善剩余页面。
原冻结节点与历史证据保留；本轮跨日成果不记为按旧截止完成。最终非作者验收、合并和统一版本验收仍须分别取得证据。

## 你的部分解决什么问题

Product Console 把已有记忆系统整理成一套评审者可以操作、演示者可以讲清楚的产品界面：

`选择对话与固定 Build → 检查 Memory 和原文 → 追溯回答及证据 → 理解实验结果与局限`

| 页面 / 任务 | 用户要解决的问题 | 本轮交付 |
| --- | --- | --- |
| Overview / #26 | 应从哪里开始、当前检查哪个版本、有哪些真实结果 | 三个任务入口、统一紧凑导航、可展开版本身份、真实报告概览 |
| Memory / #27 | 记忆说了什么、何时适用、来源是什么、是否有冲突 | 记忆列表与详情、时间边界、完整原文、关系和投影；保留已确认设计 |
| Query/Evidence / #27 | 保存的回答用了什么证据，为什么冲突、证据不足或失败 | 回答/引用优先，四阶段 Trace、来源身份和 Build 校验、可恢复的无效输入；保留已确认设计 |
| Experiments / #28 | 成绩如何解释，失败和缺测是否影响结论，成本是什么口径 | 先解释，再看完整分母/分组/成功配对/成本；统一精度和无损 JSON 导出 |
| Demo / #28–#29 | 如何连续演示并交给其他成员复现 | 约 4 分钟路线、六类可读案例、离线启动说明与截图 |

Build 是一套 Memory/来源/关系/索引共同所属的构建版本；Trace 是一次已有问答的过程记录；Run 是实验运行及报告身份。
本轮 Console 读取保存的记录。合成 Replay 演示应用链路，真实冻结 Run 说明已有实验结果，两者明确分开。

## 本轮实际改动

- Overview 的记忆、回答证据、实验入口可直接导航；没有数据时关闭依赖 Build 的入口，冻结报告仍可读。
- 所有页面沿用旧五阶段视觉语言，角色设置与导航同一行；完整身份、指纹和原始字段放详情。
- Experiments 按“选择结果集 → 解释 → 原 Run 全量状态 → 单维分组 → 配对与失败 → 成本”的顺序展示。
- 分组概览缩为四列，选组后查看完整分母和完成/成功率；百分比两位、分数/成本四位，细小非零成本用科学计数。
- 完整原数值保留在详情和下载 JSON；浏览器实际下载后与冻结源 JSON 整体相等。缺失值保持 unknown。
- 补充 Run 未提供时直接显示空态，不展示借用的原 Run 数字。
- Demo 以可读案例卡片替代默认全 ID 宽表；保存身份仍可展开。没有新增模型请求、生成按钮或固定快照重建。

## 启动与 4 分钟讲解

```powershell
.\.venv\Scripts\python.exe tools/team_v2/demo.py replay
```

打开 `http://127.0.0.1:18501`。干净 clone 使用 `uv sync --locked`，再 `uv run --locked python tools/team_v2/demo.py replay`。
安装需要获取依赖；Replay 运行只读本地快照，不需要 API、活动数据库或模型凭据。

| 时间 | 演示操作与讲解 |
| --- | --- |
| 0:00–0:40 | Overview：展示任务入口与当前固定版本，区分合成 Replay 和真实冻结 Run |
| 0:40–1:30 | Memory：打开原文，检查计划、否定和 unknown；切换历史 Build 后返回 |
| 1:30–2:30 | Query/Evidence：载入当前/历史/冲突/证据不足及两个失败案例；展开阶段 Trace 和引用来源 |
| 2:30–3:40 | Experiments：先解释 705 成功配对与全量失败；选择分组和成本；切换缺失补充 Run；展示完整精度导出 |
| 3:40–4:00 | Demo：核对六类案例、合成标识与交接入口，说明真实成员验收仍待完成 |

3–5 分钟路线是演示者操作指引，不声称已交正式全程 MP4。既有短 WebM 是素材；正式 PPTX/PDF、MP4 与报告按 Delivery 分工。

## 新鲜验证与历史证据

- 本轮运行代码 `a0a08edf7e11d4fe2d41f87a7a5c785eff9ca80e`；改动基准 `2201eeb227bba8a49b10889c7698e41bc5a86418`。
- 受影响的 Console / Experiments / Replay 定向检查：20 passed / 1 条依赖弃用 warning。未为本轮重跑无改动的独立专项。
- 本轮浏览器与独立 main 兼容性结果、实际版本和场景以 [最终证据清单](../assets/product-final/manifest.json) 为准。
- 新旧固定截图均 1280×900；`full-*` 是额外扩展高度图，不当作同视口对照。
- 首次定向运行受 Windows 临时目录权限阻塞，改用获准环境后通过。早期浏览器因 3028 同时匹配指标与隐藏原始字段而退出；定位到指标区域后通过。旧失败保留在 ignored `var/`，不计成功。
- [Memory / Query-Evidence 原同视口证据](product-ui-rework.md)、[六案例和旧入口历史回归](product-followup-validation.md)、[第一阶段与 CI 环境处理](product-closeout.md) 保留原 SHA 和结果。
- 最终 HEAD 的编译、完整 Linux 离线检查和 Demo prepare 以 [PR #39 checks](https://github.com/kenqia/locomo-dynamic-memory/pull/39/checks) 实际结果为准；不宣称 Windows 历史全套通过。

本轮 `a0a08ed` 新鲜证据：浏览器五个场景与三种聚合维度通过，源跳转和实际下载 JSON 一致性通过；页面脚本错误 0，API/数据库未启动，真实模型请求 0。
隔离 main 候选五页与 Hybrid 默认检查通过，五个 main 核心文件 SHA 未变，记录的网络/SQLite/生成尝试 0；完整范围见 [结果](../assets/product-final/main-compatibility.json)。
12 张新旧截图逐张检查；[清单](../assets/product-final/manifest.json) 包含 16 份材料的版本/场景/环境与 SHA-256。

| 对应场景，固定 1280×900 | 修改前 `2201eeb` | 修改后 `a0a08ed` |
| --- | --- | --- |
| Overview | [原图](../assets/product-final/before-overview.png) | [新图](../assets/product-final/after-overview.png) |
| Experiments 首屏 | [原图](../assets/product-final/before-experiments.png) | [新图](../assets/product-final/after-experiments.png) |
| 配对与成本 | [原图](../assets/product-final/before-cost.png) | [新图](../assets/product-final/after-cost.png) |
| 缺失补充 Run | [原图](../assets/product-final/before-missing-run.png) | [新图](../assets/product-final/after-missing-run.png) |
| Demo | [原图](../assets/product-final/before-demo.png) | [新图](../assets/product-final/after-demo.png) |

另附 [完整实验页](../assets/product-final/full-experiments.png)、[完整演示路线](../assets/product-final/full-demo.png)，均为扩展高度图。
浏览器实际下载的 [完整精度报告](../assets/product-final/exported-report.json) 与原固定证据 JSON 数值整体一致，不是新实验运行。

可复现本轮检查（每次使用新的输出目录）：

```powershell
.\.venv\Scripts\python.exe tools/team_v2/check.py -q --tb=short tests/test_console_ui.py tests/test_console_experiments_ui.py tests/test_console_replay.py
.\.venv\Scripts\python.exe tools/team_v2/verify_replay.py --browser-python var/console-browser/Scripts/python.exe --output var/new-product-before --baseline 2201eeb --browser-script browser_product_final.py
.\.venv\Scripts\python.exe tools/team_v2/verify_replay.py --browser-python var/console-browser/Scripts/python.exe --output var/new-product-after --browser-script browser_product_final.py
.\.venv\Scripts\python.exe tools/team_v2/check_product_integration.py --main-ref 0ebb2b8f832e306c37389881b9b7187129e5311a --output var/new-product-main-check
```

## 当前 main 的集成差异与风险

核对 main `0ebb2b8f832e306c37389881b9b7187129e5311a`；PR #39 目标仍为分配的 `codex/v2-6d-production-safe`，基准 `3ba1954`。
本地不是浅克隆，但 main 与团队安全分支 `git merge-base` 返回 1，没有共同历史。两边 API、Query、原 UI、Release/M5/Replay 模块与 CI 存在差异，不能把整个安全分支直接覆盖 main。

本轮隔离兼容性工具从精确 main 导出新目录，只增加四个产品模块和公开固定 fixture，再检查五页只读导航与 main 原问答 UI 的 Hybrid 默认。
main 的 `query_ui.py`、`queries.py`、`config.py`、`ui.py`、`api.py` 保留原字节 SHA；不修改默认，不连接数据库或真实网络。
该检查属于未合并的增量候选冒烟，不是 main 全套回归或正式集成验收。

负责人整合时需选择性迁入产品模块、工具、公开 fixture 与文档，并保留 main 的 Hybrid 默认、日期处理、既有 Release/M5/独立 Replay 和其 CI。
旧五阶段在不同基线上的差异仍由 main 保持；没有把团队 safe 分支的历史行为当作 main 新默认。本轮不合并、不改 PR 目标、不执行整库迁移。

## 审查、交接与剩余项

- 负责人方向已确认，后续产品页面候选已按该方向实现；不是最终验收通过。
- 非作者 xiaozhuozi39 已给出局部运行/外观正面反馈，最终版本仍须补实际 SHA、环境、命令、逐项结果与截图；可用 [真人复核空模板](../product-human-review-template.md)。
- 给 Delivery 的材料：最终同视口截图、原六类案例证据、上方固定路线、运行命令、文件校验清单和实际版本。正式媒体与统一 RC 仍由对应负责人办理。
- 真实补充/修复 Run 尚无公开冻结材料，保持未提供。语义正确性缺少独立真值，仍为未评；合成 Demo 不作为模型成绩。
- Notion 已有关联任务，但本会话没有可用工具；本轮摘要、状态和 Issue/PR 链接未同步，需负责人补录。
- Sidecar 是另外的真人非作者复核职责，本轮只完善 Product，没有代替 Thorns-06 本人的独立操作或结论。
- PR 保持 draft，Issue 保持开放；最终非作者复核、负责人批准、必要的合并与集成验证仍须完成。

## AI 代码检查

### Standards

本轮产品页面审查 0 项明确规范违规、0 项重要异味。展示精度与原数据分开，未改生产行为或数据层。

### Spec

需求轴发现 1 项 P2：实验页解释仍位于全局数字之后。`a0a08ed` 已调整为结论优先，且缺失补充 Run 不再显示原 Run 指标；复查 0 项未解决。
AI 与自动化均不替代真实成员验收。

## 回滚

按逆序撤销本轮文档/证据、`a0a08ed`、`536321f` 即返回第一阶段收尾版本 `2201eeb`。无数据库迁移，固定快照未变。
