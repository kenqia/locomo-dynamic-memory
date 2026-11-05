# Level E 来源与实际归档独立复核 v1

## 结论

2026-11-05，已完成的 **800 项来源审阅、1,796 条逐字引文、21 项标签修订及 provenance、条件配对统计与 bootstrap 均通过独立核对**。实际 tar 的 **863 个成员**逐一读回并核对 SHA、大小和白名单；三份执行数据库快照与原库的全部 schema、rowid 和行内容相等，`PRAGMA integrity_check` 均为 `ok`。未发现遗留的已证实 P0–P2 后处理问题。

这验证了身份、证据契约、汇总算术和归档一致性，不是对 800 项来源语义判断重新做一轮双审。引用逐字存在不自动证明推论正确；正确拒答的完整对话检查仍包含原审阅者声明。本报告没有计算人工、教师真值或双审一致性。

本次唯一解释性问题是错误指标中通用字段 `improved/regressed` 的方向：v1 实际分别计正差/负差，在人物、事件、时间和列表错误中应读作**增加错误/减少错误**。同工件 `positive_difference_means` 已指明方向，最终正文也按正确方向展示。数值和已归档 v1 未覆盖。

## 范围与身份

- 工作树：`/home/kenqia/my_folder/locomo-worktrees/m5-final-conv44-relations-20261104`。
- 复核者：`/root/final_code_review_v6`。
- generation freeze SHA：`3cab5d1b486290184e67906d61427f18803b415d82fe18f5f5f7190ae89664a6`。
- review manifest SHA：`b030f1cd63aeba84427827c9a750583fa346d8776821e8685401e9941ecde9a5`。
- completed reviews SHA：`5900049cd6d97f20604d09fdddc48b7288d3aedd68d382a9b9069572e360bd85`。
- 本次新证据：`experiments/m5-development/level-e-postprocessing-independent-v1.json`，SHA `b6bc113049924ab66293dd8f42551e002d85cce084c3744c967a60c6eea6fc6a`。

我此前实际实现了冻结 producer 中的 `extraction_time_diagnostics.py` 及其测试，未实现本次 query、score、生成配置或提示词，未参与候选选择。本次是独立后处理复核，不能描述为对全部冻结实现完全没有贡献。留出结果已经曝光，没有据此调整算法或重新生成。本次未重复 800 项 Gold QA 重算，也未打开 Gold SQL。

## 来源身份、引文和 provenance

首先重新运行完整 `validate_review(..., complete=True)`，结果与公共 summary 对象全等。随后使用独立代码逐项检查字段、状态、同对话逐字引文和目标证据，不仅依赖 helper 返回值。

| 分区 | 单位 | 引文 | 标签修订单位 |
| --- | ---: | ---: | ---: |
| A | 242 | 529 | 2 |
| B | 242 | 505 | 9 |
| C | 316 | 762 | 10 |
| 合计 | 800 | 1,796 | 21 |

三个分区互不重叠且完整覆盖全部匿名单位，最终分区文件逐行等于合并结果。initial/final SHA、manifest 绑定、逐单位逐标签的 before/after 差异，全部重现公共 provenance。B 的边界复核记录也绑定相同 initial/final 文件，声明未读 Gold 和其他审阅者标签。

全部 1,796 条引文均为对应 conversation 的 Source text 连续子串。对 `citation_support=supported` 的单位，支持引文的 source ID 集合精确等于全部实际 cited source ID 集合；共核对 646 个按单位计数的实际引用来源，未以一个正确引用掩盖其他未核引用。unsupported、错误标记和 false abstention 均具备约定用途的来源证据。195 个正确拒答均有 `full_conversation_checked=true` 和非空 evidence gap；17 个执行失败完整保留为失败，语义字段 N/A、错误字段 `null`。

公开去原文标签逐项精确等于约定投影，仅保留身份、臂、execution outcome、审阅者元数据和标签；不输出 question、prediction、answer、source text、quotes、rationale 或 evidence gap 字段。provenance 明确根代理的边界抽查发生在其已拥有 scored outputs 后，按标签选择，并保留初终版本。是否提供 Gold、是否实际通读完整对话等属于审阅者及根代理的过程声明，本次不能从 JSON 独立证明这些历史行为。

## 汇总与条件配对重算

独立从最终标签重算 overall、各臂及各对话的 planned/reviewed、execution outcome、answer kind、positive/negative、未确定/N/A 和分母，全部匹配。语义汇总仅纳入适用且已判断的单位；17 个失败保留在 800 planned 中，不计为来源支持或无错误。

| 指标 | Hybrid | Dynamic | 条件配对确定数 / 400 | D−H |
| --- | ---: | ---: | ---: | ---: |
| 来源支持 | 250/343 | 233/307 | 297 | +0.033670 |
| 引用支持 | 195/321 | 197/310 | 297 | +0.026936 |
| 正确拒答 | 100/143 | 95/134 | 124 | −0.016129 |
| 人物错误 | 3/351 | 2/342 | 320 | −0.003125 |
| 事件错误 | 10/351 | 13/340 | 319 | +0.009404 |
| 时间错误 | 17/344 | 11/334 | 308 | −0.012987 |
| 列表遗漏 | 25/349 | 15/339 | 317 | −0.018927 |

逐对重建全部 400 个 pair 的 execution outcome 和差值，只在两臂均运行成功、标签明确且适用时纳入。分别排除 103/103/276/80/81/92/83 对，与工件一致。独立用 seed 51104、2,000 次按题重采样，重算 overall 及每段对话的均值、区间、正差/负差/不变计数，全部匹配。

来源支持区间 [−0.010101,+0.077525]、引用支持区间 [−0.020202,+0.074074] 均跨零。拒答与列表差区间触零；不能据此宣称总体稳定改善。这些是双方成功且标签可判定的条件子集，不是全部 400 题事实正确率，也不是随机缺失样本。仅两段选定对话的题目 bootstrap 不支持对话级泛化，多指标未作多重比较校正。不同分区对 N/A 的使用存在差异，不能忽略该审阅者因素。

错误字段的计数方向已核对：人物 2 对增加、3 对减少；事件 9/6；时间 4/8；列表遗漏 2/8。`LEVEL_E_RESULTS_V1.md` 的方向解释和表格正确，未把错误增加当成质量改善。

## 实际 tar 与数据库快照

| 项目 | 独立结果 |
| --- | --- |
| tar | `var/m5-development/level-e-raw-terminal-v1.tar.gz` |
| 大小 | 55,172,721 bytes |
| 成员 | 863，包括 archive manifest |
| tar SHA | `72d6bd2dd5261ff863ec861eab780a5b580e4dec6889f5948ac73f45f44a31f5` |
| manifest SHA | `c86218adb841a95e73f8c40be42fd01602deaeb75f4dca8412f37001fc204ad9` |
| 成员权限 / backup 目录 | 0600 / 0700 |

独立重建最终明确白名单，要求 tar 名称集合精确相等、无重复、绝对路径、`..`、symlink 或其他非 regular member。每个成员的大小和 SHA 同时匹配 tar manifest、实际 tar 内容与当前原文件；末次再次守护所有原文件及 tar SHA。新增 provenance、B 边界记录、numeric v1 JSON 和两份 numeric 审阅脚本均在既定清单中。未动态纳入任意新 JSON。

实际 SQLite 成员严格只有 `conv-43.sqlite3`、`conv-44.sqlite3` 和 `physical-requests.sqlite3` 的 backup。没有 reference Gold 数据库，亦无 raw stdout/stderr、凭据、原 WAL/SHM 或 runtime locks。archive helper 在执行前要求当前完整 review 验证与公共 summary 全等；此前“仅信任 completed 数”和“动态收集 public JSON”的门禁缺口已修复。

| 快照 | 表数 | 全表行数合计 | 独立检查 |
| --- | ---: | ---: | --- |
| conv-43 | 23 | 13,466 | schema、rowid、全部行相等；integrity `ok` |
| conv-44 | 23 | 13,385 | schema、rowid、全部行相等；integrity `ok` |
| physical requests | 2 | 2,113 | schema、rowid、全部行相等；integrity `ok` |

独立逐批比较所有 schema 对象及所有表的 `rowid,*`，未将原库或 snapshot 数据输出。三份原执行库的 main/WAL 身份与 archive manifest 记录相同，快照 SHA 与实际 tar 内容绑定，读后均未变化。backup 逻辑行一致不要求原数据库物理 bytes 相同；归档仅供证据回放，不授权恢复或重启一次性生成。

## 最终交付索引核查

核对 `FINAL_DELIVERY_EVIDENCE_INDEX_V1.md` 的当前 Level E 数值、来源分母、配对错误方向、provenance、未测量项、归档身份及采用边界，未发现与本次证据冲突。被核对版本 SHA 为 `a904801ad2aef12fa198ff055cf6c3a31205b3c0da305b71cc41aacf64db902c`。结果正文 SHA 为 `62b13b4f23b0e9446d09236ae985076406e4f2d23112b7e6b5b31e58b08775bb`；两份正文明确根代理已知官方分数，按标签抽查不是严格盲审，也不构成第四名独立语义审阅者，未向来源审阅者提供 Gold 或分数。

PropMem 的“没有 Adapter、真实 canary 或完整后端安装”与 `propmem-audit.json` 的明确字段一致，未把隔离 AST/合成检查写成真实部署。报告也区分独立 E、历史成绩、工程验证、未运行的 Level D/Bonus QA、未完成的 main/Release/生产整合与人工/教师验收。

四份最终 Git 清单当时尚未生成，本次没有宣称核验其内容、截点或 SHA。它们须在内容提交后的明确 clean HEAD 上另行核对，并保留基线、内容截点和 metadata 排除边界。

## 复核代码保留与验证命令

本次复核脚本已用独有文件名保存在 ignored 私有 `var/m5-development/level-e-execution-support-v1/`，权限均为 0600，路径和 SHA 绑定在新 reviewer JSON：

| 文件 | SHA-256 |
| --- | --- |
| `m5_level_e_postprocessing_source_independent_review_v1.py` | `149cc8a0e1fc9240eeaa805bfc9765eba778b053a66d04d0db6cf4ff254fa152` |
| `m5_level_e_postprocessing_archive_independent_review_v1.py` | `bb36ac70984014db9d1957f3d19d4dd49bae0e0f7c2ce17c41eb7b3a34776d5b` |
| `m5_level_e_postprocessing_finalize_independent_review_v1.py` | `fd14c1ae511241c7602fa602ae66ccdea48578dd7f3f6b399c8582379d088d4f` |

实际执行采用现有 Python 依赖和 offline guard，命令形式如下，分别以 `source`、`archive` 完成检查，再运行 finalize 保留代码和核 integrity：

```sh
env -u DEEPSEEK_API_KEY -u OPENAI_API_KEY -u CODEX_ACCESS_TOKEN \
  -u LOCOMO_LIVE_MODEL -u LOCOMO_LOCAL_EMBEDDING -u LOCOMO_CONFIG \
  HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false \
  PYTHONPATH="$PWD/tools/integration/offline_guard:$PWD/src:$PWD" \
  /home/kenqia/my_folder/locomo-dynamic-memory/.venv/bin/python \
  /tmp/m5_level_e_postprocessing_independent_review.py source
```

archive 使用 `/tmp/m5_level_e_postprocessing_archive_independent_review.py archive`，finalize 使用 `/tmp/m5_level_e_postprocessing_independent_finalize.py`，均采用同一 offline 环境。archive reader 改为按 tar 成员顺序核对，以避免 gzip 反复后退；原先只读过程主动停止，没有产生结果或改动原件。保留脚本与实际执行脚本内容 SHA 一致。复现须使用新的审阅输出路径，既有原件不覆盖。

三份新保留脚本不追加到已冻结 863-member tar；它们单独持久保留，tar v1 保持原 SHA。numeric v1 MD/JSON 仍分别为 `a38e59bba71e742c7f87b4ea3b01f5ca2765086cee9fa0081af80f5b26c578ac` 和 `751549250b64477e6bcb2e653e9176cf18ec062f4bd1f0ab9b7b383b51e0c6a1`。本次 Provider 为 0，未读取凭据或 raw logs，未写原 stage/DB，未改 producer、标签或生成，不执行 add 或 commit。
