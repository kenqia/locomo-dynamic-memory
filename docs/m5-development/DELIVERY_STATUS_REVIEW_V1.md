# M5 公共交付状态一致性审阅 V1

结论：在本次指定的公共文档、状态 JSON 和 Level C 聚合数值范围内，未发现需要阻断交接的实质矛盾。该结论不构成 Release 批准、总任务完成验收、教师真值确认或新的付费授权。

## 审阅身份与范围

- 审阅者：独立 AI 子代理 `/root/final_actual_review`（Codex）；本次未参与所审公共交付材料的编写。
- 只读审阅时间：2026-11-04T07:42:37.380299+00:00。
- 工作树：`/home/kenqia/my_folder/locomo-worktrees/m5-final-development-20261104`。
- 审阅时 HEAD：`3335862dba1e9658f4d5c515b602c98049826d7c`（任务指定基线 `3335862`）。
- 实际读取根目录 `AGENTS.md`、`CONTEXT.md`、ADR 0001/0002，以及下方 SHA 表列出的公共文件。采用 `google-developer-docs` 技能组织本报告。
- 唯一写入文件为本报告。未修改源码、配置或其他交付文档；未 commit、调用 Provider、访问网络或重跑测试。
- 未访问 `var`、Gold、凭据、真实对话原文或留出内容；公共 JSON 中的私有路径字符串未被解引用。

## 核对结果

本次使用只读 Python 聚合检查完成 202 项断言，全部通过。检查直接读取公共 JSON，使用 `Decimal` 重算金额，未重新评分或生成答案。

| 核对项 | 可验证依据 | 结论 |
| --- | --- | --- |
| 旧 757 题与新 100 题 | `HANDOFF.md:32–40`、`LEVEL_C_RESULTS.md:7–20`、`EXPERIMENT_RESULTS.md:11–15` | 旧四策略 F1 被明确标为历史 Run；本轮为 80 普通 + 20 诊断、两臂 200 项，没有混用分母。Level B 的 753 可评分来源映射也单列。 |
| 新 QA 完整分母 | `metrics-summary.json` 的 `strata`、`runtime` 与 `level-c-outcome-v1.json` 的 `ordinary_scores`、`paired_comparisons` | 普通 H 80/80、D 41/80；诊断 H 20/20、D 10/20。合计 151 成功、49 失败。F1 与配对差均一致，普通差 −0.17155330059864465。 |
| 成功子集选择偏差 | `LEVEL_C_RESULTS.md:18`、`:69–71` 与 `semantic-paired-differences.json` | 共同成功普通 41 对、诊断 10 对；来源判断确定子集为 39/9 对。文档没有将其正差代替完整分母结论。 |
| 来源支持与语义分母 | `semantic-review-summary.json` 的 `summary`、`LEVEL_C_RESULTS.md:55–75` | 各层、各臂、各对话的指标均满足正例+反例=可判断分母，且加不确定/N/A 后等于成功项数。总体来源支持 105/141，另 10 不确定、49 失败；引用支持 93/122，另 18 不确定、11 N/A、49 失败。 |
| AI 审阅与教师真值 | `semantic-review-provenance.json`、`LEVEL_C_RESULTS.md:57`、`HANDOFF.md:38` | 每项一名 AI 审阅，没有双审一致性；公共材料明确不是人工或教师真值，没有将来源定位/逐字引用验证冒称语义真值。 |
| low、high 与最终 disabled | `metrics-summary.json` 的 `model_identity`；`MODEL_REQUIREMENTS.md:7–18`；`final-model-requirement-v1.json` | 421 次 QA 实际为 370 disabled + 51 low；原关系 high 按已批准冻结计划继续。当前文档如实保留旧实验，不冒称全链 disabled 最终成绩。后续最终评测的新生成要求明确为 disabled。 |
| 终结阶段的请求及费用 | `cost-ledger.json`、`level-c-outcome-v1.json`、`COST_ANALYSIS.md:21–33` | 抽取/恢复 78 + QA 421 = 499；预约 3.4624767 + 19.3089549 = USD22.7714316。QA 两臂费用加总及输入/输出 usage 峰价计算均等于 USD1.1698209。实际账单明确未访问。 |
| 运行快照与终态 | `cost-ledger.json:2–15`、`:47–76`；`run-manifest.json:44–60`；`HANDOFF.md:50–52` | 2026-11-04T07:34:07.332316+00:00 快照为 730 个账本请求槽，包含关系 231 项中的 1 个在途预约；Unknown 4 包含该在途项。快照范围有明确说明，没有作为最终实发数、最终失败数或实际账单。 |
| 当前交付完成性 | `COMPLETION_AUDIT.md:9–18`、`:43–47`；`M5_CANDIDATE_DECISION.md:11–19` | 关系终态审计待完成、conv-44 抽取仍失败、六份完整 Build/严格导出、符合最终设置的评测及 Level E 仍缺，未错误标记总任务完成。 |
| 历史公共快照字段 | `level-c-results-v1/README.md:5` 与 `metrics-summary.json` | `semantic_source_support=pending_independent_review` 被明确解释为数值汇总时的历史快照；最新完成状态与结果另有 semantic 文件及当前交付文档，不据旧字段判为尚未审阅。 |

## 实质问题

无。本次没有提出需要修改交付结论、数值分母、实验身份或授权边界的 finding。

## 未验证边界

- 未读取底层数据库、Provider 原响应、原文、Gold 或私有审阅引文，因此不独立证明生成/评分/引文审阅的真实性或语义判断准确性。
- 未检查原关系进程的当前存活、进度或终态。本报告只核对公共快照与其声明的时点，不推断快照之后的变化。
- 历史 757 题与 Level B 的原始逐题工件未重新计算；本次核对的是指定文档是否正确区分其身份、指标和分母。
- 未重跑已通过的测试、语义审阅或真实生成，也未验证教师隐藏评分口径。
- 文档修订、关系终态或最终全 disabled 实验产生新结果后，需要以新工件重新审阅；本报告结论只适用于以下 SHA。

## 已审文件 SHA-256

以下为本次实际读取版本的文件身份。

| 文件 | SHA-256 |
| --- | --- |
| `docs/m5-development/HANDOFF.md` | `f5ce43c1c7b5f72205ebbcc75423dd0b2682ed1c81b43beaf972594d16863ad4` |
| `docs/m5-development/COST_ANALYSIS.md` | `c84902bafdf2b7ce90e2dd69524e6a7abd9c993287415af9fff8a51ef0c33e0c` |
| `docs/m5-development/COMPLETION_AUDIT.md` | `bab8809b3649ee9ec02b62f6c96db5d64ada2baa590ffc1a9b4f203bceb42bb0` |
| `docs/m5-development/EXPERIMENT_RESULTS.md` | `81b20dbe4997fc793cf4b9533cc725305cf6c4e97f63907555b58ce2fe6435ed` |
| `docs/m5-development/ERROR_ANALYSIS.md` | `7651296889a0670cc06b8208e820effbb2773ca36ddbd46b4b307414a7d852fd` |
| `docs/m5-development/M5_CANDIDATE_DECISION.md` | `f568a30da8b5e1b904ee898a7050f309e95459c0609b7efdd097c7ab970d08e3` |
| `docs/m5-development/LEVEL_C_RESULTS.md` | `7829e615a9f685ab4c9fbdb5576ddc5752b47239fc181c25c50c11b3ee3fe664` |
| `docs/m5-development/MODEL_REQUIREMENTS.md` | `d6a700b109bbf8f006a9f02526fded32b9630f7a920b721133e9f8901d3f2bd0` |
| `docs/m5-development/LEVEL_C_PREPARATION.md` | `78e0515c2a9968b42c9dc63beac7b46ec9d3ecc8ff58ad9f7684f7fae0fac952` |
| `experiments/m5-development/cost-ledger.json` | `98aa5da175ed4102014bc0b268fa6bc905efd1a1e858cee5d3b8a33945d4df99` |
| `experiments/m5-development/run-manifest.json` | `b0a55dfe9a2ca6090c3972a50f020435cd6b32b172074c9ac53aa1a7b1202e80` |
| `experiments/m5-development/level-c-outcome-v1.json` | `c7c057831e95ef21be6bea3a9e0cf5a790193b83fc13c683cfb9a9a664f388ba` |
| `experiments/m5-development/final-model-requirement-v1.json` | `683e52ff3382104292e830fe39a1ad7637b9f72b638d6d9cd83905e89bd11fee` |
| `experiments/m5-development/level-c-results-v1/README.md` | `a232ad8208b682f1f44ba3a374f9314661ed82870dcfd503489b75006d6b0947` |
| `experiments/m5-development/level-c-results-v1/metrics-summary.json` | `62ecb7708af88634043b8a5c94cc5aff4cf5dbb7d39edf40b422e6c4796442c6` |
| `experiments/m5-development/level-c-results-v1/semantic-review-summary.json` | `cb4855886bea032ee3e46aaac4b97e5a3d84359ddcb6d5149ebd067b93330476` |
| `experiments/m5-development/level-c-results-v1/semantic-paired-differences.json` | `9daa8e9ad6d4a086d6bf94fdce98416b39bc6a4c5e530979fa93e0c2cbac6df7` |
| `experiments/m5-development/level-c-results-v1/semantic-review-provenance.json` | `f626f894f7d787bf83dd2d7fd2da19cc7a06bcc6881bc1c6033188475e316dff` |

本报告只记录审阅结果，不改写已有实验、来源审阅或费用工件。
