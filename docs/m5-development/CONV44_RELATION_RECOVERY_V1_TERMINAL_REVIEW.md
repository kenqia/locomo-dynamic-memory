# conv-44 关系恢复 v1 实际终态独立复核

2026-11-05。**结论：恢复阶段的6组独立终态检查全部通过，确认其为保留完整历史的失败终态。** 用户批准的恢复进程已以exit 1结束，383个任务成功、1个失败，共保存7114条合法关系。本轮新增141条关系；剩余任务的20次比较未持久化。Build仍为relations_failed/relations，不能执行第六份complete严格导出，也未启动Level E。

复核者为非作者代理 `/root/final_actual_review`。工作树为 `/home/kenqia/my_folder/locomo-worktrees/m5-final-conv44-relations-20261104`，实现本地提交为 `443d16b67c15af57867c67a13a4e227bec34eb3f`。审计脚本先免费准备并通过AST检查；根代理明确通知真实进程结束且公共终态就绪后，复核者才读取阶段数据库并执行脚本。没有重试真实调用、修改实现或既有审阅文件。

安全结果保存在[独立终态JSON](../../experiments/m5-development/conv44-relation-recovery-independent-terminal-v1.json)，SHA-256为 `8a2daa79aa81551577a1039f323843fa1bd5d1886dc086300ca5b962dc82a6ea`。[准备复核报告](CONV44_RELATION_RECOVERY_V1_PREPARATION_REVIEW.md)继续保留执行前快照，不因本报告更新。

## 方法与验证范围

实际执行命令如下。一次性脚本SHA-256为 `9632b46dbb2fe56a54a9f8bcc2ca77a2be83930be749d6258d47dc287ade8ceb`。

```sh
env -u DEEPSEEK_API_KEY -u OPENAI_API_KEY -u CODEX_ACCESS_TOKEN \
  HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
  PYTHONPATH=tools/integration/offline_guard:src:. \
  /home/kenqia/my_folder/locomo-dynamic-memory/.venv/bin/python \
  /tmp/conv44_recovery_independent_terminal_audit.py \
  --root-confirmed-process-terminated \
  --output experiments/m5-development/conv44-relation-recovery-independent-terminal-v1.json
```

独立SQLite连接使用mode=ro、query_only和读事务，先检查精确17表白名单、空candidate_queries及无评测annotations，再读取记录或计算逻辑快照。快照包括已提交WAL；旧表、旧attempt、provider与关系比较包含rowid。脚本独立核算新logical2及新账本，没有调用只接受logical1的原terminal_calls。production audit仅作为结果交叉核验。

Memory、关系和SourceTurn仅在内存中用于保留比较、严格schema和来源子串校验，没有人工审阅或输出正文。未读取凭据、raw provider日志、私有stdout/stderr、Gold或留出QA/evidence/answers。审计只输出安全数值和摘要，并独占创建新公共JSON；无数据库写入或新增live请求。

| 独立检查组 | 结果 |
| --- | --- |
| 1. 精确授权与冻结身份 | plan SHA、87文件producer manifest、工具和tests、settings、inheritance均匹配准备身份。授权精确绑定新plan与30请求/USD2.6196480预算，marker匹配该plan。原失败阶段DB/ledger/plan/配置及公共终态未变。 |
| 2. 原事实和历史保留 | 全部基础及索引记录、其他Build和目标配置保留。374个原成功task逐行不变；384条旧logical1、417条旧provider和6973条旧关系逐行不变。原418条metadata calls前缀完整。任务选择摘要与原7134次比较保持冻结，重试范围仍为10任务/161比较。 |
| 3. 新logical2与调用闭环 | 恰好10个新logical2，每个仅属于获授权失败task；task attempts=2，时间、状态和错误闭合。新增12条provider记录与task metadata、新Build calls后缀及新ledger逐项一致，无额外logical attempt或越界task。9次成功响应、3次invalid_output。 |
| 4. 全部关系严格校验与覆盖 | 7114条关系均通过MemoryRelation严格上下文校验、确定relation ID、端点与conv-44来源验证。每个成功task精确覆盖其全部history，失败task没有关系落盘。新141条仅属于获授权成功恢复任务：137 undetermined、4 UPDATE。失败态projection仍0；related投影重算分支未执行，不能宣称已核得成功态投影。 |
| 5. 独立账本与预约 | 新ledger policy精确一致，12条response_received与新调用顺序和usage一致。每条预约均包含完整32768输出tokens，反推输入字节为1至160000范围内整数；预约总额USD0.5913375，低于USD2.6196480。Unknown为0，已知usage峰值上界USD0.0664212。核算不包含原417次provider历史。 |
| 6. 公共终态与重复入口 | 根代理公共终态的10项检查全true，状态、身份、DB/ledger快照及完整outcome与独立结果一致。重复真实execute入口因既有marker拒绝，Mock dispatch为0；前后新DB/ledger、授权、marker、outcome以及原源身份均不变。私有目录0700、文件0600。 |

本轮报告tokens为prompt 121592、completion 24953、total 146545。总关系标签为undetermined 6906、UPDATE 95、RETAIN 106、SUPERSEDE 5、CONFLICT 2。新请求和响应model均记录为deepseek-flash，但该服务别名不是不可变权重pin。所有新调用均显式thinking disabled，无reasoning_effort。

## 安全失败诊断

按根代理要求新增私有 `var/m5-development/conv44-relation-recovery-v1/failed-safe-diagnostics.json`，权限0600，SHA-256为 `8bbdf97dfc50bdf18e3eab7bd62be80b985b68d8e8b14e6a29c65e46727f9daa`。该文件只包含允许公开的code/path、task身份、类型及候选标签聚合，不含正文或raw response。保存诊断前后DB/ledger身份相等，根代理可将其与计划、终态及账本一同归档。

唯一失败task为ordinal 163，ID为 `d9fb61417bb740e4b8eb34acb8652a46:relation:163`，包含20次比较；task最终错误为invalid_output。原logical1与新logical2各3次provider诊断均为 `same_state_dimension_required`，field_path均为 `judgments[1]`。该下标属于模型响应，不能据此断定具体history候选。

新Memory类型为event/plan。使用现有relation_label_error重算前置允许标签，得到以下聚合；这些标签仍需通过完整证据和阶段校验，不保证都能成立。

| 候选数量 | 与new同state_key | old类型/陈述性质 | 前置允许标签 |
| --- | --- | --- | --- |
| 15 | 否 | 13 state/fact、2 event/fact | undetermined |
| 4 | 否 | event/plan | UPDATE、undetermined |
| 1 | 是 | event/intention | RETAIN、UPDATE、CONFLICT、undetermined |

免费最小修复建议：在各candidate身份旁显式呈现允许labels，对只能undetermined的候选加强直接约束，并用合成跨state fact→plan案例验证输入指导和严格校验。保持端点、候选选择、UPDATE证据及validator不变。不能强改旧响应标签或自动制造关系，也不能仅凭上述结构诊断保证新提示有效。安全诊断已发送实现代理；本复核未实施修改，未授权或执行下一轮付费重试。

## 冻结身份与边界

| 工件 | SHA-256 |
| --- | --- |
| 恢复plan | `82251c43a541f86a089dd649337930c501dcb00717debeb6786651f04b93529b` |
| 新授权 | `b45a5685e984522c90f0d80924f654ff498cf481bfd72ca4dcd24a88becb0d80` |
| 新execution marker | `6d3d35c03aa9b2f564b2f4073de090d118894a34fd2add2913dd27d15a1b5756` |
| 新outcome | `6272ba9dc884844bfebaaea1d688b39d60161f74fc9d1282cba60b87f1a6fef9` |
| 新database逻辑快照 | `aa2f5984709a3702e9e9de0a4c651b14b0c9f0fb61feb007a841a4de21f5b9ca` |
| 新ledger逻辑快照 | `bd2244d24c7b876f135940f17dc452e79b677c7781bf0aa2ff78dda8e18a02cf` |
| 根公共终态 | `c6d816a97c3f4a44743f977f9a5f2ad4223eccb72b624c5accb9994b7fcba8be` |

根代理的[公共终态JSON](../../experiments/m5-development/conv44-relation-recovery-terminal-v1.json)与独立6组检查是两套验证范围，不混计。审计未重跑39项测试、重编码向量或重拼wire messages；未评估关系语义准确率和QA质量，未访问实际账单。usage峰值上界不等同于实际账单。

当前恢复阶段保持失败终态，原失败阶段及本轮历史冻结保留。不得把剩余预算自动转移给下一轮，不得覆盖本轮结果。后续如需logical3，应另行完成可审核的准备、独立验证及明确授权；只有全部关系完成并通过终态审计后，才能在另一个新副本complete/pin/export。六份完整Build、最终配置冻结与Level E仍未完成。
