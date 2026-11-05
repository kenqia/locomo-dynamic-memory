# Level C input v2 终态数值与归档复核

复核日期：2026-11-04。结论：200 项冻结结果的身份、完整分母、公共数值、配对统计、费用和原始 manifest 核验通过；新鲜终态审计与原审计完整对象相等。两个公共交付脚本经静态复核，归档文件权限问题已修复，当前未发现需要阻止这两个脚本按既定流程执行的问题。

本报告不等待来源语义盲审完成，也不构成语义审阅通过或最终归档完成的声明。归档和语义补充脚本未由本复核者执行，完整最终交付清单仍需在执行方生成后核对。

## 复核范围与身份

工作树：`/home/kenqia/my_folder/locomo-worktrees/m5-final-input-v2-20261104`。

输入 stage：`var/m5-development/level-c-input-v2-preparation-v1`。公共结果目录：`experiments/m5-development/level-c-input-v2-results-v1`。

本复核者先前参与过 input v2 执行和 audit 实现，不能作为这些 producer 的非作者代码审阅者。本报告提供独立实现的数值重算、终态审计复跑和新公共脚本静态检查；非作者代码复核另见 `LEVEL_C_INPUT_V2_REVIEW_V1.md`。

本次只读取获准的新 stage 冻结项、分数、审计、公共产物和 stage 自身 SQLite 数据库。没有打开 source 原始参考数据库，没有重新读取 Gold、holdout、凭据或原始进程日志，没有重新生成、调用 Provider 或访问网络。单题 F1 沿用已冻结的 `scores.json`，本次没有从 Gold 重算单题评分。

## 独立数值核验

独立脚本调用 `frozen_items` 验证冻结项，随后自行实现分组、配对 bootstrap、费用和账本计算；没有调用 `level_c_results.run/groups/comparisons` 或 `offline.paired`。

通过的检查如下：

- 200 个冻结文件 SHA、200 个唯一 `(question_id, arm)`、100 个配对问题、四个开发对话；每臂固定 80 普通题、20 诊断题；分数与冻结项身份及 outcome 一致，失败项为 0。
- 公共逐题记录与 `scores.json` 的 `items` 完全相同，公共失败清单与冻结项一致。
- 全部分层、对话、类别、category 1–4 与 category 5 分组的 planned、scorable、succeeded、failed、完整分母均值、成功子集均值和评分规则计数一致。
- 配对差值、改善/退步/不变计数及共同成功子集一致；独立使用 seed 51104、2000 次有放回抽样和 0.025/0.975 分位数重算 bootstrap，浮点绝对容差为 `1e-12`。
- 522 条已完成 trace call 与物理账本数量一致；按臂、重试、失败项、operation 的用量与费用一致，item elapsed 的总量、p50、p95 一致。
- `source-manifest.json` 的 10 个 stage 文件 SHA 和初始 `sha256-manifest.json` 的 4 个公共文件 SHA 均一致。后续新增交付文件不属于这份初始 4 项 manifest 的覆盖范围。

主要结果使用失败计零的完整分母：

| 分层 | Hybrid 成功数 | Dynamic 成功数 | Hybrid F1 | Dynamic F1 | D−H | 配对 bootstrap 95% 区间 |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| 普通题 | 79/80 | 80/80 | 0.4011720415458204 | 0.44470197277578744 | 0.04352993122996703 | [−0.008094517447061621, 0.09531801929467598] |
| 诊断题 | 20/20 | 20/20 | 0.4343142968142968 | 0.47347222222222224 | 0.03915792540792541 | [−0.05601442307692308, 0.13478359487734481] |

普通题改善 27、退步 14、不变 39；诊断题改善 5、退步 3、不变 12。普通题共同成功 79 对的均值差为 `0.03142271516958688`，区间为 `[−0.016986469189270423, 0.07592982737331713]`。共同成功子集由运行结果筛选，不能作为因果质量估计。

两个完整分母区间均包含 0。结果来自四个已暴露的开发对话，bootstrap 是探索性题目配对抽样；当前结果不能证明整体质量提升，不能替代留出评估或教师真值，也不是新的 757 题评分。

## 账本、费用和模型身份

本次独立以 `mode=ro` 读取 stage 的 `physical-requests.sqlite3`，使用 `PRAGMA query_only=ON` 和读事务重算：

| 项目 | 核验结果 |
| --- | --- |
| 物理请求 | 522，全部 `response_received` |
| 未知、部分用量及在途请求 | 均为 0 |
| 请求与返回 model | 全部为 `deepseek-flash` |
| thinking | 全部 `{"type":"disabled"}`，`reasoning_effort` 全部为 null |
| 输入 / 输出 / 合计 token | 7,814,253 / 201,595 / 8,015,848 |
| 预约总额 | USD 27.8063415 |
| reported usage 峰价 cache-miss 上界 | USD 2.5861899 |
| Hybrid / Dynamic 费用上界 | USD 0.2330898 / USD 2.3531001 |
| 剩余请求 / 预约容量 | 978 / USD 319.1760585 |

费用公式为 `prompt_tokens × 0.30 / 1e6 + completion_tokens × 1.20 / 1e6`，使用 `Decimal` 运算。该金额是 reported usage 的价格上界；没有读取实际账户账单。剩余容量不自动授权补跑。返回 alias 相同也不代表模型已有不可变版本 pin。

原审计记录 wall `1226.5643489190006` 秒、CPU `84.96452583599999` 秒、峰值 RSS `655556 KiB`、GPU false；新鲜完整对象比较覆盖这些字段。本次没有重新采集生成进程资源数据。

## 新鲜终态审计

复跑 `tools.m5.level_c_audit.audit(stage)` 前，对其 `readonly` 入口添加白名单包装，只有 stage 的 `memory.sqlite3` 和 `physical-requests.sqlite3` 可打开；其他路径直接拒绝。运行结果确实只打开这两个文件。

新鲜对象与 `terminal-audit-v1.json` 进行完整 Python 对象相等比较，结果为 true；独立 JSON 序列化后的 SHA 也与原文件一致：

`df4a63378a7cd0fc516bb1a9a5b90961330a4d24f2a655be1182089ded781f1e`

独立审计文件：`var/m5-development/level-c-input-v2-independent-terminal-audit-v1.json`。

## 公共交付脚本静态复核

### `archive-private.py`

复核版本 SHA：`74a624d19f917c949ce2d794e076aca20acb8f5c39096c3212f3c91f43e87f75`。

已核对固定 stage/review 白名单、200 项 freeze hash 校验、普通源文件排除 symlink、SQLite 只读 backup、归档逐成员回读长度/SHA、内部 manifest 和源文件前后完整性检查。SQLite backup 包含已提交 WAL；备份逻辑 SHA 与源逻辑 SHA 一致性检查先于归档，源数据库前后逻辑 SHA 也必须一致。脚本不纳入原始进程日志、凭据、锁或 WAL/SHM sidecar。

初版通过 `DEST.open('xb')` 在权限 0755 的父目录创建 archive，普通 umask 可能产生 0644，从而扩大原始问答和 DB 的本机可读范围。执行方已改为 `os.open(DEST, O_CREAT | O_EXCL | O_WRONLY, 0o600)` 后 `fdopen`，在创建时就限制权限；静态复查确认该修复，并记录 `archive_mode_octal`。随后还通过 tar filter 强制每个数据成员和内部 manifest 为 0600，回读时断言全部成员为普通文件且权限为 0600，避免普通解包时恢复较宽权限。修复前脚本 SHA 为 `ca981057887113d167b272810dce6db60f0e298542617aa81290aba473949584`。

归档脚本检查 semantic summary 完成状态和 freeze 绑定，但不自行重新验证语义标签。执行方应按既定流程先验证来源 review，再执行归档。归档失败可能留下未完成 tar，脚本拒绝覆盖既有 tar/report；失败后的恢复需要单独检查，不能将失败视为完整归档。

### `summarize-review.py`

复核版本 SHA：`ed92dcf9f8d16608d733d2771cae0a061d1a87c748fbae27ea8a4f2d53c878d6`。

脚本先调用现有 `score` 验证完整 200 条显式 reviewer 标签，再要求验证结果与公共 semantic summary 完整对象相等；脚本不生成标签。已核对 `private-mapping.json` 顶层 `units`、100 题 H/D 配对、明确支持/不支持的共同成功子集，以及 provenance 的引用文件 SHA。

支持差值只对双方均成功且两侧标签都确定的题目计算，其分母可能小于 80/20，已通过 `denominator` 和 limitation 公开。provenance 明确一次 AI 判断、非双审、非教师真值及策略可能从文风泄漏的限制。未发现静态阻断问题；尚未由本复核者执行，也没有检查最终语义数值。

两个脚本均已使用 `ast.parse` 解析语法。按当前任务范围，没有为两个固定一次性交付脚本新建测试框架。

### README 与复现说明

已静态核对同目录 `README.md` 和 `reproducibility-commands.md`。文档区分初始四项 SHA 清单与后续终态清单，保留初始 pending 语义状态，说明私有数据不会随 clone 提供、价格快照不互相覆盖，以及 AI 审阅和 SHA 的证据边界。复现命令的模块、参数和输出路径要求与现有 CLI 一致；审计和数值后处理路径不重新打开 Gold。一次性补充及归档命令明确拒绝覆盖，需要完整来源审阅后执行。本次没有执行这些发布命令。

文档检查版本 SHA：README 为 `45ab5a8ec99035926062ee708dc77ef509d38b5ff28bd0f770344235b412a294`；复现说明为 `d7711df1eec4e4b7c2f37ba5dd8d5e5dbd064cfe5b68bb3ead4adc13dfde07cf`。

## 实际验证入口与证据

数值重算实际命令如下，在上述工作树执行；脚本使用 exclusive-create 写入独立证据，不覆盖原件：

```sh
env -u DEEPSEEK_API_KEY -u OPENAI_API_KEY -u CODEX_ACCESS_TOKEN \
  HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
  PYTHONPATH=tools/integration/offline_guard:src:. \
  /home/kenqia/my_folder/locomo-dynamic-memory/.venv/bin/python \
  var/m5-development/level-c-input-v2-independent-numeric-review-v1.py
```

审计复跑使用相同环境和 Python 解释器，通过 heredoc 调用加数据库白名单的 `audit.audit(stage)`，将结果以 exclusive-create 写入独立审计路径，并比较完整对象。此过程未调用评分或生成入口。

| 独立证据 | SHA-256 |
| --- | --- |
| 数值复核脚本 `var/m5-development/level-c-input-v2-independent-numeric-review-v1.py` | `c392528a6cafe9d1a100cc03a9967431cf23b183da89d8f37672464e36237b91` |
| 数值复核 JSON `var/m5-development/level-c-input-v2-independent-numeric-review-v1.json` | `c0e8f26acde898753a8c6fc50f3033a097e954baf6acf43d07942c0bb14d9a3d` |
| 新鲜完整审计 JSON | `df4a63378a7cd0fc516bb1a9a5b90961330a4d24f2a655be1182089ded781f1e` |
| generation freeze | `1bfc058224d9ba1c8ba941c39f7ef0ebbc27db9736b4935d742a0e4541147de3` |
| scores | `e9f43c8ff18482eb6c4d5d470fb284f1538e11d3cdee181a8c9f4ca0d2f82f55` |

数值复核最终运行成功。首次运行在调用元数据检查处因复核脚本把 `thinking` 字典误当作字符串计数而停止；更正为字典与 null effort 断言后重新完整运行通过，没有改变冻结项或公共数值。

## 追加：后处理实际结束后的终态交付实检

2026-11-04，执行方完成两份来源审阅合并、`validate`、`score`、补充统计和私有归档后，本复核者再次检查实际产物。本节记录当前终态；上文“未执行”“待核查”均保留为第一次复核时点的事实，不表示当前阶段仍 pending。最终语义工件和归档均已存在，下面的独立检查全部通过。input v2 本阶段已结束，总 M5 任务仍未完成。

本次追加检查没有执行生成、评分 Gold、归档或 Provider 操作。仅检查匿名标签、mapping、review 元数据及字节哈希、公共产物和已有 tar 的字节完整性；`packets.json` 只做字节 SHA，不解析或阅读 conversation。没有重判原文语义、检查实际账单或打开 source 数据库、留出、日志和凭据。

### 200 项来源审阅与配对统计

独立核对两份分审文件各 100 个单位，身份互不重叠，按 conv-26/30 与 conv-41/42 归属正确；合并后 200 个单位的受控标签和 reviewer 元数据与两份输入一致，且与公开匿名标签逐项一致。每项声明独立于生成、检查全部事实断言和完整 conversation；两名 reviewer 为 `final_code_review_v6`、`level_c_source_a`。本次核对这些声明及文件身份，不把声明当作独立人类证明。

604 条 `source_quotes` 的记录数与 provenance 一致；7 个 review 引用文件 SHA 全部一致，新 manifest 与 generation freeze、plan、packets、mapping 的绑定一致。没有阅读引文原文，所以本次不独立复验逐字引文匹配；执行方此前的 `validate`/`score` 负责该验证。provenance 的 2,080 条 Source Turn 记录保留为执行方与 reviewer 的来源范围声明，本次未重读或重新计数原文。

独立从匿名标签重算 overall、by_arm、by_stratum_arm、by_conversation、by_conversation_stratum_arm 的全部计数、分母、比率、不确定与不适用项，结果与公开 `semantic-review-summary.json` 全部相等。关键计数如下，失败 1 项单列且不计入语义正负分母：

| 指标 | Hybrid | Dynamic | 总体 |
| --- | --- | --- | --- |
| 来源支持 | 68/79 | 75/84 | 143/163；35 不确定、1 N/A |
| 引用支持 | 72/77 | 76/80 | 148/157；24 不确定、18 N/A |
| 合理整体拒答 | 6/15 | 6/13 | 12/28；8 不确定 |
| 错误人物 | 0/88 | 0/91 | 0/179；20 不确定或 N/A |
| 错误事件 | 0/82 | 0/84 | 0/166；33 不确定或 N/A |
| 错误时间 | 0/56 | 0/57 | 0/113；86 不确定或 N/A |
| 列表遗漏 | 10/49 | 9/51 | 19/100；99 不确定或 N/A |

独立通过 mapping 重建 100 个 H/D 同题配对，逐对记录与公共 `semantic-paired-differences.json` 相等；使用 seed 51104、2000 次抽样重算配对 bootstrap，完整 summary 相等：

| 分层与指标 | 可判断共同成功对数 | 改善 / 退化 / 不变 | D−H | 95% 区间 |
| --- | ---: | --- | ---: | --- |
| 普通题来源支持 | 60 | 2 / 1 / 57 | 0.016666666666666666 | [−0.03333333333333333, 0.06666666666666667] |
| 诊断题来源支持 | 14 | 1 / 1 / 12 | 0 | [−0.21428571428571427, 0.21428571428571427] |
| 普通题引用支持 | 61 | 0 / 0 / 61 | 0 | [0, 0] |
| 诊断题引用支持 | 14 | 0 / 0 / 14 | 0 | [0, 0] |

这些分母经过共同运行成功和判断确定筛选，不能直接代表全部 100 题的因果质量变化。每项只有一名 AI reviewer，没有双审一致性或教师真值。不确定项没有补为“无错误”；16 次可判断错误拒答、19 次列表遗漏仍是明确质量缺口。当前结果不能证明稳定事实收益或成本收益，也不授权修改默认策略、晋级或续费。

### 已有归档逐成员回读

对既有 `var/m5-development/level-c-input-v2-raw-terminal-v1.tar.gz` 实际回读，未解包到文件系统、未创建新归档：

- SHA 为 `a04434350708642510f2f3e57d5e264c9dbb9fbd207ddd9a645a0093b2e62e6c`，大小为 `19,959,603` bytes，实际 archive 权限为 `0600`。
- 恰有 229 个唯一名称成员，没有重复；成员集合与公开归档报告一致，全部为普通文件且 mode 为 `0600`。
- 流式逐字节重算 228 个数据成员的长度和 SHA，均与报告相等；内部 `archive-manifest.json` 的对象与报告成员清单、数据库逻辑 SHA 完全相等。
- 226 个非数据库成员与当前 stage/review 原件的 SHA 和大小全部一致。两个数据库成员是 SQLite backup；本次核验其归档字节 SHA，不把备份文件字节 SHA 与活库文件混比。
- 数据库逻辑一致性沿用归档过程的前后逻辑 SHA 校验与本报告此前实际完成的完整 audit 对象比较，不再次建立归档或重新打开原参考数据库。

### 冻结实现、合并费用与交接文档

当前 80 个 producer 文件 SHA 与 stage plan 的 `implementation_sha256`、最初 `level-c-input-v2-run-manifest-v1.json` 的 `producer_sha256` 完全一致。`level_c.py` 与 `level_c_audit.py` 也与最初 `level-c-input-v2-sha256-manifest-v1.json` 一致，初始四项公共 SHA 清单仍通过。最初 run-manifest 的 running/gold 状态保留为历史观察，没有据此误判当前终态。

独立读取原树公开终态费用摘要，先确认其 SHA 为 `667de1e2d51c2b8ef6a9e6b7a08ec7c3f850c65bb123beedaf0b61cb7637b91c`，再与本阶段已核验账本相加：

| 累计项 | 原三个阶段 | 本阶段 | 四阶段合计 |
| --- | ---: | ---: | ---: |
| 物理请求 | 907 | 522 | 1,429 |
| 预约 USD | 42.9743136 | 27.8063415 | 70.7806551 |
| 已知 reported usage 峰价上界 USD | 5.3163252 | 2.5861899 | 7.9025151 |

合计与 `cost-ledger-including-input-v2-terminal-v1.json` 完全一致。历史 7 次 transport Unknown 和 USD0.3500316 全额预约仍保留，没有将未知用量按零处理；累计不包括历史 757 题的全部费用，实际账单未读取，各阶段余额不能转移或自动授权额外行为。

已核对 `docs/m5-development/LEVEL_C_INPUT_V2_RESULTS.md`、`M5_INPUT_V2_HANDOFF.md` 的本轮数值、语义分母、费用、归档身份和限制。两份文档保留四个已暴露开发对话、F1 区间跨零、AI 单审、非教师真值、可变模型 alias、Bonus 关闭、留出未评测、总任务未完成及无自动晋级的边界。历史构建/关系阶段的状态引用既有交接记录，本次没有重新进入其私有数据库验证。

复核时结果页将本数值复核者称为“非作者”，随后又注明曾参与生成实现，措辞有歧义；执行方已改成“独立数值复核者”，本复核者已实际确认该更正。本报告始终保留作者身份限制，两名来源 reviewer 与该限制分别陈述。当前实际交付未发现阻断问题。

### 本次追加检查的实际入口

```sh
env -u DEEPSEEK_API_KEY -u OPENAI_API_KEY -u CODEX_ACCESS_TOKEN \
  HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
  PYTHONPATH=tools/integration/offline_guard:src:. \
  /home/kenqia/my_folder/locomo-dynamic-memory/.venv/bin/python \
  var/m5-development/level-c-input-v2-independent-delivery-review-v1.py
```

实际退出码为 0。独立脚本 SHA 为 `9c1a7035dbfd3c05af018ae609cdbf7ffbca4017b8411cc991a95be31901b1b9`。独立证据为 `var/m5-development/level-c-input-v2-independent-delivery-review-v1.json`，SHA 为 `b01555d5d2db844b26cca250c58db61aec608b3a663fb88677441b1c2c2fd995`。该证据记录公开文档检查时的 SHA；上述文案更正随后改变了结果页 SHA，由执行方在本报告完成后建立新的最终交付清单。本次未等待或验证尚待生成的终态 manifest，没有创建 commit。
