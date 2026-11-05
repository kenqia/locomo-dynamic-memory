# Level C 独立原文语义审阅工具

`tools/m5/level_c_semantic_review.py` 为固定开发集的 200 项回答准备盲审材料，校验独立审阅记录，并汇总各指标的可判断分母。本次只实现和测试工具，没有读取真实生成结果、Gold 或 holdout QA，没有创建真实审阅包，也没有运行真实语义评分。

实现、测试及本报告是本次新增文件。未修改生成、冻结、离线重放、恢复、审计模块或 `src/`；未修改真实 stage，未提交 commit。工具当前等待非作者复核。

## 固定范围和冻结要求

工具复用 `level_c.frozen_items` 核对完整计划、实现身份及全部生成项的哈希。准备、校验和评分都要求固定的 80 道 ordinary 和 20 道 diagnostic 问题，每道包含 Hybrid 和 Dynamic 两项，共 200 项。每段开发对话恰有 50 项，每策略包含 20 项 ordinary 和 5 项 diagnostic。运行失败也必须纳入。

在完整冻结核对通过之前，工具不打开证据数据库。通过后只以只读事务访问指定 stage 的 `memory.sqlite3`：读取四段 DEV 的 `source_turns` 显式字段，以及 `conversations.turn_count` 完整性计数。工具不访问原始 reference database，也不查询任何 `evaluation_*` 表或生成状态库。

## 私有文件

`prepare` 只接受 stage 之外的新输出目录，不能覆盖已有目录。目录权限为 `0700`，文件权限为 `0600`。

| 文件 | 内容 |
| --- | --- |
| `packets.json` | 四段完整对话原文各保存一次；200 项只包含不透明 `unit_id`、对话引用、问题、outcome、prediction 和最终 answer。answer 保留直接回答、explanation、status 和 citations。 |
| `private-mapping.json` | `unit_id` 对应的 question ID、arm、对话及 ordinary/diagnostic 身份。不得提供给盲审者。 |
| `manifest.json` | 绑定 generation freeze、plan、packets、mapping 和完整原文投影的 SHA-256。不得提供给盲审者。 |
| `review-template.json` | 全部 200 项的审阅字段均为 `null`，只预填 `unit_id` 和 manifest 哈希。它不代表任何一项已经审阅。 |

`unit_id` 由协议版本、question ID 和 arm 的稳定 SHA-256 生成。材料按该 ID 排序。盲审包不包含 arm、QA 分数、resolver decisions、trace 或错误类型；原始引用保留在最终 answer 中。只将 `packets.json` 和审阅模板交给审阅者，保留 mapping 和 manifest 私有。

校验时会重新构造允许的 packet 投影和映射。因此，仅修改 packet 后重写 manifest 哈希仍不能把其他内容混入原冻结批次。校验结束前再次检查材料、review 和生成冻结的哈希及逐项冻结完整性，拒绝校验期间的文件变化。

## 审阅记录

复制审阅模板后填写记录。合并多人审阅结果时保留全部 200 个唯一 `unit_id`，每项保留实际审阅者的身份与声明。禁止按运行成败或答案表现挑选题目。

每条已审记录必须包含：

- 非空 `reviewer`、`provenance`、整体 `rationale`。
- `review_kind` 为 `human_independent` 或 `ai_assisted_independent`。
- `independent_of_generation=true` 和 `all_factual_claims_checked=true`。后者声明已检查直接回答和 explanation 中的所有事实，不能仅看短答案或引用 ID。
- `answer_kind` 为 `answered`、`abstained`、`failed` 或 `undetermined`。
- `source_support` 和 `citation_support` 分别为 `supported`、`unsupported`、`undetermined` 或 `not_applicable`。
- `abstention` 为 `correct`、`false`、`undetermined` 或 `not_applicable`。仅对整体拒答判断此指标；有部分回答、只有部分证据缺口，或 answer status 为 `insufficient`，均不能单凭该状态算整体拒答。
- `wrong_person`、`wrong_event`、`wrong_time` 和 `list_omission` 分别为布尔值或 `null`。不能把未判断的项填成 `false`。
- `source_quotes` 为数组。每条包含同一对话的 `source_id`、逐字 `quote`、非空 `rationale`、`purpose` 和 `targets`。

`purpose` 为 `support`、`counterevidence` 或 `gap`；`targets` 指明该引文服务于哪些标签，可选 `source_support`、`citation_support`、`abstention` 及四种具体错误标签。确定的 supported 必须有相应 support 引文；unsupported 可使用最近相关原文并解释证据缺口，无须伪造正证据。具体错误为 `true` 必须有相应反证或缺口引文。错误为 `false` 的记录仍受全事实检查声明约束。

将 `citation_support` 标为 supported 时，支持引文的 source ID 必须恰好覆盖实际 answer citations 中的全部不同 source ID。不能只检查一个正确引用，也不能用未被答案引用的其他原文冒称引用支持。该检查只验证引用归属和覆盖，不能自动判断引文是否在语义上支持事实。

将整体拒答标为 `false` 时，必须提供支持可回答性判断的逐字原文。标为 `correct` 时，必须设置 `full_conversation_checked=true`，并在 `evidence_gap` 中解释完整对话缺少哪项必要信息；允许没有直接正证据和空引文数组。其他记录的 `full_conversation_checked` 可为布尔值或 `null`，`evidence_gap` 可为非空文本或 `null`。

生成 outcome 为 failed 的项必须明确独立审阅，`answer_kind=failed`，两项 support 和 abstention 均为 `not_applicable`，四项错误均为 `null`。不能把运行失败当作语义错误，也不能用未填写模板绕过全量审阅。

## 命令和汇总

以下路径均为占位符。真实调用应等完整冻结和非作者复核完成后，由负责执行的 agent 进行。

```bash
PYTHONPATH=src /home/kenqia/my_folder/locomo-dynamic-memory/.venv/bin/python -m tools.m5.level_c_semantic_review prepare \
  --stage /absolute/path/frozen-stage \
  --review-dir /absolute/path/private-semantic-review

PYTHONPATH=src /home/kenqia/my_folder/locomo-dynamic-memory/.venv/bin/python -m tools.m5.level_c_semantic_review validate \
  --stage /absolute/path/frozen-stage \
  --review-dir /absolute/path/private-semantic-review \
  --reviews /absolute/path/merged-reviews.json

PYTHONPATH=src /home/kenqia/my_folder/locomo-dynamic-memory/.venv/bin/python -m tools.m5.level_c_semantic_review score \
  --stage /absolute/path/frozen-stage \
  --review-dir /absolute/path/private-semantic-review \
  --reviews /absolute/path/merged-reviews.json \
  --output /absolute/path/public-semantic-summary.json
```

`validate` 接受恰 200 条完整身份记录，允许部分记录仍是原样的全 null 模板；这些项计为 unreviewed，`completed=false`。任何部分填写的审阅必须满足已审记录的全部协议。`score` 固定要求 200 项全部明确独立审阅，包括失败项，不接受未填写记录。

公开返回值只包含计数、率、哈希、单位 ID 和受控标签，不包含问题、预测文本、原文、引文、审阅者名或自由文本理由。汇总提供总体、arm、ordinary/diagnostic 与 arm、对话，以及对话与分层及 arm 的交叉统计。

每组报告 planned、reviewed、unreviewed、运行 failed 和存在明确 undetermined 标签的单位数。两项 support 的率为 `supported / (supported + unsupported)`；具体错误率为 `true / (true + false)`；拒答正确率为 `correct / (correct + false)`，只针对整体拒答。support 和 abstention 分别报告未确定和不适用数量。四种具体错误只有 bool/null，因此其 null 使用 `undetermined_or_not_applicable` 合并报告，不能凭空区分两种原因；每组另报告含此类 null 的单位数。每项指标单列可判断分母；没有分母时，率为 `null`。失败项与未审项不进入语义分母，unknown 不会被补成正确、错误或零分。

## 合成验证结果和边界

实际运行命令：

```bash
PYTHONPATH=src /home/kenqia/my_folder/locomo-dynamic-memory/.venv/bin/python -m pytest tests/test_m5_level_c_semantic_review.py -q
```

结果为 **36 passed**。测试构造独立的临时 SQLite 和完整 200 项冻结文件，不调用 provider 或生成器，不读取真实数据。覆盖全量盲化、只读 SQL 访问限制、原 stage 文件不变、身份完整性、独立声明、跨对话及非逐字引文、引用漏查、unsupported 的缺口证据、具体错误与拒答引文、失败/unknown 分母、packet/mapping/freeze 篡改、重写 manifest、校验期间变化、未冻结拒绝和原文截断。

默认系统 Python 首次运行缺少 `rank_bm25`，未执行测试；改用项目现有 `.venv` 后完成上述验证，未新增依赖。测试输出有现有 FastAPI/Starlette 的 `httpx` 弃用警告。

工具校验审阅协议、逐字来源归属和数据身份，不自动证明自由文本判断的语义正确，也不能验证审阅者独立声明的真实性。真实 200 项仍需要独立逐题阅读原文并填写标签。独立源审阅不等同于教师真值，本报告不包含真实语义准确率。
