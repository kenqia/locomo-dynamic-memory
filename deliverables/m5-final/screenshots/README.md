# Console 截图（真实页面，离线合成回放）

采集：2026-11-09，main `5519dd2` 工作树（delivery/m5-final-20261109 基于该提交，代码未改），`tools/team_v2/demo.py replay`，Playwright Chromium headless。
模式：**OFFLINE SYNTHETIC REPLAY**——`demo_fixture/product-v1` 合成数据，0 次模型调用。Experiments 页数据为 E12 历史 757 题 Run，不是 E25。

- `1920-*.png`：1920×1080 视口，五个页面的默认视图（`deliverables/m5-final/tools/capture_console_screens.py`）。
- `viewport-replay-*.png`：1280×900，PR #41 已评审脚本 `tools/team_v2/browser_replay.py` 自动操作后的案例画面；该脚本在最后的 JSON 下载步骤超时（`Timeout 30000ms waiting for event "download"`），前序截图有效，下载功能本次**未验证**。
