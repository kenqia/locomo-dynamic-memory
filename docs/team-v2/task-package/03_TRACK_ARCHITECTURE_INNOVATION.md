# Track B｜Architecture Innovation：六天交付 Temporal/Event Sidecar v0

**建议父 Issue**：`[v2][Architecture] 6-day Temporal Event Sidecar opt-in MVP`
**Owner**：由队员自选；D1 认领。**Reviewer**：项目负责人核对语义/版本边界。
**分支**：`team/temporal-event-sidecar-v0-6d`。**代码冻结**：D4 18:00。

## 这条线必须创造增量，而非重复 E1/E5

当前已有真实四对话基线及 Failure Atlas。已知不同事件被错认冲突、计划/完成混淆、相对时间过度拒答、引用细节不匹配等输出症状；这些是**症状，不是均已确证的上游根因**。E1 Router v1 留一无实际 Fast 路由收益，E5 精确 Query Embedding Cache 已通过本地等价性/CPU 测量；**本任务不重写 E1/E5**。

选定一个高价值、六天内可独立实现和对照的工程作品：**固定旧 Build 上的 Temporal & Event-aware Memory Sidecar**。不更换默认关系存储、不迁移历史 SQLite、不加 Neo4j。Sidecar 缺证据输出 unknown；“同一人/职业/计划”不自动等于同一事件。它只在明确 opt-in 的研究查询中生效。

## 四个子 Issue

### ARCH-01｜D1 冻结规格、最小 Schema 与 12–20 个真实/合成边界案例（P0）

- 从已有报告与 SourceTurn 选案例：Event Identity、reported_at vs event_time、plan vs completed、negation、as-of、unknown。
- 设计 `SidecarRecord`、`EventLink`、`StateClaim`、`TimeInterval`，每项绑定 Build fingerprint、Memory/Source ID、生成规则/来源；合成与真实案例分开标识。
- 固定 testcase manifest 和 expected behavior，禁止在看完结果后改写预期。
- 验收：Schema + pytest + 冻结 manifest；无隐藏标签泄漏。

### ARCH-02｜D2–D3 实现 Event/Time/State 推断核心（P0）

- 基于现有 `temporal.py`、Memory/Relation/Source 实现最小 deterministic 规则与只读 Sidecar JSON/SQLite；不接新付费 LLM。
- 报告时点 vs 事件适用时点分开；相对时间未知则保留范围/原文，不擅自转换具体日期；计划≠完成；错误连接不生成。
- 产出事件连接的正/负/不确定理由，引用存在不代表语义蕴含。
- 验收：至少 20 个边界单测覆盖误连、误拆、否定、计划、时间窗、未知、重复数据和空数据；只写临时 Sidecar，旧 Build 哈希不变。

### ARCH-03｜D3–D4 opt-in 查询接入与消融（P1）

- 添加独立研究调用入口，明确 `enabled=False` 原路径完全一致；可以先做不改变最终答案的诊断注释，**若能安全接入 Query，必须保留原证据与预算**。
- 至少能比较控制与 Sidecar 在固定案例上的事件/时间状态判定，保存 case 输入、输出、来源和额外 CPU/wall。
- 不凭 Mock/合成单测宣称 QA 质量增长；如要跑新 DeepSeek 调用需用户另行明确预算与冻结实验，**本冲刺不依赖付费实验成功**。
- 验收：一键开/关、回退、来源 ID 不增造、所有默认 API/Schema/Build 不改变。

### ARCH-04｜D4–D5 离线回归、ADR、演示与交接（P0）

- 一份 ADR + 可读算法说明 + 适配示例 + 性能/成本 + 明确局限与后续配对实验计划。
- 对至少两个冻结历史 Build/fixture 做兼容性检查（如果可合法访问）；不需要改变历史数据身份。
- 提供给 Product 线一个公开可用的脱敏 Sidecar 示例，让其 Demo 展示“实验候选”，不能写“生产已采用”。
- 验收：Reviewer 实际执行离线测试，默认关闭零副作用；D5 交付小 PR 和快速上手指南。

## 时间压力下的优先级

**必须完成**：正确的 Schema、确定性事件/时间/状态边界、小数据 sidecar、测试、opt-in/回滚、可展示案例。

**可以降级**：没有时间做真正 Query 接入就只交只读 sidecar 对比和实验入口；在交付报告明确 `diagnostic_only`，绝不假装在线生成已改善。

**不做**：Graph DB 迁移、全库 Ontology、第二个 Reranker、E1 Router v2、付费全量配对、跨数据库大迁移、新生产 Schema。任何在 D4 之后产生的架构新点子进入后续 backlog，而不是加到本次 PR。
