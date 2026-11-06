# PR 草稿：增加默认关闭的时间/事件独立诊断候选

目标分支：codex/v2-6d-research-safe。
来源分支：team/temporal-event-sidecar-v0-6d。
关联：#24、#30、#31、#32、#33（待真实评审验收，不预填关闭）。

## 基准
原始 ZIP 快照提交：4d1d072f2c7075ebcac10879269bdcfd736e683b。它不自动等于当前远端分支 HEAD 或 PR merge-base。提交前执行 git rev-parse HEAD 与 git merge-base HEAD origin/codex/v2-6d-research-safe，填写实际 feature HEAD 和 merge-base SHA。

## 改动与行为
新增 Sidecar 契约、16个冻结合成案例、确定性规则、只读导出适配、研究开关、CPU/wall 合成对比及两个合成完整 Build 的兼容检查。默认关闭，开启时只增加独立诊断；不覆盖正式答案，不更新旧数据库，不增加真实模型调用。保留 unknown、冲突与历史记忆。

## 运行与证据
运行方式见 ARCH04-README。用户 Windows 已运行前三阶段144测试；本包 Linux六文件145测试通过，Windows新增测试结果待补。对比与兼容输出均是合成证据，无真实质量提升结论。当前只核验两个合成完整 Build，没有核验两个真实历史 Build。

## 风险、回滚与评审
规则覆盖有限英语表达与状态维度；没有生产默认接入。关闭显式研究开关可恢复原响应路径；撤销新增文件无需数据库迁移。需要非作者真实成员复核与负责人确认 ADR，Reviewer/结论/链接均待填。
