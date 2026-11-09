# 验证与独立 AI 审查

2026-11-09。审查固定基点 `b3c9d0f4f4929de55df714523fff2edcd28f6548`；本轮提交 `4243c57`、`3be7910`、`911ed2c`。实际付费运行器为 `3be7910`，最后一项仅离线修复，未重跑付费结果。

## Standards

按本地 code-review 技能，由非作者 AI 子代理检查仓库约定及 smell baseline。初审指出停止状态未跨生成/审阅阶段继承，已经持久化全局停止标记；并补全冻结身份门禁。消息哈希的初审疑问经实际 wire 转换核对后撤回，现另存 transport 消息哈希。最终代码复查余留 P0–P2 **0**。

独立工件复核确认：公开文件未命中凭据形态；盲包内 54 个 Source 的 speaker/text 全部逐字匹配已跟踪公开 LoCoMo；实体判断保留原文依据。原始生成及历史 Memory 包含错误，允许用于诊断，不称整体语义验证通过。

## Spec

另一非作者 AI 子代理按用户请求与 PROTOCOL 复核。初审指出读 Gold 前未验证审阅冻结/包/盲钥，及缺少共同成功子集；均修复。最终代码与冻结工件复查余留 P0–P2 **0**。确认两固定源码、实际 runner、plan/generation/review/jobs/results 哈希匹配，62 次调用的 planned/actual wire 消息哈希一致。

文档复查指出人工作业版顶层查询 `time.origin/query_interval` 可能泄露新旧身份。已从可读 HUMAN_OUTPUTS 移除该控制元数据，保留问题、来源日期、答案解释、Memory 自身时间；填写说明要求先看此版，之后再看原始包/AI/揭盲。原付费审阅包冻结不改，报告明确其仅隐藏臂标签，结构仍可能提示身份。内容差异仍不能保证审阅者无法猜测变体。

以上是 AI 代码/工件审查；AI 日期漏检、两条恢复抽取未引指代语境均另行披露。用户独立人工核查 **pending_user**，没有伪造真实成员标签或验收。未找到本轮关联 Notion 任务，未同步或标记团队任务完成。

## 回归测试

新增测试在用户预先认可的公开边界进行：真实 QueryService 固定检索回放；生成全局停止后不再发审阅请求；审阅包篡改时 score 在读取 Gold 前拒绝；零来源拒答可以合法无引文。最后一项通过 MockTransport 先复现失败再修复，定向 live_boundary 与预算测试 **9 passed**，没有实际模型请求。

零来源的旧审阅门禁要求所有项都提供引文，是可复现缺陷。`911ed2c` 只在存在来源时要求引文；原两批 invalid_output 继续保留，没有读取无效原始输出来证明这是它们唯一失败原因，没有补跑覆盖历史。

最终新鲜全套离线验证：**1024 passed、1 skipped、0 failures/errors、5 warnings，464.35 秒**。覆盖 controlled_data，排除 live_model/local_embedding；skip 为缺少私有 M5 conversation-only 快照，warnings 是现有 Starlette TestClient/httpx 弃用。临时 uv overlay 使用 pytest-xdist 3.8.0，未改项目依赖/锁文件。包含原有未跟踪 tests/test_top7_records.py 的 10 项，不将其冒称本轮提交内容。命令、JUnit SHA 和分母见 [offline-tests.json](offline-tests.json)。

```sh
uv run --locked --with pytest-xdist==3.8.0 python -m locomo_memory.release_cli run-tests -- \
  --tb=short -n 4 --dist=loadfile \
  --junitxml=/tmp/locomo-quality-20261109-backup/live-boundary-final-tests.xml
```

`python3 -m compileall -q tools/m5/live_boundary.py tools/m5/live_boundary_worker.py tests/test_live_boundary.py` 与 `git diff --check` 通过。项目未配置静态类型检查器，compileall 不冒充 typecheck。对原 20 个已跟踪用户修改与实施前二进制补丁逐字节比较一致，保留且不提交。

## 文档与工件

同步根 README、个人实验总结、实验索引、Release清单、M5实验结果/Level E后续说明、错误分析及附录勘误。Pandoc/XeLaTeX 重建 **39 页** PDF，提取新增页文本，实际渲染检查第38–39页，表格与正文可读；没有重画历史图或重评分 E0–E25。

旧 evidence-flow/provenance 的38页 PDF SHA 对应 Git `b3c9d0f` 快照，继续保留；当前39页 PDF身份由 [provenance.json](provenance.json) 单列。人工CSV仍保留18行空白真实标签，不覆盖用户填写。
