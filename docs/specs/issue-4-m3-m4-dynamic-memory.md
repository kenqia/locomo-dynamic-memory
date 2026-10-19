## Problem Statement

长期、多会话对话中的人物状态、计划和偏好会变化。单纯找到语义相关的历史，无法保证它适用于问题所指的时间和状态；初始检索也可能漏掉推理所需的前序阶段。使用者需要能回答当前与历史问题的动态记忆 Web 应用，并能核查每条记忆、关系及答案的原始证据。

当前仓库已经确定宏观路线和实现决策，下载并校验了 LoCoMo 官方数据，但源代码、应用依赖、启动入口及测试入口尚未建立。本 spec 将已确认的领域规则、模块边界、数据契约、配置及验收场景转为可实现的基线，不把文档存在当作功能完成。

## Solution

构建一个以英文为唯一检索语言、可使用中文界面的本地 Web 应用。使用者导入 LoCoMo 原始对话，构建可持久化、可恢复、可追溯的原子 Memory 与历史关系，查看 Current State，并通过英文问题检索和解析有效证据。查询展示初始候选、相关历史扩展、关系判断、采用或未采用证据的理由，以及有来源引用的答案。

构建时维护持久化历史关系与可重算状态投影；查询时根据具体问题进行有效证据解析，补判只进入本次 Trace。查询不改写全局状态，也不在线补抽原文。完整构建版本切换前保留旧版本可用性。统一 JSON 导出、针对性验证及评测接入构成代码交付的一部分；缺失课程标注不得用系统自己的判断替代。

## User Stories

1. As a developer, I want to import the official LoCoMo conversations, so that I can build memories from the intended source data.
2. As a developer, I want to retain upstream sample, session and dialogue identifiers, so that I can locate every original turn.
3. As a reviewer, I want source text, speaker and session time to remain available, so that I can verify extracted claims.
4. As an evaluator, I want QA answers and evidence annotations isolated from memory construction and retrieval, so that evaluation does not leak its targets.
5. As an evaluator, I want generated observations, summaries and event annotations distinguished from raw conversation, so that I do not mistake supplied annotations for system output.
6. As a developer, I want the dataset version, checksums and license retained, so that I can identify the exact input and its provenance.
7. As a developer, I want one Memory to express one independently assessable claim, so that changes to employment do not invalidate an unrelated residence claim.
8. As a reviewer, I want one Memory to cite multiple source turns, so that claims supported across several turns remain traceable.
9. As a reviewer, I want several memories to cite the same turn when appropriate, so that a multi-fact statement is not forced into one record.
10. As a user, I want events distinguished from continuing states, so that later changes do not erase events that happened.
11. As a user, I want facts, plans, intentions and uncertain claims distinguished, so that a planned move is not reported as a completed move.
12. As a user, I want negation preserved, so that not working for an employer is not stored as working for that employer.
13. As a developer, I want entities scoped to their conversation, so that identical names in separate conversations are not silently merged.
14. As a developer, I want state keys to identify dimensions rather than specific values, so that changes of employer remain discoverable in one employment history.
15. As a user, I want compatible facts within a state dimension to coexist, so that multiple jobs are not automatically treated as contradictions.
16. As a reviewer, I want session time, original time expressions and interpreted event time kept separately, so that relative dates can be checked.
17. As a user, I want uncertain dates represented as ranges or unknown values, so that the system does not manufacture precise timestamps.
18. As a user, I want an undated current-state question anchored to the selected conversation's last session, so that the answer does not imply knowledge of later real-world events.
19. As a user, I want explicit historical dates to control evidence selection, so that an old-state question is not answered from Current State alone.
20. As a developer, I want construction to maintain evidence-backed MemoryRelation records, so that later queries can reuse known history.
21. As a reviewer, I want relation labels accompanied by reasons, sources and applicability conditions, so that I can challenge an incorrect update.
22. As a user, I want prior stages retained after an UPDATE, so that I can ask what happened before the current stage.
23. As a user, I want superseded states retained as historical evidence, so that I can still ask where someone lived before moving.
24. As a user, I want unresolved contradictions shown with both sources, so that the system does not choose a claim merely because it is newer.
25. As a reviewer, I want insufficient relation evidence represented as undetermined, so that uncertainty is not mislabeled as conflict or retention.
26. As a developer, I want Current State to be a rebuildable projection of history and relations, so that a second independently edited truth store cannot drift.
27. As a user, I want query-specific relation judgments to remain local to the query, so that asking historical questions does not change subsequent current-state answers.
28. As a developer, I want successful construction fragments and failed fragments persisted, so that I can retry failures without rebuilding everything.
29. As a user, I want visible progress, failures and incomplete work, so that a partial memory collection is not presented as complete.
30. As a developer, I want at most one active construction task, so that the first implementation does not require a distributed task system.
31. As a user, I want the previous complete version to remain usable during a rebuild, so that a failed replacement does not remove a working memory collection.
32. As a user, I want queries pinned to one complete construction version, so that memories, relations, state and indexes cannot come from different versions.
33. As a user, I want first-time incomplete construction to allow inspection but not complete-library answers, so that the application communicates its readiness honestly.
34. As a user, I want the original English question to participate in retrieval even when query analysis fails, so that an optional analysis step cannot disable search.
35. As a developer, I want BM25 and dense candidates fused by rank, so that incompatible raw scores are not added directly.
36. As a user, I want related history added after initial retrieval, so that a before-application question can recover the earlier research stage.
37. As a reviewer, I want each added memory linked to its expansion origin and reason, so that history expansion is explainable.
38. As a developer, I want expansion depth and candidate budgets bounded and configurable, so that retrieval cannot expand indefinitely.
39. As a reviewer, I want truncation visible, so that a capped candidate set is not described as complete evidence.
40. As a user, I want effective memories selected for the question's entity, state dimension and time, so that relevant but inapplicable memories do not determine the answer.
41. As a user, I want explicit insufficient-evidence outcomes, so that the system does not invent an answer or silently repair its memory during a query.
42. As a reviewer, I want the answer, historical candidates, effective evidence and relation explanations shown together, so that I can follow the selection process.
43. As a user, I want Chinese interface labels with original English evidence, so that navigation is accessible without altering retrieval language.
44. As a developer, I want Streamlit to access business functionality through FastAPI, so that validation and state changes have one backend entry.
45. As a developer, I want DeepSeek official API access isolated behind one model adapter, so that model-specific parameters are not duplicated throughout the application.
46. As a developer, I want explicit non-thinking Chat JSON requests and schema validation, so that the baseline has a recorded and consistent generation configuration.
47. As a user, I want empty, truncated or invalid model responses surfaced after finite retries, so that failures are not treated as valid empty memories or answers.
48. As a developer, I want one local English embedding model with length checks, so that dense retrieval does not silently discard part of a memory.
49. As a developer, I want retrieval budgets and model settings centralized in configuration, so that I can change them without editing scattered constants.
50. As an evaluator, I want effective configuration, model identity, prompts and construction versions recorded, so that I can interpret differences between runs.
51. As a reviewer, I want secrets excluded from configuration snapshots, exports, traces and errors, so that reproducibility does not expose credentials.
52. As a user, I want a unified JSON export with memory sources and version identity, so that exported records correspond to the displayed collection.
53. As an evaluator, I want Memory-level rankings and Source Turn-level evidence coverage recorded separately, so that retrieval metrics have an explicit unit.
54. As an evaluator, I want initial, expanded and effective evidence stages reported separately, so that expansion gains are not hidden inside an ambiguous Recall@K.
55. As an evaluator, I want composite evidence references parsed while originals remain intact, so that valid multi-turn evidence is not lost.
56. As an evaluator, I want malformed or missing evidence mappings explicitly reported, so that excluded retrieval scores cannot silently inflate results.
57. As an evaluator, I want Full Text, Vector RAG and state-resolution ablations with recorded generation and evidence budgets, so that comparisons are interpretable.
58. As an evaluator, I want extraction, initial retrieval, expansion and resolution failures distinguished when ground truth permits, so that I can locate the cause of an error.
59. As a developer, I want deterministic behavioral tests at the public business API, so that I can validate the real storage and retrieval pipeline without relying on paid model nondeterminism.
60. As a reviewer, I want separately identified live-model and browser checks, so that mocked behavioral tests are not presented as proof of model quality or working UI integration.
61. As an evaluator, I want official course splits and dynamic annotations treated as explicit external inputs, so that the system does not manufacture a test set or its own grading targets.
62. As a project owner, I want implementation to proceed in verifiable vertical slices, so that data provenance, construction, querying and the Web application can each be reviewed before expansion.

## Implementation Decisions

### Architecture and module responsibilities

1. 首版为本地应用及单体后端。Python、FastAPI、Streamlit、SQLite、Pydantic 构成技术基线；Streamlit 只承担交互与展示，通过 FastAPI 调用业务功能，不直接读写数据库。
2. 业务模块职责为：导入与来源管理、记忆构建、Memory 与关系持久化及状态投影、查询分析、混合检索与历史扩展、有效证据解析与答案生成、JSON 导出与评测接入。模块是代码组织边界，不拆微服务，不预设插件框架。
3. 外部模型依赖集中到独立 Model Adapter；Embedding 也有窄调用边界。第一版各接一个模型，不为尚无实现的 GraphRetriever 创建空接口。
4. 构建链路为原始对话、抽取原子 Memory、校验来源与时间、比较相关历史并维护关系、重算 Current State、构建索引、检查完整性、发布完整版本。构建不读取 QA 标准答案或证据作为提示输入。
5. 查询链路为英文问题、Query Analysis、Hybrid Retrieval、Initial Top-K、Related History Expansion、Effective Memory Resolution、Answer 与 Evidence/Trace。Query Analysis 失败时仍以原问题检索，推断的实体和时间条件不能直接硬过滤掉可能相关的历史。

### Minimal data and API contracts

6. `SourceTurn` 至少保留对话 ID、会话 ID、轮次 ID、说话人、会话时间和原文。原始 `sample_id` 保持可追溯；轮次 ID 的唯一性限于对话范围，跨对话引用必须带对话身份。
7. `Memory` 至少保留 ID、构建版本、实体、状态维度、内容、Event/State 类型、陈述性质、否定信息、时间信息和一个或多个来源。一个 Memory 只表达一个可独立判断的陈述，多条 Memory 可引用同一原始轮次。
8. 事件与持续状态区分；历史发生事实不会因后续状态变化而消失。事实、计划/意愿、不确定陈述区分，否定保留。计划不成为已实现状态；事实陈述指原文的断言，不意味着系统独立核实了现实真伪。
9. `state_key` 由对话、实体和状态维度组成；雇主等具体值独立保存。实体默认按对话隔离，同名不自动跨对话合并。同键允许事实共存，不自动意味着单值、互斥或替代。跨维度不得仅因都涉及同一人物而建立替代关系。
10. 时间信息分别表达会话时间、原始时间表达、推导事件日期或范围，以及可被证据支持的状态有效区间。未知保留未知，不从会话时刻伪造事件时刻。推导保留锚点与依据。
11. `MemoryRelation` 至少保留两端 Memory、标签、适用条件、理由和来源，限定所属构建版本。关系不能永久抹除旧 Memory 的历史适用性。
12. `BuildVersion` 至少保留数据与配置指纹、生成及 Embedding 模型标识、Prompt/schema 版本、片段进度、完成状态。`QueryTrace` 至少保留固定构建版本、问题与查询时间、初始候选、扩展结果及原因、截断、有效证据、查询补判、答案与引用。
13. API 覆盖导入与数据检查、启动/查询构建及显式重试、浏览 Memory/来源/关系/Current State、提问与读取 Trace、JSON 导出。输入输出使用明确 schema，列表分页，错误形状一致，区分无完整版本、输入无效、构建未完成和外部调用失败。具体资源命名及 ID 编码属于可逆实现细节，不在此预设固定 URL。
14. API 与 LLM 返回是校验边界；来源引用必须存在且属于正确对话与版本。不能只校验 JSON 类型就信任模型编造的 Memory ID 或来源 ID。问题、导入文本及模型输出是待处理数据，不能作为修改系统规则或调用权限的指令。

### Two-stage relation and temporal semantics

15. 构建时与相关历史比较，持久化有证据支持的关系，并维护 Current State。Current State 是历史与关系的可重算数据库视图或缓存表，不是可独立编辑的第二份真相。
16. 查询时按人物、状态维度和问题时间选择有效证据，必要时补判未确定关系。补判只保存在本次 Trace，不自动写回全局关系或 Current State。查询不回原文重新抽取并修改记忆库；证据不足时说明不足，允许查看来源或显式重建。
17. RETAIN 要求证据支持旧事实在相应语境下继续适用，不能仅凭无新消息；UPDATE 表示同一过程阶段推进；SUPERSEDE 要求新证据明确替代同一状态维度旧取值；CONFLICT 表示相同适用条件下互相矛盾且无法消解。证据不足可保持关系未确定，不强迫四选一。课程标注到位后核对口径差异。
18. 默认“现在”指所选对话最后一次会话时的已知状态，界面及答案显示截止时间。明确历史日期控制有效证据选择；超出证据时间范围时不声称掌握之后的现实变化。历史问题不能固定使用 Current State 代答。
19. Caroline 从研究领养机构到申请、再到通过面试属于可检查的 UPDATE 场景；明确从住所 A 搬到 B 可支持同维度替代。失业事件与开网店事件可同时保留，开店本身不能证明不再受雇，也不能无条件标为全局 SUPERSEDE。

### Retrieval, expansion and centralized configuration

20. BM25 使用 rank_bm25；Dense 使用本地 `sentence-transformers/all-MiniLM-L6-v2` 与 NumPy 相似度检索；融合使用 RRF，不能直接相加不同通道原始分数。保留原问题及各通道排名，去重后解析状态。
21. 初始配置为 BM25 和 Dense 各 20 条、RRF 融合后初始 20 条。从初始集合扩展一跳已有关系，再补充同一 state_key 下与问题时间有关的历史。合并去重后最多 60 条；同键补充不再启动第二轮遍历。数字、RRF 参数和候选/token 预算统一放在配置文件，不能散落在业务代码中。
22. 每条扩展结果记录入口和原因，达到数量或 token 上限时显式记录截断，不能宣称证据集合完整。排序、稳定去重和最终证据预算在实现中固定并随运行保存，后续只在允许的开发数据上调整。
23. 扩展解决初始检索遗漏，不能恢复构建时未抽取的事实。Trace 和实验记录要能区分抽取遗漏、初始召回遗漏、扩展遗漏和解析错误；没有独立证据时只报告可能原因，不能伪称已确认错误归因。
24. 英文是唯一检索语言，记忆检索文本和问题使用英文。界面标签与说明可以中文，证据保留原文；首版不自动翻译中文问题进入检索，不承诺跨语言召回。
25. 集中配置还覆盖模型标识、显式思考开关、生成参数、有限重试与超时、分片和长度处理、检索与证据预算。每次运行保存去除凭据的实际生效配置；数据、模型、Prompt/schema 或会影响产物的配置变化必须体现到版本或缓存指纹，查询配置变化也要留痕，不能原地改写既有版本。

### Model integration and construction lifecycle

26. 生成模型使用 DeepSeek 官方直连，OpenAI 格式 Base URL 为 `https://api.deepseek.com`。按 2026-10-19 官方核对结果选择 `deepseek-flash`，当时对应 DeepSeek-V4.1-Flash-1017；该名称是可变服务别名，不是不可变权重快照。运行保存请求模型、返回模型标识、日期与当时已知服务版本，不自动在一次实验中途换模型。
27. 首版采用 Chat Completions，显式关闭思考，请求 JSON 对象输出，提示词要求 JSON 并给出所需结构，随后使用 Pydantic 校验。JSON 模式不等同于 schema 约束。空内容、截断、无效结构及无效来源有限重试，失败则明确报错，不能当作成功的空 Memory 或“没有事实”。
28. 费用不设上限，但不能无限重试。凭据由实现时采用的受保护本地方式提供，不写入仓库、普通配置、导出、Trace、日志或错误响应；本 spec 不包含凭据，也不要求用户在聊天发送凭据。首次真实调用必须有可验证的受保护凭据配置。
29. 本地 Embedding 在项目独立环境运行，模型输出 384 维向量。模型卡给出的默认长度上限为 256 word pieces，编码前检查，超长不能静默截断；采用的拆分、错误或聚合政策在实现中明确并测试，随索引记录模型 revision 与编码设置。首版不新增 Vector DB。
30. 构建按片段持久化成功结果、失败状态及版本，支持显式重试。相同片段重试不能无意重复插入同一版本的产物，重复导入/重启应通过可复核的身份或指纹策略处理。恢复策略应明确显示中断，不伪造继续运行；具体任务调度属于实现细节。
31. 首版至多一个构建任务运行，不新增外部任务队列。页面展示进度、失败及未完成项。未完成版本可检查，不能伪装成完整记忆库；没有任何完整版本时不提供完整库回答。
32. 每次查询固定一个完整 BuildVersion。新版本 Memory、关系、Current State 和索引完成且检查通过后整体切换；失败保留旧版本继续服务。不能混合版本，也不能在失败时破坏旧完整版本。修正错误关系通过显式构建/重建完成，不引入未讨论的在线手工状态编辑器。

### Evidence mapping, export and evaluation

33. LoCoMo 原始 conversation 是构建输入；observation 与 session_summary 是官方生成的辅助材料，event_summary 是事件任务标注，qa 是评测对象，不能将它们混作本系统抽取成果。Source Turn、Extracted Memory、Retrieved Memory 三种对象区分，Retrieved Memory 是查询结果身份而非第二份事实副本。
34. 统一 JSON 导出包含版本标识、结构化 Memory、多来源映射，以及导出范围内用于解释这些 Memory 的关系和状态信息；应可校验且与界面所选版本一致。不导出凭据，不把 QA 答案标注写进 Memory 导出。
35. 分别保存 Memory 级排序和 Source Turn 级证据覆盖。初始 Top-K、扩展集合、最终有效集合不能混称同一个 Recall@K。明确 K 的单位、来源去重、计分阶段及样本范围，课程口径确认前只报告有明确说明的诊断结果。
36. evidence 原值保留。包含多个合法 ID 的元素可显式拆分、逐个校验；畸形或找不到的引用不猜测修正。修正要有独立、可审查的映射。不可可靠映射的样本仍可计算适用 QA 指标，证据 Recall 标为不可计算，不按零或正确加入；汇总必须显示计分/未计分样本数与覆盖率。
37. QA 计分参考官方规范化、词干化与类别分支，不未经对齐就用普通 token F1 替代；缺少答案和对抗类别单独按实际可用标注处理。课程的动态关系与有效 Memory 标签不是官方 QA 脚本自动提供的，不能用 LLM 自标作独立真值。
38. 对照包含 Full Text、无状态判断的 Vector RAG，以及关闭本系统状态解析的消融。尽量固定模型、生成参数和最终证据预算，记录无法等同的上下文、截断及额外调用；记录耗时、模型调用与 token 用量，不预设提升幅度或通过阈值。
39. 官方数据已本地校验：10 段对话、5,882 轮、1,986 条 QA，上游 commit 为 `3eb6f2c585f5e1699204e3c3bdf7adc5c28cb376`。9 个 evidence 元素不能直接作为单个有效轮次 ID 使用，包含组合引用及异常，均保留原文和位置。数据与许可原件不改写。
40. 课程要求使用指定六段对话、四段开发与两段独立测试，但具体 ID、动态状态标注及最终指标口径尚未取得。不得擅自指定正式测试集或用测试集调参。此前先用人工检查的合成案例验证行为，用真实数据验证导入与来源映射，不宣称正式指标已达标。

### Delivery order and completion boundary

41. 按以下顺序推进可验证切片：数据契约/配置/SQLite/导入与来源映射；抽取/关系/投影/可恢复构建；检索/扩展/解析/回答；FastAPI/Streamlit 集成、JSON 导出及针对性验证。测试可在公开业务 API 切片形成时介入，不要求直到界面完成才验证。
42. 启动、环境和验证说明随实现保持可复现；不因本 spec 标记 ready-for-agent 就宣称代码实现、真实模型质量、成员复核、合并或课程提交完成。实现验收应提供实际命令、结果、未验证项和剩余风险。独立成员复核及必要的合并/验证仍遵循项目已有规则。

## Testing Decisions

1. 测试边界已由用户在本次 to-spec 会话确认：FastAPI 公开业务接口作为主要自动化验收边界；使用真实 SQLite、检索、关系与版本切换；只把 LLM 和 Embedding 替换为可控测试适配器。另做少量 Streamlit 浏览器冒烟，以及单独标识的真实模型集成验证。
2. 好的测试验证使用者可观察的输入输出、来源、错误、持久化和版本隔离，不断言私有函数调用顺序、SQL 文本、内部类数量或逐字复刻实现。通过一个主要高层边界覆盖模块协作，不为每个模块制造一套 mock 协议。
3. 仓库目前没有应用测试先例或测试入口，已有脚本只验证材料与打包。因此不能声称继承了现成应用测试；新测试入口优先采用适合 Python/FastAPI 的成熟工具，并由实现时依赖版本决定。
4. 通过公开接口覆盖导入、构建、关系/投影、混合检索与扩展、有效证据解析、导出、Trace 和错误。可控适配器应返回固定的独立场景结果，不能在假的检索器里预置“正确召回”来代替真实检索测试；少量算法数值测试仅在高层边界无法清晰定位时补充。
5. 当前与历史状态：给出先住 A、后明确搬到 B 的证据；当前问答采用 B，搬家前问答采用 A。先后交叉提问后，全局关系及 Current State 不被查询结果改写，原始证据仍可查看。
6. UPDATE 与历史扩展：构造研究、申请、面试三个阶段，使初始候选确实遗漏研究阶段；扩展后能找到所需前序证据，Trace 显示初始与补充集合的不同。反例中构建根本未抽到前序事实时，不能伪称扩展已恢复。
7. 类型与性质：同一原文中的住所与兼职拆开；事件不会因后来状态而删除；计划搬家不替代现住所，否定陈述不变成肯定，就业与开店不能仅凭同一人物判为互斥。两个对话同名人物保持隔离。
8. 冲突与未确定：相同适用条件的矛盾保留双方来源；无法证明关系保持未确定，不强行 RETAIN 或 CONFLICT；缺少新消息不自动证明旧状态持续。
9. 时间：相对时间保留原表达与锚点，日期范围不伪精确化；无日期“现在”显示对话截止时间，历史日期选择旧证据；证据之外的未来时间不被当作已知事实。
10. Query Analysis 失败时原问题仍参与 BM25/Dense；推断时间不能硬排除正确旧证据。融合按排名而非原始分数直接相加，排序与去重可复核。
11. 配置：用不同的小预算运行实际检索，检查各阶段上限、去重、一跳限制、同键补充、截断及实际配置记录。修改配置改变生效行为，不能仍使用散落的旧常量；不把这些初始数字写成不可更改的测试真理。
12. 构建中断与有限重试：模拟部分成功、API 超时/空返回/无效 JSON/无效来源，进度与失败可见，重试不重复写入成功产物；超过配置上限后明确失败。重启恢复行为按实现政策验证，不能假定未运行的任务仍在工作。
13. 版本：重建期间及失败后旧版本仍可查，成功才整体切换；切换中的查询仍固定其开始选择的完整版本，不混用 Memory、关系、投影与索引。首次未完成构建只能查看进度与部分产物。
14. 溯源与导出：单 Memory 多来源、多 Memory 同来源、跨会话映射均能定位；拒绝不存在或错误对话/版本的引用；JSON 可解析、字段校验通过且与所选版本的页面结果一致。
15. 模型适配：断言对外请求携带所选 model、关闭思考、JSON 约束及有限超时重试；覆盖无内容、截断和 schema 错误。固定适配器测试仅证明协议和失败处理，不证明 DeepSeek 抽取与关系判断质量。
16. Embedding：检查模型 revision/维度、英文文本、超长策略及索引一致性。固定向量只用于可复核排序；另用单独标记的真实本地模型检查加载、编码和长度行为，不能假造已经下载或运行模型。
17. 评测隔离：改变 QA 答案、evidence 或官方辅助摘要，不能改变同一 conversation 与配置下的抽取/索引输入。复合 ID 正确解析，畸形/缺失引用显式不可计分，分母、覆盖率和类别处理清楚；缺课程标签时动态准确率不得虚构数值。
18. 至少检查当前、历史、冲突、证据不足四类人工核验合成样例，覆盖主要失败路径。真实课程划分到位前，不利用全部十段对话反复调策略后再从中选测试集。
19. Streamlit 冒烟验证通过后端完成导入/构建进度/查询/证据跳转/Trace/导出及失败展示。真实 DeepSeek 集成检查独立标记、有限样例并明确前提，不默认让每次测试触发付费请求。
20. 检查配置快照、Trace、导出和错误不泄漏凭据。Trace 记录可核查的证据选择理由，不要求存储或展示模型隐含推理过程；测试不以秘密值作为可打印断言内容。
21. 所有检查报告区分通过、失败、跳过和未执行，附适用数据与配置。真实模型、Web 或课程指标没有运行时必须明确说明；不得用 spec 自审代替功能测试或非作者复核。

## Out of Scope

- Neo4j 等图数据库、Graph Memory、多跳图遍历、自适应检索，以及仅为未来扩展存在的 GraphRetriever 实现或插件框架。
- Memory 合并压缩、复杂冲突自动消解、查询时回原文在线补抽，以及查询关系自动写回全局状态。
- 中文提问自动翻译、跨语言检索、外部搜索、图片理解或下载 LoCoMo 图片。
- 公众账户、多租户、分布式部署、并行构建与外部任务队列服务。
- 预设模型质量收益、课程及格阈值、虚构动态标注、擅自确定课程测试集，或声称动态准确率和最终课程验收已完成。
- 自动发布代码、合并 PR、部署服务或进行正式课程提交；本次 spec 发布不包含这些后续远端操作。

## Further Notes

- 本 spec 汇总 2026-10-19 架构讨论已确认的 Q1–Q20，使用项目术语表及 ADR 中的定义。用户已确认最小数据契约、实现顺序及公开 API 测试边界，不需要再重复需求访谈。
- 规格覆盖首版代码与完整评测的接入要求，但正式课程数据、动态标注与计分口径是外部依赖，不能阻塞合成场景原型，也不能被原型结果冒充。先完成可运行核心，评测结论按实际获得的数据和实际执行结果限定范围。
- 具体 ID 编码、API 资源名、框架/依赖版本、数值型超时重试默认值、RRF 常量、片段长度、时间/实体规范化及最终 token 预算，由实现采用最小可逆方案并记录与测试。不得借这些细节改变本 spec 已确定的语言、来源、状态语义、版本隔离和配置边界；行为改变需显式修订。
- QA 对照参考 [LoCoMo 官方仓库](https://github.com/snap-research/locomo)，模型调用参考 [DeepSeek 官方接口说明](https://api-docs.deepseek.com/)、[模型表](https://api-docs.deepseek.com/quick_start/pricing/)、[思考模式](https://api-docs.deepseek.com/guides/thinking_mode/) 与 [JSON 输出](https://api-docs.deepseek.com/guides/json_mode/)，Embedding 参考 [官方模型卡](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2)。这些资料提供实现依据，不代表已执行模型调用或验证系统效果。
- 发布时使用 ready-for-agent，表示规格可交由 Agent 实施，不表示认领、在做、验收或完成。成功发布的正文在仓库原样保存，后续修订保持 Issue 与副本一致。
- 已知 Notion 项目和任务表只覆盖 M1/M2，本 spec 尚无明确关联的 M3/M4 记录；当前不修改历史任务或复制规格正文，不声称已同步新阶段状态。负责人补充关联后再同步 Issue/PR 链接；本次没有设置持续后台同步。
