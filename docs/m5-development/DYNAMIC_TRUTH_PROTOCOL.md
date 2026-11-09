# 独立动态审核与指标协议

固定四个开发 Build；同一 state_key 下按最早来源 position 与 Memory ID 排序，对相邻 state Memory 生成候选对。以 SHA256(seed|build|old|new) 排序，每对话取15，共60。抽样不读取关系预测、QA答案、得分或候选结果。原文包保存在忽略的 var 目录。

审核者阅读 old/new Memory 及双方原始 Source Turns，标注 RETAIN、UPDATE、SUPERSEDE、CONFLICT、undetermined。必须逐字引用来源，记录人物、状态维度、时间/条件、理由、reviewer、provenance。抽取错误直接注明；来源ID重合不产生关系标签。

本轮采用与实现者独立的 AI 不重叠分工，不是人工真值，也不是双人一致性测量。可确定证据不足建立关系时标签为 undetermined；只有参考标签本身无法评分才标 uncertain/unresolvable 并单列。

评价关系 Accuracy、出现标签的 Macro-F1、每标签覆盖、缺失预测数与未判断率。可评分单位缺失预测仍保留在分母计错。未出现且未预测的类别不虚构得分。

有效集合在本协议仅是 pair-local applicability：在两条证据范围内，哪些陈述仍可保留。它不等于 QA-specific Effective Memory 集合。没有独立 query、时间及条件参考时，课程 query-specific effective-selection accuracy 必须为 not_measured；不可拿 CurrentState 投影与 pair-local 参考直接比较。

真实样本缺少标签时单列缺口，合成机制测试不补入真实分母。评分器拒绝自标真值、未知ID、非逐字引文及越界有效集合；provenance 的真实性仍依赖独立审核。

## 问题相关的历史解析审核

`query-applicability-v1`补充独立的query-specific任务。固定历史Dynamic Run的757项，以`SHA256(m5-query-applicability-v1|question_id)`排序，每开发对话取10项，共40。选择只依赖题目身份，不按类别、成功状态、预测、答案或成绩过滤。固定样本含35项已有解析预测、5项无预测；解析后的回答失败和解析缺失分开保留。

审核者只收到问题、控制器时间条件、完整扩展候选及其来源原文。审核包不含系统有效选择、存储关系、生成答案、QA答案或证据标注，也不显示题目成功状态。原预测独立冻结，审核者禁止打开。审核范围为候选Memory及所附来源组成的证据包：若相关Memory省略细节但来源明确支持答案，可以选择该Memory并注明“来源可恢复”；这不等于Memory文本保留了该事实。

独立审核输出`unit_id`、`effective_ids`、`status`、逐字`support_quotes`、`rationale`、布尔`uncertain/unresolvable`及独立reviewer/provenance。每条所选Memory至少有一条自身来源的逐字支持。人物归属错误、计划当完成、时间/条件不符或原文不支持的候选须排除并解释。候选不含足够证据可以确定标`insufficient`；参考集合无法唯一确定或问题前提存在无法处理的歧义时标不确定，单列而不强行评分。最小完整支持集合可以包含同等支持的多个Memory；此约定仍可能产生审核者之间的集合差异。

评分器分别报告严格集合Exact Accuracy、每题集合F1平均值及状态Accuracy。可评分参考内的缺失预测保留分母计错；参考不确定/无法评分项单列。没有任何实际预测或参考时为`not_measured`。完整40份参考校验并冻结SHA后才打开预测评分。严格集合匹配对可替代证据敏感，因此它是该独立AI参考下的诊断指标，不能外推为教师动态准确率、原子事实保留率、全局召回率或QA F1。历史预测不称本轮新模型结果；40题未按动态类别分层，不声称覆盖全部时间与冲突类型。

准备和评分命令如下。新label必须未存在；评分前两份实际审核文件必须齐全。原文和参考留在忽略的var，提交紧凑指标与SHA。

```sh
PYTHONPATH=tools/integration/offline_guard:src:. /home/kenqia/my_folder/locomo-dynamic-memory/.venv/bin/python -m tools.m5.query_review --label new-query-review
PYTHONPATH=tools/integration/offline_guard:src:. /home/kenqia/my_folder/locomo-dynamic-memory/.venv/bin/python -m tools.m5.query_review --label query-applicability-v1 \
  --review var/m5-development/query-applicability-v1/independent-a.json \
  --review var/m5-development/query-applicability-v1/independent-b.json
```
