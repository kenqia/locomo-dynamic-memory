# 独立 Level E 入口的代码复核

2026-11-05（Asia/Shanghai）。Standards 与 Spec 两轴最终均为 0 项未解决发现。本报告仅覆盖入口代码、合成验证及隔离纪律；第六份完整 JSON 尚缺，最终系统配置未锁定，真实 Level E 未 prepare、未授权、未执行。真实留出 QA、evidence 和 answers 未读。

## 实现与边界

新增 `tools/m5/level_e.py` 和 `tests/test_m5_level_e.py`，复用现有查询、基线、评分与 BudgetTransport；没有修改核心 producer 或添加依赖。入口分为 `prepare`、`execute-authorized`、`score`。它不创建最终配置锁或费用授权。

`prepare --final-lock <final-system-lock.json> --output <fresh-stage>` 要求六份严格 complete 导出、两份 conversation-only Build 源、完整 Settings、producer SHA、实现 commit、参考库 main/WAL 身份和两段完整 ordinal 身份。真实锁定时，仍需独立核对 commit 与 producer 文件内容相符；入口只校验 commit 字段格式及当前 producer SHA，不替代这项实际审计。

入口先验证所有导出、Build 副本与原始轮次内容身份，再用 SQL 只投影留出 question。原参考库不进行全表快照或 backup。独立 Build 执行库不含 QA 或辅助标注。全部 `2N` 项保留成功、失败与 Unknown；生成冻结绑定计划、逐项输出、授权、启动 marker 与最终账本。中断没有完整 freeze，禁止自动重启。`score` 在核完冻结身份后才精确读取相应原始 ordinal 的 Gold。

两臂为 Hybrid 与 Dynamic，Bonus 关闭；新生成均为 `deepseek-flash`、thinking disabled、无 reasoning_effort；物理输入上限 640,000 UTF-8 字节，完整 resolve 预算 192,000 代理 tokens，输出上限 32,768。设两段完整问题总数为 N，独立请求硬上限为 `15N`，按峰价计算的费用硬上限为 `USD3.469824 × N`。N 尚未从真实留出问题读取；这不是现成付费授权，旧额度不转移。

## Standards

非作者初审发现 1 项 P2：复用的 bootstrap helper 把结果范围固定标成四个开发对话。修复在新入口内覆盖 scope，明确所选两段留出、按题重采样及不支持对话级泛化；未修改冻结 helper。最终静态复核未发现未解决标准问题或需要单列的 smell。

## Spec

非作者初审发现 1 项 P2：类别 5 literal refusal 与类别 1–4 F1 只有混合总体均值。修复新增两组独立绝对得分、完整与成功计分分母及配对差，混合指标明确标注其组成且不等同事实正确率。合成类别 5 失败保留在分母并记零。最终 Spec 复核通过。

入口输出主评分与分阶段 Source Recall 代理、逐题/逐对话/逐类别配对统计及失败率差。分臂成本、延迟、资源、token 效率、来源事实支持、人物/事件/时间错误和拒答事实审阅仍需生成冻结后的免费审计。缺少独立真值的关系、有效选择及原子事实指标保持 `not_measured`，不把入口测试称为完整实验报告。

## 新鲜验证与文件身份

- 作者最终运行 `./tools/integration/check.sh tests/test_m5_level_e.py -q --maxfail=1`：21 passed，97.59 秒。
- 非作者对修复运行针对性验证：5 passed、16 deselected，22.07 秒。首次漏设 PYTHONPATH 导致收集失败且 0 测试，修正后通过。
- 根代理在修复前完整复验初版：16 passed，93.13 秒；该历史结果不替代修复后的验证。
- 上述 pytest 仅有既有 Starlette/httpx 弃用 warning；未发起真实 Provider 请求。

最终工具 SHA 为 `f9627d91610f7cf36a3c6a0f2b179d7a1dda08f1fee88b728e9831b6d07d0fd4`，测试 SHA 为 `a96df547dd93028f50b5c714965ef5e6aa2c20bb3cdc5a28aa66907bb586a7e4`。

真实六份导出、最终配置锁定、实际 questions-only 准备及精确预算仍须另行验收。回滚时停止引用新入口与其独立 scratch，保留计划、结果、失败和账本。没有 push、PR、main 合并或部署；未识别关联 Notion，未同步或标记总任务完成。
