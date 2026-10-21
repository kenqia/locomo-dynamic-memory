# 暂时回退 P0/P1，保留 P2

2026-10-21，Asia/Shanghai。用户依据真实实验效果，明确要求撤销
`35bfcc8`、`982c44c`、`439fe93`，恢复更容易解释的旧行为。
回退起点为 `3841cac`，工作分支为 `codex/issue-15-integration`。

[真实复验分析](../issue-15-evidence-coverage-live/results/analysis.md)未验证到稳定提升：
QA 3 的完整关键组仍超预算，QA 15 额外补查时丢失原有支持。
本次按指定范围回退，不引入新的排序、枚举策略或预算例外。

## 当前行为

- 证据组按原顺序装入预算，不再按问题词面相关度重排。
- 整体或任一 coverage 项不足时才检索一次原文，有命中时联合解析一次。
  sufficient 不会仅因 activities、hobbies、list 或礼貌枚举问法触发补查。
- 原文 BM25 恢复仅匹配正文，不额外加入 speaker 或所有格去后缀词。
- 同维度、关系和 coverage 的完整分组、预算限制及遗漏审计继续保留。
- 保留 `c071cf1` 的 P2。没有可回答子问时提示使用 `No information available.`；
  真正的部分答案保留直接事实和引用，相关背景及缺口放在 explanation。

相关实现回归测试随被撤销提交还原；P2、旧支持保留、冲突、来源、预算及相对时间回归继续保留。
旧实验成绩及其检查记录均为对应历史实现的结果，不改写为回退后的成绩。

## 回退方式与身份核对

使用 `git revert --no-commit 439fe93 982c44c 35bfcc8`，保留原提交和全部实验历史。
撤销 `982c44c` 时两处 Prompt 版本声明冲突，解决时恢复旧解析版本，
保留 P2 回答版本。`git revert --continue` 生成的 `fe13a72` 同时包含
`439fe93` 与 `982c44c` 的反向变更；`f0006ae` 撤销 `35bfcc8`。

逐字节核对以下文件与 P0/P1 之前的 `4fc38d0` 一致：

- `src/locomo_memory/evidence_selection.py`
- `src/locomo_memory/raw_queries.py`
- `src/locomo_memory/raw_retrieval.py`

`query_schemas.py` 和 `tests/test_answer_regressions.py` 与 P2 提交 `c071cf1` 一致。
其余源码相对 `4fc38d0` 的差异仅为保留的 P2 规则和回答版本。
回退后源码身份为 `667d8b4a7ab835168405bb315a8a6c2b0affcdfd8926cfbccd7120f7a3d76f0b`。
不修改旧 Run、计划、指纹、构建或账本；此身份不能用于恢复旧付费实验。

## 验证

定向验证 60 passed，耗时 47.81 秒，包含旧查询行为、P2 及历史实验报告测试。
全量非 live 回归 **379 passed、4 deselected，259.68 秒**。
编译及差异检查通过，只有既有 Starlette/httpx 弃用警告。
项目未配置静态类型检查器，没有新增依赖。

```sh
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 OMP_NUM_THREADS=2 .venv/bin/python -m pytest tests/test_raw_queries.py tests/test_answer_regressions.py tests/test_queries.py tests/test_focused_queries.py tests/test_evidence_coverage_experiment.py -q
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 OMP_NUM_THREADS=2 .venv/bin/python -m pytest -q -m 'not live_model and not local_embedding'
.venv/bin/python -m compileall -q src tests
git diff --check
```

本轮没有付费调用、真实 Embedding 或浏览器端到端验证，不将受控测试通过解释为真实质量提升。
未 push、创建 PR 或更新 GitHub/Notion。后续若重新引入这些优化，可反向撤销本次回退提交，
但需先完成新的受控验证和效果核查，不能继承旧实验的通过结论。
