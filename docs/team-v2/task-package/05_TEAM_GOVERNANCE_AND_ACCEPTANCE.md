# 六天协作制度｜四个人并行而不互相阻塞

**周期**：2026-11-03（D1）至 2026-11-08（D6），Asia/Shanghai。实际启动若不是 D1，须明确重排这 6 天，不把任何阶段“自然顺延”到第七天。

## 工作所有权

- 负责人：Build/Query/QA、完整开发基线分析、北极星指标、预算、生产默认采用与发布最终决定。
- 三位成员自由认领：Track A Product、Track B Architecture、Track C Delivery。每人一个主要结果，支持 cross-review，但不让三个成员都等待负责人分配具体代码。
- D1 必须完成真实认领：Owner、Reviewer、分支、Issue、验收标准与当天第一项 PR。若有人暂时未认领，公开状态为 `unassigned`，不填写历史 Team Workflow 的姓名冒充已确认。

## 每日 15 分钟同步（不增加官僚开销）

每天固定一次：每人回答 **昨天交付了什么证据 / 今天交付什么可检查产物 / 阻塞谁来解除**。只保留一个 `docs/team-v2/sprint-status.md` 看板，GitHub Issue 为任务唯一状态源；不用复制另一份冗长任务表。任何 `blocked` 超过半天，由负责人当天决策“给接口/给 Fixture/砍 P2/降级交付”。

## 文件与接口边界

| 线 | 主写范围 | 不得碰的范围 |
|---|---|---|
| Lead | `src` 核心/`tools/research_v2` 当前实验/受控 runtime | 不被队员意外改写的 live DB/预算账本 |
| Product | Streamlit UI、主题、只读页面/测试、Demo fixtures | 默认 Build/Query/模型适配器、原始数据 |
| Architecture | 新 sidecar 模块/Schema、研究入口、边界测试、ADR | 生产默认 Prompt/Schema、活跃 SQLite |
| Delivery | `docs/team-v2`、`presentations/v2`、`deliverables/v2`、可编辑图表/视频 | 计分器、历史实验原件、封存评审 |

跨范围需求先开 Issue + 提交适配 contract：不能在 PR 中顺手重构核心代码。团队共享**固定已提交可访问基线**，各成员本机 clone/branch，不假设四个人共用 worktree。

## 合并与审查节奏

- D1：每条分支首次提交。D2：可运行/可打开阶段成果。D3：三条草稿 PR 全部存在。D4 18:00 **功能冻结**，所有新增功能只进 backlog。D5 18:00 **内容与数据冻结**，主攻验收。D6 仅修 P0 与发布。
- PR 需要 5 个信息：基准 SHA、实际修改、如何运行/打开、测试/人工检查结果、隐私/模型费用情况。非作者 reviewer 记录实际检查，而非只写“AI reviewed”。
- 新 Sidecar 没有通过真实配对实验就不能默认开启；Product 的 Replay 不能冒充实时模型；Delivery 不能把未知结果填零。
- 基于已有完整对话测试，D5/6 只跑**离线回归、只读固定结果和必要应用冒烟**。所有新的 DeepSeek 付费调用都要另行冻结和授权，不能利用旧额度延长。

## RACI 简化版

| 产物 | 做的人（R） | 最终拍板（A） | 复核（C） |
|---|---|---|---|
| 真实实验和模型成本 | Lead | Lead | 架构 Owner 或指定成员 |
| UI/Console/Demo Fixture | Product Owner | Lead | Delivery Owner |
| Sidecar/离线消融 | Architecture Owner | Lead | Product 或 Delivery Owner |
| PPT/PDF/视频/技术报告 | Delivery Owner | Lead | Product Owner + Lead 事实核查 |
| GitHub 同步与 Release | 执行 Codex/负责人 | Lead | 任一非作者成员 |

**Day 6 完整交付**并不等于教师隐藏测试最佳、完成所有未来算法研究、所有 Git 历史都必须合入 main。项目必须做到：可运行、可展示、文档可读、真实结果可追溯、核心研发分支安全可恢复。

## 阻断分级与砍需求规则

- **P0 必须修**：凭据泄漏/隐私/许可，无法运行 Demo，数据/数字虚构，引用错误解释，PPT/PDF/视频缺失或打不开，主线回归严重失败，发布不可回滚。
- **P1 尽力修**：高级 Timeline、图视觉质量、Sidecar 与 Query 的深度接线、小型新改进离线对照、团队材料细节。
- **P2 立即延后**：完全替换前端、复杂 Graph DB、全新 Agent、多轮 Prompt 搜索、重跑 3,028 组合、额外动画及海报。

若 D4 尚有 P0 阻断，立刻切换到“演示冻结的 Production v1 现有能力 + v2 Sidecar 独立研究展示”最小方案。任何情况下不允许为赶进度篡改历史错误、计量未知、原始数据或用户文件。
