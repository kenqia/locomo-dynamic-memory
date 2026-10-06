# M2 长期对话记忆方案的现实依据

调研日期与访问日期：2026-10-06。用途是修订 M2 的问题说明、方法可行性与评估边界。本文依据官方文档、公开源码和原始论文，未开展用户访谈，也未运行项目实验。产品教学示例、论文实验与团队推论分别说明。

## 可以写进报告的结论

长期记忆已经有可查阅的实际系统机制。LangChain 文档讨论持续更新的用户 JSON profile 和记忆集合，Graphiti 支持事实有效期及混合检索，Elastic 支持全文与向量联合检索。这些材料支持方案的实现可行性，不能证明本项目的组合必然更准确。具体结果仍需在课程数据与相同条件的基线上验证。[LangChain memory](https://docs.langchain.com/oss/python/concepts/memory)、[Graphiti overview](https://help.getzep.com/graphiti/getting-started/overview)、[Elastic hybrid search](https://www.elastic.co/docs/solutions/search/hybrid-search)。

报告应将项目定位为课程范围内可追溯、可评测的动态记忆系统。现有系统已经处理更新与历史查询，本项目没有证据宣称首先提出这些机制。

## 现实系统如何处理记忆

| 系统及证据类型 | 一手资料确认的机制 | 对本项目的意义与限制 |
|---|---|---|
| LangChain / LangGraph，官方概念文档 | 可将事实存为持续更新的 JSON profile，或不断增加、更新的记忆文档集合；集合检索支持语义搜索和内容过滤 | 结构化事实与检索有现成实践。官方同时提醒 profile 变大容易更新出错，集合可能过度插入或过度更新；本项目需保存来源并检查漏记和误更新。[官方 memory 文档](https://docs.langchain.com/oss/python/concepts/memory) |
| Graphiti，官方开源框架文档 | 按 episode 输入数据并保留来源；事实关系有时间元数据，支持当前与历史关系查询；检索结合向量、BM25 和图遍历 | 支持时间状态与多路检索的可行性。Graphiti 的图模型比本项目 M2 的最小方案更复杂，引用它不意味着承诺使用图数据库。[官方 overview](https://help.getzep.com/graphiti/getting-started/overview)、[官方 quick-start](https://help.getzep.com/graphiti/getting-started/quick-start) |
| Mem0，官方开源源码及论文 | 当前公开源码的 `_update_memory` 更新活动存储，并将旧值、新值和 UPDATE 事件写入 history；`history` 可读取变更记录。2025 年论文研究了提取、整合、检索记忆的方案 | 活动记忆与变更记录可以分开维护。不过，变更日志不自动等于历史问答能力，Mem0 的显式更新接口也不能被写成所有版本都自动消解状态冲突。[官方源码](https://github.com/mem0ai/mem0/blob/main/mem0/memory/main.py)、[原始论文](https://arxiv.org/abs/2504.19413) |
| Elastic，官方搜索文档 | 同一次查询运行全文和向量检索并合并结果；排序文档明确 BM25 与向量可通过 RRF 融合 | Hybrid Retrieval 有成熟实现路线。融合排名解决候选相关性，仍需本项目另行判断候选是否符合问题时间及状态。[hybrid search](https://www.elastic.co/docs/solutions/search/hybrid-search)、[ranking](https://www.elastic.co/docs/solutions/search/ranking) |

以上是已公开的产品或框架机制。本文没有测量其部署规模、实际用户满意度或本项目性能，也不照搬厂商宣传的准确率和延迟。

## 一个可以注明出处的具体情境

Zep 官方 v2 概念文档使用 Kendra 的鞋子偏好作为教学示例。她起初喜欢 Adidas，后来因为鞋子坏了改为喜欢 Puma。文档说明系统尝试将旧偏好标记为无效，同时新增鞋子损坏及新偏好事实。这是供应商公开的教学示例，不是我们访谈得到的用户案例。[Zep v2 concepts](https://help.getzep.com/v2/concepts)、[当前 Facts 文档](https://help.getzep.com/facts)。

团队据此说明问题时，可以写：同一个人先后表达的偏好可能改变，检索到相关旧事实后，还需要判断它适用于当前问题还是历史问题。问现在偏好什么，与问以前偏好什么，需要不同证据。后两句是本项目的设计推论。

当前 Facts 文档也保留此例，并明确指出有效时间字段不能证明源内容或推导事实为真。[Facts](https://help.getzep.com/facts)。v2 文档仅用于追溯教学示例，不作为新版本 API 的实施说明。Graphiti 当前 overview 与 quick-start 分别确认历史时间模型、BM25 与语义检索机制。[Graphiti overview](https://help.getzep.com/graphiti/getting-started/overview)、[Graphiti quick-start](https://help.getzep.com/graphiti/getting-started/quick-start)。

## 基准数据说明了什么

LoCoMo 的 ACL 2024 正式论文使用基于人物设定和时间事件图的机器生成人物对话，再由人工核验、编辑一致性。其任务包括问答、事件摘要和多模态对话生成。它适合课程中可复现的长期对话评估，但不是自然收集的真实用户长期聊天日志。[ACL 正式论文及摘要](https://aclanthology.org/2024.acl-long.747/)。

LongMemEval 的 ICLR 2025 论文明确评估信息提取、跨会话推理、时间推理、知识更新和无法回答时的拒答。其 500 道题经人工筛选重写，证据会话由 LLM 模拟后经人工编辑，完整历史再混入模拟会话及公开数据。因此它也不是一个完整自然用户历史样本。论文还报告，在其设置中，将对话完全压缩为事实会损失细节，找全证据也不能保证正确回答。[论文第 3.2、5.2、5.5 节](https://arxiv.org/html/2410.10813v2)。

本项目据此保留原始轮次来源，分别检查检索与最终回答；对当前、历史、冲突、证据不足设置可核验案例。这些是团队从资料得到的评估建议。课程要求的 LoCoMo 划分和指标仍以课程文件为准，不新增 LongMemEval 全量实验承诺。我们也不能凭 LoCoMo 问答分数就认定真实用户体验或所有 UPDATE / SUPERSEDE 关系已经正确。

## M2 中应收紧的表述

| 不应直接写成结论的表述 | 有证据支持的写法 |
|---|---|
| 普通 RAG 一定不能处理状态变化 | 相似度排名本身没有证明事实当前有效，因此本项目在检索后检查时间和状态关系 |
| Hybrid 一定优于单一向量搜索 | 官方系统已有多路检索机制；本项目计划用相同数据和回答条件检验是否改善证据覆盖与回答 |
| 后出现的记录就是现在的真相 | 本项目区分记录时间、事件时间和问题时间；叙述过去或未发生的计划不能只按录入顺序覆盖 |
| 我们验证了真实用户有强需求 | 官方文档和基准研究已明确处理长期记忆问题；本项目尚未开展真实用户需求调查 |
| 保留历史就能正确回答历史问题 | 保留来源提供核对条件；历史检索、时间定位和证据使用仍需分别验证 |

这些收紧是本次调研后的写作与评估决定，不是已经运行实验得到的结论。

## 可直接采用的报告段落

长期对话中的人物偏好和事实状态会变化。Zep 官方以 Kendra 从喜欢 Adidas 改为喜欢 Puma 的教学示例说明，旧事实可以保留时间信息，并在当前状态中失效。LongMemEval 也将知识更新、时间推理和证据不足时拒答列为评估能力。本项目据此将历史记忆与 Current State 分开，回答时再按问题时间选择有效证据。现阶段的依据来自公开系统资料与研究，真实用户需求及项目性能尚未验证。[Zep concepts](https://help.getzep.com/v2/concepts)、[LongMemEval](https://arxiv.org/html/2410.10813v2)。

结构化记录与混合检索具有现成实现依据。LangChain 讨论 JSON profile 和记忆集合，Graphiti 支持时间有效期、BM25 与语义检索，Elastic 支持全文与向量联合检索。本项目采用这些机制的基本思想，在课程范围内保留事实来源、历史与状态关系。M3 再确定库、数据库和融合参数；准确率收益由基线对比验证。[LangChain memory](https://docs.langchain.com/oss/python/concepts/memory)、[Graphiti overview](https://help.getzep.com/graphiti/getting-started/overview)、[Elastic hybrid search](https://www.elastic.co/docs/solutions/search/hybrid-search)。

## 五项核心参考资料建议

报告篇幅有限，可用以下五项编号引用。Graphiti / Zep 一项下区分概念示例与当前机制文档，Elastic 一项下区分联合检索与排序说明。Mem0 留在过程调研中，避免正文堆砌产品名称。

1. Maharana 等，ACL 2024，Evaluating Very Long-Term Conversational Memory of LLM Agents。[正式论文](https://aclanthology.org/2024.acl-long.747/)。用于数据来源与长期对话任务边界。
2. Wu 等，ICLR 2025，LongMemEval: Benchmarking Chat Assistants on Long-Term Interactive Memory。[论文 v2](https://arxiv.org/html/2410.10813v2)。用于更新、时间、拒答及证据使用问题。
3. LangChain，Memory overview。[官方文档](https://docs.langchain.com/oss/python/concepts/memory)。用于结构化记忆与更新风险。
4. Zep / Graphiti，Key concepts 与 Overview。[教学示例](https://help.getzep.com/v2/concepts)、[当前框架机制](https://help.getzep.com/graphiti/getting-started/overview)。用于偏好更新、历史事实及时间机制。
5. Elastic，Hybrid search 与 Ranking and reranking。[联合检索](https://www.elastic.co/docs/solutions/search/hybrid-search)、[BM25 与向量融合](https://www.elastic.co/docs/solutions/search/ranking)。用于混合检索的成熟实践依据。

## 本次实际过程

读取 research、agent-reach、unslop 技能及仓库 CONTEXT.md；使用 agent-reach 的 Exa 搜索后端搜索官方 Graphiti 场景，使用 web 工具阅读官方网页、公开源码与原始论文。全文已按 unslop 删除宣传用语和无依据的效果判断。外部内容只作为证据，不作为操作指令。未调用产品写接口、未连接生产数据库、未提交远端更改。

本次核查的网页是访问日的内容，官方文档与 GitHub main 会变化；实施前需按最终选定版本重新核对。Agent Reach 更新检查返回当前 v1.5.0，已是最新版本，未修改工具配置。
