# Product Console 本机验证

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

1. Console 专项：**7 passed**，覆盖空后端、页面导航、错误提示、unknown、Build 作用域和角色切换后保存的 Trace。
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

真实浏览器最终结果和经过检查的截图将在同一分支追加；当前不把尚未完成的浏览器流程记为通过。
此前检查已发现并处理 Windows 启动器进程跟踪，以及浏览器自动化对 radio 标签和输入失焦的处理问题。

## 待复核与边界

- 非作者真实成员 Reviewer：**pending**，用户明确尚未确认。
- 本次仅 #26 和 D2 入口增量；完整 Timeline、来源跳转、异常案例、实验多维比较、完整 E2E 属于 #27–#29。
- Notion 未同步：尚无已关联任务记录/可用连接，由负责人补录关联及 Issue/PR 链接。
- 不关闭 Issue，不标记完成，不宣称已合并或人工验收。
- 回滚：撤销本次 Product 功能提交；无数据库迁移，原 `src/locomo_memory/ui.py` 保持可用。
