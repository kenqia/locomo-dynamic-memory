# Input v2 数值与审阅工件

本目录仅对应 `codex/m5-final-input-v2-20261104` 的新 Level C input v2 阶段：固定 80 普通题、20 诊断题，Hybrid/Dynamic 共 200 项，640,000 messages UTF-8 字节、192,000 resolution 正则代理 tokens，全部新生成 thinking disabled。四开发 Build 复用，Bonus 关闭，留出未评测。完整解释见 [本阶段结果](../../../docs/m5-development/LEVEL_C_INPUT_V2_RESULTS.md)。

`metrics-summary.json` 和 `per-question-metrics.json` 保存完整分母及成功子集，`failures.json` 保留唯一失败；原文、答案和 Gold 不在本目录。初始 `metrics-summary.json` 的语义状态为当时的 pending 快照，后续独立审阅另存，不改写它。`source-manifest.json` 绑定工具既有十个输入，包含准备时 `pricing-recheck.json`；执行前重新核对的 `pricing-before-execution-v1.*` 另由最终清单绑定，二者没有互相覆盖。

`sha256-manifest.json` 只覆盖初始四个结果工件，后续新增文件由新的终态清单覆盖。SHA 证明身份和完整性，不证明模型断言正确；AI 来源审阅也不等于教师或人工真值。

复现所需私有 stage 和 review 目录位于本工作树的 Git 忽略 `var/m5-development/`。仓库克隆不会自动取得这些数据。复现命令见 [reproducibility-commands.md](reproducibility-commands.md)，归档脚本只创建本地私有文件，不上传。所有已存在结果保持原件；数值重算应选择全新输出路径。
