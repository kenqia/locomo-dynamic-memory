## Sidecar 当前复审、真实诊断研究与交叉验收请求

关联#24、#30–#33、PR#38。远端HEAD3e0b217、merge-base4d1d072已按精确SHA复核；旧CHANGES_REQUESTED属于更早0f470a3，未用于推定当前仍有旧问题。

本轮重新得到159项专项通过，但两名非作者AI复审发现出生年/出席多来源矛盾被过滤、Memory时间与来源不一致、跨年省略年份和异常隔离等相邻问题。本地研究修复已版本化保留，最终174项专项通过；没有修改生产Build/Query、Prompt、模型默认或数据库。

只读核验conv-26与conv-30两个合法冻结真实Build：503条Memory、344来源、9200历史关系，SHA/Schema/Build/来源/时间锚点校验通过。完整执行63057候选对，无截断，所有claim/pair诊断仍unknown。502条Memory不在现规则句式内，1条无合格匹配来源。

冻结40条Memory、20对事件、8个研究问题，负责人授权的68项会话内非作者AI参考均完成；不是人工/教师真值。参考有5个时间和17对事件可判断，但Sidecar没有增加有信息正确输出，预先10%覆盖门槛失败。8个状态问题均输出insufficient，其中1项与带年份运算假设的AI参考不一致，另7项参考unknown；保留完整分母，不将unknown算高准确率。

V1与安全修复后的V2都保留，68项预测逐项一致；没有换样、重标或挑最好一次。V2阻止入口网络/SQLite尝试计数均0，外部费用0；没有付费QA、Answer、Resolve或Evaluation。Sidecar仍diagnostic_only，没有可辩护的回答干预，故不付费追求QA正结果。

采用建议：**拒绝当前真实Build/QA接入，默认关闭，仅保留离线诊断和开发回归**。这是研究建议，负责人ADR决定和最终验收仍待完成。

负责人指派@Thorns-06作为真实非作者复核人，复核本轮Sidecar（不要求xiaozhuozi39自验）。负责人已授权发布本安排，成员未确认、未执行、未通过。请独立目录无凭据复现专项与off/on/off，获得合法导出访问后只读复验两个Build；记录实际版本、环境、命令、案例、失败/unknown、卡点及结论。AI审查不能代替真人。

完整报告、协议、两个冻结版本、聚合结果、ADR建议和复现/交接均位于独立研究分支research/sidecar-20261107/；原始导出/来源和参考详情只受控保存，公开只提供哈希及聚合。原Issue/PR继续开放，不批准、不合并、不关闭、不提交课程材料。

公开离线回归：`tools/team_v2/check.py -q --tb=short`得到922 passed、8 deselected、1条依赖弃用warning（358.27s）；按既有入口排除3个依赖受限材料的模块、4个指定测试，以及live_model/local_embedding标记，不把排除项算通过。日志与JUnit保存在process/sidecar-20261107/full-public-offline.*。
