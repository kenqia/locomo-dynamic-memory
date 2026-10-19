# 复盘改进验证记录

2026-10-19，WSL Ubuntu。用户批准实施复盘建议 1–4：最小 CI、浏览器夹具
稳定性回归、失败诊断和独立应用环境。起点为已合并 PR #13 的
`d5a247d4a5babfb6fb66f6082a5434c91c458f16`，分支
`codex/retro-validation-guardrails`。本轮没有修改生产业务代码、应用依赖或锁文件。

## 改动

- GitHub Actions 在 PR 和 `main` push 上执行锁定安装、变更范围空白检查、
  Python 编译、浏览器 runner shell 语法和默认测试。仅有内容读取权限，
  不接入真实模型凭据。uv 固定为本地验证版本 `0.9.11`。
- 将原 Chromium 合成来源提取到 `tests/browser/sample.json`。默认 API 回归
  与浏览器使用同一来源及受控模型，三种 Memory 插入顺序分别运行两个新构建，
  共 24 次当前、历史、冲突和证据不足查询。
- 浏览器失败记录截图、页面文本、Playwright Trace 和异常类型摘要。采集失败
  不覆盖原始异常。runner 开始及退出都报告目录，退出时保留原退出码并停止服务。
- 每次 runner 使用 `UV_PROJECT_ENVIRONMENT` 在临时目录安装锁定应用环境。
  FastAPI、Streamlit 和 JSON 导出校验都使用该解释器，不同步根目录 `.venv`。
  Playwright 继续使用独立解释器。

操作步骤与边界见 [检查指南](../docs/app/checking.md)。工作流尚未推送至远端；
本记录报告本地执行结果，不宣称 GitHub Actions 已实际运行，也没有设置必需
检查的 GitHub ruleset。

## 自动检查

在根目录运行 CI 的锁定安装、编译和默认测试命令：

```sh
uv sync --locked
uv run --locked python -m compileall -q src tests
LOCOMO_LIVE_MODEL=0 LOCOMO_LOCAL_EMBEDDING=0 uv run --locked pytest -q --tb=short
```

结果：**112 passed, 4 skipped**，83.07 秒；一条已有的 Starlette/httpx
弃用警告。四个跳过项为真实 DeepSeek 和三项真实 MiniLM 检查，本轮未执行。

新增夹具回归单独运行 **3 passed**，10.56 秒。随后仅在临时 Python 进程中
包装受控响应，将 query-analysis 的关键词恢复为空，执行同一测试，得到
预期 **1 failed**，公开问答返回 `502 invalid_output`；证明新测试能识别旧夹具
缺陷。此故障注入未改写仓库中的正常 provider，不能作为正常测试失败报告。

工作流 YAML 解析、`git diff --check` 和 `bash -n tests/browser/run.sh` 通过。
在 `/tmp/locomo-retro-tools` 安装官方 `actionlint v1.7.7` 后执行：

```sh
/tmp/locomo-retro-tools/actionlint .github/workflows/checks.yml
```

退出码为 **0**。该工具不加入应用依赖，不修改 Git hooks、认证或全局配置。

## 浏览器与环境隔离

执行：

```sh
bash tests/browser/run.sh /tmp/locomo-browser-env/bin/python
```

Playwright `1.64.0`，Chromium `156.0.8078.4`。本次应用环境实际位于
`/tmp/locomo-browser-smoke.pjCXAh/app-venv`，安装 55 个锁定包。完整流程
退出 **0**，覆盖导入、故意失败与重试、混合检索、关系与投影、完整版本发布、
四类问答、来源、Trace、下载与四策略评测。页面异常和控制台错误均为空。
下载由该临时应用解释器执行真实 `MemoryExport` schema 校验通过。
结果摘要见 [retro-browser-result.json](retro-browser-result.json)，采集器成功摘要
见 [retro-browser-diagnostics.json](retro-browser-diagnostics.json)。

对根目录 `.venv` 中 55 个包的 `METADATA` 和 `pyvenv.cfg` 在运行前后进行
SHA-256 比较，完全一致。结束后 `18000` 与 `18501` 均可重新绑定。

首次尝试曾因路径规范化使用 `realpath` 解开虚拟环境 Python 软链接，退回
系统解释器后无法导入 Playwright。该运行未计为通过。修正为只规范化目录，
保留 Python 文件及软链接身份后，以上完整流程通过。失败运行保留退出码 1
并报告了目录，其根目录环境指纹也未变化。

另外使用临时可执行文件代替浏览器解释器，故意退出 **7**：runner 保留退出码，
在开始及退出时打印同一产物目录，保留两个服务日志并完成进程清理。端口均可
重新绑定。该故障发生在浏览器启动前，因此不产生截图或 Trace。

## 真实 Chromium 诊断检查

```sh
/tmp/locomo-browser-env/bin/python tests/browser/check_diagnostics.py -v
```

结果：**3 tests OK**，2.426 秒。检查：

- 合成页面主动抛错后，保存有效 PNG、可见文本、包含 `.trace` 的 ZIP 和失败
  摘要，原始异常继续抛出。
- 页面已经关闭时，截图和文本采集失败只记类型，不替换原异常。
- 成功路径保存成功摘要，不保留失败截图或 Trace ZIP。

该脚本在独立 Playwright 环境执行，不向默认应用环境增加依赖。所有浏览器
内容均为隔离合成数据；没有访问登录 profile 或真实私密对话。

## 未执行项与回滚

未运行远端 Actions、真实付费模型、真实 MiniLM、课程正式指标或部署；未推送、
创建 PR、改 GitHub 保护规则或同步无关联的 Notion 任务。本轮不重开已验收的
Issue #4–#12，也不把测试设施改进当作模型质量证据。

改动为新增工作流、测试、诊断辅助脚本与文档，可按 Git 提交恢复，无数据库
迁移。临时应用环境与诊断产物保留于各次精确输出路径，需要时由使用者清理。
