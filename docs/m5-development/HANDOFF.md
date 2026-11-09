# M5 开发候选交接

2026-11-05 最新终态：conv-44 与六份严格 JSON 均已完成独立复核。锁定的独立 Level E 已单次冻结 800 项，根代理与非作者终态审计通过后才读取 Gold 评分。H/D 成功 394/389（每臂400）；类别1–4完整分母 F1 为 0.402606/0.409151，差值区间跨零；类别5字面拒答单列。本阶段 2,112 请求、预约 USD105.4516575，末段 HTTP402 及18次未知 usage 预约保留；没有重跑。800项来源盲审、条件语义汇总与私有白名单归档已完成；来源支持297可判定对净增10对，区间仍跨零。独立复核和14项底稿见[最终交付索引](FINAL_DELIVERY_EVIDENCE_INDEX_V1.md)。当前结果与测量边界见 [Level E 结果](LEVEL_E_RESULTS_V1.md)。下文历史检查点保留各自时点，不代表本次终态。

2026-11-05 当前状态更新（下文保留原历史时点）：conv-44 单任务恢复已首请求成功，384/384 任务与 7,134 关系完成；六份 complete 严格 JSON 均已独立复核。最终配置在读取问题正文前提交于 `191349f`，实际 questions-only Level E 准备与根 25 项、非作者 6 组审计通过。固定 400 题、H/D 共 800 项，新 ledger 0 请求；尚未授权或执行 Level E，类别/答案/证据未读。新申请上限为 6,000 请求 / USD1,387.9296，旧余额不转移。当前工作树为 `/home/kenqia/my_folder/locomo-worktrees/m5-final-conv44-relations-20261104`，见[实际准备](LEVEL_E_PREPARATION_V1.md)与[最新 gate](LEVEL_E_GATE.md)。

2026-11-04。当前为可审查的本地开发候选，总任务尚未完成，未冻结 Release。Level C 开发集真实 QA、评分、完整性审计和独立 AI 来源审阅已完成；conv-43 关系阶段已终结为related，并通过根代理终态审计。没有 push、PR、main 合并或部署；未识别关联 Notion 任务，未同步，也未标记完成。

当前 conv-44 后续状态见[关系阶段交接](../../M5_CONV44_RELATIONS_V1_HANDOFF.md)：抽取成功，新本地索引与384关系任务已准备，付费执行尚未获批；下文保留原开发候选交接时点。

## 工作树与代码

工作树：`/home/kenqia/my_folder/locomo-worktrees/m5-final-development-20261104`。分支：`codex/m5-final-development-20261104`，生产基线 `915fac02f6b9296e331f913a1e78717cfa7e2df1`。主仓 M4 未提交成果和 research-next 历史实验未被清理或改写。

全部提交可执行 `git log --reverse --oneline 915fac0..HEAD` 查看；文件清单见 `experiments/m5-development/changed-files.txt`，源码 SHA 见 `run-manifest.json`。近期新增工具提交：

- `323917c`：固定开发集 QA 准备、授权和 Gold 隔离。
- `c8e5c09`：记录明确授权和独立运行边界。
- `3b8e4b4`：冻结 QA 终态完整性、物理账本和策略身份审计。
- `b9c2b91`：独立 AI 来源审阅及逐字引文校验。
- `7cee8f9`：完整分母 QA、配对比较、运行和费用汇总。

后三项仅新增工具、测试和复核报告，未修改 `src/` 或已启动阶段的冻结生成模块。没有新增依赖、数据库迁移或认证配置修改。

## 已实现与采用建议

| 模块 | 已验证范围 | 采用建议 |
| --- | --- | --- |
| A：冲突与多版本 | 来源绑定的状态演化、历史/当前/Unknown、计划取消及共同参与者 synthetic 测试；真实 conv-26 浏览器演示 | 保留生产能力和可关闭来源面板；不宣称全部真实语义覆盖 |
| B：Graph | 图浏览、有界两跳、路径和 Build/对话隔离；444 题真实两跳路径 | 浏览适合展示；Graph 检索默认关闭，未证明 QA 收益 |
| C：Compression | 可逆分组、完整展开、实际 wire 编码与预算；含提示代理 tokens 仅降 0.02925% | 默认关闭；模型解码质量和实际账单节省未测 |
| D：Adaptive/Temporal | 可复现路由、时间范围和显式 requested_date；自适应交付来源退化 | 默认关闭；不声称复杂时间准确率改善 |

PropMem 固定官方 `807ae6d7d8a5b76f6fe964d5a581d96c036e2ac4`、Apache-2.0；源码与合成方法探针显示多人选择、名称子串、无矛盾降权和逐事实来源限制，拒绝直接采用该配置。没有真实 Canary；Hindsight 仅保留 Phase 9。详细五种采用状态见 [Bonus 功能](BONUS_FEATURES.md)。

## 真实实验与指标

历史 757 题 F1：Full Text 0.464869、Vector 0.519714、Hybrid 0.521886、Dynamic 0.515133，全部属于旧 Run，不是本轮新成绩。

Level B 已完成两轮 757 题、H/D/B1–B4 六组的真实离线 Expansion/Answer packing 回放，753 题可评分来源映射、4 题不适用。没有运行新 Resolution 或 Answer。最终包来源覆盖 D 0.773801；Graph/Compression/Temporal 相同；Adaptive 0.744452，差 −0.029349，配对题 bootstrap 95% [−0.042629, −0.016730]。Graph 扩展来源覆盖 0.819920→0.823098，最终包无收益。来源代理不代表事实召回或 QA 正确率。

Level C 已完成固定 80 普通题 + 20 诊断题、Hybrid/Dynamic 共 200 项真实生成。Hybrid 100/100 成功，Dynamic 51/100 成功；35 项因批准的 messages 字节上限拒绝、14 项因既有完整 resolve token 预算失败。普通题完整分母 F1 为 H 0.399883、D 0.228329，差 −0.171553，95% 区间 [−0.256728, −0.092833]；诊断题 H 0.456503、D 0.293302。失败记零，没有截断或补跑。

全部生成冻结后才读取开发 Gold。终态审计确认四份 Build、Memory、Source、Relation、Projection、Index 不变，200 个 candidate、200 个 expansion 和 100 个 Dynamic Trace 与冻结结果一致，evaluation 表为空，421 次请求全部有完整 usage。两个非作者来源审阅者实际核对全部 200 项和完整 2,080 条开发来源，461 条引文通过逐字校验：来源支持 105/141，另 10 不确定、49 运行失败。每项一人 AI 审阅，没有人工/教师真值或双审一致性。

Level C 没有发现 Dynamic 总体质量突破。共同成功子集中的正差值受成功选择影响，不能替代完整分母；不晋级 Bonus、Level D/E 或改变生产默认。全部新 QA、语义分母、延迟及费用见 [Level C 真实结果](LEVEL_C_RESULTS.md)。

动态关系独立 AI 审核 60 单位：50/60、Macro-F1 0.766513、系统未判断 28/60；参考 RETAIN 33、UPDATE 4、undetermined 23，无 SUPERSEDE/CONFLICT 真值覆盖。历史 query-specific 诊断 40 题中 25 可判断，严格集合 18/25、集合 Macro-F1 0.854286、状态 23/25；15 不确定单列，非新模型有效选择成绩。

## 六段数据与付费阶段

四开发 Build 完整导出并严格通过 memory-export-v2，共 1,237 Memory、884 引用 Source、22,691 关系，索引/投影/来源身份有 SHA；六段 conversation 均完成导入和身份验证。留出 QA/evidence/answers 始终未读。

抽取及唯一获批恢复已终结：78 次请求、预约 USD3.4624767、已报告 usage 峰价上界 USD0.2265405，Unknown 0。conv-43 原库为 extracted、402 Memory、34/34 片段；conv-44 为 failed、383 Memory、33/34。ordinal18 恢复三次仍为 `extraction_time_expression_required`；不放宽时间原文契约、不自动追加尝试。原成功片段和 785 Memory 保持不变。历史原件见 `live-extraction-summary.json`，恢复后当前结果见 `live-extraction-post-recovery-v1.json` 和 `extraction-recovery-outcome-v1.json`。

conv-43 独立副本已有402×384真实缓存MiniLM索引，400/400关系任务已完成、7,620条标签，终态为related。根代理终态审计通过保护表、其他Build、来源/关系及投影检查，未publish/query/QA；非作者已独立重跑并核对完整审计对象一致，见[独立终态复核](RELATION_TERMINAL_REVIEW_V1.md)。408请求含401 response_received、7 transport_unknown，预约USD20.2028820、已知usage峰价上界USD3.9199638，未知预约USD0.3500316保留。原冻结relation thinking high如实保留；原抽取库仍extracted，conv-44仍failed。剩余792请求/USD84.5830380不授权新阶段。见[关系终态](../../experiments/m5-development/conv43-relations-terminal-v1.json)。

Level C 独立授权 1,500 请求/USD130.9824；终结 421 请求、预约 USD19.3089549、usage 峰价上界 USD1.1698209，Unknown 0。剩余 1,079 请求/USD111.6734451 不自动授权补跑。三阶段终态合计907请求、预约USD42.9743136、已知usage峰价上界USD5.3163252，7项未知用量均为终态transport_unknown且保留预约。最新汇总见[终态费用](../../experiments/m5-development/cost-ledger-terminal-v1.json)；旧cost-ledger.json为历史运行中快照，原样保留。实际账户账单未读取。

## 验证、复核与复现

最新生产全仓回归为 `full-offline-final-v7`：`664 passed, 4 deselected, 325.80s`，仅既有 Starlette/httpx 弃用提示。本轮没有修改生产模块；新工具独立新鲜验证分别为 audit 24、semantic review 36、results 7 项通过，不冒称又跑过全仓。

非作者 `CODE_REVIEW_V6` 已实际交付，关系本地拒绝检查点 P2 修复后独立 37 项通过；关系阶段工具 28 项、审计工具 14 项通过。三个 Level C 工具的复核报告保留原发现和关闭记录，公共 QA 与语义数字均独立重算通过。这些是列明范围的复核，不等于全项目 Release 批准。

测试和回放入口见 [实验协议](EXPERIMENT_PROTOCOL.md) 与 `experiments/m5-development/reproducibility-commands.md`。所有新输出目录必须不存在。私有 Memory 导出、答案、Trace、Gold 评分中间件、逐字审阅和完整归档保存在被 Git 忽略的 var，不提交原文；克隆代码不会自动获得这些本地工件。公共结果仅包含数值、受控身份和 SHA。

归档说明见[关系终态私有归档v2](../../experiments/m5-development/conv43-relations-raw-archive-v2.json)：13个成员逐项回读验证，私有gzip为3,015,384 bytes，SHA-256为 `22d9cb655a975c9bc931dbd6ecbea8628ba44d5f26f1a76b6aaeda36e31d01d5`，源逻辑快照前后不变。v2以明确白名单排除运行时WAL/SHM；v1及其误含空WAL/SHM的限制说明保留，不覆盖原件。归档含私有原文和Memory，原件不提交；两次归档均无Provider调用。

## 尚需完成

关系阶段已终结并完成根代理终态审计，非作者已独立重跑并核对完整审计对象一致，见[独立终态复核](RELATION_TERMINAL_REVIEW_V1.md)。仍缺 conv-44 完整构建、两份留出 complete Build/严格导出、符合用户已确认全关闭thinking要求的最终评测，以及候选锁定后的一次独立 Level E。新的付费尝试或阶段必须有具体预算和明确授权；不能把现有额度余量当批准。完整事实召回/保留、新模型有效选择准确率、Bonus 真实 QA 和实际账单仍未测。

最终候选须锁定实现、策略、模型、Prompt、参数、评分脚本与成本政策后再评价留出；读取测试答案后不能继续调参并称独立验证。Release 冻结、生产整合、最终报告/展示/ZIP 属于下一轮，不自动执行。

## 输入上限后续方案（已准备并复核，待付费授权）

用户确认完整resolve预算96,000→192,000代理tokens及物理messages上限160,000→320,000字节，随后询问字节再翻倍是否全部可过。为保留原已执行阶段的producer身份，后续全thinking disabled方案已在独立工作树 `/home/kenqia/my_folder/locomo-worktrees/m5-final-input-v2-20261104`、分支 `codex/m5-final-input-v2-20261104` 完成准备和非作者复核，本地提交为 `b3ba45c`。准备说明见 [Level C input v2 准备结果](/home/kenqia/my_folder/locomo-worktrees/m5-final-input-v2-20261104/docs/m5-development/LEVEL_C_INPUT_V2_PREPARATION.md)。具体待审批提案为640,000字节/192,000代理tokens、同80+20两臂200项、最多1,500物理请求/预约USD346.9824；尚未批准新付费执行。原首次输入离线门槛可行性不是新生成成功率或重试保证，新旧thinking与预算不同，后续比较仍属探索性。

## 首次 resolve 输入诊断交付

`tools/m5/level_c_input_diagnostics.py` 只读重建100项 Dynamic 的完整首次调用方输入。入口和出口复用完整终态审计，绑定原 plan、producer、settings/inputs、200项冻结工件及受保护数据库逻辑快照；重建期间使用同一只读事务。它没有原始 wire capture，不把重建哈希称为实测 wire 哈希。最终工件为 `experiments/m5-development/level-c-input-diagnostics-final-v2.json`；旧 `level-c-input-diagnostics-v1.json` 保留，最终工件以 `supersedes_report_sha256` 绑定旧版。

原160,000 bytes/96,000 regex tokens门槛下，51项同时满足、35项仅超字节、14项同时超两项。原首次输入在320,000/192,000门槛下87/100可容纳，在640,000/192,000下100/100可容纳；这些是离线阈值结果，没有验证重试feedback、真实模型成功或解码质量。内层JSON空白压缩只使1项新跨越原字节门槛，可逆grouping使原失败项新跨越门槛0项。

作者定向验证：`PYTHONPATH=src:. /home/kenqia/my_folder/locomo-dynamic-memory/.venv/bin/python -m pytest -q tests/test_m5_level_c_input_diagnostics.py tests/test_dynamic_resolution_budget.py tests/test_m5_budget.py tests/test_m5_wire_compression.py`，结果28 passed。非作者复核独立新鲜运行诊断tests，17 passed；冻结归属P2已关闭，无新P0/P1/P2，见 `LEVEL_C_INPUT_DIAGNOSTICS_REVIEW_V1.md`。此前公共状态一致性审阅见 `DELIVERY_STATUS_REVIEW_V1.md`，其SHA表只代表审阅时快照。本次诊断未调用provider、未读取Gold/留出QA，也没有新的付费授权。
