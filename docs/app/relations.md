# 检查历史关系、状态与相关历史扩展

本阶段保存有来源的历史判断，重算 Current State，并扩展真实初始检索候选。完成配置要求的抽取、索引、关系和投影后，可以显式发布一个完整构建版本供后续查询固定使用。最终有效证据解析与答案生成仍由后续票实现。

## 操作步骤

1. 按 [构建指南](building.md) 和 [检索指南](retrieval.md) 得到 `indexed` 版本。
2. 点击 **构建或重试历史关系**，再刷新进度。后端为每条新 Memory 比较同对话、同实体的有界历史，保存每个比较的判断；证据不足也必须明确返回 `undetermined`。
3. 检查关系任务的成功、失败和截断计数。失败或中断使用同一按钮显式重试；成功关系任务与抽取片段不重复调用模型。
4. 状态为 `related` 时，检查 Current State 的截止时间、当前候选、历史、事件、非事实陈述、条件及冲突。需要时点击 **从历史与关系重算投影**；它重算缓存，不编辑事实。
5. 选择一条关系，检查两端 Memory、适用条件、理由和双方原文。
6. 如需供后续完整库查询使用，点击 **校验并发布为完整构建版本**。发布原子地切换所选对话的活动版本；未通过或失败的新版本保留旧完整版本。
7. 运行初始候选检查，再点击 **扩展当前候选的相关历史**，对比初始、补充与合并集合，核查每条补充的入口及截断原因。

状态路径为 `extracted → indexed → related → complete`。只有 `complete` 的 `query_ready=true`。完整版本的索引、抽取重试、关系构建和投影重算接口都拒绝修改；更正事实或关系需创建新构建。

## 判断与来源约束

| 判断 | 含义与保留规则 |
| --- | --- |
| `RETAIN` | 新证据支持旧事实继续适用；没有新消息不能证明保留 |
| `UPDATE` | 同一过程推进，旧阶段仍可用于历史问题 |
| `SUPERSEDE` | 同一实体和状态维度的事实状态被明确替代；不抹除旧原文 |
| `CONFLICT` | 同一适用条件下的矛盾尚未消解；保留双方来源 |
| `undetermined` | 证据不足，不强迫归入其他标签，也不作为跨键扩展边 |

每条判断必须引用提供的历史端点及当前新 Memory，限定同一构建、数据集、对话和实体。来源必须真实存在并支持双方。确定判断还需要实际出现在来源中的 `support_quote`。替代只允许事实状态，事件、计划或不确定陈述不能替代已发生的事实状态；`RETAIN`、`SUPERSEDE` 和 `CONFLICT` 必须同一 `state_key`。跨维度 `UPDATE` 需要明确来源支持，不因同人而自动连通就业与商店经营。

有日期的关系适用区间必须保留原始时间表达、来源锚点和依据；倒置区间、伪造锚点或不存在的表达会拒绝。条件若未知就保持未知，声称条件满足必须引用证明来源。上述校验不等于验证模型的语义判断正确性。

`relation_history_limit` 默认 20，限制每个新 Memory 的同实体先前比较量。未比较的较早历史计入 `history_comparisons_truncated`，不声称已经穷尽所有可能关系。没有先前 Memory 时不调用关系模型，也不伪造 RETAIN。Prompt、schema、投影版本和相关配置在构建开始前进入指纹。

## 保守的 Current State

截止时间从所选对话的原始会话时间解析取最大值，不使用主机当前时间或字符串排序。支持 LoCoMo 原始英文时间格式和无时区 ISO 时间；无法解释的时间阻止投影/发布，不猜测日期或时区。

事实状态默认是带“未知有效期”提示的最后已知陈述。只有有依据的替代/推进日期在截止时间内且条件成立，才将旧状态标为 `superseded` 或 `advanced`。未知日期、未来变化或未满足的条件不会无条件抹去旧状态。冲突保留双方，兼容的同键工作可以共存。事件保留在历史，计划、意愿与不确定陈述单列；否定事实保留负向性质。

投影只引用原 Memory ID 与来源，是历史和关系的可重算缓存；没有手工状态编辑器。候选查询及历史扩展不会重算或改写全局关系与状态。

## 有界历史扩展

扩展固定初始候选记录所属的 `build_id`。`expansion_depth=1` 只沿**原始初始集合**的直接、已确定关系补充历史；`0` 关闭关系边扩展。同一初始 `state_key` 的历史补充独立保留，两种补充都不会将新增 Memory 变成下一轮种子。未知时间不会被推断查询日期硬过滤。

默认合并上限 `expansion_max_candidates=60`，总扫描上限 `expansion_scan_limit=200`；共用 `candidate_token_budget` 和检索指南中的明确 regex 计数单位。原始初始记录不改写；合并集合按初始顺序、种子顺序/稳定关系 ID、同键历史来源顺序稳定去重。初始项遇预算不足停止保留其后初始项；补充项超预算跳过并记录原因，后续较小项仍可进入。重复路径保留多个 origins，不重复占用候选预算。

只有发现潜在额外候选或额外扫描记录时才标记截断；恰好达到上限不自动代表存在遗漏。补充记录携带种子、关系 ID/标签或 `state_key`、理由和适用条件。扩展无法恢复从未抽取的 Memory。

## API 与后续查询契约

| 方法与资源 | 用途 |
| --- | --- |
| `POST /builds/{id}/relations` | 首次构建或显式重试关系阶段，返回 202 |
| `GET /builds/{id}/relation-progress` | 阶段进度、错误、Prompt/schema、历史比较截断 |
| `GET /builds/{id}/relation-tasks` | 分页任务、尝试次数及安全调用元数据 |
| `GET /builds/{id}/relations` | 分页历史判断，含未确定结果 |
| `GET /builds/{id}/current-state` | 读取固定投影及截止时间 |
| `POST /builds/{id}/current-state/rebuild` | 仅未发布的 `related` 版本可重算 |
| `POST /builds/{id}/publish` | 检查全部阶段并原子切换活动完整版本 |
| `GET /versions/pin?dataset_id=...&sample_id=...` | 固定该对话的活动完整构建 ID；可传 `build_id` 检查指定完整版本 |
| `POST /candidate-expansions` | JSON `{query_id}`，扩展既有初始候选记录 |
| `GET /candidate-expansions/{id}` | 读取已保存的扩展结果 |

后续业务模块可调用 `app.state.versions.pin(dataset_id,sample_id,build_id=None)` 得到固定 ID；之后全部 Memory、索引、关系和状态读取都必须使用该 ID。无匹配完整版本返回 `no_complete_version`。`app.state.relations.current_state(build_id)` 和 `app.state.expansion.expand(query_id)` 提供相应业务入口。此基础发布契约由后续恢复/导出票继续加固。

## 验证边界

执行 `uv run --locked pytest -q`。公开 API 使用实际 SQLite、BM25/cosine/RRF 和真实扩展，只控制模型/Embedding 输出。覆盖研究阶段实际未进入初始候选后的恢复、根本未抽取的反例、单跳/同键不再扩展、深度与数量/扫描/文本预算、条件替代、冲突/并存、任务重试和完整版本 pin。实际结果见 `experiments/issue-8-relations-validation.md`。

本票没有真实付费模型调用，也未单独运行浏览器；受控判断不能当作独立动态标注或模型质量证明。
