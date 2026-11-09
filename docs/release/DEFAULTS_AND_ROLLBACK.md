# Release 默认策略、配置和回滚

2026-11-05，明确的Release增量，与冻结实验producer分开。

| 入口 | 默认 | 显式可选 | 不自动执行 |
|---|---|---|---|
| 页面 / `POST /queries` | hybrid_no_resolution | dynamic / dynamic_raw_fallback | Graph多跳、compression wire、adaptive、temporal soft priority |
| 内部历史QueryRequest | dynamic（兼容历史工具） | 由调用方固定 | 不受公共默认变更影响 |
| 只读Replay | 预录文件，无生成 | Graph浏览/可逆分组展示 | Build/Resolve/Answer/评测执行全部不可用 |

`query_api.PublicQueryRequest`仅改变公共请求省略strategy时的默认，`query_ui`默认同步。
`release_queries.hybrid_query`直接调用现有`EvaluationService.baseline(...,'hybrid_no_resolution')`，固定完整Build、保存成功/失败Trace及实际调用/送出证据，不把Answer上下文当有效Memory。
现有Dynamic解析、Prompt、关系规则、模型算法未重写。旧调用方如果依赖省略strategy的Dynamic行为，现在应显式传`strategy='dynamic'`。
旧Dynamic回归测试因此明确策略而保留全部原断言；Release专项额外验默认无resolve、显式Dynamic有resolve、状态未变、失败Trace保留上下文。

修复Hybrid历史评测实现中`requested_date`未优先采用的缺口，并把日期传给扩展。旧冻结结果未重算；E仍对应0dbd98e7...的producer，不能称当前Release与该producer逐文件完全相同或有新泛化QA成绩。
没有擅自提高Dynamic预算：应用设置仍resolution_input_budget=24000，关系thinking=high、resolution=low是历史默认；Level E的640000bytes/192000代理tokens和disabled是独立实验锁，并非未声明地迁移到新应用。选Dynamic仍可能在长输入明确失败，Trace保留；这属于已知限制。

统一启动器只新建0700运行目录和0600TOML快照，记录选择的DB路径。默认新DB=`var/personal-app/memory.sqlite3`；原配置、研究SQLite、uv.lock未覆盖。默认不下载Embedding。

## 回滚

1. 用户只需要旧问答行为时，在页面选择Dynamic或请求显式传`strategy='dynamic'`，无需迁移DB。
2. 完整代码回滚：在另一个独立目录检出28ce63d，按其README启动，或对本Release独立增量commit执行`git revert <commit>`。不要对当前有用户修改的主仓reset/checkout。
3. 回滚入口不需删除数据库；本次未引入schema迁移。新Hybrid Trace是新增记录，可读旧Trace的API保持。切回前备份需要保留的新Trace，绝不覆盖原实验。
4. 停止启动器后可保留所有var运行快照；删除另需用户确认。本轮未执行历史删除、force-push或main改动。

关键权威接口参考：FastAPI [独立子应用](https://fastapi.tiangolo.com/advanced/sub-applications/)与[TestClient生命周期](https://fastapi.tiangolo.com/advanced/testing-events/)。本次用独立只读factory避免原应用lifespan恢复研究DB，原应用仅挂载固定Synthetic只读目录。
