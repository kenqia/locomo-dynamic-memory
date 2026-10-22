# Issue 15 审查修复验证

日期：2026-10-20。基于 Standards/Spec 双轴审查，修复 P1、P2 和 P3。未读取真实凭据，未调用真实模型，未执行远端写操作。

- P1：真实 SQLite 触发器在 provider 接受请求后拒绝结果提交。修复前公开 Run 显示 unknown=0（失败）；修复后标为 unknown，默认恢复不调用 provider，显式 retry_unknown 后保留 unknown/succeeded 两次尝试。执行结束和后端启动均在独占所有权下修复遗留 running 项，包括已标 interrupted 的 Run。
- P2：受控 HTTP transport 在后端创建 Build/Run 后丢弃响应。只读 recover 能发现相关候选，显式 resource ID 接纳后原命令接续；同数据同对话但无对应 token 的 Build 被拒绝。重复 token 创建的回归先失败（Build 返回202、Run 返回201），修复后两者返回409且不创建第二资源。无 token 的旧未知记录明确拒绝认领并保留证据。
- P3：Run 和 preflight 复用同一个 implementation_sha256 函数。

最终针对性命令（在修复 worktree，使用 integration 的现有环境）：

```sh
PYTHONPATH=src /home/kenqia/my_folder/locomo-worktrees/issue15/.venv/bin/python -m pytest tests/test_experiment.py tests/test_evaluation_recovery.py -q
```

结果：22 passed，46.89 秒。已有 Starlette TestClient 弃用警告 1 条。compileall 和 git diff --check 通过。最终完整回归及真实 smoke 由集成阶段继续执行；本记录不宣称真实实验完成。
