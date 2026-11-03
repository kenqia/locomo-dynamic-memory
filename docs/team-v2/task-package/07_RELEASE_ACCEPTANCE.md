# Day 6 最终发布验收清单｜v2-demo RC

**最后验收时间：D6（2026-11-08），Asia/Shanghai。** 每一项写 `PASS / PARTIAL / BLOCKED`，附实际 SHA、测试记录、截图/文件地址及验证者姓名；未完成保留原状态，不填写假通过。

## P0：安全 / GitHub

- [ ] 远端实际 visibility 已核验；公开内容已做许可、隐私、凭据与大文件审查。新上传内容有 allowlist，HOLD 资产仍受保护。
- [ ] Production v1 和共享 Research 快照拥有可恢复的远端分支 SHA；主仓脏数据没有被覆盖、归零或误提交；旧完整实验产物和账本安全保留。
- [ ] GitHub 3 个父任务 + 12 子任务及相应标签/Milestone 实际存在且可打开；团队每条线有真实 Owner/Reviewer/PR 状态，未认领如实写明。
- [ ] 关键路径 `clone → 安装/使用已锁依赖 → 离线启动 → 查看 Demo` 在团队至少两台机器或干净隔离环境核验；未下载新 embedding/未调用付费 API（除事先独立授权）。

## P0：产品运行

- [ ] FastAPI + Streamlit 或经过审查的正式 UI 能启动，现有导入/历史 Build/Query/导出接口不破坏。
- [ ] 一个固定离线 Demo 从数据→Memory→QA/Trace→原文 citations→实验报告可连贯走通；Replay/Prototype 标签真实。
- [ ] 引用能定位正确 SourceTurn，失败/预算/unknown 有真实提示；不能把 ID 合法性当证据语义正确。
- [ ] 全套离线回归、关键 E2E、UI/演示冒烟实际执行，列出通过/失败/明确排除及阻断项；重大回归必须修或有可执行回滚。

## P0：架构候选（不等于生产采用）

- [ ] Temporal/Event Sidecar 模块、Schema、12–20 个可追溯案例、至少 20 个离线边界单测、来源与版本绑定、启停/回滚。
- [ ] Event identity、reported_at/event_time、计划/完成、否定、as-of/unknown 有可复现示例。不存在凭空补造事件/日期。
- [ ] 不触及活跃研究 DB、旧 Build 持久 schema 或生产默认模型路径；关闭 opt-in 后旧行为不变。
- [ ] 有 ADR 和局限；如没有严格真实配对 QA，则只宣称工程完成，不宣称隐藏测试、QA F1 或成本收益。

## P0：研究可信性

- [ ] 原 757 QA / 3,028 组合基线的成功、失败、unknown 原样报告；原 Run 未 completed，补充/修复 Run 单列。
- [ ] QA、证据支持、引用正确性、CPU 成本与 provider 成本分别报告；未独立复核则标未评，不填写 0 或 100%。
- [ ] E1 Router v1 负结果、E5 opt-in 本地 CPU 收益、时间/状态/来源失败边界准确；隐藏测试没有被用于调参或宣称通过。

## P0：最终素材（须有文件实物）

- [ ] `README` / 技术说明 / 架构图 / 答辩 FAQ / 源数据与实验身份索引齐全。
- [ ] 可编辑 PPTX 和 PDF 正常打开，页数/格式符合已确认课程要求，逐页截图或导出渲染核验。
- [ ] MP4 可播放、时长符合课程或约定的 3–5 分钟，画面和音轨/字幕一致，包含 Replay/Prototype 声明。
- [ ] 提交材料包含明晰 manifest 与 SHA256，未公开内容另列受控地址；无密钥、第三方未经许可材料或封存盲审 key。
- [ ] 真实团队成员完成一轮事实复核、一轮 Demo/PPT/视频复核；AI 自审不替代成员复核。
- [ ] 演示彩排已完成、离线备用视频准备妥当；课程正式提交如果未获得授权/尚未实施，明确写 `not submitted`。

## 发布说明格式

```
Release: v2-demo-rc1
Code SHA: <actual>
Build/Run IDs in presentation: <actual>
GitHub issues and PRs: <actual URLs>
Acceptance: PASS / PARTIAL / BLOCKED
What works: ...
What is prototype / opt-in: ...
QA, evidence, cost claims and denominators: ...
Known failures, unknown and constraints: ...
Safe deployment/demo steps: ...
Rollback SHA/steps: ...
Held-back files: <manifest>
Submitted to course: yes/no; receipt if yes
```

**P0 只要仍有 BLOCKED，就只能称“部分交付”，不能写全部验收完成。** 但允许按真实完成内容交付演示和文档，不为追求虚假全绿冒险改写实验数据。
