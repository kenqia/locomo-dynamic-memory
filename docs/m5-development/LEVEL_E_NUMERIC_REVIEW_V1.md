# Level E 数值与后处理独立复核 v1

## 结论

2026-11-05，独立重算的 800 项 QA 分数和来源 Recall@5/10/20、全部分组及分母、配对 bootstrap、2,112 行 ledger 归属、费用、延迟和资源均与已发布工件一致，**数值不一致为 0**。本次没有发现遗留的已证实 P0–P2 数值问题。

新运行的 reporting audit 仅有一项文件系统快照差异：stage 总大小为 509,059,714 bytes，原报告为 508,347,589 bytes。差值 712,125 bytes 正好等于原 runtime 测量后写入的 `scores.json`；两个 Build 大小一致。这是测量时点差异，不是生成结果或评分变更，原 runtime 报告保持不变。

本报告只完成数值复核及后处理脚本静态复核。来源审阅尚未最终冻结时，本复核者没有读取任何 partial 标签或盲审包，也没有执行归档或语义派生脚本。后续来源与实际归档复核应另建报告和 JSON，不改写本 v1。

## Provenance 与范围

复核者为 `/root/final_code_review_v6`。我曾实际编写 `src/locomo_memory/extraction_time_diagnostics.py` 及其测试；该模块属于本次冻结 producer。未编写或修改本次 query、score、生成配置或提示词，未参与候选选择。因此本报告属于独立数值复核，不能表述为对全部生成实现完全没有贡献。

本次在根代理确认单次完整生成冻结、终态审计通过并完成正式评分后开始。留出结果已经曝光；没有调整参数、修改 producer、重新生成或据此重新定义独立测试。

工作树为 `/home/kenqia/my_folder/locomo-worktrees/m5-final-conv44-relations-20261104`。生成冻结 SHA 为 `3cab5d1b486290184e67906d61427f18803b415d82fe18f5f5f7190ae89664a6`。

数值证据保存在 `experiments/m5-development/level-e-numeric-independent-v1.json`，SHA 为 `751549250b64477e6bcb2e653e9176cf18ec062f4bd1f0ab9b7b383b51e0c6a1`。其中保留原始比较发现的 1 项 storage 差异及其解释，`numerical_mismatch_count` 为 0，不隐去观察差异。

## 独立重算方法与结果

先通过 `level_e.frozen_items()` 完整冻结门禁，再从 reference SQL 仅投影指定 dataset、artifact、conversation、原始 QA ordinal 的 `answer`、`category`、`evidence`，每题读取一次，共 400 次精确投影。未选择完整 annotations 或 QA 对象，未备份 reference 数据库，未输出问题、预测、Gold 或来源原文。

重算使用单独审阅脚本实现 normalization、Porter F1、类别规则、来源映射、阶段 coverage、分组均值、ledger 聚合和 bootstrap，没有调用 `level_e.score()`，没有覆盖 `scores.json`。公开 `official-scores.json` 与 stage 中分数副本 SHA 一致。

### QA、失败和配对比较

| 范围 | 每臂分母 | Hybrid 完整分母 | Dynamic 完整分母 | Dynamic − Hybrid |
| --- | ---: | ---: | ---: | ---: |
| 类别 1–4 F1 | 301 | 0.402606 | 0.409151 | +0.006545 |
| 类别 5 字面拒答 | 99 | 0.858586 | 0.808081 | −0.050505 |
| 混合规则均值 | 400 | 0.515461 | 0.507886 | −0.007575 |

全部 400 题的 QA 均适用。Hybrid 成功 394、失败 6；Dynamic 成功 389、失败 11；Unknown item 为 0。17 个失败项均按适用规则记零，没有从完整分母删除。逐项 QA、完整及成功子集均值、对话和类别分组均匹配。

重新执行固定 seed 51104 的 2,000 次按题配对 bootstrap，逐题差、全部、类别 1–4/5、每段对话及每个类别的差值、提升/退化/不变计数和区间均匹配。类别 1–4 差的 95% 区间为 [−0.020133,+0.034035]，未证明稳定质量改善。bootstrap 仅描述选定两段对话内的题目不确定性，不能作对话级泛化；探索性类别比较没有多重比较校正。

### 来源 Recall

从冻结 trace 独立提取 initial、expanded、effective 和 answer-delivered 的 Memory 排序，以前 K 个 Memory 的唯一 Source Turn 集合计算标注来源覆盖。全部 800 项、四个阶段、K=5/10/20 均与逐项 scores 一致，各对话和类别的完整及成功子集聚合也一致。

每臂有 399 个可评分题和 1 个来源映射不可靠的题；后者保留 `null`，未补零。失败且可评分的项记零。Hybrid 的 effective 阶段为不适用。该指标不是原子事实召回、有效选择准确率或答案来源支持；成功子集还受到运行结果选择。

### Ledger、费用与 Unknown

独立按冻结 producer 的串行 item/operation 顺序遍历全部 completed adapter records，与 ledger rowid 顺序逐行核对 usage 和响应状态；2,112 次全部对应，无未终态 reservation。归属仍依赖固定串行约定，ledger 没有 item 外键，不能将它描述为请求 ID 绑定。

| 数值 | 独立结果 |
| --- | ---: |
| 物理请求 | 2,112 |
| Hybrid / Dynamic 请求 | 851 / 1,261 |
| 保守预约 USD | 105.4516575 |
| 已报告字段峰价金额 USD | 7.7506077 |
| usage 未知请求 | 18 |
| 未知 usage 的完整预约 USD | 0.9522705 |
| 已报输入 / 输出 tokens | 22,771,255 / 766,026 |
| partial usage 请求 | 0 |

所有分臂、对话、operation、retry、failed-attempt、failed-item、unknown-item 子集费用均匹配。重试和失败费用是重叠子集，不能再加到全部请求费用上。另以安全字段核对，17 个失败项为 8 个 `invalid_output` 和 9 个 `model_http_error`；18 个缺 usage 调用均为 HTTP 402、`insufficient_balance`，未读取错误响应正文或 headers。

七个共享 Build 阶段的公共证据 SHA、阶段金额、请求数及 Unknown 数逐项核对一致：920 次请求、预约 USD45.0439116、已报告峰价金额 USD6.6141915，历史 7 Unknown 均保留。独立部署按每臂承担完整 Build 后除以 400，联合实验计 Build 一次，均与派生工件一致。十阶段累计为 3,975 请求、预约 USD197.6108655、已报告峰价金额 USD18.1208100，25 个未知 usage 请求预约 USD1.3023021；没有再次叠加已含于历史九阶段的 Build。

已报告字段包含适用的 partial 字段，缺失字段保持未知。预约、已报告字段峰价金额和实际账户账单不是同一口径；本次没有读取实际账单，也未估算本地 embedding 的硬件货币成本。

### 延迟、资源与存储

按每臂及对话独立重算 item、stage 和 adapter-attempt 的 observed/missing、合计、p50/p95，以及全部已报 tokens 除以成功项的比值，均匹配。该 token 比值包含失败成本，不是事实收益/token。

fresh audit 使用原固定 `execution-process-resource.json`，SHA 为 `568dd4e09074deda67c0b41ef8a1812a5f93f9a36c3948a94119d30a8045f034`。wall 为 4,530.687530 秒，children user/system CPU 为 311.002229/29.620455 秒，peak RSS 为 830,608 KiB，均与原报告一致。它们是 whole-launcher 累计 child CPU 和生命周期峰值，不是瞬时采样或分臂资源；GPU 未测。

storage 是特定时点的文件大小，不是运行峰值或增长量；本次发现的 `scores.json` 落盘时点差异已在结论及 JSON 中保留。

## 后处理与归档脚本静态复核

本次曾向根代理报告归档脚本的两项门禁缺口，随后核对修复：

1. 不再仅相信公共 summary 的 `completed/reviewed` 数；现重新 `validate_review(..., complete=True)`，并要求结果与公共 summary 对象全等。
2. 不再动态纳入 public 目录下任意 JSON；现枚举四个结果文件，历史 review 版本也仅枚举 reviewer-a/b/c 的 `initial-v1` 文件。

当前归档脚本只对 `conv-43.sqlite3`、`conv-44.sqlite3` 和 `physical-requests.sqlite3` 做 SQLite backup，包含 committed WAL 数据，检查副本逻辑 hash，并在前后守护原库 main/WAL 身份与逻辑 hash。reference Gold 数据库不在备份列表中。其他成员使用明确文件清单、非 symlink 检查、SHA、tar 逐成员读回及原文件末次守护；raw stdout/stderr、凭据、WAL/SHM 和 runtime locks 不在成员中。`var` 与 `var/m5-development` 当前均为 0700。此处为静态结论，尚未实际运行 backup 或验证最终 tar。

语义派生脚本先要求完整 review 验证，再仅对两臂均运行成功且双方标签适用、确定的 pair 计算差值；输出 planned/determinate/excluded 分母。人物、事件、时间及列表错误的正差表示错误更多，支持和正确拒答的正差表示相应正向判断更多。静态未发现实质分母或符号错误；这类条件率不能解释为全部 planned 项的事实正确率。未读取实际 partial 标签，也未实际运行该脚本。

| 静态审阅脚本 | SHA-256 |
| --- | --- |
| `/tmp/m5_level_e_archive_terminal.py` | `f0a3a0069d33dc1454078cf56197962936a75b24c3de9f9f3f19774ba3f87520` |
| `/tmp/m5_level_e_semantic_derive.py` | `33be2ccf1cdb1b8e97e8344297ca5bf2fa1a83969ab9d1837721dbd0f6d25082` |

## 执行与原件守护

验证命令在上述工作树执行，使用现有依赖环境，清除进程内 live 凭据变量并启用外部 socket/DNS offline guard：

```sh
env -u DEEPSEEK_API_KEY -u OPENAI_API_KEY -u CODEX_ACCESS_TOKEN \
  -u LOCOMO_LIVE_MODEL -u LOCOMO_LOCAL_EMBEDDING -u LOCOMO_CONFIG \
  HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false \
  PYTHONPATH="$PWD/tools/integration/offline_guard:$PWD/src:$PWD" \
  /home/kenqia/my_folder/locomo-dynamic-memory/.venv/bin/python \
  /tmp/m5_level_e_numeric_independent_review.py
```

随后使用同一 offline 环境运行 `/tmp/m5_level_e_numeric_review_finalize.py`，验证 storage 差值和七阶段公共证据，给本次新建的 reviewer JSON 补充解释。它没有修改任何历史工件。

主审阅脚本 SHA 为 `4608bb42c46b035c953fc1d67aaacd8a90c9dbc5738aead01e84bd207b12ae81`；解释脚本 SHA 为 `1fdc35481151f96f4a1a914ae77fd184bbdb86f76a34731373a4a3e56baca113`。fresh audit 位于 `/tmp/m5-level-e-runtime-numeric-independent-v1.json`，身份记录在 reviewer JSON。

前后守护覆盖 800 个 item、plan、lock、inputs、authorization、执行 marker、freeze、scores、固定资源 sidecar、公共数值工件，以及两份执行 Build、ledger 和 reference 的 main/WAL 身份，全部保持一致。未覆盖 scores，未修改 82 个 producer，未读取凭据或 raw stdout/stderr，未启动 live，未执行 add 或 commit。免费数值复核不代表来源支持审阅完成，后续实际来源与归档验收另行记录。
