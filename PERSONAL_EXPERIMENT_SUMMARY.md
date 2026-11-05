# 个人实验总结

个人核心：构建可追溯的原子Memory、保存历史关系和版本、按问题检索/解析有效证据、回答并保留Source/Citations/Trace，最后以冻结实验审计质量与代价。没有发现Dynamic稳定优于Hybrid；最终推荐Hybrid默认、Dynamic可选，四类Bonus区分工程可用与QA收益。

本页为M5简洁总结；37页实验过程附录独立保留，不是团队最终报告。引页码为PDF物理页（包含目录）。勘误见docs/release/SUPPLEMENT_ERRATA.md。

## 研究问题与结果身份

RQ1（附录p3、24–25）：动态解析能否改善答案质量？RQ2（p26–27）：可靠性和成本是否值得？RQ3（p28）：证据在哪个环节损失？五阶段覆盖E0–E25，实验总表p30–32，成本p33–34，身份p34–35，未测量项p36。

| 实验身份 | 数据/分母 | Full Text | Vector | Hybrid | Dynamic | 边界 |
|---|---|---:|---:|---:|---:|---|
| 历史E12，旧757题Run | 757，失败保留；H含1unknown取下界 | .464869 | .519714 | .521886 | .515133 | 旧Run，非本Release重跑；附录p13–14 |
| Level C v1 E22 | 同一开发100=80普通+20诊断，普通完整分母80 | 未跑 | 未跑 | .399883 | .228329 | D51/100成功，49输入失败保留；p19–20 |
| input v2 E23 | 同100题，普通完整分母80 | 未跑 | 未跑 | .401172 | .444702 | D100成功/H99，差+.043530，CI[-.008095,.095318]；p20 |
| Level E E25 | 留出400题双臂；类别1–4每臂301 | 未跑 | 未跑 | .402606 | .409151 | 差+.006545，CI[-.020133,.034035]跨零；p21–22、25 |

E22原resolution low/160000bytes/96000代理tokens；E23新生成disabled/640000bytes/192000代理tokens，不能单因素归因。E25固定两臂、Bonus关，先锁配置、生成冻结、根/非作者终态审核，再读Gold；E已曝光，后续仅称回归。

权威工件：

- 历史757：research-process-archive@3e64811的V2-02/03/05条目；原Run `a2abe1fb...` 及补充/修复 `df096a57...` / `a9c2024b...`，完整身份见EXPERIMENT_ARCHIVE_INDEX。
- C v1：docs/m5-development/LEVEL_C_RESULTS.md、experiments/m5-development/内Level C冻结汇总（完整路径见索引）；具体真实路径由实验索引绑定，不虚构重跑。
- C input v2：docs/m5-development/LEVEL_C_INPUT_V2_RESULTS.md及同目录冻结公共结果。
- E：experiments/m5-development/level-e-results-v1/official-scores.json、level-e-runtime-terminal-v1.json、level-e-derived-results-v1.json；producer `0dbd98e7b296ef29d9998fa55d88d512f8ec85f1`，freeze `3cab5d1b486290184e67906d61427f18803b415d82fe18f5f5f7190ae89664a6`。

## 完整分母、语义与费用

E H394/400、D389/400成功。17失败=8 invalid_output+9 HTTP402，失败记零，未补跑/删题。类别5另99题字面拒答H .858586/D .808081，不能称事实F1；混合规则400均值也不能称纯F1。Source Recall每臂399可映射/1null，Memory排名K覆盖Source，不是Atomic Fact Recall。

800项来源盲审，每项一名非作者AI，非人工/教师真值或双审一致性。来源支持H250/343、D233/307，共同可判定297对净增10，区间仍跨零。60关系单位历史AI诊断50/60，但参考无SUPERSEDE/CONFLICT覆盖；不得声称四标签真实准确率已证明。

E查询2112物理请求，预约USD105.4516575，已报usage峰价金额H .8705958/D6.8800119（D约7.9026倍），未知usage18次预约保留。H/D p50 2.370230/8.314747秒。共享Build920请求，已知usage峰价USD6.6141915，独立部署每臂承担完整Build再÷400，不能各摊一半。
十阶段累计3975请求、预约USD197.6108655、已报usage峰价USD18.1208100；25未知usage预约USD1.3023021。没有读取实际账户账单，不把预约、峰价估算或批准上限称为实际消费。

## 失败根因和Bonus去向

E1–E24保留格式/来源ID/状态维度/时间原文锚定失败、输入上限和恢复历史；没有放宽来源或时间契约。Dynamic更复杂的全候选输入及阶段调用造成明显成本/延迟，额外解析可能删去有用来源；不能只看共同成功子集。

757题Level B回放没有新Answer/Resolve：Graph扩展来源覆盖略升（.819920→.823098），最终交付无增益；Compression完整messages代理tokens仅省.02925%；Adaptive交付来源代理下降.029349；Temporal新增软优先无总体代理收益。A关系/版本保留；B浏览可展示、多跳关；C/D默认关。它们工程通过不等于QA收益。
Hindsight、Cross-Encoder、PropMem在隔离研究档案，未完成的外部后端不进App。PropMem固定配置REJECT不能外推整个方法无效。

## 局限与个人收获

缺人工/教师动态标签、完整Atomic Fact Recall/Retention、新模型有效选择准确率、Bonus真实QA增益、实际账单、GPU与分臂资源测量。两段本地留出不代表教师隐藏评分；Bootstrap按题不证明对话级泛化。模型alias不是固定权重。原始六份JSON完整性校验通过不保证关系语义正确。

个人负责核心源码、研究/失败/成本/身份记录和本Release整合；AI代理参与实现及非作者审查，身份在原工件保留。队友Console/Sidecar/正式PPTX/MP4/团队总报告由其完成。本次只做工程修复、免费验证和安全归档，没有新算法研究或付费实验。
