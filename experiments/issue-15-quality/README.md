# 动态记忆质量增量

本阶段依据 `docs/decisions/dynamic-memory-quality-interview.md`，逐项保存身份和结果。
既有 integration 工作在本地检查点 `8258f03` 保留，未发布远端。

## A：抽取示例

- 红测：新增公开构建 API 检查在 extract-v1 下失败。
- 受控验证：`.venv/bin/python -m pytest tests/test_extraction_examples.py tests/test_builds.py tests/test_contract_recovery.py -q --tb=short`，32 passed。
- 编译：`.venv/bin/python -m compileall -q src tests` 通过。项目没有静态类型检查器，编译不等于类型检查。
- `extraction-real.json` 保存四个不同于 Prompt 示例的合成语句的真实结果及实现身份。
  共新增4次，原Campaign累计342/1000，尚需独立语义复核，不称人工真值。
- 有限验证通过现有安全 launcher 和原 `campaign.sqlite3`，没有重建额度或修改旧Build。

后续增量和总回归结果随实施记录，不把本节覆盖范围推断为总体质量。

## B：关系候选

公开API红测复现旧同键事实被近期24条计划挤出。新选择器覆盖默认20及小上限1、2，
事实保护、跨键过程、去重与失败重试名单保持一致，3项通过。既有关系与契约定向38项通过。
第一次测试读取任务列表时只取默认前20项，导致检查错误任务；改用公开分页limit=100，
未改变实现来迎合该错误断言。

`candidates-real.json` 保存原v5只读源的73/91在新候选策略下的有限回放。
新增2次，累计344/1000；历史数据库哈希核验且不写回。它不验证172，也不表示语义关卡已过。

## C：阶段证据契约，语义关卡未通过

公开API的有效阶段证据红测在旧契约下失败。新增契约覆盖合法推进、缺阶段、false谓词、
错误端点、伪造引句、字符串布尔、有限重试和旧导出读取。
定向命令：`.venv/bin/python -m pytest tests/test_update_evidence.py tests/test_relations.py tests/test_versions.py tests/test_queries.py tests/test_relation_diagnostics.py -q --tb=short`，64 passed、1 skipped。

`stages-real.json` 固定原20候选，仅更换阶段依据契约及其Prompt，不混入B的新候选名单。
新增3次，累计347/1000。73为有阶段证据的UPDATE，148为RETAIN，172仍为UPDATE，
同时输出两个true，将“完成项目→描述制作同件作品”错误描述为现实阶段变化。
这证实已确认方案的剩余风险，并不证明172已修复。

停止C的真实尝试，不继续堆Prompt、硬编码ID或强改标签。后续D/E可以独立完成受控工程验证，
完整conv-26 Build、发布和25项smoke保持阻塞；没有冻结新完整身份。

## D：有界原文兜底

新策略 `dynamic_raw_fallback` 与原 dynamic 分开，含子问覆盖、最多一次 BM25 窗口检索、
最多一次联合解析、共同证据预算、完整 messages 预算和实际联合来源指标。
新 smoke 开关可生成25项计划，默认20项及完整开发集3028项不变，未执行真实 smoke。

公开 API 回归覆盖遗漏恢复、无缺口不兜底、子问不足、部分回答、双原文与 Memory—原文冲突、
越界来源拒绝、输入/原文/交付预算、超长轮次、去重及不同对话和导入隔离。
定向命令 `.venv/bin/python -m pytest tests/test_raw_queries.py tests/test_queries.py tests/test_evaluation.py tests/test_evaluation_plans.py tests/test_full_text.py -q --tb=short`，37 passed。
一次命令误引用不存在的 `test_evaluation_execution.py`，收集前退出；随后用实际文件名执行上述命令。

真实探针使用固定合成来源，未启动完整 Build。初次输出未留正文，仅有安全错误码，
`raw-real.json` 记录首次拒绝。`raw-diagnosis-real.json` 复现模型将 Memory 来源放入独立原文 ID，
说明第一次失败的可能原因，但不能倒推两次输出相同。明确 raw_sources 独立引用范围后，
`raw-source-scope-real.json` 首次解析通过，联合解析却选中已拒绝的 Memory，被校验拒绝。
针对这两个具体契约歧义补充说明与字段描述，未放松校验；
`raw-selection-scope-real.json` 完成两次解析和一次回答，任职 Larch 有原文引用，日期未知。

D共7次真实请求，原Campaign累计354/1000，剩余646；四份记录保留各自身份与失败。
该合成控制器探针不验证真实 conv-26 兜底质量，不替代独立语义复核。
C的172仍失败，完整构建、发布及25项smoke继续阻塞。

## E：保守精简及可切换消融

公开 API 红测先复现不接受 evidence_profile，随后提供 expanded/focused 两种输入模式。
focused 按原问题词面和英文词干匹配，保留完整同键及全部关系连通组，包括未确定关系。
不按最新、标签是否确定或未知时间排除。无可靠词面匹配时回退 expanded。
受控五组对照把4条输入减到3条，同时保留历史、兼容工作、否定、冲突和未知替代条件。
新策略的预算截断也传递原文窗口限制，缺失上下文时保守保持不足。

`evidence-real.json` 保存相同合成输入的 expanded/focused 对照，共6次请求。
首次完整解析输入近似单位为3922/3524，联合解析为4107/3839。
两者回答均有来源的Larch任职事实，并保留入职日期未知和会话截止边界。
该输入只有两个 Memory，无复杂关系；不能从这个例子推断真实历史/冲突语义已通过。
E没有扩大真实Build或全量QA，默认仍expanded。

累计真实请求360/1000，剩余640。A4、B2、C3、D7、E6，共22次，均在各阶段16次封顶内。
独立代码审查及最终回归结果在后续记录中补充，172语义关卡仍未通过。

## 独立审查及修复

以 `8258f03...fdfe440` 做 Standards / Spec 双轴并行只读审查。
Standards 发现旧Run缺新增字段导致500、明确上下文拒绝缺false标记，以及失败阶段计时重复。
Spec 发现部分词面命中可能误裁复合问题的同义事实或其他人物证据。
公开API红测复现后修复，定向33项通过；复审关闭原问题。
原Run格式execution_version=1保持可读，恢复返回409；新Run为version2。

E v2仅对明确单一人物、单问且该人物有词面匹配的情况裁选，保留该人物全部候选及关系组件。
复合、间接引用、多人物、匹配仅落在其他人物时退回expanded。原E测量属于v1，不能当作v2通过。
`evidence-reviewed-real.json` 使用新固定合成输入，3条减2条，只移除Morgan爱好；
首次解析输入4310/3912，两者Larch引用正确。新增4次，E共10次，原账本累计364/1000，剩余636。

非作者代理复核发现v2这两份真实答案都漏写截止日期，不满足当前回答的边界要求。
保留原输出，不称完整语义通过。控制器随后为新策略当前/未来问题确定性附加已知截止与后续未知，
Trace记录answer_boundary及版本；公开API对模型遗漏边界的当前/未来答案先红后绿。
这项修复没有新增真实调用，不能倒推原输出已包含边界。

A四例、B73/91及C73/148的有限输出经另一代理独立核对；C172仍不支持阶段推进。
这些是非作者代理复核，不是人工真值或课程评分。完整Build、发布和25QA继续未执行。
详细双轴报告见[审查记录](review.md)，完整离线回归结果另附。

## 最终验证

首个完整离线回归为311 passed、13 failed、4 deselected，见 `offline-regression.xml`。
修复既有合法UPDATE夹具和诊断顺序后，相关126项通过；查询/导出/恢复56项通过、1项条件跳过。
两轴均独立复审该修复，通过。

因首跑失败且修改了共享校验，最终版本再做一次完整离线回归：

```sh
.venv/bin/python -m pytest -m 'not live_model and not local_embedding' -q --tb=short --junitxml=experiments/issue-15-quality/final-offline-regression.xml
```

最终324 passed、4 deselected，耗时222.21秒。只出现现有Starlette/httpx弃用提示。
`.venv/bin/python -m compileall -q src tests` 及 `git diff 8258f03...HEAD --check` 均通过；
项目未引入静态类型检查器。新鲜结果及最终源码摘要保存在 `verification.json`。
离线检查未发真实模型请求，账本仍为364/1000，未知未结束请求为0。

本轮工程实现与审查修复已本地提交，没有push、PR、Issue或Notion写入。
这不是语义验收完成：172仍误判UPDATE，新完整身份未冻结，完整conv-26 Build、发布和25项QA未开始。
