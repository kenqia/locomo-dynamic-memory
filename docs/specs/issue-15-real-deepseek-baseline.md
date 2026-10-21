## Problem Statement

肯恰大人需要从受控模型下的工程验证，推进到真实 DeepSeek、真实 LoCoMo 原始对话的课程开发集基线评测，并获得可以复查、恢复和比较的实验结果。

教师最新说明经用户转述确认：开发使用 `conv-26`、`conv-30`、`conv-41`、`conv-42`，本地测试集自行选择，最终评分集不公开。本组已预先固定 `conv-43`、`conv-44` 为本地测试集，开发期间不查看其模型成绩。四个开发对话共 2,080 个原始轮次、757 道 QA。

现有应用已具备官方数据导入、Memory 抽取、混合检索、历史关系、完整版本问答及四种策略评测，但真实生成模型质量尚未验证。当前 Full Text 受共享短证据预算限制，可能只看到原始对话前缀；评测结果在全部循环结束后才保存，中断可能丢失进度；成功样本均值也无法单独说明运行失败的影响。教师目前没有提供新增评分脚本或独立动态标签，官方 QA 来源证据不能替代动态关系或有效记忆真值。

使用者需要先取得可信的真实开发集基线与失败分析，再决定是否优化、制作模型辅助标注集，以及运行冻结后的本地测试。不能将受控测试、未核查模型标签或本地结果冒充教师最终评分。

## Solution

在现有本地应用和公开 FastAPI 边界上补齐真实基线运行所需的最小能力，保留现有 SQLite、模型适配器、检索和版本约定。固定开发/本地测试划分，提供完整对话 Full Text 基线，逐项保存与显式恢复评测，分别报告成功样本 QA、运行成功率和基线运行得分。

按离线准备、真实小规模预检、开发集全量运行、实验报告的顺序推进。四种策略为 `full_text`、`vector`、`hybrid_no_resolution`、`dynamic`，全量计划为 757 道 QA、3,028 个样本与策略组合。每一项具有可读取的执行状态、版本身份、结果或安全错误，重启后能够恢复，已持久化成功项无需重新调用模型。

Full Text 在模型上下文允许时送入完整原始对话，RAG 保留检索及证据预算；生成模型与生成参数保持一致，分别报告实际上下文、耗时和用量。动态准确率在独立标签到位前为“未评”。后续采用强模型辅助生成带原文证据的候选动态标签，由人独立核查小规模样本；本阶段不训练学生模型。

## User Stories

1. As a project owner, I want the four teacher-designated development conversations recorded explicitly, so that implementation uses the agreed course data.
2. As an evaluator, I want the local test conversations fixed before observing model scores, so that test selection does not depend on favorable results.
3. As a developer, I want development runs to exclude local test questions, so that routine execution cannot silently evaluate the held-out conversations.
4. As a reviewer, I want local test results distinguished from the hidden grading set, so that reported conclusions match the evidence available to the team.
5. As an operator, I want missing prerequisites detected before paid calls, so that avoidable setup failures do not start an expensive run.
6. As an operator, I want credential checks to reveal only availability, so that preparing the experiment does not expose secrets.
7. As a developer, I want the existing official DeepSeek adapter reused, so that the experiment does not introduce an unnecessary provider framework.
8. As an evaluator, I want requested and returned model identities recorded, so that a mutable service alias is not mistaken for a fixed weight snapshot.
9. As an evaluator, I want thinking mode and generation settings explicit, so that strategy comparisons use the agreed model configuration.
10. As a developer, I want the pinned local MiniLM model verified separately, so that controlled embeddings cannot be mistaken for a real dense retrieval check.
11. As an operator, I want a small live extraction check before a full build, so that provider and structured-output failures are identified early.
12. As an evaluator, I want a deterministic five-question development smoke set, so that pipeline checks can be reproduced without selecting questions by model performance.
13. As an evaluator, I want all four strategies exercised during the smoke run, so that the full comparison path is checked before the long experiment.
14. As an operator, I want a failed smoke run to preserve its progress and errors, so that diagnosis can precede the full run.
15. As an evaluator, I want memory construction to use only raw conversations, so that QA answers and evidence annotations cannot leak into the system.
16. As a reviewer, I want source and artifact checksums retained, so that the exact official input can be identified.
17. As an evaluator, I want each conversation pinned to a complete BuildVersion before generation starts, so that concurrent publication cannot mix artifacts within a run.
18. As an evaluator, I want Full Text to receive the complete ordered raw conversation when it fits, so that the baseline represents full-context answering.
19. As an evaluator, I want Full Text context-limit failures reported explicitly, so that a truncated prefix is not presented as complete text.
20. As an evaluator, I want RAG evidence budgets retained and disclosed, so that context costs remain understandable across methods.
21. As a reviewer, I want Full Text citations to point to actual Source Turns, so that the baseline does not invent extracted Memory records.
22. As an evaluator, I want Vector selection to remain based on the original question's dense ranking, so that its quality comparison remains a vector-only retrieval baseline.
23. As an evaluator, I want unused analysis and other baseline overhead recorded, so that reported cost differences reflect actual implementation behavior.
24. As an evaluator, I want the hybrid ablation to retain retrieval and history expansion while disabling effective evidence resolution, so that the contribution of resolution can be examined.
25. As an evaluator, I want the dynamic strategy to preserve the established query-time semantics, so that the experiment evaluates the implemented memory system.
26. As an operator, I want the full execution plan persisted before model calls, so that an interrupted run still has an identifiable scope.
27. As an operator, I want each sample and strategy result committed when it finishes, so that a later failure does not discard earlier work.
28. As an operator, I want persisted run progress readable while execution is incomplete, so that an HTTP wait is not the only evidence of progress.
29. As an operator, I want an explicit way to resume an interrupted run, so that completed work can be reused safely.
30. As an evaluator, I want resume to reject changed inputs, versions or execution identity, so that different experiments cannot be merged silently.
31. As an operator, I want completed successful items skipped on resume, so that persisted successes do not cause duplicate paid calls.
32. As a reviewer, I want in-flight calls with unknown outcomes distinguished from persisted success, so that the system does not claim exactly-once provider billing.
33. As an operator, I want failed or indeterminate items retried only through explicit recovery behavior, so that reading a run cannot silently trigger additional calls.
34. As a reviewer, I want attempt history and earlier errors retained, so that a successful retry does not erase the original reliability record.
35. As an operator, I want incompatible simultaneous executions rejected, so that two workers cannot race to execute the same unfinished item.
36. As an evaluator, I want all 3,028 planned combinations accounted for, so that omitted or pending items cannot improve the reported score.
37. As an evaluator, I want the existing official category-specific QA rules preserved, so that baseline scoring stays comparable to the retained LoCoMo implementation.
38. As an evaluator, I want successful scorable QA results reported separately, so that answer quality can be inspected without conflating execution failure.
39. As an evaluator, I want run success rates and counts reported against the planned scope, so that operational reliability is visible.
40. As an evaluator, I want a supplementary score that assigns zero to execution failures on otherwise scorable planned items, so that successful-only means cannot hide failed calls.
41. As a reviewer, I want missing gold answers, unknown categories and invalid evidence reported separately, so that unsupported labels are not fabricated or silently scored as zero.
42. As an evaluator, I want initial, expanded, effective and delivered source coverage kept distinct, so that retrieval and resolution effects remain inspectable.
43. As an evaluator, I want results grouped by strategy, conversation and QA category, so that aggregate means do not conceal specific weaknesses.
44. As a reviewer, I want build overhead separated from query-time overhead, so that construction reuse and per-question costs can be understood.
45. As an operator, I want reported token usage and missing usage distinguished, so that incomplete provider accounting is not presented as a complete bill.
46. As a reviewer, I want unassessed dynamic metrics labeled explicitly, so that model-generated tags do not become an unsupported accuracy claim.
47. As a reviewer, I want failure attribution tied to original sources and saved traces, so that a retrieval miss alone is not misreported as a semantic reasoning error.
48. As a developer, I want regression tests to use the existing public API seam, so that tests verify behavior without depending on private SQL or ranking internals.
49. As a project owner, I want machine-readable results, a concise experiment report and reproducible commands retained, so that another reviewer can inspect the actual experiment.
50. As an operator, I want isolated experiment storage and preserved existing data, so that stopping or revising the experiment does not destroy previous complete builds.
51. As a project owner, I want prerequisite blockers distinguished from completed verification, so that an unavailable credential cannot be reported as a passed live run.
52. As a project owner, I want implementation and live experiment status distinguished from review and course acceptance, so that creating this spec does not mark the work complete.

## Implementation Decisions

### Scope and dataset contract

1. 本规格承接已有动态记忆应用，首阶段交付为真实开发集基线与失败分析，不重新实现抽取、检索、关系、Current State 或问答架构。
2. 开发集固定为 `conv-26`、`conv-30`、`conv-41`、`conv-42`；本地测试固定为 `conv-43`、`conv-44`，两集合互斥。保存可复核的划分与原始数据身份。本阶段运行入口只选择开发集，不触发本地测试生成或读取其模型成绩；导入官方原件及核对元信息不等同于运行测试评测。
3. 官方原始 `conversation` 是构建来源。QA 答案、证据与辅助摘要只在评测侧使用，不传入抽取、索引、问题分析、关系判断、有效证据解析或答案生成。原始问题本身可以作为查询输入。
4. 固定四种策略及原始 QA 顺序，以原始样本身份和题目位置稳定标识计划项，避免相同问题文本导致去重误删。全量范围为每个开发问题运行四种策略，共 3,028 项；每项明确区分待执行、执行中、成功、失败或中断后结果未确认。

### Model and context behavior

5. 沿用官方直连 DeepSeek、`deepseek-flash`、非思考 Chat Completions、JSON 输出、Pydantic 校验和有限重试；不新增多供应商框架。现有默认温度为 0，最大输出为 4,096 tokens，超时为 60 秒，首次之外重试 2 次。实施前核对当时官方模型契约，保存请求/返回模型及核对日期。服务别名变化不视为固定权重复现。
6. 沿用固定 revision 的本地 `sentence-transformers/all-MiniLM-L6-v2`、384 维及实际输入长度校验，不用伪向量替代真实模型。安装仅进入项目独立环境，使用既有锁定的 Embedding extra，不引入全局依赖。
7. Full Text 使用同一对话的全部有文本 Source Turns，按原始位置组织；不存在文本的孤立会话时间不制造轮次。它不受 RAG 的最终证据截断预算限制，直接使用原始来源引用，`memory_id` 保持空值。回答模型、温度、输出上限、回答 Prompt 与 schema 和其他策略一致。
8. Full Text 必须保存全部应送达来源与实际送达来源的可核查信息；完整请求超出模型上下文时显式失败，不静默截断、摘要、分块合成后仍称完整全文。上下文能力以核对后的模型契约和实际服务结果为准；现有 regex 近似计数仅作为可复核文本预算，不冒充 provider tokenizer 或账单 tokens。
9. RAG 保留现有候选与证据预算，默认 BM25、Dense 与初始 K 均为 20，RRF 常数为 60，扩展最多 60 个候选、扫描最多 200 条、关系扩展一跳，候选近似预算 12,000、最终证据近似预算 6,000。对不同策略记录实际上下文及超预算行为，不声称与 Full Text 输入量相同。可逆参数不在本阶段按模型成绩反复优化。
10. Vector 使用原始问题的 Dense 排名，不使用分析关键词决定 Dense 选择，不做历史扩展或有效证据解析。现实现仍执行不影响 Dense 选择的问题分析和 BM25，这些调用与开销需要如实保留和披露；本规格不要求为成本美化而重构检索器。混合消融保留检索与相关历史扩展，不调用有效证据解析；动态策略使用现有完整链路。
11. 保留事件/状态、事实/计划/不确定性、来源时间及问题时间的既有语义。当前问题锚定对话已知状态截止时间，查询不写回全局关系或投影，不在线补抽原文。四种策略都不能把标准答案或证据标注作为回答依据。

### Persistent execution and public API

12. 复用本地 FastAPI、SQLite、既有完整版本发布和固定机制。运行首次模型调用前校验并保存所有对话的完整构建身份、原始输入和划分、完整计划、模型/检索/预算配置、Prompt/schema、计分版本及实现身份，状态可立即查询。版本在整个运行中固定，不随活动版本变化。
13. 保留已有评测输入和运行的创建/读取接口，并在相同公开 API 边界提供显式恢复能力。创建必须在执行前形成可持久读取的 Run ID，长运行不能要求客户端一直等待到全量完成才取得身份；读取 Run ID 不启动任何生成。具体资源命名和兼容性由实施时采用最小方案，并同步调用方和说明。
14. 每个样本与策略组合完成后立即事务保存结果、Trace 或安全错误、尝试记录、耗时及 provider 已报告用量，同时更新运行进度。运行尚未完成时也能读到计划总数和各状态数量。未执行或结果未确认项不伪装为成功或证据不足。
15. 重启后活动执行可以标记为中断，不宣称后台工作仍持续。显式恢复必须核对数据、题目顺序、划分、策略、固定构建、配置、Prompt/schema、计分版本与实现身份。实质不匹配时拒绝沿用 Run，保留旧结果并创建新运行，不原地混合实验身份。
16. 恢复跳过已持久化成功项；对已记录失败项和结果未确认项的重试需要显式选择，并保留此前尝试历史。模型已返回但事务未提交的崩溃窗口可能产生已计费而结果未知的调用，系统必须明确标注这种情况，不承诺跨外部 provider 的恰好一次调用或完整账单恢复。
17. 复用本地单进程与既有所有权/任务约束，避免同一 Run 的两次执行同时处理同一项。冲突请求明确拒绝；重复读取不重复调用，恢复完成项不重复调用。不引入外部队列、分布式锁或长期后台监控。进程内执行不等同于持续运行的独立自动化任务。
18. 尝试历史不可因恢复成功而抹去。结果汇总明确当前采用的结果，另保留首次执行失败和重试次数；同一逻辑计划项不因重试重复占分母，已报告用量覆盖全部可追溯尝试，未知用量单列。旧评测记录仍可读取，持久化调整不得清空既有构建与实验数据。

### Metrics and report semantics

19. 沿用保留的官方 LoCoMo 类别计分规则，包括类别 1 的子答案匹配、类别 2/4 的词干 F1、类别 3 的分号处理和类别 5 的拒答子串规则。类别 5 可以在没有普通 gold answer 时按既有规则计分，不把 `adversarial_answer` 当普通答案。该分类得分不统一改名为普通 accuracy。
20. 分别报告成功且可计分项的 QA 均值、可计分/不可计分数量和覆盖率；报告执行成功数相对全部计划项的运行成功率，并列出失败、待执行和结果未确认数。不完整运行必须标为部分结果，不能把已完成项数量冒充计划总数。
21. 基线运行得分以具有适用参考计分规则的全部计划项为分母，分子为成功且可计分项的实际 QA 分数总和，运行失败项贡献零分。缺 gold 或未知类别等本来不可计分项仍排除并单列。运行中尚未执行或结果未确认项不提前判零，最终得分保持未完成状态，直至范围有明确终态。该指标不覆盖或替代原 QA 结果，不称教师评分。
22. 证据映射和计分沿用对话内身份、合法复合 ID 拆分、来源去重及坏引用显式不可计分规则。不猜测修正引用，不把缺证据记零。每个阶段的来源覆盖独立报告，初始 K 的排序单位为 Memory；扩展集合、有效集合及实际回答上下文不混称同一个 Recall@K。Full Text 原始全体来源与实际回答上下文分别说明，不拿全体输入覆盖率冒充检索能力。
23. 汇总至少按策略、对话、QA 类别展示适用结果和计分分母，同时保留逐项原始分数。总体以逐题结果汇总，分对话均值单独展示，避免把不同聚合方式混写成同一数值。缺少独立动态标签时动态准确率为“未评”，关系或有效 Memory 自标不能充当 gold。
24. 构建开销与逐查询开销分开记录。保存 wall-clock 耗时、实际调用次数、重试、Embedding 已知调用信息和 provider 报告的 prompt/completion/total tokens。部分或未知用量不可写为零，不将不完整 token 合计宣称为完整费用；如提供金额，必须有当时可核查的价格口径，不能编造。
25. 失败分析检查原始证据、抽取结果、初始召回、历史扩展、有效证据解析及回答引用。只有证据足够才归因；仅命中/未命中 gold 来源不能直接证明语义事实已抽取或状态判断正确。来源级标注到固定构建 Memory 的映射仍需独立核查，本阶段不实现新的动态标注流水线。

### Execution sequence and operational boundaries

26. 先完成受控回归与真实本地 MiniLM 检查，再执行已有 opt-in 的真实 DeepSeek 小型抽取检查。检查进程是否提供凭据但不读取、打印或复制凭据值；应用仅在显式生成操作中通过现有受保护环境读取凭据。缺凭据时完成不依赖凭据的准备和验证，再报告缺项，不索取聊天中的 API key。
27. 完整构建 `conv-26` 后，按官方 QA 原始顺序为类别 1–5 各选首个问题，共五题，运行四种策略作为真实预检。它检查结构化输出、来源、完整版本、全文行为、结果保存及恢复，不设质量分数门槛。预检链路失败先定位并记录，再推进全量；不能把五题分数冒充 757 题结果。
28. 预检后对四个开发对话构建并固定完整版本，运行全部 3,028 个计划项。预检成功项只有在输入、构建、模型、Prompt、实现等身份一致且可核查复用时才复用，不通过手工抄分拼出全量结果。进度中断、凭据不可用或模型失败时保留实际已完成范围。
29. 提供能复现导入、构建/恢复、固定版本、预检、全量执行/恢复和读取报告的本地入口，优先调用现有公开 API 与已有项目工具。输出机器可读结果、非敏感运行清单和可阅读实验报告；不新增另一个业务实现或要求人为操作数据库。
30. 使用隔离的实验数据库与产物目录，保留现有数据库和完整构建。准备中的本地配置只含非敏感字段；凭据不进入配置快照、导出、请求错误、仓库或 Issue。停止运行保留结果，代码回滚和实验数据保留分别处理。
31. 同步更新受影响的运行、评测及检查说明，记录实际执行日期、模型服务身份、依赖版本、命令、结果、失败及未执行项。代码与离线准备可先完成；真实服务不可用时保留明确阻塞，不能把规格发布或测试跳过视为真实验收。

## Testing Decisions

1. 用户已明确确认沿用现有 FastAPI 公开 API 作为主要测试边界。通过应用工厂与公开 HTTP 接口完成官方导入、构建、发布、评测创建、读取和恢复；使用真实 SQLite、BM25/Dense 排序与融合、关系、扩展及版本逻辑，仅控制外部生成模型和默认测试中的 Embedding。避免依赖私有 SQL、内部循环或插入顺序断言。
2. 高质量测试验证可观察行为、输入隔离和持久化结果；不为简单文档或配置字段写镜像测试，不以受控模型的语义答案证明真实模型质量。已有评测基线测试、版本固定与契约恢复测试、查询错误 Trace 测试为先例，不引入第二套测试框架。
3. Full Text 回归使用超过现有短证据预算的有序合成对话，将必要事实放在末尾。通过公开请求触发评测，在受控 provider 边界验证实际收到末尾及全部应有 Source Turns，结果中的引用可定位真实来源。另验证超限得到明确失败，不退回前缀或切换策略。RAG 的预算仍按其原有规则执行。
4. 四策略行为测试验证 Vector 仅按 Dense 选择、混合消融不执行有效证据解析、动态策略执行解析、Full Text 不伪造 Memory，并检查标准答案及证据标注未进入生成输入。额外分析调用需要留在成本审计中。
5. 恢复测试通过公开 API 创建运行，在首个或若干项完成后模拟后续执行中断，重启应用，读取已保存进度并显式恢复。受控 provider 的调用记录证明已提交成功项没有重跑，尚未完成项有可解释状态；不能只检查最终均值相同。
6. 在 provider 返回后、结果提交前的未确认窗口测试可观察状态与恢复选择，不声称测试保证真实 provider 不重复计费。测试读取不调用模型、重复恢复完成 Run 不重跑、运行冲突被拒绝、失败尝试历史保留。
7. 身份测试分别改变问题/顺序、策略、划分、构建、配置或影响产物的契约，验证恢复不会混合不同实验。运行中切换活动完整版本后，既有 Run 仍固定原版本。保留旧格式记录的读取回归。
8. 计分测试构造成功、执行失败、缺 gold、未知类别、坏 evidence 和类别 5 缺普通答案的混合样本，核对 QA、运行成功率、补充得分、未完成状态、分母和分类汇总。独立验证重试不重复计分、失败记录不被成功覆盖、无动态真值保持未评。
9. 划分测试覆盖固定四个开发 ID、两个互斥测试 ID、开发运行不触发测试问题的生成，以及全部 757 题和四策略计划的确定性。真实 QA 结构计数检查无需付费，也不属于模型质量结论。
10. 真实 Embedding 与 DeepSeek 分别沿用 `local_embedding` 和 `live_model` opt-in 标记，默认回归与 CI 不调用付费服务。MiniLM 必须验证真实固定 revision 的加载、编码与超长拒绝；DeepSeek 小型检查不能替代真实 `conv-26` 全链路预检。
11. 现有针对性命令为 `uv run --locked pytest tests/test_evaluation.py tests/test_queries.py -q`；恢复与版本测试按实际改动加入已有入口。真实 MiniLM 使用 `LOCOMO_LOCAL_EMBEDDING=1 HF_HUB_OFFLINE=1 uv run --locked --extra embedding pytest -m local_embedding -q`；真实生成检查使用 `LOCOMO_LIVE_MODEL=1 uv run --locked --extra embedding pytest -m live_model -q`，仅在受保护凭据就绪时执行。
12. 最终真实验收核对运行身份、计划项总数、每项状态、逐项保存和恢复、四种策略结果、来源映射、失败统计及报告可复查性。不预设分数提升、通过阈值或固定调用时长。不要求新建浏览器验收范围；若实施影响现有页面调用，则运行其既有针对性检查。

## Out of Scope

- 在本阶段运行 `conv-43`、`conv-44` 的模型评测、查看其成绩、依据成绩调整系统，或改挑更有利的测试对话。
- 访问、模拟或宣称知道教师隐藏评分集，宣称完成教师正式评分、课程验收或达到未公布的分数阈值。
- 本阶段的开发集效果调优、超参数搜索、新检索架构、多跳图方案、在线补抽、跨语言支持或新的生产依赖框架。
- 强模型辅助标注流水线的实施、标注模型采购和选择、全量人工标注、LLM judge 自动充当课程真值，以及学生模型训练或蒸馏。后续方向已确认，但不作为当前基线交付的前提。
- 分布式执行、外部任务队列、供应商插件体系、持续自动化监控，以及保证跨 provider 的恰好一次付费调用。
- 修改认证源、全局 shell、hooks、MCP 或 Codex 配置，收集或保存 API key、token、cookie、session 及私密日志。
- 本次规格发布之外的代码 push、PR、合并、部署、GitHub 设置调整、课程提交或代替非作者验收。本次不自动生成或发布实现 tickets。

## Further Notes

本规格依据 2026-10-19 已确认的 Q1–Q6，与 [Issue #4](https://github.com/kenqia/locomo-dynamic-memory/issues/4) 及已完成的评测基础能力衔接；当前代码基线为 `3d9d37c`。数据划分与 Full Text 的新约定更新历史规格中的等待固定划分和共享短证据预算前提，其他领域语义沿用。原 spec、ticket 和历史实验记录保持原文。

领域术语依据 `CONTEXT.md`，完整协议与访谈记录分别位于 `docs/adr/0002-real-model-baseline-protocol.md` 和 `docs/decisions/real-deepseek-evaluation-interview.md`。这些本地记录与本规格一致使用“课程开发集”“本地测试集”“隐藏评分集”“模型生成动态标签”“已核查动态标签”和“基线运行得分”。

本轮只读准备检查发现当前进程未提供 `DEEPSEEK_API_KEY`，项目环境缺少 `sentence-transformers` 和 `torch`；固定 MiniLM 缓存目录存在但未验证加载。这些是运行前准备状态，不是本规格缺失的需求，也不代表其他终端或服务的环境。当前没有新鲜的真实服务结果，创建规格不能写成实验已完成。

用户调用 `to-spec` 授权将本规格发布为 GitHub Issue 并标记 `ready-for-agent`，成功后将正文原样保存在 `docs/specs/`。该标签表示可开始实现，不表示已经领取、实现、复核或验收。本次没有发现与新规格明确关联的 Notion 任务记录，当前也没有可用的 Notion 更新工具；Notion 状态和 Issue 链接未同步，需要负责人补录，不能把任务标为完成或复制整份规格正文到 Notion。
