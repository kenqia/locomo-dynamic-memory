# conv-44 关系恢复 v1 实际准备独立复核

2026-11-05。**结论：实际恢复准备工件的6组独立检查全部通过，可将精确恢复计划和预算提交用户审批。新阶段尚未获得付费授权，真实provider请求为0。** 仅原10个失败任务恢复为pending，覆盖原161次比较；374个成功任务及全部旧关系、attempt和provider记录保留。Build仍为queued/relations，不是complete。

复核者为非作者代理 `/root/final_actual_review`。工作树为 `/home/kenqia/my_folder/locomo-worktrees/m5-final-conv44-relations-20261104`，恢复实现本地提交为 `443d16b67c15af57867c67a13a4e227bec34eb3f`。本复核没有修改实现、原85个producer文件、core、配置或既有报告，没有重新prepare，没有创建授权或执行marker，也没有运行live请求。

安全计数和摘要保存在[独立准备检查JSON](../../experiments/m5-development/conv44-relation-recovery-independent-preparation-v1.json)，SHA-256为 `18a366ad8eabc029f1a4fc633cab13dd5ce92bc5765074d4f9e9be7f399ab10f`。[恢复代码独立复核](CONV44_RELATION_RECOVERY_V1_REVIEW.md)保留历史验证结果；本次未重跑已通过的39项测试，该测试结果属于根代理此前的验证。

## 方法与安全边界

一次性脚本为 `/tmp/conv44_recovery_independent_preparation_audit.py`，SHA-256为 `7154c58f6fc0a0cf86d0d5a728f76920e69171bd5806a8df7e8a492bd6c7258b`。实际执行命令：

```sh
env -u DEEPSEEK_API_KEY -u OPENAI_API_KEY -u CODEX_ACCESS_TOKEN \
  HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
  PYTHONPATH=tools/integration/offline_guard:src:. \
  /home/kenqia/my_folder/locomo-dynamic-memory/.venv/bin/python \
  /tmp/conv44_recovery_independent_preparation_audit.py
```

所有独立SQLite检查连接均使用 `mode=ro`、`query_only=ON` 和读事务。检查先拒绝白名单以外的表及非空评测annotations，再读取允许的记录。独立逻辑快照包括已提交WAL；逐行比较包含rowid。脚本只输出静态检查结果、计数及摘要，不输出Memory、SourceTurn、关系正文或calls私有metadata。全部断言通过后，脚本以独占创建方式新增公共JSON。

检查未读取凭据、raw provider日志、私有stdout、Gold或留出QA/evidence/answers。Memory和SourceTurn仅在内存中用于保留比较及endpoint映射检查，没有人工审阅或输出conversation正文。完整endpoint包装使用内存Capture模型；缺少授权检查向真实 `execute` 入口注入MockTransport，要求调用次数为0。

## 独立检查结果

| 检查组 | 结果 |
| --- | --- |
| 1. 范围、schema与producer | 新旧数据库均为精确17表白名单，candidate_queries为空，评测annotations仅sample_id或null，外键检查通过。87文件manifest逐文件核SHA，其中原85文件与冻结源计划完全一致；只增加恢复wrapper和既有complete-export helper。settings、inheritance与原失败阶段逐字节身份一致。明确记录额外输入契约、混合关系producer及未将额外wire契约纳入Build fingerprint。 |
| 2. 源终态、索引和抽取冻结 | 原公共终态与原独立终态SHA保持冻结，两者database/ledger身份与源实际逻辑快照相同。原授权、marker、outcome和计划配置未变；index-summary与索引数据库、原抽取来源身份一致。production parent检查作为附加检查通过，不替代独立快照和逐行比较。 |
| 3. 全部旧记录与精确重排 | 基础、索引、Memory、SourceTurn及其他Build保留。目标Build只改变允许的status/phase/updated_at，完整配置与418条历史metadata calls未变。374个成功task逐行相等；10个失败task精确等于原记录加status=pending、error_code=null，attempts仍为1，旧metadata仍保留。384个旧logical1、417个旧provider和6973条旧关系逐行相等，无logical2、投影仍0。全部384任务不可变字段摘要保持原值；10任务覆盖161次比较，总任务仍7134次比较。 |
| 4. Endpoint映射和反馈 | 对10个任务分别在内存调用实际EndpointModel。完整endpoint_source_ids与各Memory.source_ids精确一致，来源均属于conv-44且位于对应context；原new/history/context未改变。末次错误为8个known_source_required、2个same_state_dimension_required，反馈error/path经过既定白名单，指导保留allowed_labels、相同state_key限制及证据不足时undetermined。observer附加精确输入契约和wrapper SHA。未调用provider或拼装wire messages。 |
| 5. 新账本、预算和权限 | 新ledger仅policy/physical_requests两表，policy与独立常量及计划完全相等，请求为0。上限30物理请求、每次160000输入字节和32768输出tokens，单次预约上限USD0.0873216，总上限USD2.6196480。原417次provider记录属于历史保留，不计入新ledger。模板approved=false；无新authorization、execution-started或outcome。阶段目录0700、现存私有文件0600。 |
| 6. 缺授权入口与末尾不变性 | 真实execute入口因authorization.json不存在而拒绝，Mock dispatch为0，没有创建marker或outcome。新DB/ledger及计划、模板、settings、inheritance前后不变；原源、索引、抽取来源和公共终态身份也保持冻结。 |

## 冻结身份

明确Build为 `d9fb61417bb740e4b8eb34acb8652a46`。新阶段为 `var/m5-development/conv44-relation-recovery-v1`；原失败阶段为 `var/m5-development/conv44-relations-v1`。

| 工件或逻辑身份 | SHA-256 |
| --- | --- |
| 新恢复plan | `82251c43a541f86a089dd649337930c501dcb00717debeb6786651f04b93529b` |
| 新准备database | `2bc56f58a71190cff3f38d673f7ee75b4d1d757fed36281ed13a3762faacf342` |
| 新准备ledger | `d01a6912ee839883aa7c90cda49453260ddd1d0163033a9251cf064b527d6bae` |
| 原失败database | `bf747f0dba9575cf7c3d98328cfa550eab80d9b32a6304d6c9bc68553dde7f8a` |
| 原失败ledger | `aa3fedecccb9d5f292665c44f534d26cd359732e98e35fbccff6d571d0c9bd0a` |
| 原公共终态 | `ece3ef725c0bd56679809280fd9c764ed64d14197a0898cc16e5d151893ee79d` |
| 原独立终态 | `86a648f7c4b61990ecee86ce6cad66c547d178c74edee243159bfffb60ad4fa6` |
| 完整原任务身份 | `4deafd6608923998538cffc0c04183fc62ef301b92422d9c573a3696443d6d7a` |
| settings | `3e2bd434a1c75f263a35dd5f28be50d858ff8047e0e540390a68b8fce0eafe28` |
| inheritance | `b5e312b5c54bde04f57c1d6961e6dd108a1c9594c6a6ffa8526b0ce2969cdf1e` |
| 恢复工具 | `77cc554f9ebc94c70cb2f0f1e4674aeffdd3b659efaf997dcc5740371ac5120a` |
| 恢复tests | `18c803c1441a9be2bd3df58c76fb29eedd37e0e9d5d8d4f2f44f0825fa01412d` |

## 根审计交叉核对与限制

另已读取[根代理准备检查JSON](../../experiments/m5-development/conv44-relation-recovery-preparation-v1.json)，SHA-256为 `74492b8478f9a8c0ff563fafd7df21948ee0a65505432154d0a794fb7a863db0`。其13项检查全部通过；与本报告JSON的11个公共身份、状态、预算和范围字段相等。根代理报告在真实adapter的内存Mock中重建初次及length反馈路径，30次synthetic dispatch、最大40058字节；这些不是新增真实请求，也不是本复核者执行的检查。该结果只覆盖这些路径，不代表所有反馈路径均已重建。

本复核没有重新加载encoder、重编码向量或拼装wire messages，未独立重算输入字节极值。没有审阅Memory或关系的事实语义，不保证恢复成功率、关系质量或剩余任务一定能通过。没有创建新关系、投影、完整Build、第六份严格导出，也没有启动Level E。

后续付费执行仍须用户明确批准上述精确plan和独立预算。本报告不创建或替代授权。执行结束后仍需终态审计；只有恢复达到related并通过冻结检查后，才能在另一新副本complete/pin/export，不能修改原失败阶段或当前恢复阶段以冒称完成。
