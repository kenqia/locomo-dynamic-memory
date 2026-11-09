# Level C 公共数字汇总独立复核 v1

结论：当前公共工件的算术、分母和文件哈希交叉核对通过；工具发现1项P2：重复 score 单位可绕过分母守卫。该缺口未出现在本轮200行实际工件中，不推翻当前数字，修复前仍应保留代码发现。

2026-11-04。非作者审查者 `final_code_review_v6`，HEAD `c8e5c09456c8bfc3f2ad56701a0bfb56928c12b1`。按授权只读取 `tools/m5/level_c_results.py` 和 `experiments/m5-development/level-c-results-v1/` 内公共派生JSON。报告沿用已读取的 `google-developer-docs` 技能。未修改实现。

## [P2] 拒绝重复 score 单位，避免单臂统计与配对统计使用不同分母

`tools/m5/level_c_results.py` 第75—78行先将 scored 转为 `(question_id, arm)` 字典，再检查字典长度和键集合。重复行被覆盖，无法被这项检查发现。第99—110行的 `groups` 继续使用原始 scored，重复行会多计 planned、scorable、成功数及均值；`comparisons` 则再次按身份去重，两者分母因而不一致。若重复行内容有差异，身份/失败零分校验也只核对最后一条。

独立复现只在内存中读取获准的公共 `per-question-metrics.json`，不访问stage、不修改任何文件：

```python
duplicated = rows + [rows[0]]
by_id = {(r['question_id'], r['arm']): r for r in duplicated}
assert len(duplicated) == 201
assert len(by_id) == 200
assert set(by_id) == {(r['question_id'], r['arm']) for r in rows}
```

现有分母条件仍为通过，但普通题 Hybrid 会计81项，普通题配对仍为80项。建议在构造映射时要求 scored 恰好200行、每个身份恰好出现一次，再进行统计。已先将发现发送主任务；审查者没有修改作者代码。

## 当前工件的独立交叉核对

使用一段独立 `python` 脚本，从公共逐题数值重新计算计数、均值、配对差值和成本总量，未调用结果工具生成路径。40个分组、200个唯一单位、100题及4个输出manifest条目全部通过。所有QA值均为有限范围内的数值，均有Gold，49个失败项均为0；未因失败删除计划项。failures身份集合与逐题失败集合完全相等，失败类型为35项 `physical_request_policy_rejected` 和14项 `complete_resolution_input_budget_exceeded`。

| 分层 | Hybrid 成功/计划 | Dynamic 成功/计划 | Hybrid 失败计0均值 | Dynamic 失败计0均值 | Dynamic − Hybrid |
| --- | --- | --- | --- | --- | --- |
| ordinary | 80/80 | 41/80 | 0.3998827871 | 0.2283294865 | -0.1715533006 |
| diagnostic | 20/20 | 10/20 | 0.4565025253 | 0.2933021542 | -0.1632003711 |

按对话、类别和分层的计划数、成功/失败数、可评分数、评分规则计数和两种均值均与逐题数据一致。ordinary与diagnostic配对分母分别为80和20；improved/regressed/unchanged加总正确。

两臂共同成功子集分别只有41和10题，其差值均值分别为+0.0774267288和+0.1099628942。工具明确标记 `post-outcome subset; selected by runtime success, not a causal quality estimate`；这些正差值不能替代包含失败的主要结果，也不能证明Dynamic整体质量优于Hybrid。

类别5被单列，且本轮普通题与诊断题的类别5计划数均为0、均值为null。当前100题全部属于类别1—4；因此本轮不能估计类别5拒答表现。工具明确区分类别5的官方字面拒答规则与事实正确性，未将其称为来源语义真值。

按臂、operation与runtime重新加总的调用数、retry次数及已报告token一致；合计421次物理请求、2,860,923 prompt tokens、259,620 completion tokens，total tokens为3,120,543。以每百万prompt USD0.30、completion USD1.20独立Decimal重算，缓存未命中峰价金额为 **USD1.1698209**，与ledger及各臂分项加总一致。usage未知数为0。该值是对已报告用量的价格上界估计；ledger的USD19.3089549是预约金额，两个字段均不能当成实际账单。顶层和ledger均标记 `actual_invoice_usd=not_accessed`。

公开说明限定四段已暴露开发对话、固定80+20题，明确无holdout、无Bonus，并声明 `not a new 757-question score`。bootstrap字段标记为四段暴露对话上的探索性逐题bootstrap；它不是757题总体或独立holdout的推断。`semantic_source_support` 仍为 `pending_independent_review`，未把官方QA数值冒充来源支持结论。

## 工件身份

| 文件 | SHA256 |
| --- | --- |
| `tools/m5/level_c_results.py` | `cbae17f7e81b067264259ba57e28c2754abf3d9eeabe13a9119321a34bac8323` |
| `metrics-summary.json` | `62ecb7708af88634043b8a5c94cc5aff4cf5dbb7d39edf40b422e6c4796442c6` |
| `per-question-metrics.json` | `f70425c8c3979507bccc27bf6b0683b189690820b846c24a46ef7f2629e5efa9` |
| `failures.json` | `36e4613959700665a09f6febc730f8cf103e1cdea412ef912af200d09ccdc94d` |
| `source-manifest.json` | `14d0d5f433429485c14b7cd4e687f4de2380dc03d3415af4e3aac7ce12557285` |
| `sha256-manifest.json` | `7d57cb2c40f2611c8f51bb3350d2a872465ff74cfac7192242c5f0a6ecd46ad7` |

## 验证边界

本次没有运行生成、Gold评分或真实终态审计，也没有重新生成bootstrap区间；仅检查现有区间端点顺序、作用范围说明和配对基础数值。输出manifest的4个SHA均独立重算匹配；source-manifest中的私有来源SHA只作为已发布的绑定记录，没有打开对应私有文件作比较。

没有读取真实private stage、raw items、Gold/reference数据库、来源审阅packet/labels或历史预测，没有调用provider、重启会话或干预关系session85918。没有添加测试脚手架；实际验证为上述独立公共数值与哈希crosscheck。本报告不裁决答案事实性、不代替两位独立来源审阅者，也不批准总目标验收或远端写入。

## 修复后独立复核：P2 已关闭

2026-11-04，同一非作者审查者复核修复，保留初审发现及复现。工具新增 `len(scored) == 200`，结合200个唯一身份及冻结身份集合相等，拒绝201行重复输入；重复行不能再进入统计。另新增分数类型、有限性及[0,1]范围校验，拒绝bool、NaN、Inf和出界值。没有发现新的P0/P1/P2。

| 文件 | 修复后 SHA256 |
| --- | --- |
| `tools/m5/level_c_results.py` | `32a3a96b7f6f97f91c7621b0e08eb9ddab0c3819ed41980d93d6e48a64d446c5` |
| `tests/test_m5_level_c_results.py` | `09040352bc8d3ae5a53f8039d01023cc78663628afcae045066645b90799c310` |
| `docs/m5-development/LEVEL_C_RESULTS.md` | `207548a5dc55bef3b1b09bf09fa6b8cda679d1c63a1e7f49a47f4ae1a9e4ced6` |

实际独立执行：

```sh
./tools/integration/check.sh tests/test_m5_level_c_results.py -q
```

结果：`7 passed, 1 warning in 0.24s`。包括完整synthetic 200项正例、实际201行重复输入拒绝及5种非法分数。warning为既有Starlette/TestClient的httpx弃用提示。全部使用synthetic fixture，没有重新生成真实公共结果；4个公共manifest SHA再次核对仍匹配，初审核对通过的v1数值不变。

同时通读 `LEVEL_C_RESULTS.md`：其中分层F1、配对差值与区间、共同成功子集、失败计数、延迟四组p50/p95、资源、请求/token/峰价/预约/剩余容量及模型alias数字与获准公共JSON一致。文档保留了选择偏差、无类别5样本、不能外推757、账单未读取和来源语义待审的限制，没有与当前公共数字相矛盾的结论。

历史757题分数、两个离线重建messages字节数、价格页具体版本映射和私有审计细节不在本次获准公共数值集合内，未独立验证这些陈述；本次核对不为它们新增证据。仍未读取任何来源审阅packet、labels或review输出，也没有打开private stage、Gold/reference DB或干预运行会话。

## 公共来源语义汇总追加核对

2026-11-04，来源审阅交付后，按主任务新增授权仅检查三个公共语义JSON和更新后的 `LEVEL_C_RESULTS.md`，未读取私有packet、引文、review文件或Gold。结果：未发现数值或结论矛盾，无新P0/P1/P2。

独立Python crosscheck从公开200条匿名标签及100条pair的公开分层/策略/对话归属，重新计算总体、两臂、分层×策略、对话、对话×分层×策略共27组的全部计数和指标。所有组均与汇总一致；pair覆盖恰好200个唯一unit，pair中的来源/引用标签与单位标签一致。

全部200项已审，49项failed逐条保留为语义N/A及错误null，151项非失败进入语义判断集合。每组每项指标均满足“可判断分母＋unknown/N/A＝非失败项数”，没有将失败或未知算成语义正确。总体来源支持为105/141，另有10项unknown；引用支持为93/122，另有18项unknown、11项N/A。两臂来源支持64/92和41/49、引用支持53/79和40/43，与文档一致。合理拒答10/24，另14项false、2项unknown；125项实质回答不进入拒答判断分母。错误人物0/151、事件1/146、时间4/144、列表遗漏20/139的分母和剩余null均一致。

| 分层 | 指标 | 公开pair可判断分母 | 改善/退化/不变 | 平均差值 |
| --- | --- | --- | --- | --- |
| ordinary | 来源支持 | 39 | 6/1/32 | 0.1282051282 |
| diagnostic | 来源支持 | 9 | 3/0/6 | 0.3333333333 |
| ordinary | 引用支持 | 34 | 11/0/23 | 0.3235294118 |
| diagnostic | 引用支持 | 8 | 3/0/5 | 0.3750000000 |

这些分母均从两臂成功的41/10题进一步筛选双方标签可判断的单位，unknown/N/A产生null差值并排除于pair指标。逐对差值、改善/退化/不变及均值独立重算一致。此次依据公开pair身份关系核对，没有打开私有映射重新证明其原始question_id对应关系，也没有重新生成bootstrap区间。

provenance公开记录200项、461条引文、2,080条来源（文档788＋1,292），并明确AI辅助独立审阅、每项只有一人判定、无双人一致性、非人工/教师真值。该元数据内部一致；本次没有查阅私有引文，未独立复验461条原文或审阅者的全文阅读行为。文档保留运行失败和可判断条件造成的选择偏差，未把Dynamic较高的子集来源支持比例解读为全100题总体收益，未把来源支持标签称为teacher truth。文档的具体语义案例仍由来源审阅者负责，本次数值核对不新增案例层面的语义证据。

| 文件 | 本次 SHA256 |
| --- | --- |
| `semantic-review-summary.json` | `cb4855886bea032ee3e46aaac4b97e5a3d84359ddcb6d5149ebd067b93330476` |
| `semantic-paired-differences.json` | `9daa8e9ad6d4a086d6bf94fdce98416b39bc6a4c5e530979fa93e0c2cbac6df7` |
| `semantic-review-provenance.json` | `f626f894f7d787bf83dd2d7fd2da19cc7a06bcc6881bc1c6033188475e316dff` |
| `docs/m5-development/LEVEL_C_RESULTS.md` | `0ea9b56def7ccc4d4ee24b67fad44a99be6b612e166f373773d5629c1cffa6f7` |

本次只追加上述受限公共数值核对记录，没有修改其他代码、运行模型或触及真实private stage。本次crosscheck通过后不再进行无必要复跑。
