# M5 最终交付证据索引

2026-11-05（Asia/Shanghai）。本轮开发候选、六份严格 JSON、最终配置锁、一次独立 Level E、Gold 评分与全部 800 项 AI 来源盲审均已形成真实工件。类别 1–4 完整分母 F1 为 Hybrid **0.402606**、Dynamic **0.409151**，差 **+0.006545**，95% 区间 **[−0.020133,+0.034035]**；尚无稳定质量突破。保留预先确定的 Hybrid 默认候选、Dynamic 显式可选、Bonus 默认关闭建议，未切换现有生产默认。

本报告供下一轮 Release 冻结和 M5 制作使用。它不代表 main 整合、生产部署、教师隐藏评分或课程最终验收完成。未 push、PR、merge、部署或制作课程 ZIP/PDF；未识别关联 Notion，未同步或标记任务完成。旧初稿及阶段观察时点可从 Git 历史恢复。

## 14 项交付对照

| # | 交付要求 | 最终证据与结论 |
| --- | --- | --- |
| 1 | 开发分支和每个 commit | 分支 `codex/m5-final-conv44-relations-20261104`。全量范围以 `915fac02f6b9296e331f913a1e78717cfa7e2df1` 为基线；[最终 Git/文件清单说明](../../experiments/m5-development/final-delivery-v1/README.md)绑定明确截点，逐一列出祖先提交。旧 `commit-history.txt` 仅是早期快照。 |
| 2 | 实际新增/修改文件 | [最终文件差异](../../experiments/m5-development/final-delivery-v1/changed-files.txt)、[逐文件 SHA 与清单边界](../../experiments/m5-development/final-delivery-v1/manifest.json)；实现职责见[实现矩阵](IMPLEMENTATION_MATRIX.md)。私有原文、答案、引文、数据库、原始日志和凭据不提交 Git。 |
| 3 | 四类 Bonus 完成情况 | A 只读状态/版本/来源 timeline；B Graph 浏览和有实际路径的两跳检索；C 全字段可逆分组与可选 wire 适配器；D 自适应和时间软优先均已实现并有工程验证。五状态和采用边界见[Bonus 矩阵](BONUS_FEATURES.md)与下表。 |
| 4 | 已真实运行实验 | Level A 工程/合成/契约/受控 Browser；Level B 六臂各 757 题离线回放；60 单位历史关系 AI 诊断、40 题适用性 AI 诊断；两轮各 200 项开发 QA 与来源审阅；conv-43/44 构建/恢复；独立 E 400 题双臂 800 项。Level D、新 Bonus QA、组合 B5/B6 没有运行。 |
| 5 | 有真实值的指标 | [E 结果](LEVEL_E_RESULTS_V1.md)提供类别分离 QA、Recall@5/10/20 来源代理、来源/引用支持、拒答与人物/事件/时间/列表错误、请求/重试/失败预约与已报费用、Build 摊销、延迟、成功率、tokens、whole-process CPU/RSS 与存储快照。完整分母、成功子集和条件分母分列。 |
| 6 | 未测量指标 | 新模型关系 Accuracy/Macro-F1、Effective Memory Selection Accuracy、独立 Atomic Fact Recall/Retention、人工/教师真值、双审一致性、实际账户账单、GPU、分臂 CPU/RSS、本地 embedding 硬件货币成本、新 Bonus QA/解码质量与 Level D 均未测；标 `not_measured`，不补零、不推算。 |
| 7 | 历史与新成绩分开 | 历史 757 F1：F0 .464869、V0 .519714、H0 .521886、D0 .515133，属于旧 Run；本轮没有新 757 答案。两轮开发和 E 的不同样本/模型/输入/thinking 配置另列下表，不能作严格因果对照。 |
| 8 | 真正改善质量的方法 | 目前没有证明稳定事实质量突破。input v2 普通题差 +.043530，区间跨零；E 类别 1–4 差 +.006545，区间跨零；来源共同确定 297 对为 28 改善/18 退化，差 +.033670，区间 [−.010101,+.077525]。不把字面拒答或来源命中当作事实正确率。 |
| 9 | 最大收益与退化 | Graph expanded 来源代理略升但交付无增益；可逆分组仅省完整 messages 代理 tokens .02925%；Adaptive 交付来源代理 −.029349。E 列表遗漏条件净少 6/317 对、时间错误净少 4/308 对，事件错误净多 3/319 对；多指标区间/选择限制见结果页。D 已报峰价费用约 H 的 7.9026 倍、p50 约 3.51 倍；没有稳定质量/成本收益。 |
| 10 | 推荐进入最终 M5 | 原有关系/版本/时间/来源、严格 JSON；可关闭状态来源面板、Graph 浏览作为展示候选；Hybrid 默认候选建议、Dynamic 显式可选。需下一轮最终整合验收后决定，未修改生产默认。 |
| 11 | 默认关闭项 | Graph 多跳、压缩 wire、自适应和新增时间软优先默认关闭；Graph 浏览显式开启。保留原必做时间/状态能力。PropMem 固定配置 REJECT；Hindsight 仅保留既有 Phase 9 研究范围。 |
| 12 | 六段与独立测试 | conv-26/30/41/42/43/44 六份严格 JSON 完成，共 2,031 Memory、37,445 关系；[六份清单](../../experiments/m5-development/six-build-exports-v1.json)。E 800 项全部终结冻结，H394/D389成功，17失败保留；终态根/非作者审计、Gold 评分、800项来源审阅完成。测试已曝光，此后重跑只算回归。 |
| 13 | 请求与剩余预算 | 十阶段累计 **3,975 请求、预约 USD197.6108655、已报 usage 峰价金额 USD18.1208100**；25 个未知 usage 预约 USD1.3023021 完整保留。E 本身 2,112 请求、预约 USD105.4516575，未用硬限容量 3,888 请求/USD1,282.4779425；不转移、不自动重启，不是账户余额。实际账单未读。 |
| 14 | 下一轮工作 | Release 截点/生产整合、当前全仓与 Browser 端到端验收、展示脚本与最终课程文档、必要人工来源/关系审核、教师隐藏评分与关联任务状态补录。最终制作课程 ZIP/PDF另行开展；不因 E 结果调整算法再称同一独立测试。 |

## Bonus 工程与实验边界

| 类别 | 已实现、已测试 | 真实实验结论 | 推荐状态 |
| --- | --- | --- | --- |
| A 复杂状态/版本/来源 | 生产基础、只读 timeline；既有关系/时间测试、合成边界、真实 conv-26 Browser | 新面板真实 QA 收益未测；历史诊断不等于新模型关系准确率 | 保留基础，面板作为可关闭展示候选，待最终集成验收 |
| B Graph | 来源/边/Build 可追溯浏览；真实两跳、后续 Resolution 接口；HTTP/契约/Browser/合成端到端 | 757 回放：444题有新增长度2路径，共新增7,689 Memory题次；最终交付来源无增益；没有新 Bonus QA | 浏览可选展示；多跳默认关闭 |
| C 压缩/分组 | 完整字段可逆文件包、可选 wire；roundtrip、HTTP、757消息回放 | 完整 answer messages 代理tokens 5,558,932→5,557,306，省1,626（.02925%），30/757启用；Provider解码质量未测 | 保留研究与展开演示，默认关闭；文件包4.1666%节省不是查询降本 |
| D 自适应/时间 | 候选优先级、按问题关系扩展、单日/相对/未知区间软优先；合成与时间解析回归 | Adaptive交付来源代理下降.029349，新增temporal总体代理无增益；无新QA | 默认关闭新增机制，保留原时间能力；组合未晋级 |

PropMem 已固定官方 commit/许可证并对上游方法做隔离 AST/合成检查；因人物、来源和时间契约风险 REJECT 直接采用，没有安装完整后端、实现 Adapter、运行开发 canary 或付费抽取，不替换原 Memory。详见[实际审计](../../experiments/m5-development/propmem-audit.json)。没有对未经证明的 Bonus 继续付费组合实验。详细设计见 [Graph](GRAPH_MEMORY_DESIGN.md)、[压缩](COMPRESSION_DESIGN.md)、[Adaptive/Temporal](ADAPTIVE_TEMPORAL_DESIGN.md)与[候选决策](M5_CANDIDATE_DECISION.md)。

## 成绩、来源与事实性

| 实验 | 实际结果 | 解释范围 |
| --- | --- | --- |
| 历史757答案Run | F/V/H/D .464869/.519714/.521886/.515133 | 旧答案 token F1，不是本轮新757成绩 |
| 本轮757来源回放 | 753可评/4不可评；H/D/Graph/分组/时间最终代理 .773801，Adaptive .744452 | 无新生成/Resolution；Graph expanded .823098 对 D .819920，不是答案收益 |
| 旧Level C，80普通+20诊断 | 普通H/D .399883/.228329；诊断 .456503/.293302；151成功/49输入失败 | resolution low、160000bytes/96000代理tokens；失败保留 |
| input v2，同一开发样本 | 普通 .401172/.444702；诊断 .434314/.473472；H99/D100成功，输入失败0 | 新生成全disabled、640000bytes/192000代理tokens；同时改两项配置，不能归因单参数；非新757成绩 |
| E，类别1–4 | 301题，H/D .402606/.409151；差+.006545，95%[−.020133,+.034035] | 失败记零；仅成功 .405299/.417473；无稳定提升 |
| E，类别5 | 99题，字面拒答H/D .858586/.808081；差−.050505，区间[−.101010,0] | 不是事实正确率；语义盲审另报 |
| E，全部400混合规则均值 | H/D .515461/.507886；差−.007575，区间[−.032061,+.017161] | 不称纯F1或事实准确率；conv43差−.020694、conv44+.012518，区间均跨零 |

E 的完整逐题和逐组结果在[官方规则分数](../../experiments/m5-development/level-e-results-v1/official-scores.json)，来源 Recall 代理在[派生结果](../../experiments/m5-development/level-e-derived-results-v1.json)。每臂399题来源可可靠映射，1题不可评保留null；Dynamic有效集合与交付来源覆盖下降，不能据此判定事实适用性。

三名独立于本次生成实现和候选选择的 AI 已读完整来源、回答与explanation及全部citation：242/242/316项，合计1,796条逐字引文。每项一名AI，非人工/教师真值、无双审一致性。公开[来源统计](../../experiments/m5-development/level-e-results-v1/source-review-summary.json)、[条件配对](../../experiments/m5-development/level-e-results-v1/source-review-paired.json)及[标签provenance](../../experiments/m5-development/level-e-results-v1/source-review-provenance.json)；原文和引文仅留私有目录。根代理已知官方分数，按标签抽查后触发计划/事实、完整explanation边界自查；这次抽查不是严格盲审。A/B/C改2/9/10项，初终SHA均留存，未向审阅者提供Gold或分数、未改生成和评分。

原文支持为H250/343、D233/307；实际引用支持H195/321、D197/310；正确拒答H100/143、D95/134，错误拒答43/39，另12/11拒答未确定。失败、不适用与未确定分列；这些不同分母的率不代表完整400题事实正确率。错误类条件配对的正差代表更多错误；v1通用字段`improved/regressed`只是正/负差计数，必须按`positive_difference_means`解释。正文展示已使用正确方向。

历史60关系单位Accuracy .833333/Macro-F1 .766513及40题适用性中25可评、严格集合18/25、集合Macro-F1 .8542857、状态23/25，属于历史单名AI诊断；不能冒称E新模型关系真值。新关系/有效选择/Atomic Fact指标仍为`not_measured`。

## 六份导出、配置与一次执行

conv-44最终392 Memory、384/384任务、7,134关系；第六份SHA `1006ce3d855ffb496cb8a2c029276511707427bb7129474013f4b1768639611f`。完整性不等于关系语义准确率。所有旧失败和恢复费用保留，终结入口不得重启。

锁定实现 `0dbd98e7b296ef29d9998fa55d88d512f8ec85f1`，82 producer与真实blob一致；系统锁SHA `3b6e3fbcad1670226f1f9d8e1c9fa96436b104893a875527d078dc4948671ac6`早于问题正文读取。新生成thinking disabled、不发reasoning_effort；当日请求alias deepseek-flash映射Flash-1017，alias不是不可变权重pin。640000 UTF-8 bytes、resolve192000代理tokens、输出32768、模型重试2、transport重试0；Bonus全关，Build不重建，历史Build high等血缘保留。

生成冻结SHA `3cab5d1b486290184e67906d61427f18803b415d82fe18f5f5f7190ae89664a6`。H394/400、D389/400成功；8 invalid_output、9 model_http_error，后者安全元数据为18次HTTP402/insufficient_balance，不能称输入超限或语义失败。Unknown item 0，未知usage18，未重跑。根及[非作者终态审计](../../experiments/m5-development/level-e-independent-terminal-v1.json)通过后才读取Gold。

## 费用、资源与私有归档

E 查询H851/D1261请求，预约USD36.2805087/69.1711488；已报峰价金额USD.8705958/6.8800119，比例7.9026；未知usage预约USD.3424887/.6097818保留。118重试已报金额USD.2651367，是总请求的重叠子集，不重复加总。实际账单未读，授权硬上限不是消费。

共享Build七阶段920请求、预约USD45.0439116、已知峰价金额USD6.6141915，7历史Unknown预约USD.3500316；联合双臂只构建一次，独立部署每臂承担完整Build÷400。Build+Query已报部分单价H USD.01871196825/题、D USD.0337355085/题，排除缺失usage和本地硬件货币成本。十阶段累计值见第13项和[派生费用](../../experiments/m5-development/level-e-derived-results-v1.json)，不含旧757全部历史费用。

H/D item p50 2.370230/8.314747秒、p95 3.935324/12.403791秒。whole-launcher wall4530.687530秒、userCPU311.002229秒、systemCPU29.620455秒、峰值RSS830608KiB；不分摊分臂CPU/RSS。stage原大小508347589bytes是评分前快照；后续509059714bytes差额恰为712125bytes的scores.json，原快照未覆盖。GPU/分臂资源未测。

私有[归档报告](../../experiments/m5-development/level-e-results-v1/private-archive-report.json)绑定实际tar：55,172,721bytes、863成员，SHA `72d6bd2dd5261ff863ec861eab780a5b580e4dec6889f5948ac73f45f44a31f5`。逐成员SHA回读、成员0600/目录0700，三份执行库/ledger通过SQLite一致性备份并核logical hash，原stage/main/WAL身份未改变。仅收显式白名单；没有备份reference Gold库、凭据、raw stdout/stderr、WAL/SHM或锁。归档是证据回放，不能恢复一次性生成入口。

## 验证与复现入口

- [数值独立复核](LEVEL_E_NUMERIC_REVIEW_V1.md)：逐800项评分/Recall/分组、bootstrap、2112请求费用/延迟/摊销重算，数值不一致0；storage快照差异已解释。
- [来源与实际归档独立复核](LEVEL_E_POSTPROCESSING_REVIEW_V1.md)：完整来源汇总、配对方向/分母、provenance及实际tar与执行库快照核查。
- [后处理工具回归与边界](LEVEL_E_REPORTING_REVIEW_V2.md)：21项真实producer合成测试已由作者和非作者通过；不是全仓验收。
- 历史工程/Browser测试见[实现矩阵](IMPLEMENTATION_MATRIX.md)、[Bonus矩阵](BONUS_FEATURES.md)和[实验结果](EXPERIMENT_RESULTS.md)。本轮后处理未改生产/UI；旧全仓与Browser测试仅对原截点有效，未拼接成当前全仓通过声明。
- [环境锁](../../experiments/m5-development/environment-lock-application.json)、[实验协议](EXPERIMENT_PROTOCOL.md)、[E免费后处理命令](LEVEL_E_REPORTING_V1.md)、[最终SHA清单](../../experiments/m5-development/final-delivery-v1/manifest.json)。离线复现仅做冻结证据校验；禁止重复prepare/preflight/runner/execute。

下一轮先固定Release审阅截点，明确现有默认与候选默认变更，检查与main差异，再运行该截点的全仓离线测试和真实/合成Browser验收；制作状态、来源、Graph和六份JSON展示材料。如需修复，用已曝光E做回归并保留原工件；新付费实验另申请具体额度。没有人工/教师标签的指标继续保留`not_measured`。
