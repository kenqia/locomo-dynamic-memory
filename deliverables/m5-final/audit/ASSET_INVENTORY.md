# M5 Final Delivery — Asset Inventory (Phase 0)

审计日期：2026-11-09（Asia/Shanghai），审计人：Claude（AI），待负责人确认。
基准：`main = 5519dd2`（2026-11-09 15:55 合并 PR #41 后）。审计开始时 main 为 `ba349cf`，审计期间前进；下文凡未注明者以 `5519dd2` 为准。
工作分支 / worktree：`delivery/m5-final-20261109` @ `/home/kenqia/my_folder/locomo-worktrees/delivery-m5-final-20261109`。主仓工作树 48 项未提交修改未被触碰。

处理建议代码：**KEEP**（原样纳入）、**REUSE**（作为素材改写）、**REDO**（必须重做）、**ARCHIVE**（只进过程材料并建索引）、**EXCLUDE**（不进公开包）。

## 1. Git 与版本状态

| 项 | 实测值 | 说明 |
|---|---|---|
| main / origin/main | `5519dd2` | = PR #41 合并 `1549712` + `f3f785b`（11-03 会议截图）。CI `tests` 在 5519dd2 上 in_progress；1549712 上的 CI 为 cancelled |
| PR #41 | MERGED 2026-11-09 07:55Z，merge `1549712`，by kenqia | Product Console 进入 main；Issue #23 #26–#29 已于 07:55Z 自动关闭 |
| PR #40 | MERGED 2026-11-05，`0ebb2b8` | Personal Core Release |
| PR #39 | OPEN，head `0401155`，base `codex/v2-6d-production-safe` | 已被 #41 选择性整合；本身未合并 |
| PR #38 | OPEN draft，head `3e0b217`，base `codex/v2-6d-research-safe`；kenqia CHANGES_REQUESTED（针对旧 `0f470a3`） | Temporal Event Sidecar；**未进 main** |
| PR #22/#14/#13/#3/#2 | MERGED | M2–M4 历史集成 |
| Release / Tag | GitHub Release 无；本地 tag 仅 `archive/20261101-pre-v2/*` | 最终版本身份需新建 tag（待批准） |
| 团队分支 | `team/product-console-v2-6d`、`team/temporal-event-sidecar-v0-6d`、`team/research-delivery-v2-6d`、`codex/sidecar-research-20261107` | 与 main **无共同祖先**（安全快照导出），只能文件级整合 |
| 本地 worktree | 16 个 + 4 个 `/tmp` prunable | 未清理（不属本阶段） |
| 主仓未提交 | 20 modified（M4 报告/包/脚本/SRS/CONTEXT.md）、28 untracked（ADR-0003、decisions、process/m3/m5、snapshots、experiments/top7、pr-38-review 等） | **需负责人决定是否提交**；其中 ADR-0003、SRS 修改、CONTEXT.md 术语与 M5 报告直接相关 |
| 提交作者计数 | kenqia 444、Thorns-06 33、xiaozhuozi39 8、VanadisssSSS 5 | 仅作描述，**不得**用于工作量推断 |

## 2. 现有交付物（实测，不沿用旧描述）

| 资产 | 位置 | 实测 | 状态 | 建议 |
|---|---|---|---|---|
| Presentation v2 | `origin/team/research-delivery-v2-6d:deliverables/v2/update-20261108/research-delivery-v2-20261108.{pptx,pdf}`（作者 VanadisssSSS，11-08） | PDF **15 页**，16:9 | 超课程 10 页上限；Product 页引用 `44d20dc`、截图来自 11-06；内容数字与冻结一致 | **REDO** 为 10 页；图表/版式 REUSE |
| Technical Report v2 | 同分支 `.../update-20261108/technical-report.pdf` | **5 页** A4 中文 | 数字核对一致；版本身份写的是 `0ebb2b8`、Console `44d20dc`，已过时 | **REUSE** 为新报告骨架，结构与篇幅 REDO |
| Technical Report rc1 | `.../review-rc1/technical-report.pdf` | 3 页 | 被 v2 替代 | ARCHIVE |
| Presentation rc1 | `.../review-rc1/research-delivery-v2-rc1.pdf` | 未计页 | 被替代 | ARCHIVE |
| Demo 视频 v2 | `.../update-20261108/video/demo-4m30s.mp4` | 270.0 s，1920×1080 h264+aac，**无字幕流**（字幕烧录） | 抽帧 60s/180s 为 **PPT 页面 + TTS 式旁白字幕**，非真实 UI 操作 | **REDO**（真人操作） |
| M4 演示视频 | `deliverables/m4/…演示视频.mp4`（主仓 untracked） | 250.3 s，1920×1080 | M4 历史 | ARCHIVE |
| Research Supplement | `docs/supplement/supplement.pdf` + `supplement.md`（996 行）+ 20 图 + `build.sh` | **39 页**（11-09 更新；37 页版在 `3392faf`，38 页版在 `b3c9d0f`） | 有勘误文件 `docs/release/SUPPLEMENT_ERRATA.md`、282 数值叶独立核对 | **KEEP** 为正式附录（需在附录前加勘误页） |
| M1/M2/M4 交付包 | `deliverables/m1,m2,m4/` | 齐全，含 sha256 | M4 文件在主仓处于 modified 状态 | ARCHIVE（以 Git 已提交版本为准，modified 版需负责人确认） |
| M3 交付 | `deliverables/PROJECT-MILESTONE3-…报告.pdf`（modified）、过程材料 zip（untracked） | — | 同上 | ARCHIVE |
| M5 个人候选 | `deliverables/m5-personal-candidate/README.md` | 说明文件 | 非团队交付 | ARCHIVE |

## 3. 代码与产品（main 5519dd2）

| 资产 | 位置 | 状态 | 建议 |
|---|---|---|---|
| 核心后端 | `src/locomo_memory/`（imports/builds/retrieval/relations/projection/expansion/queries/release_queries/exports/evaluation*/api） | Implemented；组件矩阵 `RELEASE_COMPONENT_MATRIX.md` | KEEP，报告第 4–8 章依据 |
| Product Console（新） | `console_ui.py`、`console_replay.py`、`console_theme.py`、`console_widgets.py`、`evidence_ui.py`、`frozen_report_ui.py` + 5 个测试文件 | 已合并 main；PR 内宣称 27 项定向检查与 Chromium 场景通过、真人复核（xiaozhuozi39，绑定 `0401155`）；**本审计正在独立重跑公开回归** | KEEP；视频与截图以此为主 |
| 原五阶段 UI | `ui.py` 等，Console 内可切换 | Implemented | KEEP |
| 独立 Replay | `release_viewer.py`、`replay_ui.py`；`scripts/personal-release replay-offline-demo` | Implemented，无 key | KEEP（视频 OFFLINE 段） |
| Bonus A–D | `m5_*.py`、`temporal.py` | 已实现，默认关闭（除 A 只读展示） | 报告第 13 章 |
| Temporal/Event Sidecar | 仅在 `team/temporal-event-sidecar-v0-6d`（PR #38）与 `codex/sidecar-research-20261107` | **未进 main**；研究结论为"拒绝接入" | 只能作 Research Candidate / 负面研究 |
| Schema | `memory-export-schema.json`、`six-memory-exports-manifest.json` | KEEP | 公开包可含 |

## 4. 实验与研究证据

| 资产 | 位置 | 建议 |
|---|---|---|
| E0–E25 索引 | `EXPERIMENT_ARCHIVE_INDEX.md`、`experiments/personal-release/experiment-archive-index.json` | KEEP，作为 Experiment Registry 底稿 |
| Level E（E25）冻结结果 | `experiments/m5-development/level-e-results-v1/official-scores.json`、`level-e-runtime-terminal-v1.json`、`level-e-derived-results-v1.json`、`level-e-failures-terminal-v1.json`、source-review-*.json | KEEP，主结果唯一权威源 |
| Level E 结果文档 | `docs/m5-development/LEVEL_E_RESULTS_V1.md`、`LEVEL_E_NUMERIC_REVIEW_V1.md` | KEEP |
| Level C v1 / input v2 | `docs/m5-development/LEVEL_C_RESULTS.md`、`LEVEL_C_INPUT_V2_RESULTS.md` | KEEP |
| 历史 757 题 E12 | `research-process-archive@3e64811`；团队摘要 `team/research-delivery-v2-6d:docs/team-v2/research-evidence.json` | KEEP（引用 Git 对象） |
| 证据损失诊断（11-09） | `experiments/evidence-flow-20261109/` | KEEP（RQ3 主要证据） |
| 真实边界回归（11-09） | `experiments/live-boundary-20261109/`（含 `HUMAN_REVIEW.md`，莫远序意见含"待裁定"项） | KEEP，标注为已曝光数据回归 |
| Sidecar 研究 | `codex/sidecar-research-20261107:research/sidecar-20261107/REPORT.md` 等 | KEEP（负面结果） |
| 主仓 untracked 实验 | `experiments/top7-iteration-20261029/`、`experiments/pr-38-review-20261103/` | 需负责人决定是否提交后归档 |
| 私有归档 | 主档 35,440 成员 SHA `bfb7f58a…`、Level E 私档 863 成员（见 `LOCAL_ARCHIVE_AND_CLEANUP_PLAN.md`） | EXCLUDE 公开包；只给 Manifest/Hash |

## 5. 过程与管理材料

| 资产 | 位置 | 建议 |
|---|---|---|
| 需求 | `docs/requirements/`（SRS md、vision-and-scope、team-workflow），`process/m3/traceability.csv` | ARCHIVE 02 |
| ADR | `docs/adr/0001`、`0002`（tracked），`0003`（**untracked**） | ARCHIVE 03；0003 需提交 |
| 决策访谈 | `docs/decisions/*.md`（untracked 4 份） | ARCHIVE 03/05 |
| 会议 | `process/meetings/first-meeting.*`、`f3f785b` 新增 11-03 会议截图 | ARCHIVE 01；**会议纪要数量偏少**，不得补造 |
| 成员评审 | `process/reviews/m1-member-review.*`、`process/m4/member-review-record.md`、`process/m5/member-review-20261107/`、`process/snapshots/2026-11-0{7,8,9}-member-quality-review.*` | ARCHIVE 08 |
| Notion 快照 | `process/snapshots/2026-11-07-m5-notion-setup.*` 等 | ARCHIVE 01 |
| PR/CI 记录 | `process/prs/`、各 PR 页面 | ARCHIVE 04（需导出 #38/#39/#40/#41 快照） |
| AI 协作 | `docs/ai-workflow.md`、`docs/agents/` | ARCHIVE 09 |
| M5 开发文档 | `docs/m5-development/`（约 85 份） | ARCHIVE 10，建索引，不全量复制到正文 |

## 6. 数据与隐私敏感资产

| 资产 | 状态 | 建议 |
|---|---|---|
| `data/raw/locomo/locomo10.json` | **在 Git 中被跟踪**；上游 CC-BY-NC-4.0 | 最终 ZIP 必须 EXCLUDE；源码包用 `git archive` + allowlist，不直接打包工作树 |
| 六份真实 MemoryExport JSON | 本机受控（含人物名与原文 support_quote） | EXCLUDE；仅交 manifest/hash；披露需负责人确认 |
| `var/`（43 MB） | 运行数据库/日志 | EXCLUDE |
| `.scratch/` | untracked 临时 | EXCLUDE |
| 凭据 | 未在 tracked 文件中发现 `sk-` 形式密钥；`docs/agents/local-credentials.md` 是说明文件 | 封包前再做一次全量扫描 |
