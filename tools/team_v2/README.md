# Product Console 运行与检查工具

当前模块和复核材料见 [Product 入口](../../docs/team-v2/product-console.md)与 [复核说明](../../docs/team-v2/product-review.md)。工具只在新建的 `var/` 输出目录运行，不覆盖既有结果，不访问活动研究数据库或真实模型。

| 工具 | 用途 |
| --- | --- |
| `demo.py replay` → `replay_ui.py` | 启动静态离线 Replay，默认端口 18501，无 API/数据库 |
| `demo.py prepare/api/ui` → `demo_ui.py` | 独立合成数据与本地 API/UI，包含原五阶段入口 |
| `check.py` | 带离线保护的 Python 检查入口 |
| `verify_replay.py` → `browser_replay.py` | 六案例、版本、来源、Trace、输入恢复、实验/成本、实际无损下载及录屏素材 |
| `verify_replay.py --browser-script browser_console_controls.py` | 五页 × 两种角色 × 三种窗口宽度、版本面板、统一标签与布局 |
| `verify_replay.py --browser-script browser_query_scroll.py` | 来源 1/2 反复自动展示、字段默认折叠、桌面/手机实际鼠标滚动 |
| `verify_console.py` → `browser_console.py` | 新合成 API/UI、四案例、旧五阶段往返和启动错误透传 |
| `check_product_integration.py` | 指定 main 导出的六模块增量候选检查，不合并、不修改 main |
| `freeze_demo.py` | 维护固定快照的生成工具；普通运行/复核不需要重建快照 |
| `check_video.py` | 既有视频材料检查；不是正式 MP4 交付证明 |

浏览器检查需要独立安装 Playwright 的 Python 环境和本机 Edge，路径由 `--browser-python` 指定。示例：

```powershell
.\.venv\Scripts\python.exe tools/team_v2/verify_replay.py --browser-python var/console-browser/Scripts/python.exe --output var/new-product-check
```

每次使用全新输出目录，进程由启动工具在退出时停止。重复的 `browser_product_final.py` / `browser_console_responsive.py` 已删除，其中分母/成本/下载检查并入六案例入口，布局检查由 controls 入口覆盖。需要复现历史截图时使用历史记录绑定的 Git 提交。
