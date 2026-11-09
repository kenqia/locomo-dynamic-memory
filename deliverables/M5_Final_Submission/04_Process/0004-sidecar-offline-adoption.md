# ADR 0004：接受 Sidecar 公开离线诊断交付

日期：2026-11-09。状态：Accepted，负责人肯恰在本次会话明确授权整合 main、验证并结束工作线。

## 决定

本条取代 ADR 0003 的待采用状态，仅采用默认关闭、显式 opt-in 的独立离线诊断范围。源为 PR #38 的 `cd4db4c055d6d57256858ed3b7136ccea395122d`；非作者 Thorns-06 已[通过该范围复核](https://github.com/kenqia/locomo-dynamic-memory/pull/38#issuecomment-6738293701)，负责人接受已披露限制并授权收尾。

保留原回答、证据、Memory、Relation、Projection、Trace、预算和数据库。生产 API 与 Product Console 不导入 Sidecar，不增加模型调用、生产配置或数据库迁移。离线开关 `research_view(..., enabled=True)` 只附独立诊断，默认及回退均保持原响应。

## 限制与不采用项

已知 P2 延期：Memory 中 last/next year 的年份修饰及限定词空白归一化可能被忽略。此限制随交付公开，不宣称已修复。

真实历史导出和 68 条参考的成员独立复验未完成；现有研究聚合中 503 Memory、63,057 候选对全 unknown，68 单元有效覆盖为 0，不构成真实 QA 增益。Windows 完整公开入口有既有 fcntl/resource 限制。Linux/WSL 的整合验证单独记录。

不采用生产真实 QA 接入，不把真实质量提升列为本次完成条件；其研究方向从本轮交付范围排除。保留来源研究及未执行范围，不改写成通过。原 ADR 0003 和作者 ARCH01–04 记录按历史原样保留；当前交付以本决定和[整合冻结说明](../release/SIDECAR_FREEZE.md)为准。

## 回滚

停止调用独立 CLI，或传 `enabled=False`，原应用路径保持不变。撤销整合 PR 的 main 合并提交即可移除本次增量；无数据库恢复或依赖降级步骤。
