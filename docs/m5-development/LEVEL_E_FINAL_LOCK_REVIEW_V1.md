# Level E 最终配置锁的独立复核

2026-11-05。实际最终锁通过独立复核：18 组检查全部通过，0 项发现。本次没有执行真实 `prepare`、读取问题正文或 Gold，也没有发起 Provider 请求。结果见 [独立检查工件](../../experiments/m5-development/level-e-final-lock-independent-v1.json)。

私有 `final-system-lock.json` 与公共锁逐字节一致，SHA256 为 `3b6e3fbcad1670226f1f9d8e1c9fa96436b104893a875527d078dc4948671ac6`。实现 commit `0dbd98e7b296ef29d9998fa55d88d512f8ec85f1` 实际存在；82 个 producer 的当前文件与该 commit 的 Git blob 均匹配锁定 SHA，包括主评分脚本和 Level E 入口。依赖文件也匹配 Git blob。全部 Settings 与已完成 input v2 的开发快照完全一致。

六份导出分别通过严格 `memory-export-v2` 校验，SHA、complete 状态、Build、Dataset 和对话身份均与锁一致。两份 conversation-only Build 源通过标注隔离、表集合、外键与 SQLite 完整性检查，明确 pin 与只读重新导出的内容匹配锁定 JSON。参考 conversation 与两份 Build 的原始轮次内容一致。参考源及两份 Build 源的 main/WAL 身份在检查前后保持不变；未对参考库执行 backup 或全表逻辑快照。

参考复核只投影 dataset/artifact/sample 身份、QA 数组类型、长度和原始 ordinal：conv-43 为 242 题，conv-44 为 158 题，共 400 题。唯一 dataset、精确 artifact 与每段唯一 sample 匹配；全部 ordinal 连续并与锁定身份摘要一致，没有筛题。未投影 question、category、answer 或 evidence 值。

锁定策略为 Hybrid 与 Dynamic 两臂、Hybrid 默认候选、所有 Bonus 关闭，所有新生成 thinking disabled。物理输入上限为 640,000 UTF-8 字节，resolve 上限为 192,000 代理 tokens，输出上限为 32,768，重试参数为 2。800 个计划项对应独立硬上限 6,000 次请求、USD 1,387.9296；该上界不是付费授权，旧额度不转移。

已核对失败保留完整分母并记零、成功子集单报、Unknown 保留全部预约、不自动重启及不根据留出结果调参的政策。只有全部 800 项成功、失败或 Unknown 输出冻结，并核完授权、marker、账本、输出、producer 与参考身份后，评分入口才能读取相应 ordinal 的 Gold。类别 1–4 F1 与类别 5 literal refusal 分开报告；成本、资源和语义审阅仍待生成冻结后完成，当前复核不构成完整实验报告。

独立检查工件 SHA256 为 `769ba761764ffc2d11ce0c7ab5b518fee034338b263ff30319c4f80f6b52801c`。此次复核没有修改锁、producer 或旧源；真实 questions-only 准备与独立费用审批仍需后续执行和验收。
