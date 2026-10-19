# Issue #12 本地集成验证

2026-10-19，WSL Ubuntu。起点为集成提交 `a7830ca`，它是本票分支的祖先。
本票使用 `/tmp/locomo-issue12` 独立 worktree 和独立 `.venv`。
验证边界为浏览器 → Streamlit → FastAPI 的公开接口；SQLite、BM25、NumPy
cosine、RRF、历史关系、状态投影、完整版本和导出均使用真实实现。
本票不新增生产业务功能，也不以合成结果评价真实模型质量。

## 安装与生产入口

在全新 worktree 中运行 `uv sync --locked` 成功：Python 3.12.12，安装
55 个包。锁定版本包括 FastAPI 0.146.0、Streamlit 1.66.0、Pydantic
2.14.1、Uvicorn 0.54.0、NumPy 2.5.4、rank-bm25 0.2.2。

两个独立进程分别运行：

```sh
LOCOMO_CONFIG=/tmp/locomo-issue12-smoke.toml uv run --locked uvicorn locomo_memory.api:create_app --factory --host 127.0.0.1 --port 18000
LOCOMO_CONFIG=/tmp/locomo-issue12-smoke.toml uv run --locked streamlit run src/locomo_memory/ui.py --server.address 127.0.0.1 --server.port 18501 --browser.gatherUsageStats false --server.headless true
```

配置只含临时 SQLite 路径、本地 `api_url`、`model_retries=0` 和
`initial_k=1`。真实 Chromium 打开页面并确认空数据提示，`GET /health`
返回 `{"status":"ok"}`。该步骤使用生产 `create_app`，没有注入测试适配器。

只检查了 `('DEEPSEEK_API_KEY' in os.environ)`，结果为 `False`。
未读取认证文件、凭据内容、cookie、浏览器既有 profile 或私密日志。
另外用生产工厂在独立 SQLite 上经公开 API 导入单轮合成来源并请求构建，
实际持久化为 `failed` / `extraction`，片段错误为 `missing_credentials`。
该检查没有发送真实 DeepSeek 请求。真实 DeepSeek 调用未执行；未验证账户访问权限、真实模型结构化输出及质量。
不得将后述受控 HTTP 输出当成真实 DeepSeek 通过。

本地 MiniLM 的真实加载、384 维编码、超长拒绝及旧完整版本模型身份选择，
由此前未变化的模型与索引实现的 opt-in 检查验证，记录见
[实现总记录](issue-4-implementation.md)。执行命令为：

```sh
LOCOMO_LOCAL_EMBEDDING=1 HF_HUB_OFFLINE=1 uv run --extra embedding --locked pytest -m local_embedding -q
```

结果为 3 passed、84 deselected，固定模型为
`sentence-transformers/all-MiniLM-L6-v2`，revision
`c9745ed1d9f207416be6d2e6f8de32d1f16199bf`。
本票未修改生产模型代码，没有重复加载该模型。浏览器 smoke 使用受控
Embedding，不能据此再次宣称真实 Embedding 浏览器链路已验证。

## 重复执行浏览器 smoke

`tests/browser/server.py` 是显式测试入口。它只注入生成模型 HTTP transport
和 Embedding；生产工厂没有自动切换或失败后使用假数据的逻辑。
受控 HTTP 经真实 `DeepSeekModel` 的 JSON 解析、schema 校验和有限重试。
首次抽取故意返回 503，后续显式重试成功；评测中的 failure 问题故意返回
非法结构化响应。冲突案例有独立可核查的合成原文：Sam 分别无条件声称出生年为 1990、1992，
并明确表示报告矛盾且未消解；受控抽取生成独立 birth_year 组，持久化
有双方来源的 CONFLICT。问题检索命中该组并扩展另一侧。证据不足问题
询问原文没有的 passport number。外部响应仍受控，不是模型语义质量结果。

Playwright 安装在独立环境，未加入应用依赖或更改锁文件。本轮使用已安装的
`/tmp/locomo-browser-env/bin/python`（Playwright 1.64.0）和缓存 Chromium。
新机器可以另建独立环境安装相同 Playwright 版本并安装 Chromium；这会在该
环境和浏览器缓存中下载测试依赖，不修改全局 Python。准备后，在仓库根目录运行：

```sh
uv sync --locked
bash tests/browser/run.sh /tmp/locomo-browser-env/bin/python
```

运行前确保 18000 和 18501 端口空闲。脚本创建 `mktemp` 目录、新 SQLite、
配置和日志，启动两个真实本地进程，等待健康，再启动隔离的无头 Chromium。
脚本在启动前检查两个端口能否绑定，在退出时停止并等待这两个子进程。临时目录保留下载和截图，终端输出其位置。
数据库只通过 UI 上传导入；额外断言只调用公开 API，不直写或查询 SQLite。
浏览器没有认证 profile；仅导航已知 localhost，未访问外部页面或执行 DOM 写脚本。

Streamlit 的输入 blur 会触发 rerun。初始 harness 曾因紧接着点击刷新或提交而
取消尚未处理的操作，出现无构建和空问题；这些失败没有计为应用通过。
最终 harness 等待 `stApp` 的 `data-test-script-state=notRunning`，并校验输入值。
日期开关使用原生键盘 Space，日期使用原生 year/month/day 控件，下载通过 Playwright 原生 download 事件获取。

## 结果和边界

浏览器最终执行结果在本节留档，保留通过、失败和未执行的区分。
课程六段对话、4/2 划分和独立动态真值未提供；未运行正式测试集调参或课程指标。
本票没有远端写入、发布、部署、关闭 Issue，也没有标记项目整体验收完成。
未关联的 Notion 记录未同步，等待负责人补录；非作者复核和合并验证由后续流程处理。

最终完整运行命令 `bash tests/browser/run.sh /tmp/locomo-browser-env/bin/python`
退出码为 0。Chromium 为 `156.0.8078.4`，最终产物目录为
`/tmp/locomo-browser-smoke.1D4DCv/artifacts`；可提交的精简结果见
[`issue-12-browser-result.json`](issue-12-browser-result.json)。下载文件留在该临时
目录，使用项目 `.venv/bin/python` 调用真实
`MemoryExport.model_validate_json(...)` 校验通过。

| 项目 | 实际结果 |
| --- | --- |
| 新环境安装、生产工厂健康与真实页面空数据启动 | 通过 |
| 生产工厂无凭据构建 | 通过预期失败处理；`failed`、`extraction`、`missing_credentials` |
| UI 上传合成来源、精确定位 D1:1、检查原文 | 通过；5 个原始轮次，QA 注释独立保留 |
| 构建进度、503 故障和显式重试 | 通过；失败 1 个片段，重试后保存 4 条 Memory |
| 真实索引、BM25 / Dense / RRF 展示、关系、重算投影、完整发布和 pin | 通过；1 条 SUPERSEDE 与 1 条 CONFLICT |
| 当前 Rome、指定 2023-05-01 的历史 Paris | 通过；新 Trace 固定同一完整版本，采用对应来源 |
| Sam 出生年冲突 | 通过；初始 1 条，扩展另一条，有效集合保留 1990 和 1992，引用 D2:2 / D2:3，Trace 包含持久化 CONFLICT |
| 原文没有的 passport number | 通过；insufficient，无有效 Memory 或引用 |
| 回答引用展开、原始来源与完整 Trace / 排除理由展开 | 通过 |
| 查询前后原文、关系和 Current State | 公开 API 返回值完全一致 |
| 原生浏览器 JSON 下载、schema 与版本一致性 | 通过；`memory-export-v1`，Memory / index / projection 均属于所选完整版本 |
| 四策略评测展示与失败记录 | 通过；8 行中 4 行故意失败，每策略 QA scored=1、unscored=1；失败不计作零分或证据不足 |
| 浏览器 pageerror / console error | 均为 0 |
| 子进程清理 | 通过；退出后 18000 / 18501 均可重新绑定 |
| Python 编译、`bash -n tests/browser/run.sh`、`git diff --check` | 通过 |
| 真实 DeepSeek、正式课程指标、正式测试集调参 | 未执行；缺少凭据或独立课程材料 |

初版 harness 的 rerun 时序、关闭 JSON 内的隐藏文本匹配和 checkbox 指针定位
曾失败，修正后完整重跑通过；这些失败没有作为产品能力通过的证据。
日期开关改用键盘 Space，展示断言限定可见元素，实际答案另通过新 Trace 的公开
API 校验。没有因此修改生产业务代码。

本票未改变 `src/`、依赖或锁文件，因此没有再次重复完整默认测试或真实 MiniLM
测试。最近的默认回归为 #11 的 90 passed、4 个 opt-in 检查 skipped，见
[实现总记录](issue-4-implementation.md)；该结果没有冒充本票新运行。

三张截图只含合成数据和非敏感版本信息：

- [失败片段与显式重试入口](screenshots/issue-12-build-failure.png)
- [历史答案与展开 Trace](screenshots/issue-12-history-trace.png)
- [四策略评测摘要](screenshots/issue-12-evaluation.png)

检查图片后，评测截图的初始位置只显示长 Trace 底部，因此用同一完整版本重新
在 Chromium 显示评测摘要并截图。该局部重现再次核验四策略的成功 / 失败分母，
不替代上述从空数据库启动的完整运行。
