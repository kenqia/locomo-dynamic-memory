# 最终 Git 与文件清单

2026-11-05。分支 `codex/m5-final-conv44-relations-20261104`，基线 `915fac02f6b9296e331f913a1e78717cfa7e2df1`，交付内容截点 **`e369a12f2405916634e0d1b1407adb7b9110be3c`**。

- `commit-history.txt` 列出基线之后、截点可达的全部 79 个提交；完整父提交和时间见 `manifest.json`。
- `changed-files.txt` 列出基线到截点的 460 个实际差异路径（关闭 rename 推断）。`manifest.json` 对每个存续文件保存提交 blob ID、SHA-256 和字节数；删除文件保存 D/null。
- 生成时工作树 clean；全部 SHA 使用截点的真实 Git blob 计算，并要求与本地文件逐字节一致。
- 这四个清单文件在截点之后的一个仅含清单元数据提交中加入；其提交号可用 `git log -1 --format=%H -- experiments/m5-development/final-delivery-v1` 查得。该提交不是本清单内容范围，避免自引用 SHA。若有后续行为或内容改动，必须建立新截点/清单，不能复用本清单宣称覆盖。
- 只枚举当前候选祖先范围；其他分支或主仓未提交文件不属于此范围。私有 `var` 工件不纳入 Git 全文件 SHA；它们由各阶段归档 manifest 绑定。未重新读取原始日志、凭据或私有 provider body。

可复核命令（从工作树根目录执行）：

```sh
git log --reverse --format='%H %s' 915fac02f6b9296e331f913a1e78717cfa7e2df1..e369a12f2405916634e0d1b1407adb7b9110be3c
git diff --no-renames --name-status 915fac02f6b9296e331f913a1e78717cfa7e2df1 e369a12f2405916634e0d1b1407adb7b9110be3c
git status --short
```

逐文件内容以 `git show <截点>:<path>` 重算 SHA-256。六份严格 JSON 与 800项原始生成/审阅的私有归档另见 `../level-e-results-v1/private-archive-report.json`，不可据归档重启一次性生成。
