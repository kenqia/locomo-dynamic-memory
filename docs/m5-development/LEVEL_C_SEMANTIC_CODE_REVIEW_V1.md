# Level C 来源语义审阅工具独立代码复核 v1

结论：本轮未发现 P0/P1/P2。独立新鲜验证为 `36 passed`。此结论针对工具的输入、证据与汇总契约，不证明任何真实答案的语义正确性，也不表示200项真实审阅已经完成。

2026-11-04。非作者审查者 `final_code_review_v6`，未参与实现。工作树 `/home/kenqia/my_folder/locomo-worktrees/m5-final-development-20261104`，HEAD `c8e5c09456c8bfc3f2ad56701a0bfb56928c12b1`。报告遵循已读取的 `google-developer-docs` 技能；完整读取下列实现、测试、协议，并核对既有 `frozen_items` 和生成路径。

| 文件 | SHA256 |
| --- | --- |
| `tools/m5/level_c_semantic_review.py` | `933bdeac1a9a4498b6cf74a971583e9d5e219fd38c66e290c922f65861369ba2` |
| `tests/test_m5_level_c_semantic_review.py` | `e70083943c3a342fe596a14e9c4647a3ebe0c502e51d5114029149cd27b548f8` |
| `docs/m5-development/LEVEL_C_SOURCE_REVIEW_PROTOCOL.md` | `015ec8e8b54a9ff9e4cdad435c000cd954eb7e95fdad8407a1c46a15e8676131` |

## 核对结果

- 在读取来源数据库前，完整验证冻结 plan、全部200项文件与身份；严格限定四段开发对话、100题、80/20分层及每对话每臂20/5项。不会按成功状态、得分或预测内容选样。
- 来源只从独立阶段数据库的 `conversations.turn_count` 和明确列出的 `source_turns` 字段读取。核对完整 turn_count、唯一来源与位置及非空文本；不查询 evaluation、Gold 或 holdout 表。测试用数据库 authorizer 和额外 holdout 对话作访问边界检查。
- packet 使用允许字段投影，只包含匿名单位、问题、结果、最终答案及解释、引用和共享完整来源；不投影 arm、question_id、分层、官方分数、resolver 决策或关系预测。私有映射单独保存；匿名 ID 和答案风格均不构成完全盲法保证，协议明确要求审阅者不打开映射和官方评分文件。
- 每条已审记录要求独立审阅身份、provenance、审阅种类和全部事实陈述已检查的声明。逐字引文必须来自该单位同一对话，包含有效用途、目标和理由；跨对话或非逐字内容被拒绝。工具验证可追溯性，不从 Source ID 自动推导语义真值。
- supported、unsupported、错误 true 和 false abstention 分别要求对应目标及用途的引文；citation_support 为 supported 时，支持引文的来源集合必须与答案实际引用集合完全相等，不能用未引用来源补齐，也不能只检查一个好引用掩盖其他引用。correct abstention 要求全文检查声明及明确证据缺口。
- 失败项保留在计划与已审计数中，必须明确标注 failed、语义标签不适用及错误 null；不混入支持率和错误率。无法判断和不适用保留独立计数，四类错误的 null 按协议合并为 `undetermined_or_not_applicable`。每项率使用实际可判断分母，零分母返回 null。汇总覆盖总体、策略、分层×策略、对话及对话×分层×策略。
- validate 要求完整200个唯一单位，仅原样全 null 模板可作为 pending；score 要求200项均有显式独立审阅，包括失败项。缺失、重复、额外单位或半填模板均不能产生完成状态。
- 验证绑定 freeze、plan、manifest、packet、mapping 和 review file 哈希，并从冻结 generation 与当前来源重新生成允许投影。重算篡改 packet/mapping 的 manifest 哈希仍被拒绝；验证期间文件变化和生成 item 变化也被拒绝。公开返回值只含计数、受控标签和匿名 ID，不返回答案、原文、引文或审阅者 provenance。
- prepare 输出目录必须在 stage 外，新建私有目录及文件权限分别为0700和0600；CLI 公开输出同时排除 stage 和私有审阅目录。测试核对 synthetic stage 文件集合与哈希保持不变。

## 新鲜验证

实际执行：

```sh
./tools/integration/check.sh tests/test_m5_level_c_semantic_review.py -q
```

结果：`36 passed, 1 warning in 7.91s`。warning 为既有 Starlette/TestClient 的 `httpx` 弃用提示。测试包含完整 synthetic 200项 freeze、4项运行失败、无法判断及各指标分母、引文与引用集合、全文拒答条件、完整审阅覆盖、文件/来源篡改和验证中途变化。

## 边界

所有运行仅使用 synthetic 临时 fixture；真实 provider 请求为0。没有打开真实 stage 数据库、真实 items、Gold、holdout、历史预测或敏感日志，没有干预会话89061或85918，也没有修改作者代码、冻结 producer、计划或数据库。

该工具接受审阅者的独立性与语义判断声明，不能自行证明审阅者未看过私有映射、引文足以支持全部事实、缺口确实不存在，或审阅者与生成实现独立。协议已说明 AI 辅助审阅不属于人工/教师真值，也不提供双人一致性保证。真实200项来源审阅、终态审计、官方 QA 和非作者验收仍需各自完成；本报告不批准发布或远端写入。
