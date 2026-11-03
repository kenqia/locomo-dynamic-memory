# 运行检查与诊断浏览器失败

默认检查使用真实 SQLite、检索和业务接口，以受控适配器替代外部生成与
Embedding。不需要凭据，不下载模型，也不验证真实模型质量。

## 运行与 CI 相同的检查

在仓库根目录运行：

```sh
uv sync --locked
uv run --locked python -m compileall -q src tests
LOCOMO_LIVE_MODEL=0 LOCOMO_LOCAL_EMBEDDING=0 uv run --locked pytest -q --tb=short
git diff --check
```

`.github/workflows/checks.yml` 在每个 PR 和 `main` 的 push 上运行锁定安装、
变更范围的空白检查、编译和默认测试。工作流只有 `contents: read` 权限，
不使用仓库秘密，不运行真实 DeepSeek 或 MiniLM。固定 uv 为 `0.9.11`，
Python 版本取自 `.python-version`。

此工作流提供检查结果；要求检查通过才允许合并，需要仓库负责人另行配置
GitHub ruleset。本次没有更改仓库保护设置。当前未引入 lint 或静态类型检查器。

默认测试中的 `tests/test_browser_fixture.py` 与 Chromium 共用合成来源及受控
模型。它改变 Memory 插入顺序，在六个新构建上验证当前、历史、冲突和证据不足
问题。断言覆盖 Top-1 初始候选、实际历史扩展和公开问答结果，防止排名并列时
随机 Memory ID 掩盖夹具错误。它不能代替浏览器检查。

## 准备独立浏览器环境

以下命令只在指定临时环境安装 Playwright，并下载其 Chromium 到用户浏览器
缓存，不修改全局 Python 或项目 `.venv`。首次准备需要网络与本机浏览器系统库。

```sh
uv venv /tmp/locomo-browser-env --python 3.12
uv pip install --python /tmp/locomo-browser-env/bin/python playwright==1.64.0
/tmp/locomo-browser-env/bin/python -m playwright install chromium
```

如果该路径已有可用环境，直接复用。缺少 Chromium 系统库时，按 Playwright
安装提示由本机管理员安装，不把系统安装混入应用脚本。

## 运行完整浏览器流程

先确保本机 `18000` 和 `18501` 端口空闲。在仓库根目录运行：

```sh
bash tests/browser/run.sh /tmp/locomo-browser-env/bin/python
```

脚本为每次运行创建 `/tmp/locomo-browser-smoke.*`，通过
`UV_PROJECT_ENVIRONMENT` 将锁定应用依赖安装到其中的 `app-venv`。
FastAPI、Streamlit 和导出 schema 校验均使用这个解释器；Playwright 使用传入
的独立解释器。根目录 `.venv` 及其 embedding extra 保持原样。

脚本在开始和退出时打印产物目录与退出码。成功退出为 `0`，浏览器失败保留
非零退出码。退出时停止并等待本次启动的两个服务；已生成的临时目录保留。
依赖安装或服务启动阶段的失败也会报告目录，但尚无浏览器上下文时不会产生
截图或 Playwright Trace。

## 查看诊断材料

产物目录仅用于隔离的合成数据测试。不要将此采集器用于登录后的浏览器或真实
私密对话；Playwright Trace 和页面文本会保留当时的页面及网络内容。

| 文件 | 用途 |
| --- | --- |
| `api.log`、`ui.log` | 本次测试后端与页面进程日志 |
| `artifacts/diagnostics.json` | 成功/失败状态、异常类型、页面和控制台错误；不包含请求凭据或异常输入值 |
| `artifacts/failure.png` | 浏览器步骤失败时的页面截图 |
| `artifacts/page-state.txt` | 浏览器步骤失败时的可见页面文本 |
| `artifacts/trace.zip` | 浏览器步骤失败时的 Playwright Trace |
| `artifacts/issue-12-result.json` | 完整成功流程的业务结果摘要 |

失败时先查看 `diagnostics.json` 和页面文本，区分 API 错误、校验拒绝与定位器
超时。截图或 Trace 无法采集时，摘要记录采集失败类型，同时保留原始异常。

用本地 Trace Viewer 打开 Trace，将下例路径替换为终端报告的实际目录：

```sh
/tmp/locomo-browser-env/bin/python -m playwright show-trace /tmp/locomo-browser-smoke.EXAMPLE/artifacts/trace.zip
```

检查采集器本身的成功和故障路径：

```sh
/tmp/locomo-browser-env/bin/python tests/browser/check_diagnostics.py -v
```

它启动真实 Chromium，在合成页面主动抛出异常，验证截图、页面文本、可解析的
Trace ZIP 与原始异常保留，还检查页面关闭后采集失败不会替换原异常。成功路径只保存摘要。这三项检查不需要应用服务，
也不属于默认 pytest 或 CI 的无浏览器测试集。

运行结束后可以保留产物供排查。确认不再需要时，按终端提供的精确路径清理
临时目录；应用数据库和开发环境不在其中。停止使用本轮改动时可通过 Git
恢复工作流和测试脚本，不涉及数据库迁移。

## 参考

- [uv 项目环境路径说明](https://github.com/astral-sh/uv/blob/main/docs/concepts/projects/config.md#project-environment-path)
- [setup-uv 使用说明](https://github.com/astral-sh/setup-uv)
- [Playwright tracing API](https://playwright.dev/python/docs/api/class-tracing)
- [GitHub Actions 工作流语法](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax)
