# M5 实验复现入口

在独立开发工作树执行。应用解释器为 /home/kenqia/my_folder/locomo-dynamic-memory/.venv/bin/python，Python 3.12.12。全量测试入口：

    ./tools/integration/check.sh tests -q

757题回放、盲审评分、真实数据Browser与只准备预算的完整命令见 docs/m5-development/EXPERIMENT_PROTOCOL.md。所有新输出使用未存在目录；既有历史SQLite只读打开。详细原文、导出、审阅和真实截图在忽略的var/m5-development，克隆代码不会自动获得这些文件。

最终结果以delivery-final-v2、delivery-analysis-final-v2、dynamic-review-final-v2为准。dynamic-review-v1的未执行有效选择0%已纠正，旧件只作审计。delivery-v1最初4个parity差异按失败行would-be上下文补充核对为757/757，不修改历史运行状态。

详细gzip与原始详细逐题文件仅本地保留，SHA和压缩往返清单在analysis目录；不将原文或派生私有描述提交Git。紧凑per-question-metrics用于逐题统计复核。

holdout-extraction-proposal-final.json是已单独批准并执行的18USD/204次抽取阶段；初次75次、1失败片段，唯一获批恢复后累计78次且仍失败，最新见live-extraction-post-recovery-v1.json，不能重跑原抽取或恢复目录，合成smoke不代表真实抽取。最终独立代码批准尚缺，不能据测试通过声称Release已冻结。


最后一轮补充：显式requested_date排序、预算并发/金额拒绝及synthetic取消计划/共同参与者回归，命令和限制见EXPERIMENT_PROTOCOL。只读关系预估tools.m5.relation_preflight使用已接受Memory快照；不启动Provider。日期修复mutation仅修改隔离副本，证据date-priority-mutation.json，生产源码不变。
# 留出离线索引与关系阶段准备（2026-11-04）

以下命令从M5开发工作树运行。输出目录必须未存在；已运行的holdout-local-index-v3和conv43-relation-proposal-v1不要覆盖。

真实缓存MiniLM索引复验，禁止下载和Provider请求：

    PYTHONPATH=tools/integration/offline_guard:src:. HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false /home/kenqia/my_folder/locomo-dynamic-memory/.venv/bin/python -m tools.m5.holdout_index --stage var/m5-development/holdout-extraction-proposal-final-v2 --output var/m5-development/NEW-INDEX

关系阶段离线准备，不构造模型请求、不读取留出QA：

    PYTHONPATH=tools/integration/offline_guard:src:. /home/kenqia/my_folder/locomo-dynamic-memory/.venv/bin/python -m tools.m5.holdout_relations --index-stage var/m5-development/holdout-local-index-v3 --output var/m5-development/NEW-RELATIONS

定向工程验证：

    ./tools/integration/check.sh tests/test_m5_holdout_relations.py tests/test_m5_budget.py tests/test_relation_diagnostics.py -q
    LOCOMO_LOCAL_EMBEDDING=1 PYTHONPATH=tools/integration/offline_guard:src:. HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false /home/kenqia/my_folder/locomo-dynamic-memory/.venv/bin/python -m pytest tests/test_local_embedding.py -q

关系阶段已获用户明确独立授权，正在原session85918执行，不得重复启动。范围、上界和一次性要求见docs/m5-development/HOLDOUT_RELATIONS.md；该阶段只到related，不发布或QA。

## 已冻结Level C的只读复核

以下入口不调用模型、不重新读取Gold。已有输出不可覆盖，示例的新路径须不存在；原始stage与审阅文件为私有本地工件。Level C已生成、冻结、评分及完成200项独立AI来源审阅，禁止重新执行execute-authorized。

```sh
PYTHONPATH=tools/integration/offline_guard:src:. /home/kenqia/my_folder/locomo-dynamic-memory/.venv/bin/python -m tools.m5.level_c_audit --stage var/m5-development/level-c-preparation-v1/final/final-v2 --output var/m5-development/NEW-LEVEL-C-AUDIT.json
PYTHONPATH=tools/integration/offline_guard:src:. /home/kenqia/my_folder/locomo-dynamic-memory/.venv/bin/python -m tools.m5.level_c_results --stage var/m5-development/level-c-preparation-v1/final/final-v2 --output var/m5-development/NEW-LEVEL-C-NUMBERS
PYTHONPATH=tools/integration/offline_guard:src:. /home/kenqia/my_folder/locomo-dynamic-memory/.venv/bin/python -m tools.m5.level_c_semantic_review score --stage var/m5-development/level-c-preparation-v1/final/final-v2 --review-dir var/m5-development/level-c-source-review-v1 --reviews var/m5-development/level-c-source-review-v1/merged-reviews-v1.json --output var/m5-development/NEW-LEVEL-C-SEMANTIC.json
```

三个新工具的synthetic验证分别为24、36、7项通过，非作者报告见LEVEL_C_AUDIT_CODE_REVIEW_V1、LEVEL_C_SEMANTIC_CODE_REVIEW_V1和LEVEL_C_RESULTS_REVIEW_V1。无需为复现数字再次调用Provider。完整公共结果哈希为level-c-results-v1/complete-sha256-manifest.json；原四数字文件及初始manifest不改写。

用户随后确认最终评测版本DeepSeek-V4.1-Flash-1017、全链thinking disabled，记录见final-model-requirement-v1.json及docs/m5-development/MODEL_REQUIREMENTS.md。旧Level C的resolution low、原关系阶段high如实保留，不作为全关闭的最终成绩；本确认不批准新付费阶段或读取留出答案。
