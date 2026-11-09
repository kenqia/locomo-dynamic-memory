# Product 与 main 整合验收

## 最新候选：0401155 与当前 main

负责人在本轮再次授权更新、同步 Notion、收尾并冻结 Product。main 最新基准为 `ba349cf7a8b784ff6c739767ee392802055feff5`，其时间范围、上下文与证据回归更新均通过普通 merge 保留，README 冲突保留双方内容。

本轮 Product 来源为 `0401155aa2c270c48b942e4b410a9f4b390156b3`（运行代码 `60f14bf`），代码整合提交 `4081ece`。新增 `console_theme.py`、`console_widgets.py`，以及来源自动显示、分页、原始字段默认折叠和整页滚动、窄屏与角色布局。原五阶段、main Hybrid 默认及独立 MemoryExport Replay 保持。

xiaozhuozi39 的[最新真人逐项记录](product-integration-20261109/Product-Human-Review-PR39.md)明确绑定 `0401155`，通过项包括来源 1→2→1→2→1、六案例、字段与滚轮、分页/窗口/角色及旧五阶段。[原附件回执](https://github.com/kenqia/locomo-dynamic-memory/pull/39#issuecomment-6734327474)。旧入口命令参数仍有一处待补占位；负责人明确接受当前复核并授权冻结，未将占位误写为完整命令证据。

已独立取得 27 项定向检查通过（包含 main 入口往返），以及六案例 Chromium、历史 Build、来源、无效 ID 恢复、实验完整分母、成本和实际无损下载通过。30 场景布局、11 场景实际滚轮和正常 main 启动器四案例/原五阶段往返均已独立通过，页面脚本错误及真实模型调用均为 0。作者 16 份材料 SHA 全部匹配；最新运行结果与六模块/主线指纹见 [本轮证据](product-integration-20261109/latest-validation/provenance.json)。本地完整公开回归已通过：1018 passed、28 deselected、1条既有依赖弃用warning，899.01秒；原始JUnit仅本地保留，公开[聚合结果及摘要](product-integration-20261109/latest-validation/public-tests.json)。最终CI以PR41最新提交的检查为准；冻结范围与标签见[Product冻结记录](PRODUCT_FREEZE.md)。

上一候选 `8bc8499` 的 [完整 CI](https://github.com/kenqia/locomo-dynamic-memory/actions/runs/42554239053)成功；上一轮本地 full 只留下中断进度，没有完整结果，不将其记为通过。以下为上一候选的历史核验记录，当前状态以本节及最终结果为准。 最新CI前两次在下载固定Python补丁版时遇504，尚未进入测试；已将CI解释器选择改为runner自带Python 3.12，保留uv锁和所有检查，记录实际补丁版本。原workflow备份于本地var/checks-before-product-ci.yml，回滚可恢复或revert。自动化原始 JSON 中的 human_review pending 是工具模板字段，不推翻独立人工记录；人类验收以绑定0401155的附件为准。


日期：2026-11-09，Asia/Shanghai。负责人授权整合 Product、最终验证并收尾。本文记录当前候选的实际验证，不代表 Delivery、Sidecar 或课程平台已完成。

## 版本与真人复核

- main 基准：`0ebb2b8f832e306c37389881b9b7187129e5311a`。
- Product 作者：Thorns-06；来源 [PR #39](https://github.com/kenqia/locomo-dynamic-memory/pull/39)，最终原始交付 `739888347e5651036a1c42040f75dbe0d8f6f456`。
- 真人非作者复核：xiaozhuozi39。证据为[本地跑通反馈](https://github.com/kenqia/locomo-dynamic-memory/pull/39#issuecomment-6723185216)、[真人截图附件](https://github.com/kenqia/locomo-dynamic-memory/pull/39#issuecomment-6730042061)，以及负责人确认其已完整复核。AI 未成功下载该 ZIP，不冒称逐张看过真人截图。
- 安全分支与 main 无共同历史，采用产品文件增量整合，保留作者原 PR 与版本来源，不将安全分支整段历史并入 main。

## 实际改动

迁入 Console、Memory/来源检查、已有 Trace、冻结实验比较、公开合成 Replay、测试、演示工具和原作者证据。正常 `personal-release start` 进入 Console；顶部“五阶段工作流”调用 main 原 `ui.py`。

main 的 `query_ui.py`、`queries.py`、`config.py`、`ui.py`、`api.py`、独立 `replay_ui.py` 及其 M5/Bonus 实现保持原字节。公共查询继续默认 Hybrid，Dynamic 显式可选。没有生产数据库迁移、新增生产依赖或付费模型调用。

整合适配包括：合成验收与快照重建显式使用 Dynamic；公开测试入口复用 main 的排除标记；浏览器脚本支持 WSL Chromium，并保留浏览器 venv 的 Python 符号链接。

## 已取得的新鲜证据

使用 WSL / Python 3.12.12、现有应用环境与独立 Playwright 环境，没有安装新依赖。

| 检查 | 实际结果 |
| --- | --- |
| 四个 Product 专项文件 | 22 passed，1 条既有依赖弃用 warning |
| 正常 Console 入口与原工作流往返 | 1 passed，1 条既有依赖弃用 warning；所有记录的 API 方法均为 GET |
| 六案例离线 Chromium | 通过；历史 Build、计划/否定、来源、四阶段、冲突/不足/失败、无效 Trace 恢复；页面脚本错误 0、外部请求 0 |
| 最终页面 Chromium | Overview/Experiments/成本/缺失 Run/Demo 通过；三维分组与无损 JSON 下载通过；1280px 主文档无水平溢出 |
| 正常 Release 启动器 Chromium | 实际启动 API 与 Console，四个合成 Trace、来源、实验与五阶段往返通过，启动器正常退出，真实模型请求 0 |
| 合成快照重建 | 新临时目录生成两个 Build、六案例，冲突/不足/引用异常/预算失败断言通过，未替换原冻结 fixture |
| 测试敏感性 | 独立副本反转 Replay 的只读条件后，既有边界测试按预期失败；未修改主候选进行中的回归 |
| 编译与 shell 语法 | `compileall`、`bash -n tests/browser/run.sh` 通过 |

完整公开回归仍在执行；本轮出现的一项 setup error 的目标测试独立重跑已通过，待全程结束后核对原始原因并记录最终结果。未把尚未完成的检查计为通过。

执行入口：

```sh
python tools/team_v2/check.py --tb=short --junitxml=var/product-main-public-tests.xml
python tools/team_v2/check.py --tb=short tests/test_product_main_integration.py
python tools/team_v2/verify_replay.py --browser-python /absolute/path/to/browser-env/bin/python --output var/new-replay-check
python tools/team_v2/verify_replay.py --browser-python /absolute/path/to/browser-env/bin/python --output var/new-pages-check --browser-script browser_product_final.py
python tools/team_v2/verify_main.py --browser-python /absolute/path/to/browser-env/bin/python --output var/new-main-check
python tools/team_v2/freeze_demo.py --output var/new-generated-fixture
```

`python` 指已安装锁定应用依赖的 Python 3.12。公开回归排除 live_model、local_embedding、controlled_data，排除项不计通过。浏览器为自动化核验，非新的人类验收签名。

## 审查与已知限制

仓库 code-review 技能的 Standards 与 Spec 两轴独立 AI 审查分别发现：快照重建器需要显式 Dynamic；默认冻结报告 JSON 需要随文档提交。前者已修复并实际重建验证，后者随本次文档完整迁入。最终提交后复查，不将 AI 审查冒充真人批准。

浏览器初轮失败包括 AppTest 对 HTML heading 的断言位置、工作流往返的页面假设、覆盖 input 的 label 与 Streamlit rerun 等待。失败日志保留于本地 `var/`；后续修正验收定位与等待后，正常入口验证通过。没有因此更改生产 Query 行为。

Product Experiments 保留历史 757 题报告，与后续 M5 结果分开；真实模型语义质量没有因本次 UI 整合重新评分。正式 MP4/PPTX/统一提交包仍由 Delivery 负责；Sidecar 真人复核也不由本次 Product 验收替代。

## 回滚

需要临时恢复原入口时，直接运行 `src/locomo_memory/ui.py`。需要完整撤销时，对最终 main 整合提交执行 `git revert` 并重跑公开回归；没有数据库回迁步骤。原作者 PR、原 main 基准及原冻结 Replay 保留可追溯记录。
