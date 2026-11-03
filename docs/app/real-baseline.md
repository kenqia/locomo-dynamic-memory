# 准备并运行真实开发集基线

2026-10-21：原 Issue #15 已决定停止扩展，课程项目转向增量质量迭代。原定757题、四策略3,028项全量评测未执行，#21本轮实验取消；#20原固定五题四策略预检仍有缺口，低优先级延期。下文保留运行入口说明，不表示当前计划执行或已通过全量验收。详见[范围结案与独立工程验收](../../experiments/issue-15-closure/README.md)。

后续获授权的[当前系统展示实验](../../experiments/current-showcase/README.md)单独固定20题五策略配对、40题来源Recall、10个动态场景、20条回答语义核验及Web场景。它复用既有完整Build，不恢复原全量任务，也不将模型关系标签当作独立动态真值。

本地命令复用公开 FastAPI 完成固定开发计划、真实预检和全量评测。离线准备不调用生成模型。实际运行状态以 SQLite 中的 Build/Run 和实验目录记录为准；入口实现、受控回归和计划数量不代表真实模型评测完成。

## 准备隔离环境

在仓库根目录使用现有锁文件安装项目与 Embedding extra。依赖只进入项目 `.venv`：

```sh
uv sync --locked --extra embedding
```

为本次实验选一个专用目录。以下示例使用仓库忽略的 `var/real-baseline`，其中 `memory.sqlite3` 与其他应用数据库独立。启动专属后端：

```sh
.venv/bin/python -m locomo_memory.experiment serve \
  --directory "$PWD/var/real-baseline" --port 18000
```

`serve` 使用明确的默认模型和检索配置，不读取或改写用户配置文件。后端只监听回环地址，数据库使用已有单进程所有权锁。不要将另一个应用后端指向此数据库。

在另一终端执行离线准备：

```sh
.venv/bin/python -m locomo_memory.experiment prepare \
  --directory "$PWD/var/real-baseline" --api-url http://127.0.0.1:18000
```

命令先核对后端数据库路径，再导入已校验的官方原件，保存五题 smoke 计划和四对话全量开发计划。预期产生 `experiment.json`、`preflight.json`、`plan-smoke.json` 和 `plan-development.json`。全量为 757 题、四策略、3,028 组合；smoke 为五题、20 组合。原件身份与来源版本随计划保存。

`prepared_offline` 表示离线准备完成。`blockers` 列出缺凭据、MiniLM 未验证或真实预检未运行等缺项。缺凭据不会阻止原始数据和计划准备，也不会产生模型调用。

## 核实模型条件

真实模型凭据必须由已有受保护方式提供给后端进程的 `DEEPSEEK_API_KEY`。本入口不读取凭据文件、不加载 `.env`，只检查进程变量存在性；不将值写入命令、日志、配置或导出。补充环境后重启专属后端，保留相同目录。不要在聊天或命令正文中填写真实密钥。

执行真实 MiniLM 检查：

```sh
.venv/bin/python -m locomo_memory.experiment verify \
  --directory "$PWD/var/real-baseline" --api-url http://127.0.0.1:18000
```

该命令仅加载本地固定 revision，实际编码两段文本，检查 384 维、有限且归一化的向量，并验证超长输入拒绝。缺依赖、缺本地权重或长度政策失败分别保存安全错误，不自动下载权重。结果保存在 `verified-preflight.json`。受控 Embedding 即使通过结构检查，也不会取得真实预检资格。

首次付费请求前，核对 DeepSeek 官方服务表和请求契约，将人工核对结果保存为独立 JSON。字段示例见 [模型契约示例](../../experiments/deepseek-contract.example.json)。这个记录是公开文档核对，不是真实调用成功证明。应保留核对范围与未能核对的限制；服务别名不保证固定权重，实际返回模型由每次调用记录。

早期 2026-10-20 预检使用全部关闭思考的请求。当时 thinking、JSON 和 Chat API 指南重新获取失败，历史预检记录保留该限制。后续分阶段实验重新读取了官方 thinking 和 Chat API 指南，默认改为关系判断 `high`、有效证据解析 `low`，其余阶段关闭；字段和输出覆盖规则见[构建配置](building.md#分阶段思考配置)。该实验使用独立构建和运行身份，不恢复早期全关闭协议下的 Run。

`deepseek-flash` 的已知服务别名仍记为 `DeepSeek-V4.1-Flash-1017`，实际返回模型逐次记录。Full Text 的 regex 计数只是文本近似，不是提供方 tokenizer 或账单 token。

`conv-26` 的分阶段思考实验已建立完整版本，并执行 10 道固定开发集 QA 的四策略比较。
40 项中 24 项成功、16 项输出校验失败；[原始得分](../../experiments/issue-15-thinking-qa/results/report.md)
与[失败诊断及解释](../../experiments/issue-15-thinking-qa/results/analysis.md)分别保存。
该实验使用 `expanded` 证据配置，未运行全关闭思考对照、开发集全量或本地测试集。

2026-10-21 的[答案优化复验](../../experiments/issue-15-answer-output-live/results/comparison.md)
复用同一构建和 10 题，40 项全部执行成功。Dynamic F1 为 0.334，Raw Fallback 为 0.340；
Dynamic 的官方拒答匹配仍为 1/2，Raw Fallback 的研究对象题仍有遗漏。
见[目标核对与限制](../../experiments/issue-15-answer-output-live/results/analysis.md)。

其后的[证据覆盖 A/B 实验](../../experiments/issue-15-evidence-coverage-live/results/analysis.md)
固定 5 道定向题及 10 道同对话的新问题，仅选两种策略分别比较。
30 项均执行成功，但 QA 3 的关键证据仍未交付，QA 15 的补查丢掉已支持活动，
Dynamic 的 QA 53 也出现时间退化；不能将受控回归通过当作真实质量提升。
B 是 conv-26 内的问题级留出，不能外推为跨新对话泛化。

## 小型抽取和五题预检

显式授权付费后运行小型原始对话抽取检查：

```sh
.venv/bin/python -m locomo_memory.experiment probe \
  --directory "$PWD/var/real-baseline" --api-url http://127.0.0.1:18000 \
  --allow-paid --contract-record /absolute/path/checked-contract.json
```

`probe` 通过现有 `/imports` 和 `/builds` 检查三轮合成原文，确认 Memory 非空、来源可读取并保存请求与返回模型身份。它检查真实集成，不作为官方 QA 分数。既有独立检查仍可显式运行 `LOCOMO_LIVE_MODEL=1 .venv/bin/python -m pytest tests/test_live_model.py -q`。

运行固定 `conv-26` smoke：

```sh
.venv/bin/python -m locomo_memory.experiment smoke \
  --directory "$PWD/var/real-baseline" --api-url http://127.0.0.1:18000 \
  --allow-paid --contract-record /absolute/path/checked-contract.json
```

smoke 先确认小型抽取，再依次推进 `conv-26` 抽取、索引、关系、投影与完整发布，最后创建异步五题 Run。每次命令只有限推进当前可执行阶段；任务运行时返回，使用 `status` 检查后再次运行相同 `smoke` 命令推进后续阶段。已有 Build/Run 会复用，不自动重试失败任务，不对已成功项重新调用模型。

```sh
.venv/bin/python -m locomo_memory.experiment status \
  --directory "$PWD/var/real-baseline" --api-url http://127.0.0.1:18000
```

Run 进度读取使用轻量 `/evaluation-runs/{run_id}/progress`，页面也可通过已保存 Run ID 读取结果。smoke 只有在 20 项全部成功、四策略和原始问题身份匹配、完整全文全部来源送达、固定版本和执行配置一致时，才取得运行资格。答案质量不设最低分数。受控 provider 或 Embedding 只记录 `controlled_validation_only`，不能解锁全量。

## 显式恢复

发生构建失败时，先检查 `builds/<build_id>/fragments.json` 和 `relation-tasks.json`，再选择恢复该阶段：

```sh
.venv/bin/python -m locomo_memory.experiment resume \
  --directory "$PWD/var/real-baseline" --api-url http://127.0.0.1:18000 \
  --allow-paid --build-id '<本实验 build_id>'
```

运行恢复默认只继续未执行或中断项；失败、结果未知项需分别选择：

```sh
.venv/bin/python -m locomo_memory.experiment resume \
  --directory "$PWD/var/real-baseline" --api-url http://127.0.0.1:18000 \
  --allow-paid --retry-failed --retry-unknown
```

若创建 Build 或 Run 后 HTTP 响应丢失，`experiment.json` 保留 `pending_initiation` 并返回 `initiation_outcome_unknown`；后续付费命令拒绝自动再次创建。创建请求带有随机 `creation_token`，后端将它与资源一起持久保存。先发现与该次请求关联的候选资源：

```sh
.venv/bin/python -m locomo_memory.experiment recover \
  --directory "$PWD/var/real-baseline" --api-url http://127.0.0.1:18000
```

检查输出中的 `recovery_candidates`，再显式接纳一个 ID：

```sh
.venv/bin/python -m locomo_memory.experiment recover \
  --directory "$PWD/var/real-baseline" --api-url http://127.0.0.1:18000 \
  --resource-id '<已核对的 build_id 或 run_id>'
```

`recover` 只读取后端并更新本地 receipt，不调用生成模型。它核对关联 token、专属数据库、配置与实现身份，再核对 Build 的数据集、对话和来源，或 Run 的计划、输入、策略、原件与固定版本。成功后重新运行原命令，入口接续同一资源。候选不自动接纳；身份不匹配时保留未知记录并拒绝继续。旧版本未知记录没有关联 token 时返回 `legacy_initiation_ownership_unverifiable`，保留旧目录和服务器结果，不能仅凭相同对话或时间认领，也不要手工清空记录重试。公开 `GET /evaluation-runs?creation_token=...&limit=100&offset=0` 返回轻量分页身份列表，可用于独立核对 Run。成功返回的身份也会立即存入 initiation receipt；即使客户端尚未更新阶段字段，再次执行也读取同一资源。

结果提交失败后，执行所有者将仍在运行的项标为 `unknown`，保留未确认尝试。后端启动也会修复中断 Run 中遗留的运行项。只有显式 `--retry-unknown` 才会重新调用这些项。

保留首次失败、所有尝试和最终采用结果，成功项跳过。读取、导出不启动生成。输入、Prompt/schema、配置、固定版本或实现身份变化时，运行 API 拒绝原地恢复。不要手工改写旧记录或拷分拼接。外部模型调用可能已计费但结果尚未提交，未知结果重试可能再次计费，不承诺恰好一次调用。

## 全量运行与导出

真实 smoke 通过后，使用同一目录、实现、模型及参数执行全量：

```sh
.venv/bin/python -m locomo_memory.experiment full \
  --directory "$PWD/var/real-baseline" --api-url http://127.0.0.1:18000 --allow-paid
```

入口重新读取实际 smoke Run 并核对原件、计划、固定 `conv-26` 版本和配置身份，然后构建其余三个开发对话，创建 3,028 项全量 Run。全量不手工复用 smoke 分数；它在自己的持久计划内执行，保留所有分母。使用 `--scope development` 读取、恢复或导出全量结果。

```sh
.venv/bin/python -m locomo_memory.experiment export \
  --directory "$PWD/var/real-baseline" --api-url http://127.0.0.1:18000 \
  --scope development
```

导出在 `runs/<run_id>/` 保存完整 `run.json`、`grouped-summary.json`、`failure-cases.json`、`report.md` 和 `report.html`。实验目录也生成对应范围的 `report-<scope>.html`，用于直接展示或打印；机器核查仍以 Run JSON 为准。构建目录保存完整版本导出，运行记录保留所有尝试、用量、来源和 Trace。`experiment.json` 保存精确命令、阶段 HTTP 时间和状态观察时间；观察间隔包含操作人员空闲时间，不作为纯构建计算耗时。provider 已报告调用耗时和查询用量分别保留，未知用量不计为已知零。

报告分列成功 QA、执行成功率、基线运行得分及分母，按策略、对话和类别展示。失败案例包含原始来源映射、Memory 排名、阶段来源和引用指针；自动根因标为未确定，独立复核后才做语义归因。部分运行、服务失败或中断只能报告实际完成范围。

本入口只运行四个开发对话，不生成 `conv-43`、`conv-44` 的模型成绩，不访问教师隐藏评分集。动态准确率缺独立标注时为未评；实验产物不代替非作者复核、合并验证或课程验收。停止后端不会清除实验数据库。回退代码时保留旧数据库和产物，另选新目录启动，不覆盖旧结果。
