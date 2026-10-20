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

## 当前边界

本记录建立时，runner 的真实 probe、完整 `conv-26` smoke 及全量评测尚未执行。恢复审查修复合入后继续运行，并在此记录实际结果。没有生成 `conv-43`、`conv-44` 的模型成绩。

GitHub Issue 和 Notion 未执行写操作；尚未找到明确关联 Issue #15 的 Notion 任务记录，不宣称已同步或已验收。
