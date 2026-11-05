# Personal Core Release — pending team integration

2026-11-05，个人主线已经进入Release收口；最终验收和source commit见RELEASE_MANIFEST。三位队友的任务仍由其本人交付，本次未改Issue状态、未合并PR、未推他人分支。

## Product：#39、#26–29

GitHub只读核实：PR39 OPEN，head `7a159d7e3f2baacdc7ae510cb42a060befb1afba`，base `codex/v2-6d-production-safe`，分支`team/product-console-v2-6d`；目前标题仅Overview/Console导航(#26)，不能据此宣称Timeline/比较/视频均完成。

接入边界：继续Streamlit→FastAPI，不让Console直接访问SQLite。Build、Source、Relation、Projection和Index必须来自同一完整build_id；Trace读取`GET /queries/{id}`，引用定位(dataset_id,sample_id,dia_id)。公开默认Hybrid，Dynamic显式可选；新Console不可暗自恢复Dynamic默认。

Timeline接现有`/builds/{id}/bonus/timeline?entity=...&dimension=...`，Graph接`/bonus/graph`并保留结构归属边与模型关系边的区别。实验比较读取冻结公开聚合JSON，不触发评测run；答案、Gold及逐字source审阅留受控目录。

离线演示独立factory=`locomo_memory.release_viewer:create_replay_app`，UI=`replay_ui.py`；共享ExportCatalog负责SHA/身份/来源/时间。可在Console里增加链接，不得把只读按钮转到`POST /queries`/Build/Resolve/Answer。独立Replay目前不依赖PR39。

队友仍须提供最终Console/Timeline/Trace/比较页面的可审查commit、浏览器证据和无key路径；合流只调整展示/HTTP契约，不重写个人QA或重新调参。

## Architecture：#38、#30–33

只读核实PR38仍OPEN、CHANGES_REQUESTED，head `0f470a3b3aac782b42b082b199e2fa81a12cf837`，base `codex/v2-6d-research-safe`。语义审查问题未关闭，不进入个人默认问答链。

后续仅在非作者复核通过后按opt-in Sidecar接入；默认关闭不产生新字段语义或额外检索/模型调用。复核顺序：source身份/原文支持→事件归属→报告时间与事件时间→显式冲突/替代条件→并列/Unknown保留→关闭路径等价。Sidecar不能改写已有Memory/Relation/Projection或隐藏失败Trace。

队友需提供修复commit、逐项审查关闭证据、开/关隔离回归和回滚命令。现有个人Graph不是该Sidecar已通过验收的替代证据。

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
