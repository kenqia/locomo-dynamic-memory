# 证据组排序、枚举补查与拒答约定的本地验证

2026-10-21，Asia/Shanghai。用户通过 `implement` 指定三项交接优化，
实现基点为 `4fc38d017e9d2a367663e4029ae537dd4f780f5c`，
工作分支为 `codex/issue-15-integration`。
本轮只使用本地受控模型传输和 Embedding，不进行付费调用或远端任务操作。

## 实现范围

- P0，`35bfcc8`：混合证据在首次解析、联合解析和最终回答的打包入口，
  按完整组中最佳证据与原问题的词面及英文词干重合数排序，人物重合作为次序，
  并列稳定。不改变初始或扩展召回集合，不切换 expanded 默认。
  同维度、关系及 coverage 引用继续联合分组。超预算组完整省略并审计，
  解析输入预算及最终共享证据预算保持有效。
- P1，`982c44c`：明确的 activities、hobbies 和句首 list/enumerate 问法，
  在初判 sufficient 时也执行现有的一次原文检索，有命中时联合解析一次。
  枚举检索将原始 speaker 字段加入原 BM25 corpus，使人物名可匹配其 I 自述。
  Trace 记录 `enumeration_coverage_check` 和 `speaker_matching`。
  具体事实问题的充分结果不增加请求，补查不改变原命中、窗口、轮次或 token 上限。
- P2，`c071cf1`：普通及混合回答共用 `ANSWERABILITY_GUIDANCE`，
  按人物、时间与所问事实区分真正部分答案和仅主题相关的背景。
  无任何可回答子问时提示精确输出 `No information available.`；
  有受支持子问时保留直接事实及引用，缺口与背景放在 explanation。
  没有按 insufficient 状态强制改写答案，没有修改官方评分器。

复核修正 `439fe93` 识别常见礼貌前缀，并为原问题中的 's 形式增加去后缀匹配词。
例如 `Can you list Alex's hobbies?` 能触发覆盖补查，并匹配 Alex 的自述来源。
该覆盖策略版本单独进入查询指纹和 Trace。
最终源码实现身份为 `61f7d8a0d8cec821e3c4ded7c0a5c1ac36cceb2706e34c800c24424d94a8c8cf`。
Prompt 版本、打包版本及检索版本随行为更新，查询和评测使用新的身份。
旧 Run、构建、来源、索引、账本和成绩均不修改，不用新身份恢复旧实验。

## 受控回归

新增测试沿用交接指定的 `pack_payload` 与 `POST /queries` 边界，
外部模型使用 `httpx.MockTransport`，持久化及检索走现有实现。

- P0 的两个预算场景在修复前均只交付先出现的无关 Memory，
  修复后优先交付研究事实及完整冲突双方。另检查混合 coverage 连接的超大组
  整组省略、稳定并列、来源交付和省略原因。
- P1 首个回归在 sufficient 后未补查，修复触发后又发现 hobbies 问法无法匹配
  只有 I 的自述轮次。加入真实 speaker 字段后，8 个枚举/具体事实及有无新增项目
  场景通过。复核追加两个礼貌问法后，12 个枚举回归通过。已支持的 running 引用保留，从交付原文补入 camping、swimming，
  不将另一人物的 surfing 加入答案；无新增项目时保留原答案。
- P2 回归先在实际发送的 Prompt 中缺少所问支持与背景的区分而失败。
  共享规则后，两种策略各覆盖无支持、仅错误季节背景、真实部分答案，
  检查精确主答案、独立解释及部分答案引用。现有 QA 53 的 this week 来源锚点
  回归和旧支持修订、冲突、非法引用、未来日期及预算回归继续保留。

这些测试验证确定性流程、来源送达及 Prompt 契约。模型语义输出受控，
不能证明真实模型已经补齐所有活动或稳定使用拒答短语。词面排序也不保证语义最优。
枚举最多补查一次，不能保证穷尽所选对话；不支持的项目不能编造。
真实阶段诊断及历史结果继续引用
[前轮分析](../issue-15-answer-output-live/results/analysis.md)和
[既有约束验证](../issue-15-answer-output/validation.md)，本轮没有新真实质量成绩。

## 检查与独立复核

项目未配置静态类型检查器，没有新增检查依赖。复用既有 pytest 和编译入口。
初轮四个查询相关测试文件合计 69 passed。复核修复的 12 项枚举回归通过。
恢复执行前的全量进程已不可访问，没有取得最终结果，不将其计为通过；
在最终实现身份下重新运行全量，结果为 **392 passed、4 deselected，267.39 秒**。
编译与差异检查通过。
仅有既有 Starlette/httpx 弃用警告。

### Standards

基点 `4fc38d0` 至 `c071cf1` 的独立复核：0 项硬性违规，0 项需提出的代码异味。
复核确认查询只读边界、候选与证据预算、版本审计及 QA 标注隔离保留；
公共回答规则复用常量，行为说明同步更新，没有新增依赖或扩展机制。
`c071cf1...439fe93` 的独立增量复核同样为 0 项硬性违规、0 项可操作代码异味。
礼貌前缀和所有格处理局限于现有接口，没有引入不必要抽象或重复分支。

### Spec

初次复核：1 项 P2。需求“what activities / which hobbies / list 尽可能覆盖全部有来源的相关项目”，
实现却只认句首 list/enumerate，漏掉 `Can you list Alex's hobbies?` 与
`Could you enumerate Alex's activities?`。新增 API 回归先确认 sufficient 后未补查，
`439fe93` 修复礼貌前缀及 possessive 名字匹配。独立关闭复核确认原 P2 关闭，
没有未解决发现或新增需求偏离，并独立运行枚举回归，12 passed、28 deselected。
复核确认首次 sufficient 仍触发一次补查、原支持保留、有无新增项目分支及既有预算约束。
其他 P0、P1、P2 范围未发现缺失、错误实现或范围扩张。
初次 Spec 代理独立定向检查为 18 passed、29 deselected。
P2 的复核范围为 Prompt 交付及受控输出，不证明真实模型语义。

```sh
.venv/bin/python -m pytest tests/test_answer_regressions.py tests/test_queries.py tests/test_raw_queries.py tests/test_focused_queries.py -q
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 OMP_NUM_THREADS=2 .venv/bin/python -m pytest -q -m 'not live_model and not local_embedding'
.venv/bin/python -m compileall -q src tests
git diff --check
```

未运行付费模型、本地真实 Embedding 或浏览器端到端验收，未新增依赖。
本轮未 push、创建 PR 或更新 GitHub/Notion，不代表合并或任务验收完成。
回退可逆序对本轮四个实现提交执行 `git revert`，无需数据库迁移。
