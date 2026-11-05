# Level C input v2 执行记录

2026-11-04。用户明确批准的独立 1,500 次物理请求／USD346.9824 阶段已完成生成、200 项完整冻结、终态审计、开发 Gold 评分、200 项独立 AI 来源审阅及本地私有归档。199 项成功、1 项 `invalid_output`，输入上限失败为零；失败保留，不补跑。数值与语义限制见[本阶段结果](LEVEL_C_INPUT_V2_RESULTS.md)；总任务仍有未完成项。

工作树为 `/home/kenqia/my_folder/locomo-worktrees/m5-final-input-v2-20261104`，分支 `codex/m5-final-input-v2-20261104`。实现提交 `b3ba45c`、准备身份提交 `4aadaff`、明确授权提交 `2a3cd85`。本阶段范围和冻结身份见[独立运行清单](../../experiments/m5-development/level-c-input-v2-run-manifest-v1.json)，精确授权见[批准记录](../../experiments/m5-development/level-c-input-v2-authorization-v1.json)。本树根目录其他历史实验清单和旧 Level C 结果保留原观察时点，不能当成本阶段当前成绩。原关系阶段与旧 QA 仍由原工作树审计，不在这里重跑。

本次固定既有 80 普通题、20 诊断题，Hybrid／Dynamic 共 200 项；四开发 Build 原样复用，Bonus 关闭，不恢复 conv-44，不读取留出 QA/evidence/answers。所有新生成请求显式 `thinking={"type":"disabled"}`，不发送 `reasoning_effort`；640,000 messages UTF-8 字节上限、192,000 完整 resolution 代理 tokens、32,768 最大输出 tokens、每操作最多 3 次尝试。历史 Build 的模型和 thinking 血缘不改写，本阶段没有 extraction/relation 调用。

执行前重新读取官方定价页，确认 alias `deepseek-flash` 映射 `DeepSeek-V4.1-Flash-1017`，峰时每百万 cache-miss 输入 USD0.30、输出 USD1.20，与批准上限匹配。新价格原件为 stage 内 `pricing-before-execution-v1.md/.json`，绑定在授权记录的 pricing 字段；原 `pricing-recheck.*` 保持准备时点原件。官方 alias 不能证明不可变服务端 pin，实际返回 model 另记录。

启动前核对 plan、全部 producer SHA、独立数据库／空账本快照、参考源 main／WAL 身份均一致；100 个问题实际通过本地 pinned MiniLM 100×384 编码检查，无 Provider 请求。52 项既有 v2 定向测试和独立 24 项子集复核已完成，详见[准备记录](LEVEL_C_INPUT_V2_PREPARATION.md)及[独立复核](LEVEL_C_INPUT_V2_REVIEW_V1.md)。

全部 200 项生成冻结后，先运行终态完整性审计，再执行独立开发 Gold 评分。结果使用完整分母，普通／诊断分开；后续在独立新目录生成匿名来源审阅 packet，绑定本次 freeze，不复用旧 labels。AI 来源审阅和官方字面 F1 分开报告，不冒称教师或人工真值；新旧 thinking 与输入预算均变化，只能作探索性比较。

费用区分保守预约、已报告 usage 的峰价上界及实际账单。Unknown 保留全预约，各阶段额度不转移；实际账单未读取。新阶段不授权 Level D/E、发布或远端写入。未识别关联 Notion 记录，本次未同步，也未标记总任务完成。
