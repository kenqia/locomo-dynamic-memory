# Codex 总执行任务｜LoCoMo Dynamic Memory v2 六天冲刺（2026-11-03—11-08）

## 最高指令：六天内交付，不是开启一个六周研发计划

你是项目的交付工程师和 GitHub 工作流搭建者。**现在直接执行**仓库安全同步、三条研发主线 Issue/分支设置、团队任务入口与可运行的协作基线；随后由四名成员并行开发。先读本目录 `01`—`08` 的所有文件，其中 `06_SIX_DAY_SPRINT_BOARD.md` 是唯一冲刺日程，`07_RELEASE_ACCEPTANCE.md` 是最终验收标准，`08_GITHUB_ISSUE_MAP.json` 是机器可读任务台账。执行前再次核验远端与本地状态，不把历史快照当实时事实。

**必须完成（P0）**：安全、可访问的 GitHub 代码/任务基线；能运行并离线演示的端到端系统；统一的 v2 研究演示和真实已有实验结果；完整可编辑 PPT、PDF、视频、README、课程交付核对；所有成员有可独立推进的任务与 PR；第六天形成可恢复发布候选。

**限时完成（P1）**：一个 Temporal/Event Sidecar opt-in MVP 与边界测试；前端 Memory Timeline + Evidence/Trace Inspector；GitHub 的技术报告和研究证据索引。**有余力才做（P2）**：高级图可视化、花哨动效、新前端框架、新 Reranker/新 Router、更多付费实验。P2 不得挤占 P0。

我们能在六天内交付一个**经工程验收、可以真实展示、研究结果透明**的项目，不能承诺六天内证明教师未知数据的最优成绩。North Star 是：未知对话 QA 质量、事实/引用正确性和完整运行成本；未经独立测试不能声称这些指标已最优。

## 实际仓库与证据（2026-11-03 检查时，执行时重查）

- `https://github.com/kenqia/locomo-dynamic-memory`：**PUBLIC**，已存在 `main` 与旧研究分支；四位团队账号可访问。公开性是硬性安全风险。**严禁把“全部上传”理解为上传受控 SQLite、provider 原始 wire、封存盲审映射、账号凭据、私人内容或未经审查的课程材料。**
- 主仓 `<LOCAL_REPOSITORY>`：`main@f5a5dfd`，约 20 个已修改文件 + 大量未跟踪文件；不可 reset/clean/擅自 stash，也不能 `git add .`。
- Production v1 工作树 `<LOCAL_WORKTREES>/production-integration-20261101`，分支 `codex/production-integration-20261101@915fac0`；离线工程已验收，尚未与 main 合并。
- Research v2 `<LOCAL_WORKTREES>/research-next-20261101`，分支 `codex/research-next-20261101` 正在快速更新，2026-11-03 已有 E1 Router、E5 Query Embedding Cache 及全量分析，另存在未提交文件。**不可改写运行时数据库、执行账本与正在生成的报告。**
- 4 开发对话、757 QA、3,028 组合原真实 Run：2,969 success / 56 failed / 3 unknown，状态不是完整成功。Dynamic 完整分母得分 0.515133，成功子集均值不代表全量。Hybrid 比 Dynamic 技术完成率更高且更便宜；不能选择性只展示 Dynamic 成功均值。
- E1 Router v1 LOCO 无有效 Fast 路由，当前不值得另开新付费试验。E5 本地 Query Embedding 复用等价且降低局部 CPU，**只是一项 opt-in 本地优化，不代表 DeepSeek 降本**。
- 课程旧 M4 材料存在，但不能当成 v2 最新实验报告；课程提交格式、时长及版权需由团队核对。

## 六天交付架构与人员

- **负责人（用户）**：Production/Research 主线、Build/Query/QA、实验身份与预算、发布采用、最后效果结论。
- **Track A Product**：Research Console、Memory/Timeline、Evidence/Trace、离线 Demo，独立可运行交付。
- **Track B Architecture**：Temporal/Event Sidecar v0，独立 opt-in，严格测试、对比与回滚；不触碰生产默认。
- **Track C Delivery**：v2 技术报告、可编辑 PPTX/PDF、3–5 分钟演示视频、图表与课程提交包。
- 三条线由三位成员**自由认领，一人一主线**；不得按旧 Team Workflow 预设人名分配。每个 Track 有 Owner 和非作者 Reviewer，实际确认后才记录。

## 立即执行顺序（D1 必须在当天完成）

1. **安全只读审查**：检查 Repo PUBLIC、main 脏改动、分支/远端同步、运行中进程、文件许可、秘密/隐私/大小；创建/核验不改变原件的可恢复备份和 SHA manifest。以路径白名单为唯一上传依据。
2. **明确用户授权边界**：已允许同步不含敏感内容的代码、经审查的公开文档、团队任务；**未批准改变 GitHub PUBLIC/PRIVATE**。仓库可见性或待审材料公开权不明时只能 HOLD，不能自行改变权限；不因一项 HOLD 阻断其他安全任务。
3. **最短 GitHub 路径**：为 Production v1 建安全可共享的远程基线；为 Research v2 建**已提交、审查过的固定快照分支**；不复制 live DB、不试图在 6 天内消除所有旧分支或强推 main。记录各分支实际 SHA。若 Research 仍在写，可先基于已提交 commit 冻结团队接口基线，之后经审查 fast-forward 更新，避免等到实验结束才启动团队。
4. **选择可用且最少冲突的三条任务起点**：Product 与 Delivery 优先基于 Production v1 安全快照；Architecture 若需要 `tools/research_v2` 等研究工具，则基于已审查且已提交的 Research Next 安全快照。记录实际 SHA 和依赖，绝不为“同一 commit”而剥夺独立研发必要模块。
5. **发布协作任务**：创建三父 Issue + **每 Track 四个子 Issue，共 15 个 Issue**（见 `08`），设置可用标签、D1–D6 截止检查点和里程碑；存在重复时复用。Owner/Reviewer 暂为空，要求 D1 认领。Project board 如权限/时间允许创建，否则 Issues + labels + milestone 足够，**不要为看板配置消耗半天**。
6. **建立三个独立远程工作分支**：`team/product-console-v2-6d`、`team/temporal-event-sidecar-v0-6d`、`team/research-delivery-v2-6d`。共同基准须是已推送的安全已提交源码，记录各分支对照 commit；成员各自在本机 clone/checkout，不共享研究工作树物理目录。
7. **建立 `docs/team-v2/` 协作入口**，PR 模板、CI 最小验证、贡献规范、每日交付板和内容/证据台账。保留/链接本套任务书。**D1 傍晚三个成员都应该能 clone、看到自己的 Issue、开始写代码/制作材料**。

## D2–D6 的并行交付（由团队成员完成，Codex 负责设置与必要实现支持）

- **D2**：A 有核心只读界面可运行；B 有 Schema/事件时间案例与测试；C 有事实台账、完整 PPT 大纲/首版页和视频分镜；负责人建立可共享的冻结演示数据与当前实验摘要。
- **D3**：A 有 Query Trace + 来源跳转；B 有事件身份、时间/状态规则 MVP；C 有完整 PPTX 初稿和报告初稿；全部产出 push 到各自分支并开草稿 PR。
- **D4：功能冻结**：A 有离线 Demo 流程；B 有可插拔 Sidecar + opt-in 开关 + 边界测试；C 有完整 PPT/PDF 草稿和录屏脚本。18:00 后不接受新增功能或新架构方向，只允许修复阻断。
- **D5：集成与验收**：API/UI 离线 E2E、兼容性和回归；独立测试 Sidecar 默认关闭；C 完成正式 MP4、导出 PDF、讲稿；跨成员 Review。发布 v2-demo RC。
- **D6：只修阻断 + 演示交付**：锁定 release SHA、证据来源、成绩分母；最终 PPTX/PDF/MP4/技术报告/README/许可证/manifest；完整彩排与备用离线录屏；通过安全审查后提交课程与远端同步。是否提交课程由用户最终确认，不能假冒已提交。

## 冻结规则 / 退出标准

- 从 D4 18:00 开始**Feature Freeze**；D5 18:00 开始**Content/Data Freeze**；D6 只处理 P0 阻断和错误数字。所有时间用 Asia/Shanghai，自 2026-11-03 算 D1，2026-11-08 为 D6；如团队实际启动更晚，立即按相同六天工期重排，不默默延长。
- 新功能默认 opt-in；优先复用 FastAPI+Streamlit、现有真实实验及冻结可共享数据。不得为 UI 演示发出真实生成请求。**六天内不启动额外 DeepSeek 模型实验**，除非用户另行冻结题单、请求/金额/时间预算并明确授权；现有运行任务不受此文档干预。
- 每个人的最小交付必须有实物、启动/打开命令、测试/人工复核记录、截图或视频、真实 PR 链接。不能拿草稿当完成、拿 AI 复核当人工、拿原 3,028 分母全部当成功。
- 若时间紧，先砍 P2、然后缩小 P1 可视化复杂度，**绝不砍**安全、可运行演示、真实来源、最终 PPT/视频、基础回归、版本与回滚。
- 任何阶段都不得 `git reset --hard` / `git clean -fd` / force push / 改写主仓脏工作区 / 覆盖研究数据库。不得将权限变更、公开视频发布或课程正式提交当成自动授权。

## 最终报告（必须是事实，而不是计划）

1. 四个工作方向的 Owner/Reviewer、真实 GitHub Issues/PR URLs、代码与材料 commit SHA。
2. 已上传与 HOLD/DENY 清单，远端 PUBLIC 状态、敏感文件扫描、备份与恢复方式。
3. A/B/C/负责人各交付什么、实际演示链接与启动命令；未实现功能列为未完成，不虚构。
4. QA 正确率、证据正确性、成本仅使用明确 Run/分母/评审类型；新增模块无独立真实对照就不称 QA 提升。
5. 单元、离线 E2E、API/UI 浏览器/应用检查、真实播放/渲染核验、回滚和 P0 缺陷。
6. Day 6 最终验收表：`PASS / PARTIAL / BLOCKED`，不能为完美结项改写失败历史。

**开始执行；不要再拆成新的长期研究计划，不要为了创建几十个 Issues 延误真正交付。**
