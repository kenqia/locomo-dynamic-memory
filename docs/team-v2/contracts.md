# 共享接口与修改边界

Production 来源 `915fac02f6b9296e331f913a1e78717cfa7e2df1`，Research 来源 `f41c94b79d0d59a81a1a26ac343ac82420560898`；逐文件身份见各分支的 [source-manifest.json](source-manifest.json)。快照只固定已提交代码，不含研究工作树未提交的 resume/phase4 改动。

| Owner | 主写范围 | 依赖与交接 |
| --- | --- | --- |
| Lead | Core Build/Query/QA、研究结论、采用和预算 | 提供经审查聚合与接口；维持原生产默认 |
| Product | `src/locomo_memory/*ui*.py`、主题、只读展示、`demo_fixture/`、相关测试 | 使用现有 API；缺字段先给 Lead 适配合同；向 Delivery 提供截图/操作路线 |
| Architecture | 新增 `tools/research_v2/sidecar*` 或独立模块、Schema、案例、测试、ADR | 复用已提交研究工具，默认关闭；给 Product 脱敏示例；不得碰活动 DB/生产 schema |
| Delivery | `presentations/v2/`、`deliverables/v2/`、`process/v2/`、相关 `docs/team-v2/` | 事实台账与来源优先；公共协作入口由 Lead 协调改动，避免覆盖状态 |

现有合同在 `src/locomo_memory/api.py`、`schemas.py`、`query_schemas.py`、`retrieval_schemas.py`。沿用实际字段；SourceTurn 身份含 dataset/sample/source，不以单个 dia_id 跨对话合并。QueryTrace 区分 initial、expanded、resolution、effective memories、answer/citations；exact wire 未记录时显示未记录，不造字段。

Sidecar 每条记录绑定 Build fingerprint、Memory/Source ID、规则版本；reported_at 与 event_time 分离，计划、否定、unknown 不补成确定事实。`enabled=False` 保持默认行为，若仅完成诊断则标 `diagnostic_only`。新 Sidecar 无真实配对独立评估时不得声称 QA 提升。

公开 Demo 合同：合成案例可公开，真实聚合只读；UI 操作不得触发真实生成。API/UI 仍是现有 FastAPI + Streamlit，不新增生产依赖或数据库迁移。

跨基线集成仅挑选经过审查的实际 feature commits；不要将原研究分支或其受控历史合并到安全 Production。
