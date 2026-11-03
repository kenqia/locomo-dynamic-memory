# 唯一冲刺看板｜2026-11-03—11-08（Asia/Shanghai）

**六天不是六天研究计划，而是六天最终交付倒计时。** 四人并行；每天都要提交真实可检查文件/代码，尽量不要把大量工作留到 D6。项目最终不宣称隐藏测试最优，但必须可运行、可演示、可提交、可追溯。

## 四条并行泳道

| 日期 | 负责人：Core/Research | A：Product Console | B：Architecture Sidecar | C：Delivery / Media |
|---|---|---|---|---|
| **D1 11/03** | 冻结已提交基线；完成安全 GitHub 同步/Issues/Owner；当前实验做只读状态摘要 | 确认 API 与 Demo fixture，页面导航/信息架构可运行 | 固定 12–20 个边界案例和 Schema；测试框架 | 证据数字台账 + 叙事骨架 + PPT 风格样页 + 视频分镜 |
| **D2 11/04** | 共享脱敏只读数据/接口契约；研究指标与版本状态复核 | Overview + Memory/Trace 入口首个可运行 PR | Event/Time/State 核心规则及初测 | 至少 6 页实版 PPT；视频操作路线；报告目录 |
| **D3 11/05** | 统一研究分母/成本/局限；阻断快速决策 | Evidence Trace/Source 跳转；实验对比页；草稿 PR | 事件连接与时间状态边界单测；研究 opt-in | 完整 12–15 页 PPTX 草稿、报告初稿、视频台词 |
| **D4 11/06** | 18:00 功能冻结；仅合入可回滚/安全的修改 | 固定离线 Demo，准备截图和浏览器 E2E | Sidecar 可单独启停；边界测试/小对照/ADR | 完整 PPT/PDF 草稿、Demo 粗剪、讲稿与复核请求 |
| **D5 11/07** | 集成检查、全量离线回归、最终真值边界审查 | E2E、修 bug、交付截图和演示启动命令 | 审查/测试、脱敏 Sidecar 演示、PR 交接 | 正式 MP4/PPTX/PDF、报告、字幕、SHA manifest；18:00 内容冻结 |
| **D6 11/08** | P0 修复、锁定 Release SHA、准许公开清单和课程最终提交 | 锁定可运行 Demo、备用环境/录屏 | opt-in 说明、限制、回滚确认；不追加新算法 | 打包并复查全部文件、彩排、答辩 FAQ、提交清单/回执（实际提交后） |

## 每日 Checkpoint（均需证据，不是“完成了”三字）

- **D1 Gate**：远端安全基线/任务能访问、三人真实认领、每条线第一份提交、秘密/许可待办单。
- **D2 Gate**：A 有可运行代码；B 有边界用例和可测 Schema；C 有可编辑 6 页 PPT；Lead 有可共享冻结数据。
- **D3 Gate**：三条主线均有 draft PR，出现依赖已在 Issue 标注，至少一个人能从另一个人的说明复现。
- **D4 Gate（18:00）**：切断所有新 Feature；A Demo 可以连贯演示；B sidecar 已可运行或明确降级诊断；C 完整幻灯片与粗剪就位。
- **D5 Gate（18:00）**：全套产物齐备；两个真实成员交叉检查不同产物；有统一版本与数字来源、严重缺陷已列。
- **D6 Gate**：4 个泳道均 PASS/PARTIAL/BLOCKED 逐项报告；可运行、可打开、可播放、可回滚、可公开范围正确，提交/未提交状态真实。

## 六天内的“完整”应该包括什么

**Engineering complete**：现有 Production/Research 基线可克隆复现；API/UI Demo 可走完整主要业务路径；Sidecar 作为可选择研究能力有可执行测试；运行不收费，来源可回查。

**Research complete for this sprint**：有 757 QA/3,028 原 Run 的真实数据、失败和成本；区分原 Run 和补充/修复；当前新架构没有配对真值就不写质量提升，不靠补跑大量实验取得好看数字。

**Presentation complete**：PPTX/PDF/MP4/技术报告/数据图/讲稿/过程与版本证据/备份一套齐全；能 3–5 分钟讲出价值、问题、方法、真实结果和未完成边界。

**Collaboration complete**：GitHub 可见三条主线、12 子任务、成员真实 Owner、PR、review、最终 RC commit 及未推送材料 manifest。

## 如果进度落后：明确降级（最迟 D4 上午决策）

| 风险 | 安全降级 | 不能牺牲 |
|---|---|---|
| Product UI 来不及 | 复用原 Streamlit 五阶段；Timeline 用表格，Trace 用已有 expander + 来源跳转 | 真实结果、引用可回查、可运行 Demo |
| Sidecar 实现来不及 | 保留确定性事件/时间规则和只读可视化，标 `diagnostic_only`、不称接入 QA | 默认关闭、边界测试、来源可信 |
| PPT/视频进度落后 | 用无动画的可编辑模板、固定离线录屏、简洁旁白；3 分钟短版优先 | 可播放 MP4、可编辑 PPTX、真实数字与来源 |
| GitHub 有未决 PUBLIC 权限 | 仅推可安全公开的代码与简化 Issue；媒体/受控实验留本地 manifest | 不泄露凭据、数据、个人信息 |
| 未完成新的付费 QA 对照 | 用已有冻结真实 Run 诚实汇报；新 Sidecar 只报告工程与离线语义边界 | 不伪造新质量成绩、不改动旧实验 |

**不允许**将 v2 功能开发、正式媒体、完整测试和 GitHub 发布全部堆到 D6。每天结束后必须有带 commit/文件地址的实物。
