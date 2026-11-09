# Final Technical Report — 大纲与图表规划（Gate 1）

标题：**Dynamic Memory Management for Long-term Conversations: System Design, Implementation, and Evidence-grounded Evaluation**
副标题（中文）：面向长期对话的动态记忆管理：系统设计、实现与证据约束评测
语言：中文正文，术语首次出现附英文；数字一律引用 `METRIC_LEDGER.md`。
篇幅：正文 10–12 页 A4（约 9,000–11,000 汉字 + 8 图 + 5 表）；附录 = 39 页 Research Supplement（原样）+ 勘误页 + 复现信息。
版本绑定：main `5519dd2`（最终冻结前若 main 前进，统一替换为最终 tag 对应 SHA）。

## 章节与页数预算

| § | 标题 | 页 | 要点 | 主要证据 | 图/表 |
|---|---|---:|---|---|---|
| — | Abstract | 0.3 | 问题、方法、E25 主结论（无稳定提升 + 成本/延迟）、默认策略 | M01–M09 | — |
| 1 | Introduction and Motivation | 0.7 | 长期对话状态演化；相关≠有效；计划/否定/矛盾；"现在"的定义；三条 RQ；贡献 K1–K5 列表 | CONTEXT.md | — |
| 2 | Research Questions and Scope | 0.4 | RQ1–3 正式定义、指标与分母；范围（英文检索、LoCoMo 10 段、开发 4 段/留出 2 段）；不做的事 | ADR-0001 | T1 实验层次表 |
| 3 | Requirements and System Overview | 0.6 | SRS 主功能需求 → 模块映射（压缩为一表）；用户：研究者/评审；质量属性：可追溯、可复现、失败可见 | SRS、RELEASE_COMPONENT_MATRIX | F1 System Architecture |
| 4 | Memory Data Model and Temporal Relations | 1.0 | SourceTurn / Memory（原子、陈述性质、state_key）/ MemoryRelation（5 类）/ CurrentState 投影 / BuildVersion；reported_at vs event_time vs 已知状态截止时间；合成 Alex 搬家案例 | ADR-0001、memory-export-schema.json | F2 Data Model & Relation；T2 关系标签定义 |
| 5 | Hybrid and Dynamic Retrieval Architecture | 1.0 | Build Pipeline；Query Pipeline；BM25/Dense 各 20 → RRF60 → 初始 20 → 扩展 ≤60 → [Resolve] → Answer 预算 6000；Dynamic 与 Hybrid 差异仅在 Resolve；查询补判只入 Trace | ARCHITECTURE.md、Settings | F3 Build Pipeline；F4 Query Pipeline（Hybrid/Dynamic 分叉） |
| 6 | Evidence Grounding and Traceability | 0.6 | 引用 = (dataset, sample, dia_id)；四阶段 Trace；合法 ID ≠ 语义支持；失败 Trace 保留 | query_schemas、evidence_ui | （复用 F4 标注） |
| 7 | Web Application and System Implementation | 0.8 | 技术栈；Product Console 五页；离线 Replay（hash 校验、只读、0 provider 调用）；默认 Hybrid 与回滚；测试：CI success + 本地回归 | PR #41、PRODUCT_FREEZE、M50–M52 | F5 Console 截图拼版（Memory→Source→Trace） |
| 8 | Experimental Methodology | 1.0 | 数据划分与锁定；E25 流程（锁配置→冻结生成→根/非作者终态审计→读 Gold）；指标定义（类别 1–4 token F1、类别 5 字面拒答、Source Recall 代理、来源盲审）；完整分母与失败记零；bootstrap；费用口径（预约/已报峰价/账单）；E12/E22/E23 的角色 | LEVEL_E_*、EXPERIMENT_PROTOCOL | F6 Experimental Setup 流程 |
| 9 | Experimental Results (RQ1) | 1.0 | 主表：M01–M05、M12、M13；配对变化；按对话与类别（探索性，未校正）；来源盲审 M26–M27 | M01–M05、M12–M13、M26–27 | F7 F1 + 配对 CI；T3 主结果表 |
| 10 | Cost, Latency and Reliability (RQ2) | 0.8 | M07–M11、M14–M16；Resolve 占比；失败构成；共享 Build 摊销口径；非账单声明 | M06–M18 | F8 Cost / Latency 双面板 |
| 11 | Error Analysis and Evidence Loss (RQ3) | 1.0 | 四阶段 Recall 漏斗；107/400 与 2/400；K 前缀回放；3–4 个真实案例（含"排除可能正确"的 conv-43:qa:135）；明确未完成人工语义核查 | M20–M25、evidence-flow audit | F9 Evidence Loss Funnel；T4 案例表 |
| 12 | Research Extensions and Ablations | 0.8 | Graph/Compression/Adaptive/Temporal（定性 + 指向 Supplement）；E1 路由、E5 缓存；Sidecar 负面结果；11-09 已曝光回归（M36）；E12→E23→E25 研究演进 | M30–M46 | F10 Research Evolution Timeline；T5 扩展采用矩阵 |
| 13 | Engineering Decision: Default Strategy | 0.3 | 决策理由四点；Dynamic 何时可能值得（未来条件） | DEFAULTS_AND_ROLLBACK | — |
| 14 | Limitations | 0.5 | Narrative §6 原样 | — | — |
| 15 | Conclusion and Future Work | 0.3 | 回到 RQ；Future：人工动态标签、Resolve 选择准确率、来源语义核查、对话级评测 | — | — |
| 16 | Reproducibility and Release | 0.3 | tag/SHA、`uv sync --locked`、Replay 命令、公开包排除项、受控数据政策、Supplement 位置 | RUNBOOK、DATA_POLICY | — |
| 17 | Team and AI Collaboration | 0.2 | 成员职责（来源待负责人指定）；AI 辅助与人工复核边界 | member-review 记录 | — |
| — | References | 0.3 | LoCoMo 论文、BM25、RRF、MiniLM、DeepSeek API 文档、项目 Git 对象 | — | — |
| App. | A 勘误 · B 实验档案 E0–E25 · C Research Supplement（39 页） | — | — | SUPPLEMENT_ERRATA、EXPERIMENT_ARCHIVE_INDEX | — |

合计正文约 11.7 页（含图）。

## 图表规划

所有架构图依据实际代码与 ARCHITECTURE.md；所有数据图由脚本从冻结 JSON 生成（`deliverables/m5-final/figures/make_figures.py`，只读 OS/RT/audit.json），生成脚本与输出 SHA 入 MANIFEST。PPT 复用同一图文件。

| ID | 图 | 类型 | 数据/依据 | 复用 |
|---|---|---|---|---|
| F1 | System Architecture | Graphviz/Mermaid 框图 | ARCHITECTURE.md mermaid；console_ui.py；release_viewer.py | 报告 §3、PPT p3 |
| F2 | Memory / SourceTurn / Relation 数据模型 + Alex 搬家合成例 | ER + 时间轴 | memory-export-schema.json；demo_fixture 合成数据 | 报告 §4、PPT p5 |
| F3 | Build Pipeline | 流程图 | builds.py / versions.py 阶段 | 报告 §5、PPT p4 |
| F4 | Query Pipeline（Hybrid vs Dynamic 分叉 + Trace 四阶段） | 流程图 | queries.py / release_queries.py；Settings 数值 | 报告 §5–6、PPT p4 |
| F5 | Console 截图拼版 | 真实截图 | main 5519dd2 离线 Replay，1920×1080（已采集：`var/m5-final-screens-1920/`、`var/m5-final-screens-replay/`），每张角标 "OFFLINE SYNTHETIC REPLAY" | 报告 §7、PPT p6 |
| F6 | Experimental Setup（E25 锁定→冻结→审计→评分） | 流程图 | LEVEL_E_GATE / RESULTS | 报告 §8、PPT p7 |
| F7 | 类别 1–4 F1 两臂 + 配对差 CI（forest） | 点图 + 误差线 | M01–M02；附 M12 类别 5、M13 混合 | 报告 §9、PPT p8 |
| F8 | 成本（已报峰价，按 operation 堆叠）+ 延迟（p50/p95） | 双面板条形 | M07–M10 | 报告 §10、PPT p8 |
| F9 | Evidence Loss Funnel（initial→expanded→effective→delivered，@10，两臂） | 漏斗/阶梯线 | M20–M22；标注 107/2 | 报告 §11、PPT p9 |
| F10 | Research Evolution Timeline（E0→E25 + 11-09 回归；标注每次决策） | 时间线 | EXPERIMENT_ARCHIVE_INDEX | 报告 §12、PPT p9 |

表：T1 实验层次（E12/E22/E23/E25/11-09）、T2 关系标签、T3 E25 主结果、T4 证据损失案例、T5 扩展采用矩阵（已实现/已测试/可演示/证明有益/默认采用 五态）。

Supplement 已有 20 图（`docs/supplement/figures/`）；F7/F8/F9/F10 先检查 f06_forest、f11_cost、f12_latency、f09_recall_funnel、f01_timeline 是否可直接复用（口径与本台账一致则复用，避免两套图）。

## 写作约束清单（Gate 2 逐条核对）

- [ ] 每个数字带 M-ID 且口径齐全（分母、失败处理、样本身份）。
- [ ] "Recall" 一律写"来源覆盖代理"。
- [ ] 107 题写"标注来源被排除"，不写"误删"。
- [ ] 费用写"估算，非账单"。
- [ ] 11-09 结果写"已曝光数据上的回归"。
- [ ] Sidecar 写"研究候选，未进入 main"。
- [ ] 合成示例（Alex/Sam）标注"合成"。
- [ ] Console 实验页显示的是 E12 历史 Run，不是 E25（截图说明写明）。
- [ ] DOC 等级数字不出现在正文（或出现时标注来源文档）。
