# Product Console 后续增量验证

日期：2026-11-06，北京时间（D4，功能冻结前）。基准：`7a159d7e3f2baacdc7ae510cb42a060befb1afba`。
范围：#27 Timeline / Evidence，#28 比较与无数据库 Replay，#29 自动化验收与素材。
继续使用 A 线分支和 draft PR #39；不将此记录当作真实成员复核或任务关闭。

## 功能与边界

| 验收对象 | 实际实现 / 待核对 |
| --- | --- |
| Memory Timeline | 来源记录顺序表；报告、事件、有效时间分列；plan、negative、unknown 保留；关系、冲突和投影可检查 |
| 来源跳转 | 选择引用后读取完整 SourceTurn；校验 dataset/sample/dia/source 身份，不一致或缺失时保留异常 |
| Trace | 四阶段切换；初始/扩展/有效 Memory、引用、送达记录、错误、预算和耗时分开显示；无 exact wire / event_ref 不补造 |
| 冻结案例 | success、historical、conflict、insufficient、citation_anomaly、budget_failure 六例，均来自合成 API 实际运行 |
| 实验比较 | 策略/对话/题型单维聚合、完整分母、成功子集、成本缺测；705 配对优势与全量失败并列 |
| 补充/修复 Run | 当前公开材料未提供，独立空态，不合并原 Run，不补填未知成绩 |
| 独立 Replay | 三个 hash-checked JSON，无 API、数据库或真实模型请求；两个 Build 可切换 |
| 人工 Reviewer / 集成 | pending；AI 和浏览器自动化不能替代另一真实成员复核 |
| Notion | 未同步：尚无关联任务记录/连接，由负责人补录 Issue/PR 链接 |

## 运行

无数据库入口与 3–5 分钟操作脚本见 [demo_fixture/README.md](../../demo_fixture/README.md)。
原 `demo.py prepare/api/ui` 合成应用模式和原五阶段工作流保留。

```powershell
.venv\Scripts\python.exe tools/team_v2/check.py -q --tb=short tests/test_console_ui.py tests/test_console_evidence_ui.py tests/test_console_replay.py tests/test_console_experiments_ui.py tests/test_strategy_ui.py tests/test_browser_fixture.py
.venv\Scripts\python.exe tools/team_v2/verify_replay.py --browser-python var/console-browser/Scripts/python.exe --output var/new-replay-check
.venv\Scripts\python.exe tools/team_v2/verify_console.py --browser-python var/console-browser/Scripts/python.exe --output var/new-live-check
```

浏览器使用独立 Playwright 1.64.0 和本机 Edge，交互视口 1280×900，截图按内容扩展高度、保持宽度。
录屏编码器放在 `var/pw-browsers`，不增加应用依赖。服务由验证器创建并在结束时停止。
Playwright 环境准备：`uv venv var/console-browser --python 3.12`，然后
`uv pip install --python var/console-browser/Scripts/python.exe playwright==1.64.0`；
设置 `PLAYWRIGHT_BROWSERS_PATH` 为本 clone 的 `var/pw-browsers` 后运行该解释器的
`-m playwright install ffmpeg`。Linux 可使用已安装的 Chromium，并通过浏览器工具调整 channel；本机证据仅声明 Windows Edge。

## 实际结果

- 首轮相关 AppTest / Replay / 原 UI / 检索回归：23 passed。新增身份异常检查及最终浏览器结果待下方追加。
- 冻结器初次发现新增合成主题与旧受控向量并列导致偶发排名失败，已通过隔离 fixture 的主题向量修复；生产检索代码未变。
  失败保留于本机 `var/product-d3-freeze-01/02`，不当作真实模型评测或已成功的案例。
- 早期浏览器运行因选择器定位失败退出；仅修验证定位，不将失败运行记为通过。
- 完整回归以更新后的 PR Linux CI 实际结果为准。此前 Windows 历史 POSIX / 凭据工具限制见 [首批验证记录](product-validation.md)，未扩大为本次产品核心修复。

## 回滚

只撤销本次 #27–#29 的 Product 提交即可返回 #26 的 `7a159d7`；无生产数据库迁移，
无 Build/Query、Prompt 或模型默认参数变更。固定快照可单独恢复至经过复核的 commit。
录像是合成应用操作素材，供 C 线剪辑；正式 3–5 分钟 MP4、PPT/PDF/报告和最终验收仍按团队分工办理。
