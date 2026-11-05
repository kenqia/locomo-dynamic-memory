# 最终评测模型与思考设置

2026-11-04，用户在本聊天对“最终评测的模型 ID 或 thinking 模式”确认：

> DeepSeek V4.1-Flash-1017 ，然后不给开思考

将其作为本任务后续最终评测的明确要求：DeepSeek-V4.1-Flash-1017，所有新生成操作显式 thinking disabled，包括 extraction、relation、query analysis、resolution 和 answer。不得把 low 当作关闭。该依据为用户确认；已读取的课程 PDF 未独立写出精确 ID/thinking，不编造教师文件出处。

官方当日定价页将 API alias deepseek-flash 映射为该版本。已有421次QA响应仅返回alias，不能证明不可变版本pin；新阶段须重新核对官方映射、保存来源和实际响应model。如果服务只提供alias，报告该版本身份限制，不自行发明可请求的日期版ID。

## 已有实验的处理

- 历史四份开发Build和757题Run保持原件及完整模型血缘，继续遵守任务书复用要求；不因为新确认而未经授权重建或改写。
- 本次Level C为analysis/answer disabled、resolution low，200项已终结。它是真实开发诊断，**不是全链禁用thinking的最终成绩**；不得修改标签或把low写成disabled。
- 原批准的conv-43关系阶段为relation high，已按冻结计划完成400任务至related，根审计和非作者独立终态审计均通过，未修改其配置；它同样不作为全链禁用thinking的最终合规证明。
- 本次确认发生在现有阶段冻结/启动之后，且澄清问题明确现有阶段继续按已批准配置执行。不得据此清marker、重启、追加尝试或把既有费用授权挪给新的全关闭阶段。

后续若需要新的生成实验，先生成单独的全disabled计划、模型/Prompt/输入预算身份、请求/费用硬上界和独立ledger，再取得所需付费授权。最终留出评价仍须在候选锁定后一次执行；此确认不授权读取留出答案或发起新调用。
