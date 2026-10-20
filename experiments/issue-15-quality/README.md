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
