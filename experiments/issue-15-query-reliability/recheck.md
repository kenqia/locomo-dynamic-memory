# 查询可靠性复验与展示检查

2026-10-21，Asia/Shanghai。复验查询实现为提交 `7546b41`。本轮不修改查询行为或 UI，
只补充验证与有界真实复验入口。沿用 implement、tdd 和 code-review 的本地流程；
遵从用户不使用多 Agent 的要求，由作者复核，不能视为非作者审核。

## 离线验证

在 `/home/kenqia/my_folder/locomo-worktrees/issue15` 运行既有入口：

```sh
LOCOMO_LIVE_MODEL=0 LOCOMO_LOCAL_EMBEDDING=0 .venv/bin/python -m pytest -q --tb=short
.venv/bin/python -m compileall -q src tests experiments/issue-15-query-reliability
git diff --check
```

首次完整回归 396 passed、4 skipped，耗时 279.25 秒。增加展示验证后，
发现 AppTest 留下的临时 `__main__` 导致三个 multiprocessing 重启测试失败。
新增测试通过 pytest monkeypatch 恢复该模块；针对展示与重启的联合复验为
16 passed、1 skipped。最终全量结果为 397 passed、4 skipped，248.58 秒。
编译检查与 `git diff --check` 通过；既有 Starlette/httpx 弃用警告 1 项。

覆盖边界如下。所有生成响应由既有 HTTP transport 受控提供，不冒称真实模型能力。

| 边界 | 现有测试入口 |
| --- | --- |
| 核心证据、大型同键组预算、必要关系双方、缺失端点不确定性 | `tests/test_query_evidence_delivery.py` |
| 首次不足但有部分支持、补查反驳、联合失败恢复、混合冲突 | `tests/test_raw_queries.py` |
| 来源锚定相对时间、人物归属、部分事实及多项目输入 | `tests/test_answer_regressions.py` |
| 引用、版本、身份、时间、来源合法性 | `tests/test_queries.py`、`tests/test_raw_queries.py` |
| 策略切换、部分答案、来源和解释可见 | `tests/test_strategy_ui.py` |

重跑 `replay.py`，20/20 历史问题的联合载荷均保留首次支持，
全部完整请求保持在 12,000 近似预算单位以内。该重放没有生成新答案。
另以 `LOCOMO_LOCAL_EMBEDDING=1 HF_HUB_OFFLINE=1` 运行 `tests/test_local_embedding.py`，
2 passed，固定 MiniLM 本地缓存与真实检索入口可用，没有付费请求或模型下载。

## 展示检查

使用既有隔离环境与 Chromium 156.0.8078.4：

```sh
bash tests/browser/run.sh /home/kenqia/my_folder/locomo-worktrees/browser-env/bin/python
```

退出码为 0，浏览器 pageerrors 和 console_errors 均为空。完成当前／历史／冲突／
证据不足问答、双方关系来源展开、回答引用展开、历史 Trace、Memory 导出与评测结果页检查。
该脚本只在临时合成库构建 Memory，真实 272 条 Memory 和 4,902 条关系保持原样。
脚本在专属临时虚拟环境安装已有锁定依赖，未新增项目依赖，也未改根 `.venv`。

产物保留在 `/tmp/locomo-browser-smoke.5Ty70a/artifacts`，
精简结果另存为本目录的 `browser-result.json`。测试结束时停止本次后端和 Streamlit 服务。

新增 AppTest 通过真实公开查询 API 得到“联合解析校验失败，恢复首次部分支持”的 Trace，
再交给真实 `render_queries`。检查简短答案 `Paris.`、原始来源、证据不足状态及
新原文未核查说明均可见，切换策略后答案仍保留。只控制外部模型与 Embedding，
不修改生产页面。该场景由 AppTest 验证，未宣称 Chromium 已执行同一补查场景。

## 冻结的真实复验

用户已明确批准本轮最多 64 次新调用。历史 1,097 次继续计数，
累计硬上限为 1,161；失败与重试占用额度，不自动扩大或重复整轮。

| 组 | 策略 | 固定 QA index |
| --- | --- | --- |
| primary | `dynamic_raw_fallback`，expanded | 0、3、15、18、32、36、53、60、74、136、153 |
| dynamic_nonregression | `dynamic` | 3、15、53 |

复用 Build `5c7699dd6543407697ae232633154036`。来源库为
`/home/kenqia/my_folder/locomo-worktrees/real-baseline-issue15-evidence-coverage-ab/memory.sqlite3`。
通过 SQLite backup 建立独立快照，构建产物摘要前后一致才可执行。
不重新抽取、判断关系、建立索引，不查看 `conv-43`／`conv-44` 成绩。

冻结目录为 `/home/kenqia/my_folder/locomo-worktrees/real-baseline-issue15-query-reliability-frozen`。
`plan.json`、`plan.sha256` 固定题目、策略、参数、实现摘要、来源版本和预算。
沿用 DeepSeek Flash、temperature 0、输出上限 8,192、timeout 120 秒、model_retries 2，
Resolution low、Answer disabled；输入预算 12,000、证据预算 6,000、原文预算 2,000。

`live.py` 复用既有 Campaign 逐请求预留额度、校验与 evaluation API。
`report.py` 读取 API 已有分数和 Trace，不调用模型、不增加评估器。

```sh
python3 scripts/with_deepseek_env.py -- .venv/bin/python \
  experiments/issue-15-query-reliability/live.py execute \
  --directory /home/kenqia/my_folder/locomo-worktrees/real-baseline-issue15-query-reliability-frozen \
  --authorized-call-limit 64
```

题目顺序固定，每项只跑一轮。查看已有 provider/schema 有限重试，禁止依据结果修改题单再跑。
历史同题结果只作描述性对照，不声称随机同期 A/B 或统计显著性。

语义核对同时检查首次输入、联合输入、最终送达和引用。
QA 3 核对 adoption agencies 与 D2:8；QA 15 核对部分支持是否保留、是否得到额外有效活动；
QA 18、32、136 区分来源未送达与已送达后生成遗漏；QA 60 核对两种乐器；
QA 53 核对包含来源日期的一周，QA 0、36、74 核对原始会话相对时间；
QA 153 核对人物归属与真正不知道。按原文判断，不把 F1 当语义正确率。

## 真实复验结论

冻结执行于 2026-10-21 09:53–09:59 UTC。实际调用 44/64 次，历史合计 1,141/1,161 次；
包括 41 次成功响应与 3 次结构输出无效。输入 token 530,221、输出 76,714，共 606,935，
所有调用均报告用量。来源库和快照的 Build 摘要前后未变。

结果为 `completed_with_errors`。`dynamic_raw_fallback` 11/11 完成，可回答题平均类别 F1
为 0.3184；与可匹配的10题同策略历史结果相比为 0.2094 → 0.3184。`dynamic` 2/3 完成，
成功的2题平均 F1 为 0.3230；另保留既有失败计0口径的3题平均 F1 为 0.2154，
3题历史结果为 0.2704。分别报告执行失败和成功项评分，避免只看成功项掩盖失败。固定小样本、单轮且非同期，
分数只作描述性线索，不能证明普遍提升。QA 3 的 `dynamic` 在三次 resolver 尝试后仍未
通过校验：一次未为每个候选恰好给出一项 decision，两次生成未正常结束。未追加重跑。

| QA | 作者核对原文与 Trace 的结论 |
| --- | --- |
| 0 | yesterday 锚定 2023-05-08，回答 2023-05-07，保持正确 |
| 3 | raw_fallback 首次交付核心 Memory 和 D2:8，回答 adoption agencies，历史拒答已改善；dynamic 仍失败 |
| 15 | raw_fallback 保留多项活动，但遗漏 painting，回答较长且重复；D17:10 和 D8:6 等 painting 来源未进入首次输入，判 sufficient 后未补查。dynamic 回答包含 painting |
| 18 | mountains、beach、forest 均回答，改善原来只有 beach 的结果 |
| 32 | 回答 workshop、pride parade 等6项；首次未交付 D1:3，仍漏 support group，判 sufficient 后未补查 |
| 36 | 来源 2023-07-17 的 last weekend → 2023-07-15 至16，保持正确 |
| 53 | 两策略均按来源 this week 得到 2023-08-21 至27；dynamic 不再沿用旧 previous week 错误 |
| 60 | clarinet 与 violin 均保留 |
| 74 | 来源 2023-10-20 的 this past weekend → 2023-10-14 至15，保持正确 |
| 136 | reading 与 painting 均回答，D17:10 已交付，改善原来只有 painting 的结果 |
| 153 | 实际触发补查，首次用于不足解释的记忆仍保留；原文仅有不确定的收养想法，无夏季计划，继续正确拒答 |

成功13项的引用均未越出最终回答上下文，也未越出对应 Memory 来源。原文的说话者和
会话时间另作人工核对，没有发现人物混用。QA 153 没有可直接回答问题的首次答案，
不能把该真实拒答案例当作 QA 15 部分答案恢复已获真实验证；后者由离线受控回归及
20题打包重放覆盖，本轮 QA 15 没有触发补查。

多项目覆盖的 QA 15/32 与 dynamic QA 3 的稳定性仍未通过验收；不能宣称所有问题已解决。
输入覆盖仍是主要缺口，Answer Prompt 无法补齐未交付的事实。活动答案也仍存在过度
展开日期和重复细节，短答案展示体验尚有改进空间。

逐题结果与历史对照见 [report.md](live-results/report.md)，机器可读 Trace 摘要见
[results.json](live-results/results.json)，核对的原文与引用检查见
[source-audit.json](live-results/source-audit.json)，执行摘要见
[outcome.json](live-results/outcome.json)，安全校验错误见
[validation-causes.json](live-results/validation-causes.json)。未复制数据库、密钥或原始 provider 日志。

## 复核与回滚

本轮仅新增测试、实验入口及记录。没有数据库迁移、新模型、新依赖或 UI 重设计。
作者按 Standards／Spec 两轴复核，以 `7546b41` 为本轮固定比较点。
Standards：本轮复用既有 API、Campaign、Schema 校验和浏览器入口，无新依赖；
额外核查冻结校验、逐请求硬上限、重复执行保护、Build 不变与敏感输出，未发现剩余可操作
违规。Spec：离线、编译、展示及授权的14项单轮真实复验均已执行；真实失败与覆盖不足
明确保留，没有用离线结果替代真实验收，也没有为跑分追加调用。
最终新增实验脚本的编译检查及 `git diff --check` 再次通过。
回滚本轮本地提交可移除这些验证增量，已保存旧 Build 和历史实验仍保留。
未执行 push、PR、Notion 写操作，未将任务标记为完成。
