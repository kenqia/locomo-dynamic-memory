# Product Console 本机验证

> 历史记录：以下行为、命令、截图与结果仅对应文内注明的版本。复现历史命令请使用当时的 Git 提交；当前送审入口见 [Product 复核说明](../product-review.md)。

日期：2026-11-04，北京时间（D2）。Owner：@Thorns-06。
基准：`3ba1954bd0c188ad84d80dd4a4f94618857b0109`。
关联：#23 / #26；#27–#29 仍待后续交付。

## 环境与实际运行

- Windows 原生 PowerShell；项目独立 Python 3.12.12、uv 0.9.11。
- `uv sync --locked` 成功；不安装 embedding extra，不下载模型。
- 本机初始离线 `prepare` 成功：当前 Rome、历史 Paris、1990/1992 冲突、passport 证据不足。
- 合成 Demo 的真实 provider 请求为 0。运行文件、SQLite、服务日志只留在被忽略的 `var/`。
- Console 新增固定五项导航、展示者/评审者视图、分页数据/对话/Build 选择、版本身份、后端 Run/报告入口、冻结真实报告和 Memory/Trace 只读入口。
- 原五阶段流程通过开关保留；默认生产 API、构建、问答、Prompt、模型配置未修改。

## 检查结果

```powershell
.venv\Scripts\python.exe tools/team_v2/check.py -q --tb=short tests/test_console_ui.py
.venv\Scripts\python.exe tools/team_v2/check.py -q --tb=short
```

1. Console 专项：**8 passed**，覆盖空后端、页面导航、错误提示、unknown、Build 作用域、角色切换后保存的 Trace 和按真实完成时间查找本页最近报告。
   同时复查原 UI 与合成检索：`tests/test_console_ui.py tests/test_strategy_ui.py tests/test_browser_fixture.py` 合计 **17 passed**。
2. 首次 Windows 完整可收集回归：**537 passed / 40 failed / 6 deselected**，不能标为全绿。
   失败涉及未改动的 POSIX `os.O_DIRECTORY`、历史实验 `fcntl`、默认 GBK 编码、凭据启动器的 HOME/exec 行为及子进程检查。
3. 检查入口现对子进程启用 UTF-8；重查 `test_credential_launcher.py`、`test_answer_regressions.py`、`test_dynamic_review_scoring.py`、`test_evaluation_recovery.py`：**47 passed / 9 failed**。
   剩余 9 项均为历史凭据启动器的 Windows HOME/exec 问题，未修改该凭据工具。
4. Windows 检查入口显式不收集 `test_relation_replay.py`（导入 POSIX `fcntl`）；不计为通过。
   另外三个缺历史材料的模块和原有排除项保持基线规则。Linux CI 不新增此 Windows 排除。
5. 本次编译与 `git diff --check` 通过。完整 Linux CI 结果需在 draft PR 中核对。

## 浏览器证据

使用独立环境的 Playwright 1.64.0 与本机 Edge；应用依赖不加入 Playwright。
验证器创建全新的合成 fixture 和独立端口，浏览器阻断外网访问，结束后停止所启动的 API/UI。

```powershell
.venv\Scripts\python.exe tools/team_v2/verify_console.py --browser-python var/console-browser/Scripts/python.exe --output var/product-console-browser-new
```

最终运行目录：本 clone 的 `var/product-console-browser-08/`（不提交运行日志和数据库）。
API/UI 健康检查、共享启动配置、CLI 退出码传播、五项导航、四例保存 Trace 重放、旧五阶段入口均通过；真实 provider 调用 **0**，浏览器页面脚本错误 **0**。
CLI 端口占用探针确认直接服务和启动器均返回实际退出码 **3**，不将失败冒充成功。
浏览器为 Edge **156.0.4314.58**，Playwright **1.64.0**；交互检查使用 **1280×900**。
截图保持宽度 1280，高度扩展至实际内容，避免 Streamlit 内部滚动区域被截断。

已逐张检查的合成 UI 截图：

- [Overview](../assets/product-console/overview.png)
- [Memory](../assets/product-console/memory.png)
- [Query / Evidence](../assets/product-console/trace.png)
- [Experiments](../assets/product-console/experiments.png)
- [Demo](../assets/product-console/demo.png)
- [浏览器结果 JSON](../assets/product-console/browser-result.json)

这些是 #26 的 Console 冒烟证据，不冒称 #29 全流程浏览器验收或另一台机器的人工复现。

## AI 代码审查

按仓库 `code-review` 技能，以 `3ba1954` 为固定点，分 Standards 与 Spec 两个独立代理审查。
Standards：0 项明确规范违规；1 项启动配置重复的维护性意见，已通过共享环境/命令构造及 CLI 探针解决。
Spec：1 项最近报告缺口，已按本页真实、带时区的完成时间排序并补测试；缺时间保持 unknown。
两轴均已复查，当前 **0 项未解决发现**。此记录不代替真实成员 Reviewer。

## 待复核与边界

- 非作者真实成员 Reviewer：**pending**，用户明确尚未确认。
- 本次仅 #26 和 D2 入口增量；完整 Timeline、来源跳转、异常案例、实验多维比较、完整 E2E 属于 #27–#29。
- Notion 未同步：尚无已关联任务记录/可用连接，由负责人补录关联及 Issue/PR 链接。
- 不关闭 Issue，不标记完成，不宣称已合并或人工验收。
- 回滚：撤销本次 Product 功能提交；无数据库迁移，原 `src/locomo_memory/ui.py` 保持可用。
