# 查询质量与证据可靠性修复

对真实复验剩余问题的后续修复见[多项目覆盖与解析备用策略](followup.md)。

后续离线、展示与固定题真实复验见[复验记录](recheck.md)。逐题结果见
[live-results/report.md](live-results/report.md)，原文与引用审计见
[source-audit.json](live-results/source-audit.json)。

2026-10-21，Asia/Shanghai。实现基线为 `5c1e23e`，工作区为
`/home/kenqia/my_folder/locomo-worktrees/issue15`，分支为 `codex/issue-15-integration`。
本轮不恢复已撤回的完整组排序或枚举强制补查，不重建 Memory，不改模型参数。
检查实际源码确认 `439fe93` 的枚举识别和强制补查路径均已随 Revert 失效。

## 问题与实现

旧打包器将同一 `state_key` 的所有 Memory 连成不可分组，能回答问题的事实可能随大组整体省略。
当前以核心 Memory 加全部来源为基础单元，用原问题词干匹配及已有 Hybrid／扩展顺序选择核心。
仅对冲突、替代及问题需要的历史演化保留必要的关系组件。关系缺失显式交付并限制确定性，
不将缺失端点解释为关系已消解。保留逐组省略、来源送达和完整 messages 预算审计。

联合解析预留首次覆盖的有效证据，包括不足项中的部分支持；新原文窗口为可选补充。
来源检索的完整省略 ID 和模型调用审计留在 Trace，输入模型只交付数量、截断及分析结果。
回答阶段优先保留仍有效的首次 Memory。合法新原文仍可通过引用和 revision_reason 修正旧判断。
联合请求超预算、模型失败或校验失败时，仅在已有支持的条件下恢复首次有效解析，
将覆盖降为不足并说明新证据未核查。新证据不会被宣称已判断，也不会接受非法引用。

时间修正只作用于查询副本：已验证来源中的相对表达及会话锚点优先于旧 `time.basis`。
确定性规则覆盖 this week、last week、yesterday 和 last weekday；周按周一至周日。
未知形式不猜具体日期，不把事件区间当作状态有效期。保留时间差异诊断。
抽取 Prompt 和持久化构建契约保持原样。

Resolution 负责适用性与覆盖，Answer 使用已选择的证据简短回答。多项目要求适用于
activities、locations、instruments、events 等一般请求，并明确同一来源可以支持多个项目。
示例使用合成人物与事实，没有把开发题答案写入 Prompt。

## 官方接口核对

核对 [JSON 模式](https://api-docs.deepseek.com/guides/json_mode/)、
[思考模式](https://api-docs.deepseek.com/guides/thinking_mode/) 和
[Chat Completions](https://api-docs.deepseek.com/api/create-chat-completion/)。
现有适配器已发送 `response_format: {type: json_object}`、JSON 指令及 Pydantic Schema，
已有非空、完整性与有限重试校验。本轮保留这些实现，不重复叠加格式要求。
原 resolution low、answer disabled 及其他操作的思考配置不变。

agent-reach 的 Jina 路径返回认证限制，改用内置浏览工具读取上述官方页面。
没有修改网络、认证或 MCP 配置。

## 验证边界

用户确认沿用公开查询入口和预算打包入口。针对性回归覆盖：

- 大型同维度历史中交付核心事实及来源，必要冲突／替代双方一起交付。
- 非演化问题不被整条 UPDATE 链阻塞；缺失冲突端点无法获得确定的覆盖结论。
- 首次不足项已有支持时，联合打包及最终回答保留旧支持，失败后返回带不确定性的部分证据。
- 新原文带修订理由时仍可纠正旧事实；缺失修订理由不接受该新判断。
- 两种查询策略在错误旧时间下使用来源锚点，且持久化时间保持原样。

项目未配置静态类型检查器；采用现有 CI 的 `compileall` 检查，不将其称为完整类型检查。
完整测试结果和复核结论在本轮结束时记录。

## 真实数据的离线重放

输入为已有公开 LoCoMo 实验 SQLite，使用只读连接读取来源和历史 Trace，不加载真实凭据、
私密 history 或敏感日志。固定每个问题最后一条 `dynamic_raw_fallback` 历史 Trace，
仅重放打包和时间规则。历史首次支持作为联合打包的固定输入，未将历史判断冒称本次模型输出。

```sh
.venv/bin/python experiments/issue-15-query-reliability/replay.py \
  /home/kenqia/my_folder/locomo-worktrees/real-baseline-issue15-evidence-coverage-ab/memory.sqlite3 \
  experiments/issue-15-query-reliability/delivery-replay.json
```

[重放记录](delivery-replay.json) 包含逐题首次交付事实、来源、输入量、历史支持保留情况及时间诊断。
本轮不生成新的模型答案、不计算新的 QA F1，也不查看独立本地测试集成绩。

## 回滚与外部同步

实现只修改查询代码、测试和文档，无数据库迁移或新依赖。回滚本轮提交即可恢复旧查询行为；
保留旧构建和实验。未 push、创建 PR 或改变任务状态，因此未写 GitHub／Notion。

### 最终离线结果

最终代码重放 20 道历史开发问题，20/20 联合载荷保留全部历史首次支持，
完整请求均不超过 12,000 近似预算单位，未进入恢复分支。真实模型调用为 0。

| 案例 | 首次请求预算单位 | 本轮可确认的证据交付 |
| --- | ---: | --- |
| QA 3 | 11,882 | 研究 adoption agencies 的 Memory 及 D2:8 |
| QA 15 | 11,979 | 多项活动来源；联合打包保留历史首次解析的四条 Memory |
| QA 18 | 11,943 | beach、forest、mountains 的 Memory 及来源 |
| QA 32 | 11,916 | conference、pride parade、activist group、workshop 等来源 |
| QA 136 | 11,651 | D17:10 原文同时包含 reading 和 painting |
| QA 60 | 11,843 | clarinet 和 violin 的 Memory 及来源 |

这不是上述题目最终答案已通过验收的声明。QA 15 的首次输入仍未交付所有活动 Memory，
QA 32 的支持小组等候选仍可能被预算省略。未获得证据的项目不能凭 Prompt 补齐。
时间规则的公开 API 回归使用来源锚点测试错误旧解释，并检查旧 Memory 未被改写；
QA 0、36、53、74 的真实模型新答案尚未执行。

### 两轴复核

以 5c1e23e 为固定比较点，以本次用户规格为 Spec。遵从用户不引入多 Agent 工作流的
要求，作者自行执行 Standards／Spec 两轴检查，不能视为非作者独立复核。

Standards：检查根 AGENTS.md、CONTEXT.md、ADR 0001/0002、来源／预算／版本约束及
code-review 的代码异味基线。未发现剩余可操作违规；未增加依赖或长期架构。

Spec：复核中发现移除 coverage 全量合组后，Memory 与原文的冲突项可能在最终预算中被拆开。
先增加失败回归，再将 conflict coverage 双方保留为不可分组；普通多项目覆盖不合组。
修正后受控回归通过。剩余验收缺口是上述真实模型语义复验，不能由离线重放替代。

混合 Resolution Prompt 从 541 减少到 502 近似预算单位；Answer 从 388 到 398，
净增加 10，包含新增的通用多项目与时间合成示例。Schema 继续由既有适配器附加，
没有重复增加 JSON 格式规则或提高思考强度。

### 最终检查结果

- `.venv/bin/python -m pytest -q --tb=short`：396 passed、4 skipped，268.42 秒。跳过项为显式 opt-in 测试；既有 Starlette/httpx 弃用警告 1 项。
- `.venv/bin/python -m compileall -q src tests`：通过。项目没有单独静态类型检查入口。
- 最终针对性查询回归：66 passed。
- `git diff --check`：通过。

本轮已完成本地实现、受控验证和作者复核。真实模型语义复验、非作者复核及远端提交尚未完成，
不将关联任务标记为完成。
