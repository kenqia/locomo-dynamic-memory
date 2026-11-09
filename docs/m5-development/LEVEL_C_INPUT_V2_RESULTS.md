# Level C input v2 开发集结果

2026-11-04。input v2 已实际完成 200 项生成、完整冻结、终态审计、开发 Gold 评分、200 项独立 AI 来源审阅和本地私有归档：Dynamic 100/100 成功，Hybrid 99/100 成功，没有输入限制失败。普通 80 题 Dynamic−Hybrid F1 为 +0.043530，但题目 bootstrap 95% 区间包含零，尚不足以认定稳定质量收益。独立来源支持的同题改善也很有限，不能用字面 F1 代替事实正确性。

本页仅描述分支 `codex/m5-final-input-v2-20261104` 的独立新阶段。执行和范围见[执行记录](LEVEL_C_INPUT_V2_EXECUTION.md)，数值见[metrics-summary](../../experiments/m5-development/level-c-input-v2-results-v1/metrics-summary.json)。本树继承的旧 Level C 文档保留旧实验观察时点，不代表 input v2 当前状态。

## 完整分母评分

全部 100 道固定开发题均可评分，类别为 1–4，没有类别 5。本阶段未测 adversarial refusal。只有全部生成冻结且审计通过后才读取四开发对话的 Gold；留出 conv-43/44 的 QA/evidence/answers 未读。

| 分层 | 策略 | 计划 | 成功 | 完整分母 F1，失败记零 | 仅成功 F1 |
| --- | --- | ---: | ---: | ---: | ---: |
| 普通 | Hybrid | 80 | 79 | 0.401172 | 0.406250 |
| 普通 | Dynamic | 80 | 80 | 0.444702 | 0.444702 |
| 诊断 | Hybrid | 20 | 20 | 0.434314 | 0.434314 |
| 诊断 | Dynamic | 20 | 20 | 0.473472 | 0.473472 |

普通题配对差 +0.043530，95% 区间 [−0.008095, +0.095318]，27 提升、14 退化、39 不变；诊断题差 +0.039158，区间 [−0.056014, +0.134784]，5 提升、3 退化、12 不变。区间来自固定 seed 的 2,000 次题目 bootstrap，仅四个已暴露开发对话，属于探索性比较，不保证跨对话泛化。

普通题各对话差值依次为 conv-26 +0.073853、conv-30 +0.039104、conv-41 +0.051830、conv-42 +0.009332，每对话 20 题。两臂共同成功的 79 普通题上，Hybrid 0.406250、Dynamic 0.437673，差 +0.031423；该子集按运行成功筛选，不能代替完整分母。

唯一失败发生于普通题 Hybrid 的 answer 操作，三次输出均触发 `answer_evidence_status_required`，终态为 `invalid_output`。该项此前的 query analysis 也计入费用，四次物理请求合计峰价上界 USD0.006765。没有截断输入、替换策略、放宽契约或追加补跑。

## 延迟、资源及成本

| 分层 | 策略 | item p50，秒 | item p95，秒 |
| --- | --- | ---: | ---: |
| 普通 | Hybrid | 2.506 | 5.192 |
| 普通 | Dynamic | 8.848 | 14.253 |
| 诊断 | Hybrid | 2.519 | 3.229 |
| 诊断 | Dynamic | 8.461 | 11.719 |

真实生成进程耗时 1,226.564 秒，CPU 84.965 秒，峰值 RSS 655,556 KiB，未使用 GPU。item 时长包含运行失败；模型单次尝试与各阶段时长另存，不能混称服务延迟基准。

| 策略 | 物理请求 | 内部重试 | 已报告 usage 峰价上界，USD | 其中重试，USD |
| --- | ---: | ---: | ---: | ---: |
| Hybrid | 211 | 11 | 0.2330898 | 0.0081639 |
| Dynamic | 311 | 11 | 2.3531001 | 0.0875961 |
| 合计 | 522 | 22 | 2.5861899 | 0.0957600 |

522 次全部 `response_received` 且 usage 完整，Unknown 为零。输入 7,814,253、输出 201,595、合计 8,015,848 tokens。Dynamic 每 100 项的峰价上界是 Hybrid 的 10.0953 倍，普通题 item p50 约为 3.5311 倍；这些比值只描述本次成本和时长，不代表质量性价比已通过。

独立额度硬限为 1,500 请求／USD346.9824，已预约 USD27.8063415，剩余容量 978 请求／USD319.1760585。预约是保守风险上界，已报告 usage 金额按执行前核对的官方峰时 cache-miss 单价计算，**实际账单未读取**。额度不跨阶段转移，余量不授权补跑、Level D/E、构建或发布。

## 运行身份与结论边界

实现 `b3ba45c`，准备身份 `4aadaff`，明确授权 `2a3cd85`；后处理合成夹具修复为 `e2af676`。生成冻结 SHA 为 `1bfc058224d9ba1c8ba941c39f7ef0ebbc27db9736b4935d742a0e4541147de3`，plan SHA 为 `3c9adc27b22d1b1da0175a508636ba51e8cdb2fd744a6faed566a963c2a79af6`。

全部新 query analysis、resolution、answer 请求显式 thinking disabled，不发送 `reasoning_effort`；522 次请求与响应 model 均为 `deepseek-flash`。执行前官方页面映射为 `DeepSeek-V4.1-Flash-1017`，响应只提供可变 alias，没有不可变服务端 pin 证明。messages 上限 640,000 UTF-8 字节，完整 resolution 预算 192,000 正则代理 tokens，最大输出 32,768 tokens，每操作最多三次尝试。四开发 Build 原样复用，历史 extraction/relation thinking 血缘没有改写，Bonus 关闭。

终态审计重建准备时保护快照，确认 Source、Memory、Relation、Projection、Index、Build 不变；candidate query 200、expansion 200、Dynamic Trace 100，与冻结文件逐项一致。evaluation 表为空，审计未打开 Gold 源库。评分是随后单独执行的开发 Gold 投影读取；审计工件中的 `gold_read=false` 描述审计工具自身，不能解释为整个阶段从未评分。

旧 Level C resolution low／160,000 字节／96,000 代理 tokens 的普通 F1 为 Hybrid 0.399883、Dynamic 0.228329，Dynamic 输入失败 49 项。本次同时改变 thinking 和两项输入预算，又是已暴露开发样本，不能把差异归因于单一参数。原实验完整保留，不补算失败，也不复用其来源标签。

历史 757 题仍为 Full Text 0.464869、Vector 0.519714、Hybrid 0.521886、Dynamic 0.515133，属于旧 Run；本轮 100 题不是新 757 题成绩。没有运行 Bonus QA、Level D 或 Level E；动态关系准确率、有效 Memory 选择准确率、独立原子事实召回等没有因此获得新真值。

## 独立来源审阅及交付

两名未参与本次生成实现的 AI 审阅者分别负责 conv-26/30 与 conv-41/42，各 100 个匿名单位，实际通读全部 2,080 条 Source Turn，逐项核对答案、解释和全部实际引用。604 条逐字引文、200 个唯一身份与新 manifest 绑定均通过固定 `validate` 和 `score`。包隐藏策略、Gold、分数及 resolver 选择；每项一名审阅者，没有双审一致性或人工真值，文字风格仍可能泄露策略。没有复用旧标签。

| 指标 | Hybrid | Dynamic | 总体 |
| --- | --- | --- | --- |
| 来源支持 | 68/79；20 不确定 | 75/84；15 不确定、1 N/A | 143/163；35 不确定、1 N/A |
| 实际引用支持 | 72/77；12 不确定、10 N/A | 76/80；12 不确定、8 N/A | 148/157；24 不确定、18 N/A |
| 合理整体拒答 | 6/15；4 不确定 | 6/13；4 不确定 | 12/28；8 不确定 |
| 错误人物 | 0/88；11 不确定或 N/A | 0/91；9 不确定或 N/A | 0/179；20 不确定或 N/A |
| 错误事件 | 0/82；17 不确定或 N/A | 0/84；16 不确定或 N/A | 0/166；33 不确定或 N/A |
| 错误时间 | 0/56；43 不确定或 N/A | 0/57；43 不确定或 N/A | 0/113；86 不确定或 N/A |
| 列表遗漏 | 10/49；50 不确定或 N/A | 9/51；49 不确定或 N/A | 19/100；99 不确定或 N/A |

语义统计单列唯一运行失败，不将它计为正确或错误。支持分母为 supported+unsupported；拒答分母仅含可判断整体拒答；错误分母为 true+false。判断不确定或不适用时保留原值，不补成“无错误”。当前没有检出确定的人物、事件和时间错误，不能据此宣称所有答案正确，尤其时间与列表的未判断比例较高。16 次可判断错误拒答和19 次列表遗漏仍是质量缺口。

两臂都运行成功且来源判断确定的普通题共有 60 对：2 对改善、1 对退化、57 对不变，平均差 +0.016667，95% 区间 [−0.033333, +0.066667]；诊断题 14 对为 1 改善、1 退化、12 不变，平均差零。引用支持差在普通 61 对和诊断 14 对中均为零。这些是经过共同成功及可判断筛选的探索性 AI 判断，不能作为全部 100 题的因果收益。分层、逐对话、匿名逐项标签、配对差和 provenance 另存，不覆盖初始数值结果中的 pending 快照。

原始答案、Trace、完整 conversation、逐字审阅和数据库留在 Git 忽略的 `var/m5-development/`。实际归档为 `level-c-input-v2-raw-terminal-v1.tar.gz`，19,959,603 bytes，SHA `a04434350708642510f2f3e57d5e264c9dbb9fbd207ddd9a645a0093b2e62e6c`；SQLite backup 纳入已提交 WAL，显式白名单排除 WAL/SHM、锁、原始日志和凭据，229 个成员逐项回读通过，原始文件和两数据库逻辑快照未变。tar 及每个内部文件均为 `0600`。公开仅提交身份、数值、匿名标签和复现入口，详见[归档报告](../../experiments/m5-development/level-c-input-v2-results-v1/private-archive-report.json)。

独立数值复核者已重跑终态 audit 并核对完整对象相等，独立重算全部200项数值、配对 bootstrap、费用和初始 manifest，见[终态复核](LEVEL_C_INPUT_V2_TERMINAL_REVIEW_V1.md)。其曾修改本次生成前实现，因此工具作者身份限制如实记录；两名来源审阅者则未参与本次生成实现。后处理合成测试 43 passed，未因本次文档与数据归档重跑全仓。

input v2 本阶段已结束，总任务仍未完成。四个已批准付费阶段累计 1,429 物理请求、预约 USD70.7806551、已报告 usage 峰价上界 USD7.9025151；原关系阶段的 7 次 transport Unknown 全额预约 USD0.3500316 保留，实际账单未读，见[合并终态账本](../../experiments/m5-development/cost-ledger-including-input-v2-terminal-v1.json)。这些不包括既有历史757题的全部成本，也不能将未知usage当零。

原实验树 `codex/m5-final-development-20261104` 的 `0aae59c` 记录 conv-43 已 related、未 complete/publish；conv-44 仍 failed，唯一恢复三次仍违反时间原文契约。六段完整导出、最终候选锁定与 Level E 仍缺；不自动续费、恢复、整合 main 或远端写入。未识别关联 Notion 记录，本次未同步或标记总任务完成。

本次证明扩大输入预算后当前100项 Dynamic 可以完成运行，并显示正向的小样本 F1；没有证明稳定事实收益或良好的总成本效率。保留 Dynamic 作为可选候选，当前不据此改变默认策略或自动晋级 Level D/E。四类 Bonus 的工程与既有离线结论保持原记录，本轮 Bonus 关闭，没有新增 Bonus QA 成绩。
