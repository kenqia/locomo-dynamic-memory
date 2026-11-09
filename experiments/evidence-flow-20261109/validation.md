# 验证和独立 AI 代码审查

2026-11-09。代码审查基点 `d3c4ae10fb73d70eabea42f5333e721168574190`；功能提交 `1edb31a`，审查修正 `82f2356`、`334289d`。现有用户工作区的 20 个已跟踪改动与实施前二进制补丁逐字一致，未纳入本轮提交。

## Standards

独立子代理按 `.agents/skills/code-review/SKILL.md` 检查仓库约定与 smell baseline。初审发现复合时间范围丢前端点、审计未绑定 final lock 两项 P2；修正后的普通 `from John … and …` 反例又触发一项 P2。三项均修复并逐一复测。最终余留发现 **0**。

离线测试稳定时钟补丁经同一轴再次审查，余留发现 **0**。生产时钟、来源时间和冻结校验均未改变。

## Spec

另一独立子代理依据[本轮需求记录](../../docs/specs/evidence-flow-regression-20261109.md)审查。初审发现混合范围退化为点日期、案例包不包含完整来源两项 P2，均已修复。复查确认 20 案具备阶段流、全部 Memory、决策和引用原文，人工核查继续标记 pending。最终余留发现 **0**。

测试时钟修正和作者 AI 逐案初判也完成范围复查，未扩大生产语义，新增余留发现 **0**。以上是 AI 代码/工件审查，不是独立人工语义标签或教师验收。

## 工程验证

- 时间解析与抽取边界先复现失败，再最小修复。最终定向边界覆盖 20 项；关系审计与模型诊断补充回归 92 项通过。
- `python -m compileall -q src tests tools/m5/evidence_flow_audit.py tools/m5/time_scope_replay.py`、`bash -n tests/browser/run.sh` 和 `git diff --check` 通过。项目没有配置静态类型检查器，编译不冒充 typecheck。
- 20 案全部引用来源存在于包内，并逐字匹配已跟踪公开 LoCoMo 数据。原 generation freeze SHA 保持不变。
- 收尾时重新执行冻结审计和时间解析回放，两份 JSON 都与首次产物逐字节一致；时间解析仍为旧代码 11/21、新代码 21/21，模型调用 0。
- `pandoc`/XeLaTeX 重新生成 38 页汇总 PDF，提取文本并实际渲染、检查新增第 37–38 页；没有重画历史图表或重评分。

首轮完整公开验证有 990 通过、1 个关系审计 setup error。单独复测通过；再次全量时在另一关系恢复审计发现同类时间顺序失败，为定位而提前中断，不视作通过。[合成夹具记录](clock-observation.json)显示同一 logical attempt 的 `completed_at` 比 `started_at` 早 0.458802 秒，宿主 UTC 出现回拨。

仅离线 pytest 现使用从测试开始 UTC 锚点投影的单调时钟；`live_model` 不适用。它消除合成夹具对墙钟稳定性的依赖，不证明生产环境回拨时可以完成审计，也没有放宽真实记录的审计要求。

最终全套验证采用临时 `uv --with pytest-xdist==3.8.0` 环境，四进程按文件分配；项目依赖和锁文件未修改。上一轮进程未留下最终报告，不计作通过；本轮重新执行后得到 **1020 passed、1 skipped、0 failures/errors**，pytest 耗时 **501.35 秒**。唯一跳过项需要本机缺失的私有 M5 conversation-only 快照；5 条警告是现有 Starlette TestClient/httpx 弃用提示。此轮包含 controlled_data，排除 live_model/local_embedding。其中 10 个通过项来自原有未跟踪的 `tests/test_top7_records.py`，未纳入本次提交，不冒称它们属于远端提交测试集。结构化结果和 JUnit SHA 见[离线测试记录](offline-tests.json)。

```sh
uv run --locked --with pytest-xdist==3.8.0 python -m locomo_memory.release_cli run-tests -- \
  --tb=short -n 4 --dist=loadfile --durations=12 \
  --junitxml=/tmp/locomo-quality-20261109-backup/full-offline-tests.xml
```
