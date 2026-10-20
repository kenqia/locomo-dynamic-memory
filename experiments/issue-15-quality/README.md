# 动态记忆质量增量

本阶段依据 `docs/decisions/dynamic-memory-quality-interview.md`，逐项保存身份和结果。
既有 integration 工作在本地检查点 `8258f03` 保留，未发布远端。

## A：抽取示例

- 红测：新增公开构建 API 检查在 extract-v1 下失败。
- 受控验证：`.venv/bin/python -m pytest tests/test_extraction_examples.py tests/test_builds.py tests/test_contract_recovery.py -q --tb=short`，32 passed。
- 编译：`.venv/bin/python -m compileall -q src tests` 通过。项目没有静态类型检查器，编译不等于类型检查。
- `extraction-real.json` 保存四个不同于 Prompt 示例的合成语句的真实结果及实现身份。
  共新增4次，原Campaign累计342/1000，尚需独立语义复核，不称人工真值。
- 有限验证通过现有安全 launcher 和原 `campaign.sqlite3`，没有重建额度或修改旧Build。

后续增量和总回归结果随实施记录，不把本节覆盖范围推断为总体质量。

## B：关系候选

公开API红测复现旧同键事实被近期24条计划挤出。新选择器覆盖默认20及小上限1、2，
事实保护、跨键过程、去重与失败重试名单保持一致，3项通过。既有关系与契约定向38项通过。
第一次测试读取任务列表时只取默认前20项，导致检查错误任务；改用公开分页limit=100，
未改变实现来迎合该错误断言。

`candidates-real.json` 保存原v5只读源的73/91在新候选策略下的有限回放。
新增2次，累计344/1000；历史数据库哈希核验且不写回。它不验证172，也不表示语义关卡已过。
