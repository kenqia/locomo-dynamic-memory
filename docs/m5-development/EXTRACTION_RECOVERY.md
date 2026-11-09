# 单片段抽取恢复

当前状态：用户已明确授权并执行本次恢复，3次均未通过校验；恢复目录已终结，禁止重复执行。下列步骤保留操作协议，不能视为新授权。该入口仅重试conv-44的ordinal 18，最多新增3次请求、预约上限USD0.2619648，并继续受原阶段18USD/204次全局限制。它不建立索引、关系、完整导出或执行QA，不放宽时间及来源校验。

## 准备与核查

在M5开发工作树运行以下命令。输出目录必须未存在。准备阶段只读取既有计划、配置及SQLite，不读取凭据，不发模型请求。

```sh
PYTHONPATH=tools/integration/offline_guard:src:. /home/kenqia/my_folder/locomo-dynamic-memory/.venv/bin/python -m tools.m5.extraction_recovery \
  --stage var/m5-development/holdout-extraction-proposal-final-v2 \
  --output var/m5-development/failed-fragment-recovery-v1
```

上面这个目录已准备，不要重复运行。`plan.json`记录原阶段计划和配置SHA、恢复脚本SHA、数据库及全局账本的逻辑快照。逻辑快照包含已提交的WAL内容，不依赖单个SQLite主文件哈希。原阶段只能有两份指定状态的Build，且只有目标片段失败、该片段没有已保存Memory。

核查证据在`experiments/m5-development/extraction-recovery-prepared.json`。已在真实快照验证：缺少授权时入口停止，Memory数据库和全局账本均不变，真实请求0。

## 授权后执行

先取得用户对上述恢复对象、次数、金额和范围的明确批准。现有18USD/204次抽取批准不自动扩展原片段三次尝试。脚本不会生成或推断授权。获批后才在恢复目录创建`authorization.json`，字段必须与下面模板完全一致；`plan_sha256`必须取该目录实际`plan.json`的SHA256。批准人负责保存聊天批准记录，文件匹配本身不证明用户已同意。

```json
{
  "approved": true,
  "scope": "retry one conv-44 extraction fragment; no index/relation/publish/QA",
  "build_id": "bef9f685957843698b3083ff4cbc79a4",
  "fragment_ordinal": 18,
  "max_additional_requests": 3,
  "max_additional_reserved_usd": "0.2619648",
  "plan_sha256": "REPLACE_WITH_ACTUAL_PLAN_SHA256"
}
```

获得明确批准并完成记录后，通过既有凭据launcher执行，禁止输出环境或凭据内容：

```sh
PYTHONPATH=src:. /home/kenqia/my_folder/locomo-dynamic-memory/.venv/bin/python scripts/with_deepseek_env.py -- \
  /home/kenqia/my_folder/locomo-dynamic-memory/.venv/bin/python -m tools.m5.extraction_recovery \
  --output var/m5-development/failed-fragment-recovery-v1 --execute-authorized
```

执行先检查原配置和生产契约，取得后端独占锁，再核对两份快照。独占`execution-started.json`标记阻止重复调用，包括中途崩溃后的自动恢复。入口复用`BuildService.retry/run`；其他成功片段不重建。恢复账本包裹原全局账本，两层均在HTTP之前预约。全局账本拒绝时本地可能已有保守预约；实际物理请求以原全局账本为准，不能将两个账本相加。

## 检查结果与失败处理

查看恢复目录的`outcome.json`。成功应为`extracted`，仍不等于完整Build；失败或Unknown保留，不自动再次运行。用新的输出路径重新执行`tools.m5.extraction_audit`核查全局请求和用量，禁止覆盖原75次审计。conv-44的Memory数变化后，用新路径重新运行`tools.m5.relation_preflight`，旧关系估计不再代表恢复后的快照。

如果启动前发现快照或配置变化，调查变化来源并重新准备；不得修改计划SHA绕过检查。启动后失败应保留执行标记、两个账本及诊断，不删除标记重跑。代码可通过后续revert提交撤回；SQLite与已发生请求不能通过代码回滚，禁止为回滚删除新增账本或真实计费记录。

## 离线验证

```sh
./tools/integration/check.sh tests/test_m5_extraction_recovery.py tests/test_m5_budget.py tests/test_builds.py -q
```

结果29 passed，覆盖单片段成功、三次失败、重复执行、授权缺失/不匹配、数据库/账本变化、全局金额耗尽和竞争后端。测试使用独立synthetic数据库及MockTransport，不证明实际模型能够修复原时间表达错误。隔离脚本副本禁用授权匹配后，对应测试失败；生产脚本未变，证据为`extraction-recovery-mutation.json`。


## 2026-11-04 单片段恢复授权与实际结果

用户在本聊天明确回复“接受恢复授权申请”，批准只恢复conv-44 ordinal18，最多新增3请求、预约上限USD0.2619648，仍受原18USD/204次全局账本约束。已绑定原计划SHA并执行一次；未index/relate/publish/QA，未读取留出答案或证据。

实际新增3请求全部返回usage，三次均在domain_validation以extraction_time_expression_required失败（memories[7]、[8]、[6]）。该规则要求time.original_expression逐字出现在其anchor原文中；不能将归一化或改写后的时间当原文表达接纳。没有网络Unknown，也没有放宽契约。conv-44仍33/34成功、383 Memory；conv-43仍34/34、402 Memory。原67成功片段及785条已接纳Memory逐行摘要前后完全一致。恢复入口已终结并保留一次性标记，不自动追加尝试。

本次保守预约USD0.1335684，按usage峰时cache-miss上界USD0.0091488；不是账户账单。累计78物理请求、保守预约USD3.4624767、usage峰价上界USD0.2265405，Unknown用量0；全局剩余容量USD14.5375233/126次不自动授权更多片段尝试或关系/QA。原75次审计保留，新件为live-extraction-post-recovery-v1.json和extraction-recovery-outcome-v1.json。最新恢复结果优先于较早“待授权”段落，旧记录保留过程历史。
