# Issue #15 真实运行记录

2026-10-20。用户已确认在受保护的本机文件填入凭据。凭据仅载入独立进程环境，不进入仓库、命令参数、输出或实验导出。远端写操作未执行。

## 已通过的检查

在 integration `db70cf0` 上运行既有小型真实抽取检查：

```sh
LOCOMO_LIVE_MODEL=1 .venv/bin/python -m pytest tests/test_live_model.py -q --tb=short
```

结果为 1 passed，耗时 1.97 秒。测试通过公开 FastAPI 创建真实 DeepSeek 抽取 Build，检查 Memory 非空，并逐个读取其来源引用。该结果只证明小型抽取与来源读取可用，不证明官方对话构建或 QA 预检完成。

独立实验目录为 `/home/kenqia/my_folder/locomo-worktrees/real-baseline-issue15`，数据库为该目录下的 `memory.sqlite3`。通过 `experiment prepare` 保存了固定原件、smoke 计划和完整开发计划。计划分别包含 5 题、20 个组合，以及 757 题、3,028 个组合。

`experiment verify` 使用真实本地 MiniLM，通过固定 revision 加载、384 维有限归一化编码与超长输入拒绝检查。对应 revision 为 `c9745ed1d9f207416be6d2e6f8de32d1f16199bf`，长度政策为拒绝，设备为 CPU。机器记录位于实验目录的 `verified-preflight.json`。

## 固定实现的真实构建

恢复修复合入 `6a2918383aa10c906a2e3d350a9ccb495fe7bd1f` 后，真实 runner probe 通过。实现 SHA-256 为 `543cb6e3f768c60a8dff1cec56437e3d5d87ac0cd77a3aa560ccc8cb6c9bb40a`；之后的提交仅增加实验文档。实际请求与返回模型均为 `deepseek-flash`，请求关闭思考、温度为 0、输出上限 4,096 tokens、每次调用最多重试两次。

probe Build 为 `41cbe0b907ee4d7c983f3b24082d970f`，三个来源引用均可读取。完整 `conv-26` Build 为 `91f1f50938064972820e3ab7b390d9dd`。首次抽取完成 20/21 个片段，序号 3 的片段在三次模型调用后返回 `invalid_output`。首次失败快照位于实验目录的 `observations/conv-26-first-extraction-failure/`，保留完整 Build 和片段记录。

使用相同配置显式恢复失败片段一次后，21/21 个片段全部成功，得到 295 条 Memory；已成功片段没有重跑。真实 MiniLM 索引通过。关系阶段生成 292 个持久任务，其中 29 项在有限重试后仍为 `invalid_output`，阻止完整版本发布。继续处理待执行项不会自动修复已失败项，因此停止本轮付费构建，保留冻结配置和断点，没有重新提交失败关系任务。

后端收到正常停止信号后仍在等待后台构建；等待 8 秒后终止该独立进程，再以不含凭据的进程重启，仅通过公开 API 恢复状态和导出。最终关系状态为 89 成功、29 失败、1 中断、173 待执行。中断任务为 `91f1f50938064972820e3ab7b390d9dd:relation:120`，其本次逻辑尝试最多三次提供方调用可能缺少已持久化的结果与用量，不能当作已知零，也不能保证未计费。未自动重试该任务。

所有已提交结果仍可读取，数据库保留原件、计划、构建、索引、Memory、关系、阶段任务及模型元数据。最新任务导出为 `builds/91f1f50938064972820e3ab7b390d9dd/relation-tasks.json`，停止前快照及停止记录位于 `observations/stopped-after-relation-failures/`，阶段观察时间线为 `observations/relations-progress.jsonl`。这些观察时间包含操作等待，不能代替纯计算耗时。

完整 `conv-26` Build 已持久记录 220 次提供方调用，已报告输入 1,592,801 tokens、输出 689,406 tokens、总计 2,282,207 tokens。成功与无效输出各 110 次，失败和内部重试没有从用量中剔除。runner probe 另有一次调用，共 1,654 tokens。独立 opt-in 测试另有一次成功调用，但本报告未保留其用量。中断任务未持久化的用量另列未知，因此这些数字不是完整账单或金额估计。机器摘要见[真实运行结果](issue-15-live-outcome.json)。

初次只读诊断无法证明具体失败规则，见[关系失败诊断](issue-15-relation-failure-diagnosis.md)。随后针对已失败的序号 2 任务进行一次独立诊断回放，复用相同 Prompt、JSON schema、来源、Memory 及生成参数，只将适配器重试次数设为零，以限定为一次提供方调用。该回放不写入原 Build 或改变原失败任务状态，只通过代理校验器记录白名单中的错误规则、字段位置及类型，不保存响应原文。

回放确认 `judgments[0]` 违反 `This judgment requires the same state dimension`。同一实体的两条 Memory 分别为 `support_group_attendance` 和 `emotional_response`，两端 `state_key` 不同，模型却输出了要求同维度的关系判断。因此该案例确认为输出未符合既有关系契约，不是凭据缺失或输出 token 达到上限。它不能证明其余 28 项失败具有同一原因，也不能确认具体是 RETAIN、SUPERSEDE 或 CONFLICT；未保留模型原文供事后猜测。回放调用返回 `deepseek-flash`，已报告 1,782 输入、266 输出、2,048 总 tokens，耗时 1.34 秒。安全记录见[独立诊断回放](issue-15-relation-diagnostic-replay.json)。

没有据此改 Prompt、schema、分段、生成参数或校验约束，也没有将回放结果覆盖原任务或重新计分。

后续完成了[全部失败任务的零模型调用诊断](issue-15-offline-relation-diagnosis/README.md)，核对数据库及任务导出的 29 个失败任务、87 次原始提供方尝试和 490 个输入候选对。原始 29 项均缺少具体规则与字段路径，根因子类仍未知。上述独立回放只确认该次回放的违规，不能反推原任务三次尝试的具体错误，也不计入原始 29 项的归因统计。

## 当前边界

五题 QA smoke 未启动，757 题全量入口仍受真实 smoke 门槛约束。没有生成 `conv-43`、`conv-44` 的模型成绩。#20 和 #21 的入口代码已实现，但真实实验未完成。本次保留失败基线，不通过调整参数、放宽约束或生成伪真值补齐结果。

GitHub Issue 和 Notion 未执行写操作；尚未找到明确关联 Issue #15 的 Notion 任务记录，不宣称已同步或已验收。
