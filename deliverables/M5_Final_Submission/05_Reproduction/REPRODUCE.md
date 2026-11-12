# 复现指南

## 环境

- Linux / WSL
- Python 3.12
- uv
- 锁定依赖安装完成后，离线演示不需要 API key、本地 embedding 缓存或互联网访问；首次 `uv sync` 可能需要网络

先将 `source-code.tar.gz` 解压到新目录，以下命令均在该源码目录执行。`SOURCE_VERSION.json` 记录实际源码版本；解压目录中的 `SUBMISSION_SOURCE.json` 记录逐文件哈希。

## 一键启动离线演示

在仓库根目录：

```bash
uv sync --locked --python 3.12
uv run --locked python tools/team_v2/demo.py replay
```

浏览器打开 `http://127.0.0.1:18501`。

该模式读取公开合成快照，不连接研究数据库、不调用模型、不产生 API 费用。画面中的 Experiments 页为 E12 历史运行结果，不是 E25 最终留出实验。

## 测试

公开离线回归：

```bash
uv run --locked python tools/team_v2/check.py --tb=short
```

提交快照排除了依赖原始对话的 `test_answer_regressions.py`、`test_imports.py` 和对应原文 fixture，沿用已有公开打包规则。该快照可收集 1,171 项离线测试；完整研究 worktree 的 1,201 项结果另行记录，两者不混报。

逐文件验证源码快照：

```bash
uv run --locked python -m locomo_memory.release_cli verify-public-evidence --manifest public-evidence-manifest.json --directory .
```

Sidecar 离线专项测试（独立诊断）：

```bash
uv run --locked python tools/team_v2/check.py tests/test_sidecar_schema.py tests/test_sidecar_core.py tests/test_sidecar_io.py tests/test_sidecar_research.py tests/test_sidecar_compare.py tests/test_sidecar_release.py tests/test_sidecar_adjacent_research.py --tb=short
```

## 实验结果复核

- E25 冻结逐题分数：`experiments/m5-development/level-e-results-v1/official-scores.json`
- E25 请求、用量、耗时与失败：`experiments/m5-development/level-e-runtime-terminal-v1.json`
- 图表生成：`deliverables/m5-final/figures/make_figures.py`
- 图表输入与输出哈希：`deliverables/m5-final/figures/figure-provenance.json`

重新生成图表只读取冻结文件，不调用模型。图表脚本另需 Matplotlib（原生成环境为 3.11.2）；它不属于应用运行依赖。证据损失图读取 `deliverables/m5-final/figures/evidence-flow-summary.json` 中的聚合数字，原始摘录留在研究归档，不随源码快照分发。不要重跑历史付费实验，也不要将已公开的留出集称为新的独立测试集。

## 数据边界

LoCoMo 原始对话和标准答案不随提交包分发。真实记忆导出仅在受控环境中使用。公开演示使用合成数据。

## 重建材料包

在完整交付 worktree 根目录执行，输出目录必须尚不存在：

```bash
python deliverables/m5-final/tools/package_submission.py --output /tmp/m5-submission-rebuild
```

脚本验证已有公开证据清单中的全部哈希，复用现有隐私扫描，再生成源码归档、材料目录、校验清单与 ZIP。脚本不执行远端发布或课程提交。源码快照包含应用及其验证材料；重建报告和完整课程包仍使用完整交付 worktree。
