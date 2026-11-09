# 冻结证据损失诊断与边界回归

2026-11-09。对已经曝光的 Level E 做只读诊断，对确定的查询时间与抽取窗口边界做工程回归。没有新增模型请求、没有重建 Build，没有新的问答 F1 或独立留出成绩。

## 结果

[机器审计](audit.json)核查 400 条 Dynamic 冻结记录，其中 399 题来源可评分、389 题执行成功。冻结 SHA 仍为 `3cab5d1b486290184e67906d61427f18803b415d82fe18f5f5f7190ae89664a6`。

| 观察 | 题数 | 含义 |
| --- | ---: | --- |
| 完整解析输入在预算内 | 400 | 输入审计没有裁掉候选，不等于每次模型返回合法解析 |
| 解析后失去至少一个标注 Source Turn | 107 | 比较完整 resolver input 与有效集合，不自动判定误删 |
| 回答预算后进一步失去标注 Source Turn | 2 | 有效集合已有，送达集合因预算失去该来源 |
| Answer 发生 Memory 预算截断 | 12 | 其中只有 2 题失去标注来源；其余可能仍由别的 Memory 交付同一来源 |

因此，冻结结果的主要标注来源下降发生在 **Resolver input → Effective**。单纯增大 Answer 预算无法解释或修复主要下降。原 Level E 的 Memory-rank Recall@10 仍为 initial **0.679678**、effective/delivered **0.534318**；这些历史成绩没有被改写。

全部成功且来源可评分的子集中，不限制 K 的来源覆盖分别为 initial 0.745732、expanded/resolver input 0.787377、effective 0.552580、delivered 0.551077。该成功子集口径与上述完整分母 Recall@10 不同，不能混用。

## K 前缀回放

固定已记录的扩展顺序、解析决策和交付结果，只观察扩展集合前 K 个 Memory 对正确来源及原有交付来源的覆盖：

| K | 已观察候选来源覆盖 | 固定决策下交付来源覆盖 |
| --- | ---: | ---: |
| 5 | 0.609983 | 0.429240 |
| 10 | 0.694048 | 0.475251 |
| 20 | 0.742132 | 0.509649 |
| 40 | 0.776217 | 0.529305 |
| 60 | 0.784885 | 0.535884 |

每行分母为同一 399 题。候选列使用失败项仍观察到的候选；交付列对失败记零。它不等于原报告运行失败记零的初始 Recall，也不是改变 K 后重新排序、扩展、解析和生成的消融。不能从本表推算新答案、噪声事实比例或 F1 收益。它说明增加候选覆盖并不保证同等程度的最终交付覆盖。

## 20 个典型案例

`audit.json.cases` 保存每案的原始问题、来源标注、全部扩展 Memory、阶段 IDs、所有解析决策、全部被引原文、排除理由和已有答案。`gold_losses` 记录的是引用标注来源的 Memory 排除或截断；同一来源仍可能经其他 Memory 送达，必须结合 `flow.stages` 和 `rejected_gold_source_ids` 判断是否真的丢失 Source Turn。为可核查性保留失败及对照案例。选择规则为预算损失、解析来源损失、失败、保留对照分层；不足 20 时按冻结顺序补入来源损失例。这不是代表性质量抽样。

[作者 AI 的逐案初判](author-review.json)区分局部原文支持的排除、联合推断边界、预算损失和运行失败；它不计算正确率。下表为复核关注点，不是独立语义标签。所有人工判定、不同意见和签名均待真实成员填写。

| 问题 ID | 优先核对的边界 |
| --- | --- |
| conv-43:qa:67 | 旅行愿望来源在回答预算丢失；候选建议是否仍有支持 |
| conv-44:qa:33 | 徒步习惯和现实限制被预算截断；是否影响建议完整性 |
| conv-43:qa:38 | 多次旅行的联合比较；不能要求单条 Memory 单独证明频率 |
| conv-43:qa:14 | Memory 是写作进展，但原文含 fantasy novel；来源覆盖下降而答案仍包含小说 |
| conv-43:qa:19 | 品牌合作愿望与慈善组织不同，检查排除是否合理 |
| conv-43:qa:20 | 去过 Chicago 不等于去 Chicago 之前的城市 |
| conv-43:qa:50 | 其他阶段读书是否适用于受伤恢复期 |
| conv-44:qa:20 | 偏好鸡肉菜肴能否支持“最偏好的肉”，需明确推断边界 |
| conv-43:qa:1 | 原文同轮包含球场内外目标，排除某项是否丢掉共同来源的有效内容 |
| conv-43:qa:10 | 比赛与 Seattle 地点是否有同事件证据 |
| conv-43:qa:119 | 照片地点来源与 sunset 描述的支持；文本缺失不能靠 ID 补足 |
| conv-43:qa:128 | 常做的菜与慢炖锅烹饪不能直接等同 |
| conv-43:qa:135 | 标注来源谈 John，问题问 Tim；删来源未必是错误 |
| conv-43:qa:136 | John 的伤情与 Tim 的陈述分开核查，包含多来源 Memory |
| conv-43:qa:65 | 失败项有候选/有效/拟交付记录，不等于成功回答 |
| conv-43:qa:7 | 地理列表失败项保留，不能从成功子集删去 |
| conv-43:qa:0 | 正常交付对照：篮球生涯目标 |
| conv-43:qa:100 | 正常交付对照：高中队友共同打球时长 |
| conv-43:qa:4 | “没读 Dune”与同轮已读另一书分开判断 |
| conv-43:qa:8 | 想合作的品牌与已签约户外品牌分开判断 |

机器自动排除理由是模型输出，不是被验证的正确理由。真实成员可记录：判断人、逐字引文、适用/不适用/不确定、原因、是否影响答案、异议及复核人。未收到独立人工结论前不计算有效选择准确率。

## 修复与前后对比

[时间解析回放](time-scope-replay.json)运行实施前真实 Git 代码与本轮代码，对固定的合成边界做对比。它覆盖 ISO/英文点日期、before/after/since/by/until、月份/闰年、混合范围和普通 from 人物用法。
这验证解析结构，不评估模型答案或代词消解。抽取窗口回归通过公开 Build API 与受控模型，验证上下文交付、目标引用约束、同会话边界以及拒绝只引用上下文的结果；真实模型是否正确理解仍未测量。

本轮没有实体别名合并、独立知识时间 API、语义引用 judge 或基于 QA 的筛选算法。Joanna/Nate 归属仍需要有来源的身份标注；没有证据时继续保留独立实体。提高来源覆盖不是放宽身份和事件支持要求的理由。

## 复现与身份

代码先提交为 `1edb31a`，审查修正为 `82f2356`，后续普通介词回归和记录另有提交。实验输出独立于历史 stage。

```sh
.venv/bin/python -m tools.m5.evidence_flow_audit \
  --stage /home/kenqia/my_folder/locomo-worktrees/m5-final-conv44-relations-20261104/var/m5-development/level-e-preparation-v1 \
  --freeze-sha256 3cab5d1b486290184e67906d61427f18803b415d82fe18f5f5f7190ae89664a6 \
  --output experiments/evidence-flow-20261109/audit.json
.venv/bin/python -m tools.m5.time_scope_replay \
  --baseline-ref d3c4ae10fb73d70eabea42f5333e721168574190 \
  --output experiments/evidence-flow-20261109/time-scope-replay.json
```

stage 与参考 SQLite 是本地只读工件，公开仓库不包含它们；缺少这些工件时不能声称重跑了冻结审计。脚本校验 freeze、plan、final lock、inputs、每个 item 和 reference 数据库存储身份，不读取凭据、历史执行 stdout/stderr 或预算授权文件。

案例原文逐字匹配仓库已跟踪的 `data/raw/locomo/locomo10.json`，该文件 SHA 写入工件；来源为 snap-research/locomo，遵守 [CC-BY-NC-4.0](../../data/raw/locomo/LICENSE.txt) 及[数据 provenance](../../data/raw/locomo/README.md)。不存在于该公开原文的内容会阻止生成案例包。

验证与两轴 AI 审查见[检查记录](validation.md)。没有创建、领取或验收新的 Issue/Notion 任务，本轮没有关联的 Notion 记录可同步，也不标记任务完成。
