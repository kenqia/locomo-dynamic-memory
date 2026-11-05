# Input v2 后处理复现

在 `/home/kenqia/my_folder/locomo-worktrees/m5-final-input-v2-20261104` 执行。使用现有虚拟环境和离线网络守卫，不加载模型凭据。需要既有本地私有 stage 和完成的审阅包；本页不启动 Provider，不授权重新生成或重新评分留出。

```sh
export PYTHONPATH=tools/integration/offline_guard:src:.
LC_PYTHON=/home/kenqia/my_folder/locomo-dynamic-memory/.venv/bin/python
LC_STAGE=var/m5-development/level-c-input-v2-preparation-v1
LC_REVIEW=var/m5-development/level-c-input-v2-source-review-v1
LC_PUBLIC=experiments/m5-development/level-c-input-v2-results-v1
```

## 只读检查已有冻结和审计

以下命令不创建输出，不读参考 Gold 库，失败时停止。

```sh
"$LC_PYTHON" - <<'PY'
import json
from pathlib import Path
from tools.m5.level_c_audit import audit
stage = Path('var/m5-development/level-c-input-v2-preparation-v1')
fresh = audit(stage)
assert fresh == json.loads((stage/'terminal-audit-v1.json').read_text())
print({'items': fresh['items'], 'requests': fresh['ledger']['physical_ledger_requests'], 'audit_matches': True})
PY
```

生成后实际执行过 `tools.m5.level_c.score(stage)`，先检查完整 freeze，再通过 SQL 投影读取四开发对话 Gold，输出 `scores.json`。此原件已保留，不需要再次打开 Gold。

## 用已保存分数重算数值

替换下方路径为一个尚不存在的私有输出目录。结果包含每题数值，不含原文，不调用 Provider，也不重新读取 Gold。

```sh
"$LC_PYTHON" -m tools.m5.level_c_results \
  --stage "$LC_STAGE" --output /absolute/new/private/input-v2-numeric-check
```

## 校验独立来源审阅

以下命令验证本阶段新 manifest、200 唯一单位、固定来源归属和逐字引文。它不自动生成或修正语义标签。`score` 只接受全部 200 项完成；不确定和运行失败仍显式保留。若指定 `--output`，使用 stage、review 之外的新路径。

```sh
"$LC_PYTHON" -m tools.m5.level_c_semantic_review validate \
  --stage "$LC_STAGE" --review-dir "$LC_REVIEW" \
  --reviews "$LC_REVIEW/independent-reviews.json"
"$LC_PYTHON" -m tools.m5.level_c_semantic_review score \
  --stage "$LC_STAGE" --review-dir "$LC_REVIEW" \
  --reviews "$LC_REVIEW/independent-reviews.json"
```

## 一次性发布补充工件和私有归档

下面两步用于本阶段首次发布，已存在时主动拒绝覆盖。重新复现时先在另一个本地副本调整独立目的路径，不删除旧档。

```sh
"$LC_PYTHON" "$LC_PUBLIC/summarize-review.py"
"$LC_PYTHON" "$LC_PUBLIC/archive-private.py"
```

补充脚本先运行现有完整 `score`，核对已公开语义 summary 全对象相等，然后输出同题确定支持差值和来源身份。归档脚本用文件白名单和 SQLite backup 包含已提交 WAL，归档文件创建权限为 `0600`，逐成员回读并检查原始文件及数据库逻辑快照前后未变。不包含 WAL/SHM、锁、原始进程日志或凭据；生成的 tar 只保存在忽略目录。

## 已完成的针对性测试

生成／审计：52 passed；非作者定向子集：24 passed。后处理合成夹具修复后实际执行下列命令，43 passed、1 项既有 warning。当前无生产源码改动，没有再次运行全仓测试；原分支全仓 664 passed／4 deselected 属于原时点记录。

```sh
./tools/integration/check.sh tests/test_m5_level_c_semantic_review.py tests/test_m5_level_c_results.py -q
```
