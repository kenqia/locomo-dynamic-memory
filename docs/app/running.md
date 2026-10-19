# 运行原始来源浏览应用

本地应用通过 FastAPI 导入 LoCoMo 数据、持久化至 SQLite，并在 Streamlit 页面浏览原始英文对话。来源管理与原子 Memory 抽取已实现，抽取与重试步骤见 [构建指南](building.md)。初始混合检索见 [候选检查指南](retrieval.md)。关系与完整构建发布见 [历史状态指南](relations.md)。完整版本的有效证据问答见[问答指南](querying.md)。正式课程评测由后续票实现。

## 准备环境

需要 WSL Ubuntu、Git 和 [uv](https://docs.astral.sh/uv/)。仓库的 `.python-version` 选择 Python 3.12；`uv.lock` 固定依赖。首次同步会下载依赖并在仓库 `.venv` 中安装，不修改全局 Python。SQLite 数据默认写入被 Git 忽略的 `var/`。

在仓库根目录运行：

```sh
uv sync --locked
```

默认配置可直接启动。需要覆盖设置时，将 `config.example.toml` 复制到自己的本地文件，并在两个终端设置相同的配置路径：

```sh
cp config.example.toml /tmp/locomo-local.toml
export LOCOMO_CONFIG=/tmp/locomo-local.toml
```

配置字段由 `src/locomo_memory/config.py` 校验；未知字段被拒绝。生成模型固定使用官方 Base URL `https://api.deepseek.com` 并关闭思考，不能通过普通配置改向其他服务或开启思考。`db_path` 相对启动目录解析。示例也列出后续模型与检索预算，来源导入不调用模型；显式发起构建、候选问题分析和完整版本问答会调用生成模型。配置文件不接受 API key；不要将凭据写入示例、配置、JSON 导入内容或仓库。

## 启动应用

1. 在第一个终端启动后端：

   ```sh
   uv run uvicorn locomo_memory.api:create_app --factory --host 127.0.0.1 --port 8000
   ```

2. 在第二个终端启动页面：

   ```sh
   uv run streamlit run src/locomo_memory/ui.py --server.address 127.0.0.1
   ```

3. 打开终端显示的本地 Streamlit 地址。点击 **导入仓库官方数据（校验版本与许可证）**，或选择本地 LoCoMo JSON 并填写数据版本与许可证。
4. 选择数据集、`sample_id` 和会话，按页浏览轮次。输入 `dia_id` 精确定位原文。
5. 检查后端健康与交互式 API 文档：

   ```sh
   curl http://127.0.0.1:8000/health
   ```

   预期返回 `{"status":"ok"}`。接口文档位于后端 `/docs`。

页面通过 HTTP 访问后端，不直接读取数据库。页面支持数据集、对话、会话和轮次分页。重启后端保留已导入数据；停止两个进程不会清空 SQLite。

## 导入与来源契约

`sample_id` 保持上游值，`session_id` 使用 `session_1` 等原始键，`dia_id` 使用 `D1:1` 等原始值。Source Turn 保留说话人、原始会话时间字符串、英文原文及稳定顺序。来源身份为 `<dataset_id>/<sample_id>/<dia_id>`，不同对话中同名人物或相同 `dia_id` 不合并。

导入先校验全部数据再事务写入。缺失字段、重复 `sample_id`、对话内重复 `dia_id`、不匹配的会话 ID 和非参与者说话人会拒绝整次导入。允许原始轮次携带上游图片元数据，但不下载或解析图片。

来源指纹只包含对话参与者、会话和文本轮次；数据集身份还包含版本与许可证。同一来源及相同版本/许可证重复导入复用数据集。更改 QA 或辅助标注生成不同导入 artifact，不改变来源指纹或来源列表。`qa`、`event_summary`、`observation`、`session_summary` 只存于独立的 artifact 注释字段，不进入 Source Turn 视图。后续构建必须使用 `source_turns`，不得将 artifact 注释传入模型。

上传文件与官方文件的 `artifact_sha256` 是原始字节 SHA-256；JSON 请求的 SHA-256 使用校验后 JSON 的规范表示，`checksum_basis` 明确记录该区别。官方导入同时核对 `data/raw/locomo/provenance.json` 中的数据和许可证校验值，并保存上游 commit、许可证名和许可证校验值。此校验验证仓库内清单一致性，不提供独立的上游签名认证。下载原件不改写。

官方 `conv-26` 包含 `session_20_date_time` 至 `session_35_date_time`，但没有对应文本会话。导入保留这些时间为 provenance 中的 `unpaired_session_times`，不制造空会话或来源轮次。

## API 参考

除单项资源和导入结果外，列表返回 `{items, total, limit, offset}`。`limit` 范围为 1–100，默认 20；`offset` 为非负数，默认 0。无匹配资源返回 404，已有列表超出末页返回空 `items`。

| 方法与资源 | 用途 |
| --- | --- |
| `POST /imports` | JSON `{data: [LoCoMo sample], version, license}` 导入 |
| `POST /imports/file` | multipart `file`、`version`、`license`，保留原始字节校验值 |
| `POST /imports/official` | 导入仓库固定的官方数据，不能指定任意本地路径 |
| `GET /datasets` | 分页列出数据集 |
| `GET /datasets/{dataset_id}` | 读取版本、许可证与来源数量 |
| `GET /datasets/{dataset_id}/provenance` | 分页读取 artifact 校验依据与溯源信息 |
| `GET /datasets/{dataset_id}/conversations` | 分页列出对话与参与者 |
| `GET /datasets/{dataset_id}/conversations/{sample_id}/sessions` | 分页列出会话、原始时间与轮次数量 |
| `GET /datasets/{dataset_id}/conversations/{sample_id}/turns` | 分页读取来源；可用 `session_id` 筛选 |
| `GET /datasets/{dataset_id}/conversations/{sample_id}/turns/{dia_id}` | 精确定位单个来源 |

错误统一返回 `{"error":{"code":"...","message":"..."}}`。输入错误为 `invalid_input`，未知资源为 `not_found`，官方原件/清单校验失败为 `invalid_official_data`。错误不会回显输入值或校验异常。接口目前面向本地进程，默认只监听回环地址。

## 验证

```sh
uv run pytest -q
```

测试从公开 FastAPI 接口验证真实 SQLite 的导入、重启持久化、分页、错误、隔离与官方来源映射；不调用付费模型。不以 SQLite 私有查询作为断言，也不把官方数据结构检查当作检索效果评测。

TDD 使用 FastAPI 测试客户端与 Pydantic 模型校验，参考 [FastAPI 测试指南](https://fastapi.tiangolo.com/tutorial/testing/) 和 [Pydantic 模型文档](https://docs.pydantic.dev/latest/concepts/models/)。运行记录见 `experiments/issue-5-import-validation.md`。浏览器与真实模型检查单独记录，API 测试通过不证明两者通过。
