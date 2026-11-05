# 成本与预算分析

2026-11-05 最新终态：conv-44 与六份严格 JSON 均已完成独立复核。锁定的独立 Level E 已单次冻结 800 项，根代理与非作者终态审计通过后才读取 Gold 评分。H/D 成功 394/389（每臂400）；类别1–4完整分母 F1 为 0.402606/0.409151，差值区间跨零；类别5字面拒答单列。本阶段 2,112 请求、预约 USD105.4516575，末段 HTTP402 及18次未知 usage 预约保留；没有重跑。800项来源盲审、条件语义汇总与私有白名单归档已完成；来源支持297可判定对净增10对，区间仍跨零。独立复核和14项底稿见[最终交付索引](FINAL_DELIVERY_EVIDENCE_INDEX_V1.md)。当前结果与测量边界见 [Level E 结果](LEVEL_E_RESULTS_V1.md)。下文历史检查点保留各自时点，不代表本次终态。

2026-11-05更新（北京时间）：conv-44关系阶段已失败终结，实际417请求、预约USD20.5545036、已知usage峰价上界USD2.3807064、Unknown0。七个获批阶段累计1,850请求、预约USD91.5141141、已知usage峰价上界USD10.2965160；历史7项Unknown预约USD0.3500316完整保留，实际账单未读。见[最新累计终态](../../experiments/m5-development/cost-ledger-including-conv44-relations-terminal-v1.json)。原余量不转移，新的10任务恢复拟为30请求/USD2.619648，尚未授权；下文保留原阶段记录。

2026-11-04。开发集 Level C 与conv-43关系阶段均已终结；关系终态为related，未publish/query/QA。所有额度独立，不可互转；剩余容量不授权额外片段尝试、补跑或新阶段。费用分为保守预约、已报告 usage 的价格上界和实际账单；**实际账户账单未读取**，不能将前两者称为付款金额。

## 当日价格与请求政策

已从 DeepSeek 官方 Models & Pricing 核对 `deepseek-flash`，当日公开映射 `DeepSeek-V4.1-Flash-1017`。峰时每百万 cache-miss 输入 USD0.30、输出 USD1.20，非峰时减半。官方页面 SHA 和来源见 `pricing-20261104.json`；每个付费阶段执行前又核对价格。响应只返回可变 alias，不能声称不可变服务端版本 pin。课程正式课件未规定精确 ID/thinking，背景记录原为课堂转述。用户本次已确认最终评测用该版本且禁止thinking，见[模型要求](MODEL_REQUIREMENTS.md)；既有low/high实验不冒称最终符合设置。

BudgetTransport 在 HTTP 前以 SQLite BEGIN IMMEDIATE 预约，每次 schema/transport 重试都消耗次数和金额。底层 HTTP retries=0；模型、官方域名/路径、输入 messages bytes、输出 max_tokens 和非流式请求均检查。跨进程共享上限，不允许静默扩大同一账本政策。Unknown/部分 usage 保留全预约，不用缺失值估算退款；本地明确 pre-HTTP 拒绝不算发送，之前真实请求保留。

每次消息上限 160,000 UTF-8 bytes、输出上限 32,768 tokens，峰价最大预约为：

```text
(160000 × 0.30 + 32768 × 1.20) / 1000000 = USD0.0873216
```

输入字节采用保守 token 上界，不是精确 tokenizer 账单预测；各请求按实际输入字节预约，所以终结预约低于全次数乘最大上界。

## 已获批阶段

| 阶段 | 明确批准的请求/美元硬限 | 当前状态 | 实际物理请求 | 保守预约 USD | 完整已知 usage 峰价上界 USD |
| --- | ---: | --- | ---: | ---: | ---: |
| conv-43/44 抽取及唯一恢复 | 204 / 18；恢复额外最多3次仍在原账本内 | 终结，conv-44 仍 failed | 78 | 3.4624767 | 0.2265405 |
| conv-43 关系 | 1,200 / 104.78592 | 400/400任务终结为related | 408 | 20.2028820 | 3.9199638；7项Unknown另列 |
| 固定开发集 QA | 1,500 / 130.9824 | 200 项终结，151 成功/49 失败 | 421 | 19.3089549 | 1.1698209 |

三阶段终态合计 **907请求、预约USD42.9743136、已报告usage峰价上界USD5.3163252**，没有在途请求。最新[终态费用汇总](../../experiments/m5-development/cost-ledger-terminal-v1.json)以observed_utc记录身份；旧cost-ledger.json原样保留为运行中历史快照，不作为当前终态。7项transport_unknown均来自关系阶段，未知预约USD0.3500316完整保留，不将其用量补零或从预约退款。

抽取初始 68 片段、每片段最多3次，204请求的最大预约 USD17.8136064，小于批准 USD18。初次实际75请求、预约USD3.3289083、usage峰价上界USD0.2173917；conv-43 34/34、402 Memory，conv-44 33/34、383 Memory。用户随后明确批准只恢复 conv-44 ordinal18 最多3次/USD0.2619648；实际3次、预约USD0.1335684、usage上界USD0.0091488，仍全部失败。累计 Unknown 0。原剩余126次/USD14.5375233不授权继续尝试；唯一恢复入口保留终结 marker。

conv-43 关系按生产顺序固定400任务、7,620对比较，最多三次内部尝试，故1,200请求×USD0.0873216=USD104.78592。使用既有独立索引副本，relation thinking high，不包含 conv-44、重建、publish、query 或 QA。原抽取及index-v3库保持保护；根代理终态relation_audit已通过，公共结果见[关系终态](../../experiments/m5-development/conv43-relations-terminal-v1.json)，非作者已独立重跑并核对完整审计对象一致，见[独立终态复核](RELATION_TERMINAL_REVIEW_V1.md)。实际408请求为401 response_received、7 transport_unknown；剩余792次/USD84.5830380不授权重跑或转移。conv-44 当前关系预估375任务/1,125请求/USD98.2368来自不完整快照，不是授权或可直接执行的完整构建方案；抽取改变后必须重算。

Level C 为固定80普通+20诊断、H/D两臂；每题操作上限2+3、每操作最多3次，所以100×5×3=1,500请求，最大预约USD130.9824。analysis/answer disabled、resolution low，Bonus off，四开发 Build 不重建。421请求全部返回完整usage：输入2,860,923、输出259,620 tokens。H210次/USD0.2301042、D211次/USD0.9397167（均为峰价上界）；重试分别10次/USD0.005415和9次/USD0.0018105。49个D输入失败中已发送55次analysis尝试/USD0.00687；本地拒绝本身不算发送。剩余1,079次/USD111.6734451不自动批准补跑。结果和实际时长见 [Level C 真实结果](LEVEL_C_RESULTS.md)。

## 离线、历史与摊销边界

Level A/B、合成测试、来源审阅工具校验和本地 MiniLM 编码不产生本项目新的 Provider 请求；stub 的零费用不代表真实模型成本。757题六臂回放有本地CPU/RSS/存储测量，排除新模型操作；压缩完整请求代理 tokens 仅节省0.02925%，没有实际账单节省或模型解码非劣证据，不晋级付费组合实验。

历史四 Build 已知费用 ¥89.65501696、Unknown 预约 ¥7.077888；历史 Hybrid Query 已知 ¥9.59767936、Unknown ¥2.359296；历史 Dynamic Query 已知 ¥98.93052152，来自 Phase 7 冻结账本，不重复消费、不改价。不同日期/模型/Prompt/wire 不作严格因果成本比较。

摊销使用 Build/Q + Query + Retry + Unknown预约，并单列CPU、RSS、存储；硬件单价未知时为 not_measured。本轮实际账户账单、本地硬件货币成本仍未测量。凭据仅由既有 launcher 在子进程加载，没有输出或提交真实值。

## 待审批的输入扩容方案

用户确认token预算翻倍至192,000；对再次翻倍字节的追问形成具体640,000字节方案。保持输出32,768和最多1,500物理请求时，峰价最大预约为1,500×(640000×0.30+32768×1.20)/1,000,000=USD346.9824。它是新阶段的独立提案，未获预算授权，不与旧QA剩余容量合并或互转；新thinking全disabled，原低/高思考实验不重标。仅字节320,000方案对应最大预约USD202.9824，两种金额均不是实际账单预测。原获批三阶段均已终结；新v2真实调用仍为0。

`level-c-input-diagnostics-final-v2.json` 的阈值和无损编码探针均为离线数值诊断，provider请求为0，没有改动任何原账本。640,000字节/192,000 regex tokens可容纳100项历史完整首次输入，只说明首次输入门槛；后续重试、模型context接受情况及实际usage未验证，不能把此计数当作预算消耗或成功率预测。用户参数记录见 `experiments/m5-development/input-limit-followup-request-v1.json`。
