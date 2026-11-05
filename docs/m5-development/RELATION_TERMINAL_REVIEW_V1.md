# conv-43 关系终态独立复核 v1

结论：**实际独立只读审计通过，与根代理终态审计返回的完整JSON对象一致。** conv-43为`related`，400/400任务成功，保存7,620条关系；仍未publish、查询或评测。此结果不等于complete Build、语义准确率、全disabled最终评测或发布批准。

非作者复核者：`final_code_review_v6`。实际观察时间：2026-11-04 09:19:00 UTC（Asia/Shanghai 17:19:00）。工作树为`/home/kenqia/my_folder/locomo-worktrees/m5-final-development-20261104`，审查时HEAD为`8868a58e74bbb72d24caeedc02389f8c86195ffa`。报告遵循已读取的`google-developer-docs`技能。

## 实测范围与身份

独立调用既有`tools.m5.relation_audit.audit`，由工具只读访问已获批的关系阶段构建副本、冻结源索引快照、计划、provider checkpoint与独立ledger。工具内部核验Memory、关系和Source契约，只返回allowlist中的数值、状态及摘要；复核者未打开QA/evidence/answers、raw日志、凭据或手动浏览来源原文，没有Provider请求或数据库写入。

| 工件 | SHA256 |
| --- | --- |
| 实际审计器`tools/m5/relation_audit.py` | `039c02b6390eab5366745514524428f9b28a39f7e6962ed7f852da5ff4d25bc8` |
| 已有`terminal-audit-v1.json` | `93ba6dd8a92e2f95985d3eb2aa00928e0e9ed507314f2458c1e56970e86ce793` |
| 审计返回的冻结plan身份 | `3ecc4142916a7959b2c4fde9d421214ee872d0401bc5bf82f8d07b10478495c6` |
| 核验通过的保护表摘要 | `7fb769de068529544249b061c248edf6549c4f70cef10a9cfee0bbb8eccea01d` |

实际执行使用以下解释器与核心调用，并在同一脚本中断言完整对象相等、任务/关系/请求数量、金额、余量与关键边界布尔值；实测`audit`与比较耗时0.357秒。原终态文件仅为纯数值/状态审计结果，未覆盖或另写它。

```sh
PYTHONPATH=tools/integration/offline_guard:src:. /home/kenqia/my_folder/locomo-dynamic-memory/.venv/bin/python - <<'PY'
from pathlib import Path
import json
from tools.m5.relation_audit import audit
stage = Path('var/m5-development/conv43-relation-proposal-v1')
result = audit(stage)
assert result == json.loads((stage / 'terminal-audit-v1.json').read_text())
print(json.dumps(result, ensure_ascii=False, indent=2))
PY
```

## 终态与阶段边界

以下值由独立调用实际返回，与[公共终态审计](../../experiments/m5-development/conv43-relations-terminal-v1.json)对应。先前[审计器代码复核](RELATION_AUDIT_REVIEW_V1.md)的synthetic验证与本次真实终态实测分开保留；本次未重复运行测试套件。

| 核查项 | 独立实测结果 |
| --- | --- |
| Build终态与任务 | `related`，`terminal=True`；`succeeded=400`，无pending/running或任务错误码；计划任务总数匹配 |
| 关系总数与契约 | 7,620；undetermined 7,465、RETAIN 60、UPDATE 94、SUPERSEDE 1；逐条生产来源/schema、端点、同Build与conv-43归属校验通过 |
| 索引源冻结基线 | 原索引库逻辑快照等于冻结plan中的`source_index_snapshot` |
| 保护数据与conv-44 | 固定保护表摘要与冻结源索引库一致，涵盖Source、Memory、来源连接、片段和索引；其他Build完整行不变，包含conv-44；无其他Build关系任务 |
| 投影 | 按真实生产`create_projection`重算，与保存的完整投影JSON相等 |
| 发布、查询与评测 | 未发布；工具检查存在的active_versions、candidate_queries、query_traces、evaluation_runs、evaluation_run_items均为空；留出QA/evidence/answers未读 |
| 物理请求与checkpoint | ledger 408次，与provider调用checkpoint数量408一致；401次response_received、7次transport_unknown；未知用量7次 |
| 调用结果 | succeeded 400、model_timeout 5、model_http_error 2、invalid_output 1；调用错误码为timeout 5、HTTP 2、known_source_required 1，与任务最终成功分开记录 |
| 已知报告用量 | 输入4,044,162、输出2,255,596、合计6,299,758 tokens；不包含7次未知用量 |
| 保守预约与已知usage峰价 | USD20.2028820预约；已知报告usage按峰时cache-miss计算USD3.9199638，未知请求继续保留预约；实际账单未测 |
| 独立批准上限与余量 | 1,200次/USD104.7859200，完整ledger policy匹配冻结plan；剩792次/USD84.5830380，不自动授权任何后续阶段 |

索引不变性在本次以冻结逻辑快照和保护表摘要核验；没有重新执行embedding编码或将既有402×384验证冒称本次重新测量。关系来源/schema通过不证明关系标签在真实语境中的语义准确率。

## 三阶段费用独立重算

另一个只读Python脚本读取[恢复后抽取结果](../../experiments/m5-development/live-extraction-post-recovery-v1.json)、[旧Level C结果](../../experiments/m5-development/level-c-outcome-v1.json)与上述纯数值终态文件，使用`Decimal`相加，并断言请求907、预约USD42.9743136、已知usage峰价USD5.3163252。结果与[终态费用汇总](../../experiments/m5-development/cost-ledger-terminal-v1.json)对应，不改写旧运行中观察快照。

| 阶段 | 物理请求 | 保守预约USD | 已知报告usage峰价USD | 未知用量请求 |
| --- | ---: | ---: | ---: | ---: |
| 抽取及唯一恢复 | 78 | 3.4624767 | 0.2265405 | 0 |
| 旧Level C开发QA | 421 | 19.3089549 | 1.1698209 | 0 |
| conv-43独立关系 | 408 | 20.2028820 | 3.9199638 | 7 |
| 合计 | 907 | 42.9743136 | 5.3163252 | 7 |

USD5.3163252只汇总已知报告usage，不能称为含未知请求的全部用量上界或实际付款；USD42.9743136为保守预约，不是账单。三阶段账本和授权独立，任何余量均不可自动转移。

## 未覆盖范围

本次没有执行publish、完整导出、查询、QA、评分、恢复或新模型调用，没有修改Build、索引、投影、冻结计划或ledger。conv-44仍保留失败，六份完整Build/严格导出仍未齐备；关系阶段原thinking high如实保留，不能作为全disabled最终合规证明。真实语义准确率、实际账户账单、Level E与整个Release验收均未完成；本报告只确认上述真实关系阶段终态及费用核算。
