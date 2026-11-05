# Release 工作记录

- 2026-11-05：核实 Release 干净，HEAD=28ce63d73d6736c7812aa0be4425a0d9650dd09e；915fac0 是祖先。
- 主仓 docs/experiment-supplement@3392faf，36 项 dirty，保留；只从 Git 对象导入 docs/supplement，不复制主仓工作区。
- 阅读 AGENTS/CONTEXT/ADR、production acceptance、全部 M5 handoff 及最新终态索引。conv44、Level E 已完成；旧 incomplete 是历史时点。
- Python3.12.12 独立 .venv，uv sync --locked 成功，未修改 uv.lock。未读取凭据、私有日志或重新执行 paid runner。
- 后续实际命令和结果见 experiments/personal-release；验收基于新鲜输出。

## 最终验收收口（2026-11-05）

固定c7eae7a应用/测试源，全仓991 passed/4 deselected，公开sanitized独立安装包937 passed/28 deselected，均0 failed/error/skipped。公开分母：两含上游派生案例模块30项源码不入包，包内24 controlled_data及4 opt-in显式排除。M5全仓342、Release12；普通Web与Replay Chromium通过，附录重核282数值0差异。完整失败/中断/成功测试记录27成员已受控归档。

文档结论更新为PERSONAL_READY本地候选；双轴非作者复核后冻结源码commit，按allowlist封包，最终SHA/成员/运行文件等价验证由包外FINAL_ACCEPTANCE_RECEIPT绑定。无远端写入、课程提交、付费请求或历史删除；主仓36项状态保持。
