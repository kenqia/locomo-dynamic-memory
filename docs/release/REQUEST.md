# Personal Core Release 验收规格

来源：肯恰大人于 2026-11-05 的 M5 Personal Release 总任务；截止 2026-11-09 24:00 Asia/Shanghai。

1. 在已有 codex/m5-release-integration-20261105 上，以 28ce63d 为基线增量整合 docs/supplement@3392faf，仅该目录，不改 main/其他工作树/冻结实验。
2. Python 3.12、uv sync --locked、FastAPI/Streamlit/SQLite 启动、健康、预检、安全停止、端口及子进程失败处理。
3. Hybrid 为 Release 默认，Dynamic 显式可选，既有关系/版本保留；Graph 检索、compression wire、adaptive、temporal soft priority 默认关闭。默认变更有测试、身份及回滚说明。
4. 无 key、无收费/联网/数据库依赖的 Synthetic Offline Replay，覆盖选择 Build、Memory、状态历史/关系、Graph、问题、证据、Source Turn、Trace、评测对照和 JSON 导出。不得伪装真实分数。
5. 六份原 JSON 只读验证 schema-v2、完整 build、来源/时间/关系/投影/索引/指纹/数量/SHA，与实际 Web 读取入口一致。公开只含 schema/清单/合成；受控原件在0700本地区，渠道未确认不得发布。
6. 全部个人核心及四 Bonus 有模块/入口/输入输出/开关/测试/实验/局限矩阵，外部研究后端不接默认链。
7. 研究附录 E0–E25、五阶段/RQ、失败/成本/身份保留；运行 build.sh、PDF 页数字体版面/数据来源核验，不改冻结成绩。简洁 PERSONAL_EXPERIMENT_SUMMARY 引页码/工件。
8. 索引 E0–E25，保留原始证据/成本/失败；verify-public-evidence、verify-private-archive、replay-offline-demo、run-tests 可执行。缺失如实 unavailable，禁止付费重跑。
9. 新鲜离线全仓/M5/schema/关系/开关/API/UI/浏览器/无 key/失败路径/公开扫描/冷启动验证，失败及排除透明，不用历史测试替代。
10. 独立 staging、公开代码与受控数据分包、SHA及版本；不冒充团队 PPTX/MP4/总报告。
11. 不破坏性清理。全部工作树/脏状态/目录分类清单，B 类文件SHA及已有/新增归档验证；D/E仅提议删除和容量，主仓不stash/reset/clean。
12. Product #39/#26–29、Architecture #38 opt-in sidecar审核阻塞、Delivery #34–37 接口交接，不改队友状态。
13. code-review 技能双轴非作者审阅，16项对抗性检查 PASS/PARTIAL/FAIL/NOT_MEASURED；无P0才能 PERSONAL_READY。明确团队依赖/受控渠道/远端发布状态。
14. 允许本地独立增量commit；远端仅个人分支，经权限/扫描/验证后且明确授权；不推他人/main、不合PR38/39、不覆盖历史、不正式课程提交。
