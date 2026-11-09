# Personal Core Release — pending team integration

2026-11-05，个人主线已经进入Release收口；最终验收和source commit见RELEASE_MANIFEST。三位队友的任务仍由其本人交付，本次未改Issue状态、未合并PR、未推他人分支。

## Product：#39、#26–29

2026-11-09：按负责人授权，将Thorns-06最终候选`0401155aa2c270c48b942e4b410a9f4b390156b3`的产品模块与公开证据选择性整合到main基准`ba349cf`。没有合并安全分支的不同历史或覆盖个人核心。

正常`personal-release start`进入Console，顶部“五阶段工作流”保留原有上传、构建、问答、M5/Bonus与导出。公共查询及原页面仍默认Hybrid；Console读取已有Build和Trace，不自动生成或连接SQLite。六个产品模块和合成Replay的具体入口见[Product指南](docs/team-v2/README.md)。

原独立MemoryExport/Graph Replay继续使用`personal-release replay-offline-demo`。Product合成Replay使用`tools/team_v2/demo.py replay`；两者入口及数据契约分开，未将真实导出误标成合成，也未把历史757题报告当作新的M5成绩。

真人复核由xiaozhuozi39完成，公开留有本地跑通反馈与真人截图；负责人明确确认其已完整复核并授权整合。整合验证、版本、局限与回滚见[Product整合验收](docs/release/PRODUCT_INTEGRATION.md)。任务关闭以实际main合并及验证证据为准。

## Architecture：#38、#30–33

2026-11-09：负责人接受默认关闭、仅公开离线诊断范围，授权将已由 Thorns-06 复核通过的 `cd4db4c` 选择性整合 main 并冻结。研究规则、七文件专项与合成兼容入口保留，生产应用与 Product 不导入 Sidecar。已知时间修饰 P2 延期，真实 QA 接入不在本轮采用范围。

采用决定见 [ADR 0004](docs/adr/0004-sidecar-offline-adoption.md)，当前启动、验证、冻结与回滚见 [Sidecar 冻结说明](docs/release/SIDECAR_FREEZE.md)。原 ARCH01–04、ADR 0003 为历史材料，不代表当前仍等待复核。任务完成状态以实际合并及验证记录为准。

## Delivery：#34–37

提供可引用材料：

- 架构：docs/release/ARCHITECTURE.md；组件/入口/开关/测试：RELEASE_COMPONENT_MATRIX.md。
- 六份JSON：six-memory-exports-manifest.json，2031 Memory/37445关系/1465引用Source；完整副本本地受控，许可证/课程渠道确认前不放公共ZIP。
- 精确指标：experiments/m5-development/level-e-results-v1/official-scores.json和LEVEL_E_RESULTS_V1.md；E类别1–4 H=.402606/D=.409151，301/臂，CI[-.020133,+.034035]，失败记零。类别5为99题字面拒答，非事实F1。
- 历史757四策略和开发两版100题另见PERSONAL_EXPERIMENT_SUMMARY，绝不混在一个新全量成绩标题下。
- 图表/37页独立附录：docs/supplement/，引用时附SUPPLEMENT_ERRATA；不是团队最终报告。
- 个人演示：README/RUNBOOK，真实合成浏览器截图在experiments/personal-release；独立Replay无付费。
- Bonus采用边界：A保留；B浏览可选、多跳默认关；C/D默认关，未证明QA增益。
- 失败与费用：17个E失败保留；8 invalid_output、9 HTTP402；预约/已报usage峰价/实际账单分开。十阶段3975请求，预约USD197.6108655，已报usage峰价USD18.1208100，25未知usage预约USD1.3023021。不是实际账户账单。
- producer：E `0dbd98e7b296ef29d9998fa55d88d512f8ec85f1`；原M5开发28ce63d；当前Release代码身份见清单。页面修复没有新的泛化成绩。

队友仍须交可编辑PPTX/PDF、3–5分钟MP4、团队技术报告/总包，核对许可、命名、成员分工、所有引用和单包提交要求。个人包是版本化候选，不能当团队提交。课程平台最终提交还需要用户明确批准。

## 协作及状态同步

当前未找到明确关联本次个人Release的Notion任务记录，不声明已同步。已有关联任务应由负责人补录本文件与Release/Issue/PR链接；只有非作者复核通过且合并/验证完成后才标完成。本次没有替队友领取、送审或关闭任务，也没有持续后台监控。
