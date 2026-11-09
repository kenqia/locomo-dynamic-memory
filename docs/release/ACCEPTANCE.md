# 个人Release实际验收

日期2026-11-05；可执行代码/测试截点`c7eae7a2f4ed667e83f2520e000e33aee7314e2b`，核心源最后变更`c7eae7a`。不以历史664/198测试数替代本次结果。测试没有真实模型请求，不重跑历史实验。

## 当前记录

| 项目 | 实际状态与证据 | 复现方式与边界 |
|---|---|---|
| Python/锁/安装 | PASS，Python3.12.12，独立Release .venv与公开tar解包独立.venv均uv sync成功 | `uv sync --locked --python 3.12`，冷安装见cold-start-sanitized-final.json |
| 编译/格式/脚本 | PASS compileall、uv lock --check、bash -n、git diff --check；仓库无配置的formatter入口，不冒称ruff/black通过 | RUNBOOK命令；未新增格式依赖 |
| 全仓适用离线pytest | PASS，991 passed / 4 deselected / 0 skipped / 0 failed，1300.91秒 | `scripts/personal-release run-tests -- --junitxml=var/release-full-final.xml`；仅排live_model/local_embedding4项，controlled_data仍运行 |
| 公开包离线pytest | PASS，937 passed / 28 deselected / 0 skipped / 0 failed，997.96秒 | 解包根目录`run-tests --public`；包内排24 controlled_data及4 opt-in；另两含上游派生案例模块30项源码不入包：991−30−24=937，不替代工作树全仓 |
| Release/API/默认/故障 | PASS，最新16 passed；非作者35专项通过 | `pytest -q tests/release tests/test_answer_repeat_experiment.py tests/test_evidence_coverage_experiment.py`；合成适配器、默认Hybrid无resolve、显式Dynamic、失败Trace/来源/DB错误 |
| M5、状态关系及开关隔离 | PASS，342项M5包含于991全仓，分模块数量见full-tests-final.json | `pytest -q tests/test_m5_*.py`及queries/relations/versions；默认关闭与显式开关分别测试 |
| Memory Schema/六段 | PASS，2031/37445/1465；六完整Build共享loader逐份通过，另六份API下载SHA、UI选择数量与Source端点均通过 | `validate-six-exports --directory <controlled memory-exports>`；schema/typed roundtrip/源时间锚/指纹/SHA，不重新写出原JSON |
| 本地真实Embedding | PASS，2 passed，opt-in离线MiniLM | 借主仓既有embedding依赖环境，`LOCOMO_LOCAL_EMBEDDING=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 ... pytest -q tests/test_local_embedding.py -m local_embedding`；不声称冷环境已下载/装载模型 |
| 普通API/UI启动 | PASS，双health/datasets/builds/OpenAPI/replay均200 | normal-startup.json；使用本轮独立DB，未覆盖历史SQLite |
| 启动失败与安全停止 | PASS，端口占用非零、杀API后停UI并非零、TERM及6次SIGINT正确回收、同端口重启通过 | independent-standards-review.json；只操作本轮自有PID/进程组 |
| 普通Web Chromium | PASS，8条评测结果/4条合成失败，page/console error0 | browser-app/issue-12-result.json及7张截图；新临时venv/DB，Mock LLM/Embedding，无真模型评分 |
| 无凭据Replay Chromium | PASS，仅GET、外域请求0、模型0，全部控件/失败Trace/JSON下载 | browser-offline/browser-result.json与3张截图；独立浏览器profile，无登录cookie |
| 归档CLI | PASS，主档/源码补档逐文件及tar成员SHA/size/order/path通过 | `verify-private-archive --manifest <manifest> --directory <archive>`；不恢复执行授权、不覆盖原件 |
| 附录构建/数据审计 | PASS构建37页/20图/文本一致；数值审计PARTIAL（282/282核对0差异，历史raw/日期/因果未全重新评分） | supplement-rebuild.json、independent-metrics-audit.json、SUPPLEMENT_ERRATA |
| 公开包/扫描/冷启 | PASS，sanitized冷启与完整公开测试通过；正式tar身份另绑定最终回执 | allowlist排var/Gold/raw；credential形状+已知Source>=80字/官方问题>=18字匹配（含Python），无全面语义隐私保证 |
| 实际账户账单/教师真值/新Bonus QA收益 | NOT_MEASURED | 不读取账单、不编造教师评分、不付费补测 |

## 保留的失败与调试过程

v1全仓：6 failed、983 passed、1 skipped、4 deselected，998.13秒。五处旧测试未显式Dynamic而走新Hybrid默认，现已明确strategy且原断言保留；一处冻结producer身份检查恰逢代码并行编辑，独立单项通过后须固定源重跑。六conversation-only快照原缺失skip，现合法本地快照就位，公开包仍排除此数据依赖。

v2全仓主动中断以定位问题：1 failed、187 passed、4 deselected；该失败为Chromium展开大型Trace时负载下AppTest默认3秒timeout。独立与全collection选择单项均通过；改为明确30秒等待，未放宽行为断言。公开冷包v1主动中断：2 failed、132 passed、31 deselected，另外一个失败缺历史真实题单plan.json；三项实际题单依赖标controlled_data，不把题单/Gold补进公共包。v3因受控标签修复主动中断并重新固定源；中断恰逢pytest fixture建立时另有清理KeyError，保留诊断，不视为完成的产品测试。最终full-final固定c7eae7a重跑，全仓保留这些测试。

普通Browser v1完整走到最后Trace展开后30秒timeout；v2收起单条大JSON后再展开完整记录、设120秒明确等待，最终成功，未跳过该操作。失败日志和临时trace保留var及本轮/tmp诊断目录；公开仅收合成成功截图与结果，不上传私密日志。

## 可复现范围

安装可访问依赖仓库；安装完成后的Synthetic Replay不访问互联网。正常真实Build需要锁定Embedding缓存及用户授权Provider。冷安装不是完整历史付费实验重算，公开包没有受控原文。`uv.lock`未改变，尚有Starlette/httpx弃用warning，当前测试通过不等于未来未锁版本兼容。

公开scan比对已知Source长字面片段与官方问题字面量（含Python），未读取私有Gold/账户凭据，也不能覆盖短人物名、改写、PDF图片文字或未知秘密形状。结合显式目录排除、Schema审查、原创Fixture及非作者复核评估；未知内容风险保留，不声称全面匿名化。

公开候选追加隐私修复：非作者发现test_answer_regressions.py含上游派生问答案例。该整份测试文件、test_imports.py（另含44字符真实Source用例）与answer-source-turns.json均从公开白名单排除，本地全仓仍保留；同文件内合成测试随文件排除，不伪称它们在公开包运行。扫描扩展至Python、官方问题>=18字符与Source>=80字符；非作者另对748个文本/PDF文件（含Python AST与JSON解码字段）严格复扫，完整Source与问题均>=18字符，0匹配。先前公开候选仅为本机rehearsal，未发布；最终公开测试使用sanitized重新解包包，数量以最终XML为准。

## 最终结论

PERSONAL_READY（本地个人候选）。全仓与公开包均0 failure/error/skip；两个独立复核分别记录Standards和Spec结论。最终tar与已测试sanitized包的src/tools/tests/锁/运行配置逐文件等价核验，以及最终封包SHA/成员校验，见staging的FINAL_ACCEPTANCE_RECEIPT.json。该回执是封包之后的外部记录，不形成包内自引用。团队交付、远端发布和受控数据披露仍有独立门禁。
