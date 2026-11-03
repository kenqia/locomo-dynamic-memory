# 本次归档验证

本次只验证公开档案和已存在的离线代码，不执行历史模型实验、重建Build或读取运行数据库。

| 检查 | 新鲜结果 |
| --- | --- |
| E6原有合成纯函数测试 | 17 passed，1集成用例明确排除；0.40秒 |
| 研究分析/Router/Cache受控回归 | 最初45 passed/1 failed（官方语料未公开）；排除该依赖语料用例后45 passed/1 deselected；2.16秒 |
| 警告 | 既有Starlette/httpx弃用警告1条 |
| 历史全套/Embedding/模型/完整浏览器 | 本次未执行；既有报告中的测试数属于当时版本，不能当作本次重跑 |

E6合成测试原件逐字节保存到 [历史测试](code/test_phase4_resolution.py)，新增 [编码源码](../../tools/research_v2/resolution_planner.py) 与来源commit一致。排除的test_real_queryservice_mock_injection_keeps_answer_and_default_rollback依赖较新的Research QueryService/phase4_offline，未把研究生产代码带入本归档分支。

分析测试首次失败为test_offline_preparation_reuses_the_official_plan_and_refuses_started_runs；invalid_official_data来自安全分支故意不含官方数据，不下载/补上传数据来凑全绿。两次JUnit在本地私有归档保留，公开摘要不携带临时路径和日志。

命令在本分支根目录运行：

    ./tools/integration/check.sh docs/research-process/code/test_phase4_resolution.py -k "not real_queryservice" -q
    ./tools/integration/check.sh tests/test_research_v2.py tests/test_phase3_router.py tests/test_phase3_cache.py -k "not test_offline_preparation_reuses_the_official_plan_and_refuses_started_runs" -q
    python3 tools/research_archive_check.py

后一个检查核对全部白名单SHA、JSON、公开Markdown文件链接、42条唯一探索身份、163份来源及基线/配对/补充/修复/E6的统计一致性。它不是语义评分或人工审核。

[发布审计](publication-audit.json)记录所有可达祖先和blob扫描结果；扫描中间提交，不能只看最终目录。检查高置信凭据模式、带认证URL及禁止路径。ALLOW仅来自白名单；原受控source commit不成为祖先。原文件路径在分类索引出现仅为元数据，不代表上传内容。

每个公开文件均有AI审阅类型、来源/生成方式、许可证依据及SHA。新增文本逐项核对；继承源码复用六天冲刺已审白名单，另对全部可达内容做发布扫描。没有独立人类出版审核；无LICENSE不会擅自改为MIT/Apache。

[保护核验](preservation.json)检查工作树HEAD/status和可安全读取的非runtime文件；活动DB、账本、敏感材料按禁止规则不读取/复制，因而不声称其字节哈希已在本次重验。

[返回入口](README.md)
