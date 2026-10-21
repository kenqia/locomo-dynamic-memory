# 当前系统的五策略展示实验

本轮是课程项目的增量质量展示，不恢复已取消的Issue #15/#21全量实验。固定使用 `conv-26` 已有完整Build，保留历史实验，禁止重抽Memory或重跑关系构建。全部生成沿用现有评测、查询与候选检查API，不新增LLM评估器。

## 固定范围

| 检查 | 固定范围 | 结果与口径 |
| --- | --- | --- |
| QA配对 | 20题，每个官方类别4题，五策略共100项 | 既有官方类别计分、成功率、分题差异；类别5拒答匹配单列 |
| 证据Recall | 40题，类别1–4各10题，来源均可映射 | 实际初始RRF排序的Recall@5/10/20；K计Memory，覆盖计去重Source Turn |
| 动态场景 | 10个真实关系对，4 UPDATE、3 RETAIN、3未确定 | 存储关系、原文语义审阅、实际查询关系及有效Memory分别记录 |
| 来源语义 | 固定20条配对实验中的Dynamic + 原文兜底回答 | 核对引用身份及来源是否支持结论；失败不换题，拒答与正面断言分开 |
| Web | 5个合成边界场景，另检查本次真实结果的保存记录 | 截图、操作记录、来源/解释/历史关系、策略切换；回放不冒充实时生成 |

五策略依次为 `full_text`、`vector`、`hybrid_no_resolution`、`dynamic`、`dynamic_raw_fallback`。每题依次运行相同五策略，每个逻辑项单轮；适配器原有有限重试保留，不能按成绩挑选重试。Full Text输入完整对话，其他策略保留各自预算，不宣称输入量相同。

使用种子 `showcase-20261021`，按SHA256种子与题号排序，在每个类别中取固定数量，再恢复原始题号顺序。题单在结果产生前冻结，不根据本轮成绩换题。全部属于已用于开发的同一对话，不能称为独立测试或统计显著性证据。

## 身份与额度

隔离目录为 `/home/kenqia/my_folder/locomo-worktrees/current-showcase-five-strategies-frozen-20261021`。原始来源为 `real-baseline-issue15-citation-followup-frozen`，通过SQLite备份复用完整Build。Build ID、原件/构建/源码/共享实验脚本摘要、模型、Prompt及配置见 [plan.json](plan.json) 和 [plan.sha256](plan.sha256)。

用户明确批准最多420次新DeepSeek调用，失败及重试同计；历史1,169次保留，累计上限1,589。授权范围见 [authorization.json](authorization.json)。仅凭据存在性检查不计费，实际凭据由现有launcher载入单个执行进程，不进入产物。

最终执行状态以隔离目录的 `outcome.json`、`campaign.sqlite3` 和保存Run为准。执行期间不得修改 `run.py`、共享执行脚本或生产源码；若身份变化，既有保护停止新调用。本轮报告脚本只读已有结果。

## 复现入口

在工作区根目录离线冻结新目录：

```sh
HF_HUB_OFFLINE=1 .venv/bin/python experiments/current-showcase/run.py prepare --directory /absolute/new-showcase-directory
```

明确确认新目录的范围和额度后执行，不复用旧授权重复跑：

```sh
HF_HUB_OFFLINE=1 python scripts/with_deepseek_env.py -- .venv/bin/python experiments/current-showcase/run.py execute --directory /absolute/new-showcase-directory --authorized-call-limit 420
```

从已保存结果生成报告，不调用模型：

```sh
.venv/bin/python experiments/current-showcase/report.py --directory /absolute/completed-showcase-directory --output experiments/current-showcase/results
```

## 审阅边界

[调用前来源审阅](dynamic-source-review.json)在本轮生成前完成。审阅者为当前开发助手，不是独立人类标注或课程动态真值；两处存储关系存在来源语义异议，保留异议，不把模型存储标签当成正确答案。当前Build没有真实SUPERSEDE/CONFLICT，不能用此样本估计这两类关系质量。

Web合成检查使用真实Streamlit/HTTP/SQLite及浏览器，但LLM与Embedding受控；真实结果展示使用未改动的Streamlit和只读API读取本次保存Trace，禁止新生成或构建。两者各自注明，均不计为新的真实QA样本。

## 离线与浏览器验证

执行前验证：

```sh
LOCOMO_LIVE_MODEL=0 LOCOMO_LOCAL_EMBEDDING=0 .venv/bin/python -m pytest tests/test_evaluation.py tests/test_evaluation_recovery.py tests/test_full_text.py tests/test_evaluation_reports.py tests/test_browser_fixture.py -q --tb=short
```

结果24 passed，57.20秒，1条既有Starlette/httpx弃用警告。编译、题单分层、来源映射、预算连续性及冻结阶段零生成检查通过。

```sh
bash tests/browser/run.sh /home/kenqia/my_folder/locomo-worktrees/browser-env/bin/python
```

退出0，Chromium156.0.8078.4，无pageerror/console error。五张合成截图和机器结果保存在 [web-controlled](web-controlled/issue-12-result.json)。截图包括当前问答、历史问答、冲突、证据不足和评测结果；同次还验证构建失败后显式重试及Memory导出。

本轮未获远端任务写入请求，不更新Issue/Notion或推送代码。
