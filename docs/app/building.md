# 构建与检查原子 Memory

你可以从已导入的原始对话抽取 Memory，检查每条陈述及其来源，并显式重试失败片段。抽取结束的版本标记为 `extracted`，`query_ready=false`；它还没有完成索引、关系与完整版本发布。

## 前提

- 按 [运行指南](running.md) 启动 FastAPI 与 Streamlit，并导入一个数据集。
- 由你已有的受保护本地凭据方式向**后端进程**提供 `DEEPSEEK_API_KEY`。应用只在显式生成请求时读取该环境变量，不读取凭据文件，不加载 `.env`，不要求在聊天或配置文件中填写密钥。不要把真实值写进命令正文、仓库或实验记录。
- 本地只运行一个后端进程。SQLite 旁的 `.runtime.lock` 使用 Linux 内核文件锁防止第二个进程错误地把正在工作的构建判为中断；适用环境是项目当前的 WSL Ubuntu。

缺少凭据时，构建记录显示 `missing_credentials`，不会发送模型请求。补齐受保护凭据后需要重启后端使其获得环境，并点击显式重试；系统不自动无限重试。

## 从页面构建

1. 选择数据集和对话 `sample_id`。
2. 点击 **构建所选对话的 Memory**。后端接受任务后，按片段处理原始来源。
3. 点击 **刷新构建进度**，查看成功、失败或待处理片段。已成功的 Memory 即使在其他片段失败时也可检查。
4. 展开 **版本、配置与模型调用记录**，核查数据指纹、实际配置、模型标识、Prompt/schema 版本、每次调用的时间及 token 用量。
5. 在 Memory 列表检查 `event/state`、`fact/plan/intention/uncertain`、正负性质、状态维度与独立的状态值。展开 Memory 查看时间字段及一个或多个原始英文来源。
6. 若状态为 `failed` 或 `interrupted`，检查片段错误码，然后点击 **仅重试失败或中断片段**。成功片段不会重新调用模型，也不会生成重复 Memory。

同一时刻最多一个活动构建。另一个构建请求返回 `409 build_already_running`。后端重启将未完成的活动构建标记为 `interrupted`，保留成功产物，不假称任务仍在后台继续。修改配置后必须创建新版本，不能用新配置重试旧版本。

## Memory 与时间契约

每条 Memory 表达一项独立陈述。`source_ids` 至少包含一个当前片段提供的来源；模型不能自行生成来源，不能引用另一对话或未提供给该片段的轮次。多条 Memory 可以共享来源，一条 Memory 可以引用跨会话的多轮来源（前提是它们在该片段中）。业务层再次校验注入适配器的产物。

`state_key` 使用 `<sample_id>:<entity_id>:<state_dimension>`，实际状态值独立存于 `state_value`。Memory 还归属唯一 `build_id` 与 `dataset_id`，不同对话不会因同名实体合并。同键事实允许并存，本阶段不推断互斥、替代或冲突关系。

`session_times` 来自原始来源；`time` 分开保留原始表达、锚点、推导日期或区间及依据。未知日期保留 `null`。推导日期必须有原始表达、来源锚点和依据；锚点必须在该 Memory 的来源内，原始表达必须实际出现在锚点文本中。计划仍标为计划，不因拥有未来日期而变成已发生事实。

原子性、事实性质和时间解释仍由模型输出决定。结构与来源校验、受控输出测试不能代替真实模型质量验证。

## 模型协议与有限重试

模型适配器通过现有 `httpx` 依赖直接请求官方 `/chat/completions`，不增加 SDK 或供应商插件框架。请求明确携带 `deepseek-flash`（可配置模型名）、`thinking={"type":"disabled"}`、`response_format={"type":"json_object"}`、JSON 提示和输出 schema。普通 JSON 模式不等于 schema 约束，响应仍须经过 Pydantic 和来源校验。

`model_retries` 表示首次请求之外的重试次数，默认 2，即每片段最多 3 次；`model_timeout_seconds` 默认 60 秒。没有额外 SDK 重试层。超时、HTTP 错误、空内容、截断、无效 JSON、无效 schema 或来源会有限重试，耗尽后失败。有效 `{"memories":[]}` 必须带非空 `no_facts_reason`，区别于提供方返回空内容。

每次尝试只保存请求模型、返回模型、时间、允许的 usage 计数与结果分类，不保存提供方原始异常、响应正文、认证头或隐含推理。已知服务版本记为 2026-10-19 官方说明中的 DeepSeek-V4.1-Flash-1017；服务别名可能变化，不能当作权重快照。

实现依据：[DeepSeek Chat API](https://api-docs.deepseek.com/api/create-chat-completion/)、[思考模式](https://api-docs.deepseek.com/guides/thinking_mode/)、[JSON 输出](https://api-docs.deepseek.com/guides/json_mode/)；本地核查摘要保存在实验记录。对话、QA 及辅助标注的隔离规则沿用来源导入契约，模型输入仅由 `source_turns` 构成。

## API 参考

列表继续使用 `{items,total,limit,offset}`，错误继续使用 `{error:{code,message}}`。

| 方法与资源 | 用途 |
| --- | --- |
| `POST /builds` | JSON `{dataset_id,sample_id}`；接受后返回 202 与新版本 |
| `GET /builds` | 分页列出构建；可按 `dataset_id`、`sample_id` 筛选 |
| `GET /builds/{build_id}` | 版本身份、状态、进度、配置及模型记录 |
| `GET /builds/{build_id}/fragments` | 分页读取片段来源、尝试次数、成功/失败状态及错误码 |
| `POST /builds/{build_id}/retry` | 仅重试失败/中断片段；成功或运行中版本不能重试 |
| `GET /builds/{build_id}/memories` | 分页检查该版本已持久化的 Memory |
| `GET /builds/{build_id}/memories/{memory_id}` | 精确读取该版本的一条 Memory |

任务由本地 FastAPI BackgroundTasks 执行，SQLite 持久化进度并用唯一索引限制活动构建；没有外部任务队列。片段的 Memory、来源映射与成功状态在同一事务提交。

## 验证

默认不触发真实付费请求：

```sh
uv run pytest -q
```

公开 API 测试使用真实 SQLite 与真正的模型适配器，只把外部 HTTP 模型响应替换为受控输出。测试覆盖多事实、多来源、事件/状态、计划、否定、不确定陈述、模糊日期、有限失败重试、错误对话来源、单活动构建以及失败片段恢复。

若你明确要执行付费集成检查，并已通过受保护方式向进程提供凭据，可单独运行：

```sh
LOCOMO_LIVE_MODEL=1 uv run pytest -m live_model -q
```

该检查只有一个小型合成构建，模型重试为 0，超时 30 秒。默认测试报告将它标记为跳过。它只检查真实提供方到来源映射的集成，不证明正式课程指标或整体抽取质量。实际执行状态见 `experiments/issue-6-extraction-validation.md`。
