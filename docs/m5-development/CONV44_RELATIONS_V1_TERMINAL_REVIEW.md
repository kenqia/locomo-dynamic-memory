# conv-44 关系阶段 v1 失败终态独立复核

2026-11-05（北京时间）。**结论：失败终态的完整性独立复核通过；关系阶段未成功。** 目标Build为 `relations_failed`，384任务中374成功、10失败，保存6,973条合法关系，物理请求417。来源、Memory、片段、索引、其他Build和继承血缘保持冻结身份；失败任务没有被当成成功或自动追加尝试。Build未complete，第六份严格JSON尚未导出，Level E未执行。

复核者为非作者代理 `/root/final_actual_review`。真实进程终结并由根代理明确通知后，复核者才读取终态。复核工作树为 `/home/kenqia/my_folder/locomo-worktrees/m5-final-conv44-relations-20261104`，目标Build为 `d9fb61417bb740e4b8eb34acb8652a46`，stage为 `var/m5-development/conv44-relations-v1`。本次没有运行真实prepare/live、创建新授权或修改producer文件。

结果保存在[独立终态JSON](../../experiments/m5-development/conv44-relations-independent-terminal-v1.json)，SHA-256为 `86a648f7c4b61990ecee86ce6cad66c547d178c74edee243159bfffb60ad4fa6`，审计时间为 `2026-11-04T16:23:10.712291+00:00`。该结果的 `passed_failed_terminal_not_complete` 表示失败状态与账本、诊断和保护记录一致，不表示关系质量或完整构建通过。

## 方法与检查范围

独立脚本位于 `/tmp/conv44_independent_terminal_audit.py`，通过只读SQLite连接、`query_only=ON` 和读事务检查已终结数据。沿用[独立准备复核](CONV44_RELATIONS_V1_PREPARATION_REVIEW.md)的保护范围，将终态检查归为下列7组。脚本只输出安全计数与摘要，断言全部通过后独占创建新JSON；不覆盖准备工件。

实际执行命令为：

```sh
env -u DEEPSEEK_API_KEY -u OPENAI_API_KEY -u CODEX_ACCESS_TOKEN \
  HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
  PYTHONPATH=tools/integration/offline_guard:src:. \
  /home/kenqia/my_folder/locomo-dynamic-memory/.venv/bin/python \
  /tmp/conv44_independent_terminal_audit.py \
  --output experiments/m5-development/conv44-relations-independent-terminal-v1.json
```

| 检查组 | 独立验证结果 |
| --- | --- |
| 1. 精确授权与冻结身份 | 实际plan与准备时SHA一致；批准文件精确匹配目标、scope、policy与plan，单次marker身份相同，原未批准模板保留。85个producer、工具SHA、settings和inheritance均与冻结计划一致；所有新生成thinking disabled。 |
| 2. 来源、索引与原记录保护 | 源抽取database/ledger/plan/settings/inheritance和index-summary及索引库逻辑摘要保持不变。逐行比较index副本与终态基础表、索引表和其他Build；仅允许目标Build阶段状态及新关系metadata变化。抽取call前缀和混合producer继承记录完整保留，schema与保护摘要一致，外键无失败。 |
| 3. 向量与任务选择 | 392条384维向量全部finite且归一化；与原索引记录完全相同。重新按原production排序和 `select_history` 计算任务，384个完整任务身份与selection逐项相等；仍为7,134比较、28,644省略历史比较。 |
| 4. 任务、attempt与provider闭环 | 384任务均为succeeded或failed，各有一次已关闭logical attempt。task与attempt的状态、error及时间相符；provider序号连续且每任务最多3次，SQL身份与metadata六个身份字段一致。所有417个provider记录均有终态，task metadata与有序provider calls相同，Build metadata等于冻结抽取前缀加完整新calls，返回model集合一致。Build与phase均为失败终态，Prompt/schema身份保持冻结。 |
| 5. 全部关系与投影边界 | 对6,973条关系逐条运行当前 `MemoryRelation` schema及endpoint/source上下文验证，核SQL字段、确定性relation ID、Build/对话/实体范围和双方证据。成功任务恰好覆盖全部既定历史端点；失败任务没有持久化关系。存在失败任务时投影为0，未构造可供complete使用的投影。 |
| 6. 独立物理账本与费用 | 417行ledger与有序provider calls逐项对应，usage与receipt状态一致，policy精确匹配批准计划。逐预约金额落在policy范围内，并可反推为含完整输出预约及合法整数字节数的金额；此检查未捕获或重拼实际wire messages。总额与usage、Unknown及原outcome全部重新计算并相等。 |
| 7. 单次门禁与最终不变性 | 向真实执行入口注入MockTransport后，已存在marker立即拒绝再次执行，Mock调用0。终态database、ledger、marker、outcome及所有冻结文件摘要均未改变；来源和索引再次核对不变。stage/index目录0700，现存私有文件0600。无active/publish、query或评测表，candidate_queries为空。 |

补充只读SQL计数独立确认：34个片段成功、392 Memory引用281个Source，投影0。10个失败任务的末次安全诊断计数为8项 `known_source_required`、2项 `same_state_dimension_required`；没有输出错误响应正文或来源内容。

## 实际结果与费用

下表记录本阶段结果；schema与来源校验不能替代关系语义准确率。

| 项目 | 独立结果 |
| --- | --- |
| Build / phase | `relations_failed` / `relations`；relation phase为failed |
| 任务 | 374 succeeded、10 failed，无pending/running |
| 已保存关系 | 6,973；失败任务对应的161次比较未形成持久化关系 |
| 关系标签 | undetermined 6,769；RETAIN 106；UPDATE 91；SUPERSEDE 5；CONFLICT 2 |
| Logical attempts / provider calls | 384 / 417；全部关闭 |
| Call outcomes | succeeded 374；invalid_output 43 |
| Ledger receipt状态 | response_received 417；Unknown usage 0 |
| 输入 / 输出 / 总reported tokens | 4,154,084 / 945,401 / 5,099,485 |
| 保守预约 | USD20.5545036 |
| 已知usage峰价上界 | USD2.3807064；不是账户账单 |
| Unknown预约 | USD0 |
| 请求与返回model | `deepseek-flash`；可变alias，不是不可变服务端版本pin |
| 新call设置 | 全部 `thinking={"type":"disabled"}`，不发送reasoning_effort，32768输出tokens |

## 终态身份与交叉核对

独立结果与[根代理公共终态](../../experiments/m5-development/conv44-relations-terminal-v1.json)的15个身份、计数与费用字段相等；根代理工件有20项checks为true，其SHA-256为 `ece3ef725c0bd56679809280fd9c764ed64d14197a0898cc16e5d151893ee79d`。两者使用独立检查路径；本报告不把根代理的20项计为独立脚本的7组检查。

| 身份 | SHA-256 |
| --- | --- |
| 精确plan | `0920823b2c04d5d632df481df24ca60348b182fc760da8bb3a28f02cc5eb94cf` |
| 批准文件 | `e9b398234690427cf970f4745595522e53e37f99291c4bbab891c2bc8302cfdb` |
| 单次marker | `860fa22efe9b4f9f7efd3cb3b03e955a8ba5c0e07bddafc1560fd63267e677f9` |
| outcome | `69b09a6b01aca5b43d3aa140e3a1e522c4a31fcae88ee869e98b47cdedb51e3c` |
| 最终database逻辑快照 | `bf747f0dba9575cf7c3d98328cfa550eab80d9b32a6304d6c9bc68553dde7f8a` |
| 最终ledger逻辑快照 | `aa3fedecccb9d5f292665c44f534d26cd359732e98e35fbccff6d571d0c9bd0a` |
| 原索引database逻辑快照 | `0663f0548e5be21a4cef1d468e47d26d00210fd430293c99eec1bb12d99a1f3f` |
| 原抽取database逻辑快照 | `07ce1ee6d2a32c9b4c310e520c328134fea00cb7fc041776425770e618034e79` |
| 原抽取ledger逻辑快照 | `ece4a12e1128428da2aaee99fadf13272457fa1fb4e7df8c01a527b37bcfddf0` |

## 未验证项与下一步边界

本次没有审阅或输出conversation正文，没有读取raw provider日志、私有stdout、凭据或留出QA/evidence/answers。自动schema校验只在内存中核对来源子串与endpoint约束；未做关系语义准确率或Memory事实语义复审。未重新加载encoder或编码向量，未重拼wire messages，未读取实际账单。复核者新增live请求0。

当前没有可验证的成功投影，因此没有宣称projection全量重算通过。第六份complete Build与严格导出仍blocked。现有一次性入口已封闭，原预算余量不授权恢复；任何新恢复必须保留本终态、原logical attempt及账本，另建明确失败范围、独立预算、计划与授权。恢复工具的代码审查不替代真实准备与付费批准。
