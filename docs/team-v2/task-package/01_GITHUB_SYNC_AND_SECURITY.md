# Track 0｜GitHub 安全同步与团队启动（D1 完成，D6 收尾）

**任务性质：发布基础设施与权限审查，不是另一条长期研发主线。** GitHub 仓库 `kenqia/locomo-dynamic-memory` 于 2026-11-03 查询为 **PUBLIC**；公开仓库不能当作私人备份盘。已有四位 collaborator，具体账号与个人身份的映射只能由本人确认。不得擅自修改 visibility。

## D1 当天必须交付

| 时间点 | 可验收结果 |
|---|---|
| D1 上午 | Git/工作树/远端/运行任务只读快照；本地原件可恢复备份及 SHA manifest；上传白名单与 HOLD 清单 |
| D1 中段 | Production v1 安全基线已推送或准确记录阻断；Research Next 用**已提交且已审查的安全快照**建立团队共享基线，不处理 live DB |
| D1 傍晚 | 3 Track + 12 子 Issues、标签、最小 Milestone 可访问；3 个独立远端分支；每位成员能 clone/启动自己项目、提交第一份 PR |
| D2 | PR 模板 + 无付费 CI 实际触发并验证；README/团队任务入口可找到三条主线 |
| D5–D6 | 再次检查所有待合并 PR 与发行资产；发布 v2-demo Release Candidate（允许使用 tag 或受控分支），上传授权可共享物，保留需要 HOLD 的原件在本地归档 |

## 内容决策矩阵（逐文件、逐提交审查）

| 类型 | 建议操作 |
|---|---|
| 安全代码、接口、测试、ADR、配置模板 | 扫描后推送到明确的 Production/Research/Team 分支 |
| 已脱敏的真实实验摘要与可验证数字 | 附 Run/Build ID、统计口径、hash 与限制后可推送 |
| 未审课程课件、截图、报告、个人姓名、原版 ZIP/视频 | **HOLD**，需许可/隐私和用户批准；可用脱敏演示副本 |
| `.env`、token、cookies、原始 provider 请求与回答、sealed review key、私有对话原件 | **DENY**：不提交到 PUBLIC 或 PUBLIC LFS；不打印 secrets |
| SQLite、模型缓存、运行中数据库、备份、GB 级原始结果 | 原地保留/受控离线归档，只公开 manifest、哈希和脱敏聚合 |
| 来源授权不明的第三方数据、教师隐藏测试 | **HOLD/DENY**；不可用来调参或上传 |

**权限闸门**：用户此次授权的是“上传项目中可安全共享的内容并开启协作”，不是批准改变 PUBLIC/PRIVATE 可见性、分享所有课程资料、公开所有原始会话或正式提交课程。对于可公开源码和已审摘要无需等待所有 HOLD 全部解决，可并行推进；对公开权限不明确的具体文件必须停止发布并列入 HOLD。对于已经跟踪的敏感历史，也要做安全审查，`.gitignore` 不能代替历史扫描。

## Git 策略（最少动作，无损）

1. 记录 `git status --porcelain`、分支 SHA、`git worktree list`、`git branch -vv`、远端 refs；确认没有意外运行 `git fetch` 修改工作树的行为（fetch 可更新 refs，但不改变工作文件）。
2. 检查此前已有的 Git Bundle/未跟踪原件归档；如有缺口只补覆盖缺口并校验，不大规模重复复制当前数 GB SQLite。
3. 主仓 `main` 脏文件约 20 modified 和大量 untracked：绝不 `git add -A`、`git clean`、`reset --hard` 或强制 stash；按 *allowlist* 分批在独立工作树提交。
4. **三条 Track 的起点必须明确而不是强行相同**：Product 与 Delivery 优先从冻结 Production v1 安全 commit 创建；Architecture 为复用研究工具，优先从 Research Next 的**已审查、已提交、已安全推送**的固定 SHA 创建。若该研究 SHA 暂不能安全推送，先从 Production v1 启动 Schema/测试，再把必需的安全研究代码作为单独可审查提交引入。任何跨分支接口合同必须记录，不得拷贝活动中的 `var/`。
5. Production v1 来源 `codex/production-integration-20261101@915fac0`；Research Next 源头每天推进，**仅以可验证 committed SHA 建共享分支**。Research 未提交与受控 `var/` 不因为六天压力而整体 add/拷贝。快照后新的合法研究提交通过后续独立 PR 引入。
6. 推荐远端长期分支：`codex/production-integration-20261101`（或经审查重命名稳定基线）、`codex/research-next-20261101`（安全快照）；协作分支 `team/product-console-v2-6d`、`team/temporal-event-sidecar-v0-6d`、`team/research-delivery-v2-6d`。短期并行不要求把 main 当前所有历史一口气合并。
7. 检查 README、CI、Run/Build/QA 的恢复能力：没有可共享数据库时必须提供**确定性的脱敏离线 fixture**和启动命令，避免队员因没有本机私有数据而被阻断。
8. 不需要配置复杂 GitHub Projects；Milestone 只需 `v2-6day-demo`。Issue 与子任务标签见 `08_GITHUB_ISSUE_MAP.json`。创建幂等：先查询同标题/标识，不重复创建。

## D1 一页发布核验报告

在 `docs/team-v2/github-sync-report.md` 写明：PUBLIC 实际状态、远端每个新 branch SHA/URL、已推送文件 allowlist、HOLD/DENY 及原因、本地归档与 manifest、CI 状态、三个父 Issue 和子任务 URL、Owner/Reviewer 真实认领状态、需用户处理的许可或可见性问题。

必要保护：每次 push 前检查 `git diff --cached --name-only`，大文件与秘密扫描仅输出路径/哈希和分类；不把原文 secrets 复制到日志/Issues。必要时使用 PR 审核，而不是六天内直接改写 main。不要因为登录了 gh 就认为任何资料都可公开。

## D6 的发布边界

- 发布**已获许可**的 code/docs/PPT PDF/脱敏 demo；MP4 如过大或涉及隐私，在受控共享位置存放并提交可访问说明或授权后的 release asset。
- 文档注明 `actual/live`、`offline replay`、`prototype`；实验成绩有 Run/分母和复核身份。
- 留下还未上传的准确 manifest，**HOLD 不等于失败或遗忘**。
- 所有实际 PR/Issue/Release URL 必须可查询，未创建或未授权的不能虚构。
