# Product UI 返工：第一步方向确认候选

日期：2026-11-08（北京时间）。负责人：Thorns-06。关联 #23 / #26 / #27、Draft PR #39。

依据：[11 月 7 日负责人修改与交叉验收安排](https://github.com/kenqia/locomo-dynamic-memory/issues/23#issuecomment-6703489480)、
[11 月 8 日 xiaozhuozi39 的试用反馈](https://github.com/kenqia/locomo-dynamic-memory/pull/39#issuecomment-6718206030)。
修改基准：`44d20dc6779c26b89a9cd76b1b022474d380ff5d`；PR 的 production-safe 基准仍为 `3ba1954bd0c188ad84d80dd4a4f94618857b0109`。

## 本次交付边界

只先交 Memory 和 Query/Evidence 两页以及它们需要的紧凑页头。沿用旧五阶段 `ui_theme.py` 的品牌、容器、按钮和问答气泡。
Overview、Experiments、Demo 的整体重排与数字呈现留在负责人确认方向之后；未宣称整个 Product 返工完成。
本轮依据负责人明确安排实施，没有自行更改原冻结节点。

| 页面 | 现在的默认阅读顺序 | 保留的检查能力 |
| --- | --- | --- |
| Memory | 记忆列表 → 所选内容/时间 → 完整原文 → 与该记忆相连的关系 | 分页、历史 Build、完整来源身份、全部当前页关系/适用条件、状态投影、Memory 原字段 |
| Query/Evidence | 选择保存案例 → 问题/回答/状态 → 回答引用与原文 → 评审详情 | 同一 Build 校验、四阶段 Trace、有效选择与实际送达区分、诊断/预算/耗时、完整已保存 Trace |

两页首屏复用旧版紧凑品牌样式，视图设置与导航同一行。完整 ID/指纹移入数据版本展开区，来源身份与 Trace 原字段可展开核对。
Replay 使用一条固定合成标识；不重复叠放大块连接成功/合成警示。
Memory 使用可读列表与选中卡片，阶段候选也使用内容卡片；核心流程不再依赖宽表横向滚动。
Timeline 仍按 API Memory 记录顺序呈现，不冒称事件时间排序。报告、事件及有效区间分别显示；plan、negative、unknown 保留。

## 无效 Trace ID 反馈

冻结案例有独立的主操作“载入冻结案例”。手动输入收进“按 Trace ID 读取已有记录”，空输入时读取按钮禁用。
不存在的 ID 显示“未找到此 Trace ID 对应的已保存记录”，而非提示检查后端服务；清除先前载入的结果。
之后仍可通过主按钮重新载入有效案例。HTTP 404 以外的服务错误保持错误处理，不将它们伪装成记录不存在。
手输 ID 仅允许字母、数字、连字符和下划线；路径/查询/编码分隔符在读取前拒绝，不把任意输入拼成其他 API 资源路径。
这解释了空输入时下方读取按钮禁用的规则；成员原评论没有足够步骤确定所指按钮，不能宣称已复现其全部现场。

## 操作与方向审查

```powershell
.\.venv\Scripts\python.exe tools/team_v2/demo.py replay
```

打开 `http://127.0.0.1:18501`。干净 clone 可先 `uv sync --locked`，再 `uv run --locked python tools/team_v2/demo.py replay`。

1. 进入 Memory，逐项选择 Paris / Rome / Tokyo 计划 / car 否定记录，点“查看完整原文”。检查可读性、unknown、原文及时间分列。
2. 展开“数据 / 对话 / Build”，切换两个历史版本，确认当前内容与版本一致。完整身份在此展开区；模式在“视图设置”切换。
3. 进入 Query/Evidence，选择案例并点“载入冻结案例”。先看回答状态和引用原文；检查历史、冲突、证据不足、引用异常和预算失败。
4. 展开“评审详情 · 阶段 Trace”，切换 initial / expanded / effective/delivered / answer/citations。原字段、错误预算和完整 Trace 均保留。
5. 展开“按 Trace ID 读取已有记录”，输入不存在的 ID，点击读取。应得到可恢复的未找到提示，再载入 success 应恢复正常。

负责人本轮确认重点：是否沿用旧版视觉语言，首屏主次是否清楚，列表/回答/来源是否易读，1280px 下能否顺畅操作。
方向确认后才进入其余页面重排；这份记录不构成方向确认或真实成员验收结论。

## 验证与证据

专项回归命令：

```powershell
.\.venv\Scripts\python.exe tools/team_v2/check.py -q --tb=short tests/test_console_ui.py tests/test_console_evidence_ui.py tests/test_console_replay.py tests/test_console_experiments_ui.py tests/test_strategy_ui.py tests/test_browser_fixture.py
```

同视口新旧浏览器验证：

```powershell
.\.venv\Scripts\python.exe tools/team_v2/verify_replay.py --browser-python var/console-browser/Scripts/python.exe --output var/new-ui-before --baseline 44d20dc
.\.venv\Scripts\python.exe tools/team_v2/verify_replay.py --browser-python var/console-browser/Scripts/python.exe --output var/new-ui-after
```

每次使用新的 `var/` 输出目录。baseline 从 Git 导出历史源码到该新目录，使用相同合成固定快照与浏览器脚本；不切换或覆盖当前工作树。
`viewport-*.png` 固定 1280×900；另一组扩展高度截图只用于查看完整内容，不当作相同视口比较。
实际运行版本、环境、场景与结果以本页后续证据清单为准。历史素材和失败记录保留，不覆盖原结论。

不调用真实模型，不连接研究数据库，不改 Build/Query/Prompt/模型默认值，不重建固定快照。
合成回放不代表模型成绩，也未宣称已接入 Sidecar。

## 待确认与回滚

- 负责人：第一步 UI 方向待确认；其余页面等待此确认。
- 非作者：负责人指派 xiaozhuozi39；已有局部试用反馈，尚无本次新版本的逐项实操验收或正式 Approve。
- PR 保持 draft；不关闭 Issue，不标完成。自动化与 AI 检查不能替代成员实操。
- Notion 未同步：当前会话无可用 Notion 工具或已关联任务记录，需负责人补录摘要与本轮 Issue/PR 链接。
- 仅撤销本轮 UI/浏览器验证提交即可回到 `44d20dc`；没有数据库迁移或固定快照内容更改。
