# 复现指南

## 环境

- Linux / WSL
- Python 3.12
- uv
- 离线演示不需要 API key、本地 embedding 缓存或互联网访问

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
scripts/personal-release run-tests --public
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

重新生成图表只读取冻结文件，不调用模型。不要重跑历史付费实验，也不要将已公开的留出集称为新的独立测试集。

## 数据边界

LoCoMo 原始对话和标准答案不随提交包分发。真实记忆导出仅在受控环境中使用。公开演示使用合成数据。
