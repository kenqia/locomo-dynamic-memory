# 独立 Level E 执行状态

2026-11-05（Asia/Shanghai）。本次独立 Level E 已获明确批准并单次启动，当前正在生成。尚未形成完整生成冻结、读取 Gold 或计算留出成绩；不能将运行中的请求数或成功率写成最终结果。

## 授权与执行身份

用户明确批准：

> 授权本次 USD1,387.9296 / 6,000次独立 Level E

固定 conv-43/44 完整 400 题、Hybrid/Dynamic 共 800 项，不启用 Bonus、不重建 Build。旧余额不转移，中断不自动重启。所有新生成 thinking disabled，640,000 UTF-8 字节、resolve 192,000 代理 tokens、32,768 输出 tokens，模型重试 2 次、transport 重试 0 次。

- 准备提交 `41a3386`，授权与执行前价格提交 `ee546fc`。
- 实现 commit `0dbd98e7b296ef29d9998fa55d88d512f8ec85f1`，82 个 producer 与真实 Git blob 精确匹配。
- 计划 SHA `5d99378868a5aed92889ff3995ae7771270b91d8effb373fb6d7e85672484c92`。
- 配置锁 SHA `3b6e3fbcad1670226f1f9d8e1c9fa96436b104893a875527d078dc4948671ac6`；先于问题正文读取提交。
- [明确授权记录](../../experiments/m5-development/level-e-explicit-authorization-v1.json)绑定实际授权文件、冻结身份和执行前检查。
- [当日价格复核](../../experiments/m5-development/level-e-execution-pricing-v1.json)：官方仍将 `deepseek-flash` 映射为 Flash-1017；峰价输入 cache-miss USD0.30/M、输出 USD1.20/M。alias 不是不可变权重 pin。

根 25 项、非作者 6 组实际准备审计均通过，新 ledger 初始 0 请求，参考与两份 Build 源 main/WAL 不变。完整范围见[实际准备](LEVEL_E_PREPARATION_V1.md)。该文件及旧 gate 保留准备时点；本页记录随后获批和启动的状态，不覆盖原身份证据。

## 运行与后处理

私有 stage 为 `var/m5-development/level-e-preparation-v1`。凭据仅由现有 `scripts/with_deepseek_env.py` 加载到单一子进程。真实执行的 `PYTHONPATH=src:.` 允许已批准 Provider 访问，`HF_HUB_OFFLINE=1` 与 `TRANSFORMERS_OFFLINE=1` 保持本地 embedding 离线。准备审计时使用的 `offline_guard` 仅用于免费验证，未带入真实调用。

外层一次性 runner 记录进程开始与结束、wall time、等待子进程的 user/system CPU、Linux 峰值 RSS（KiB），范围为整个 launcher 子进程；不分摊为两臂资源，不称 GPU 采样。stdout/stderr 只保存在私有文件，不读取或提交原始响应。runner 身份见[启动记录](../../experiments/m5-development/level-e-runner-prelaunch-v1.json)。

运行时只查看安全计数、状态和预算。所有成功、失败、Unknown 保留。全部 800 项冻结后，先验证授权/marker/ledger/输出/producer/源身份和查询 checkpoint，再开启 Gold 评分。类别 1–4 F1 与类别 5 字面拒答得分分别报告；后续来源事实/拒答审阅不向审阅者提供 Gold、QA 分数或标准证据。缺独立真值的指标保持 `not_measured`。

## 已完成的 Build 与历史费用

六份严格 JSON 均已独立复核：共 2,031 Memory、37,445 关系，见[六份清单](../../experiments/m5-development/six-build-exports-v1.json)。conv-44 为 392 Memory、7,134 关系、384/384 成功；原恢复已经终结，不得重启。标签数量是结构计数，不代表语义准确率。

本次启动前九阶段累计 1,863 请求、预约 USD92.1592080、已知 usage 峰价上界 USD10.3702023；历史 7 Unknown 预约 USD0.3500316 完整保留。见[历史累计终态](../../experiments/m5-development/cost-ledger-including-conv44-relation-successor-terminal-v1.json)。新 Level E 另有独立账本，保守预约和 usage 上界均不是实际账单。

本轮未 push、PR、合并 main 或部署。未识别关联 Notion，未同步或标记完成。总任务仍需真实终态、评分、指标与来源审阅，并整理最终交付证据；不自动制作课程 ZIP/PDF 或冻结 Release。
