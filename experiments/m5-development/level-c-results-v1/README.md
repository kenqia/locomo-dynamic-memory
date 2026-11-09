# Level C 公共结果工件

固定四开发对话80普通+20诊断、Hybrid/Dynamic共200项：151成功、49输入失败。生成冻结后才读取开发Gold；独立AI来源审阅200项完成，不是人工/教师真值。实际报告见 docs/m5-development/LEVEL_C_RESULTS.md。

metrics-summary.json、per-question-metrics.json、failures.json、source-manifest.json以及原sha256-manifest.json保留数值汇总生成时的快照。metrics-summary中的semantic_source_support=pending_independent_review是当时状态；后续完成的来源审阅见semantic-review-summary.json、semantic-paired-differences.json及semantic-review-provenance.json，不改写原数值快照。complete-sha256-manifest.json覆盖当前整个目录（不含自身）。

raw-results-archive-manifest.json记录私有206成员归档的SHA和逐成员回读校验。原始答案、来源、Gold中间件、Trace和审阅引文均未提交Git。两臂共同成功或可判断的配对子集有选择偏差，不能替代包含49失败的完整分母结论；本轮不是新的757题或留出成绩。
