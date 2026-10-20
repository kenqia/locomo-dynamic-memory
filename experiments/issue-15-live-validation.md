# Issue #15 真实运行记录

2026-10-20。用户已确认在受保护的本机文件填入凭据。凭据仅载入独立进程环境，不进入仓库、命令参数、输出或实验导出。远端写操作未执行。

## 已通过的检查

在 integration `db70cf0` 上运行既有小型真实抽取检查：

```sh
LOCOMO_LIVE_MODEL=1 .venv/bin/python -m pytest tests/test_live_model.py -q --tb=short
```

结果为 1 passed，耗时 1.97 秒。测试通过公开 FastAPI 创建真实 DeepSeek 抽取 Build，检查 Memory 非空，并逐个读取其来源引用。该结果只证明小型抽取与来源读取可用，不证明官方对话构建或 QA 预检完成。

独立实验目录为 `/home/kenqia/my_folder/locomo-worktrees/real-baseline-issue15`，数据库为该目录下的 `memory.sqlite3`。通过 `experiment prepare` 保存了固定原件、smoke 计划和完整开发计划。计划分别包含 5 题、20 个组合，以及 757 题、3,028 个组合。

`experiment verify` 使用真实本地 MiniLM，通过固定 revision 加载、384 维有限归一化编码与超长输入拒绝检查。对应 revision 为 `c9745ed1d9f207416be6d2e6f8de32d1f16199bf`，长度政策为拒绝，设备为 CPU。机器记录位于实验目录的 `verified-preflight.json`。

## 固定实现的真实构建

恢复修复合入 `6a2918383aa10c906a2e3d350a9ccb495fe7bd1f` 后，真实 runner probe 通过。实现 SHA-256 为 `543cb6e3f768c60a8dff1cec56437e3d5d87ac0cd77a3aa560ccc8cb6c9bb40a`；之后的提交仅增加实验文档。实际请求与返回模型均为 `deepseek-flash`，请求关闭思考、温度为 0、输出上限 4,096 tokens、每次调用最多重试两次。

probe Build 为 `41cbe0b907ee4d7c983f3b24082d970f`，三个来源引用均可读取。完整 `conv-26` Build 为 `91f1f50938064972820e3ab7b390d9dd`。首次抽取完成 20/21 个片段，序号 3 的片段在三次模型调用后返回 `invalid_output`。首次失败快照位于实验目录的 `observations/conv-26-first-extraction-failure/`，保留完整 Build 和片段记录。

使用相同配置显式恢复失败片段一次后，21/21 个片段全部成功，得到 295 条 Memory；已成功片段没有重跑。真实 MiniLM 索引通过。关系阶段生成 292 个持久任务，执行中已有多项 `invalid_output`，尚未发布完整版本。具体状态以数据库及最新 `builds/<build_id>/relation-tasks.json` 为准。首次失败、恢复调用和后续所有已报告用量均保留。

只读诊断未证明具体校验失败规则，见[关系失败诊断](issue-15-relation-failure-diagnosis.md)。没有据此改 Prompt、schema、分段、生成参数或校验约束，也没有自动重试失败关系任务。

## 当前边界

五题 QA smoke 尚未启动，757 题全量入口仍受真实 smoke 门槛约束。没有生成 `conv-43`、`conv-44` 的模型成绩。当前不能把 #20 或 #21 标为真实实验完成。

GitHub Issue 和 Notion 未执行写操作；尚未找到明确关联 Issue #15 的 Notion 任务记录，不宣称已同步或已验收。
