# Sidecar 离线诊断交付与冻结

2026-11-09，负责人接受公开离线诊断范围，授权整合 main 并结束本工作线。源为 [PR #38](https://github.com/kenqia/locomo-dynamic-memory/pull/38) 的 `cd4db4c055d6d57256858ed3b7136ccea395122d`；main 整合基准 `5519dd299dc561a9edcdfad8813ff7e60334a159`。完成须以实际 main 合并、完整 CI 与合并后核验记录为准。

冻结标签为 `sidecar-v0-final-20261109`，完成合并验证后指向实际 main 整合提交。代码使用 GitHub 标签下载入口；不覆盖已冻结 Product 标签。

## 采用范围

采用[ADR 0004](../adr/0004-sidecar-offline-adoption.md)：默认关闭、显式 opt-in、仅独立离线诊断。生产 API、Product Console、现有回答与证据保持原路径；不修改数据库，无新依赖或额外模型调用。

[Thorns-06 的非作者复核](https://github.com/kenqia/locomo-dynamic-memory/pull/38#issuecomment-6738293701)明确接受当前版本及已知 P2 延期；[原文归档](sidecar-integration-20261109/human-review.md)区分本人执行与 AI 辅助范围，不冒称全部案例均由真人逐项执行。原 ADR 0003 和 ARCH01–04 是历史原件，待复核措辞由当前决定及复核记录更新，原文件哈希保持。

## 快速复现

在 Linux/WSL 项目根目录，使用已安装锁文件依赖的 Python 3.12 环境：

```sh
uv run --locked python tools/team_v2/check.py tests/test_sidecar_schema.py tests/test_sidecar_core.py tests/test_sidecar_io.py tests/test_sidecar_research.py tests/test_sidecar_compare.py tests/test_sidecar_release.py tests/test_sidecar_adjacent_research.py --tb=short
uv run --locked python -m tools.research_v2.sidecar_compare --output var/new-sidecar-comparison --repeats 2
uv run --locked python -m tools.research_v2.sidecar_compatibility --output var/new-sidecar-compatibility
```

输出目录必须不存在，重跑时改用新路径。前两份报告使用冻结合成输入；兼容入口新建并清理两份合成 Build，均不读取活动数据库或调用真实模型。研究包装器使用 `research_view(original_response, snapshot, enabled=True)` 显式诊断，默认不运行。

本次 main 基准上 183 项专项通过（1 条既有依赖弃用 warning）；16 冻结例保留 15 合法比较及 1 契约拒绝，原响应、引用和输入均不变；两份合成 Build 兼容通过、临时库已清理。完整公开回归使用现有 `Checks` CI，排除 live_model/local_embedding/controlled_data，结果链接记录在整合 PR。本次运行输出与摘要见[验证目录](sidecar-integration-20261109/validation.json)。

## 已知限制

- 时间修饰 P2 延期：last/next year 年份修饰及限定词空白归一化仍可能被忽略。它没有被标成已修复。
- 真实历史导出与 68 参考的成员独立复验未执行；现有研究的 503 Memory/63,057 对全 unknown、有效覆盖 0，不支持真实 QA 收益结论。真实 QA 接入排除于本轮采用范围。
- Windows 完整公开入口仍有历史 fcntl/resource 依赖限制；Windows 专项通过不等于完整回归通过。

## 回滚

停止离线 CLI 或传 `enabled=False` 即不运行诊断。需要整体移除时，对 main 的实际整合合并提交使用 `git revert -m 1 <merge-commit>`，经正常复核后合并；无数据库恢复或依赖降级步骤。
