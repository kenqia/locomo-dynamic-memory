# 独立定位少量历史关系失败

使用 `locomo_memory.relation_replay` 从停止的旧数据库重建固定输入，并在独立目录记录诊断。
工具只调用现有 `DeepSeekModel.generate`；不启动后端，不复制旧库，不创建或修改原 Build，
也不重跑抽取、Embedding 或 QA。真实调用前必须先确认总调用预算和本地凭据注入方式。

## 准备离线计划

先停止源数据库的后端，确认没有未合并 WAL。准备新目录，运行：

```sh
cd /home/kenqia/my_folder/locomo-worktrees/issue15
.venv/bin/python -m locomo_memory.relation_replay prepare \
  --source-database /home/kenqia/my_folder/locomo-worktrees/real-baseline-issue15/memory.sqlite3 \
  --build-id 91f1f50938064972820e3ab7b390d9dd \
  --ordinals 2 44 90 \
  --directory /absolute/path/to/new-isolated-directory
```

源库以 `mode=ro&immutable=1` 和 `PRAGMA query_only=ON` 读取，读取期间持有共享非阻塞运行锁。
非空 WAL、源后端占锁、输出位于源目录或目录已经存在时，准备会停止。
`plan.json` 固定原任务身份、完整候选顺序、输入和请求 hash、输入规模估计、生成配置及实现身份。
它只保存 ID、hash 和配置，不复制 Memory 或来源文本。

准备过程仅通过 `MockTransport` 捕获请求 hash 和本地输入估计，真实调用数为零。
`plan.status=awaiting_budget_approval` 和 `proposed_call_limit` 均不表示已经获准付费调用。
`model_retries=0` 仅用于此次独立定位，区别于旧 Build 的 `model_retries=2`；
其他模型参数保持源构建配置。生产配置和原 Build 不变。

## 获准后执行修改前定位

通过既有安全方式为执行进程注入 `DEEPSEEK_API_KEY`，不要把密钥写入计划、仓库或聊天。
准备命令无需凭据；缺少凭据时运行命令不会发出请求，也不会占用调用次数。

以下命令只在用户明确确认最多 6 次调用后使用：

```sh
.venv/bin/python -m locomo_memory.relation_replay run \
  --directory /absolute/path/to/prepared-directory \
  --phase before --approved-call-limit 6 --allow-paid
```

该命令仅执行 `before` 组，每个选定任务最多一次真实请求。它会重新核对源库 hash、
完整输入 hash、实现身份与请求 hash。源库、输入或修改前契约变化时，在真实调用前停止。
不对真实实验目录执行带测试 transport 的回放；受控运行只使用 pytest 的独立临时目录。

查看持久记录：

```sh
.venv/bin/python -m locomo_memory.relation_replay status \
  --directory /absolute/path/to/prepared-directory
```

`calls.sqlite3` 保存每次调用的开始意图、响应检查点、安全错误分类、实际结束原因和用量。
结果只保存通过领域校验后的关系标签、端点 ID、来源 ID、标签分布与候选覆盖数，
不保存响应原文、理由、support quote、Memory 文本或任意异常字符串。
`status` 输出这些安全字段，可重定向为独立 JSON 报告。

调用前的预算预留先提交到 SQLite。每个任务、每个阶段只有一个槽位；预算、计划 hash
和运行模式首次执行时冻结。重复命令跳过已完成槽位，不能借此增加预算或重发请求。
进程中断后的预留可能尚未实际发送，也可能已经计费，始终计入上限，不自动返还。
`result=null` 表示任务结果未提交，未知用量保持未知。遇到这种状态，或此前发生
网络、HTTP、超时、上下文拒绝等失败，后续命令会停止，等待独立复核。
不会在失败之后静默发送探针或额外请求。

## 取得证据后执行最小修复与比较

先检查 `failure_stage`、`error_code`、`field_path`、`finish_reason` 和全部调用用量。
只有输出失败可继续下一选定候选；如果全部候选成功，工具拒绝进入 `after` 组，
保留“错误未复现”的观察，不为了耗尽预算强行改代码。

根据具体证据只调整一个契约问题，保留关系领域约束和固定候选。先通过对应受控回归，
再使用相同的已批准总上限执行：

```sh
.venv/bin/python -m locomo_memory.relation_replay run \
  --directory /absolute/path/to/prepared-directory \
  --phase after --approved-call-limit 6 --allow-paid
```

`after` 需要完整的修改前记录、至少一次 `invalid_output` 和不同的实现身份。
两组复用相同源输入、模型参数、输出上限和 `retries=0`，分别记录实现、Prompt、Schema
版本及实际请求 hash。比较每项错误、标签分布和候选覆盖，不能把“校验通过”当作语义真值。
小样本单次比较不能证明原始 29 项全部解决或显著降低错误率。

达到上限时不新增槽位。若预算、输入或实验策略需要改变，另行制定计划和确认授权，
不要编辑旧 ledger、重置计数或直接重试旧 Build。
