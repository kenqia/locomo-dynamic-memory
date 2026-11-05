# Level C 固定开发集准备结果

2026-11-04。当前状态：**generation_scored_and_source_review_complete**。用户明确批准“授权本次 130.9824 USD / 1,500 次开发集 QA 阶段”，已保存批准回执、执行前完整性与官方价格复核，并启动唯一冻结入口。200项已全部冻结，随后读取开发Gold完成评分、终态只读审计和200项独立AI来源审阅。最新结果见[Level C真实结果](LEVEL_C_RESULTS.md)。

执行目录为 `var/m5-development/level-c-preparation-v1/final/final-v2`。`plan.json` 保留原准备状态及原SHA，真实批准另存 `authorization.json` 和 `user-authorization-receipt.json`，不改写冻结计划。根目录第一稿和 `final/` 第一稿仅作历史准备证据，不能执行。

## 已准备的实验

复用 `experiments/m5-development/replay-v1/fixed-live-sample.json` 的既定 80 普通题 + 20 诊断题，不重选题。每个开发对话分别为 20+5 题。对照为现有 `hybrid_no_resolution` 和 `dynamic`，共 200 个计划回答；两臂共享四个已完成 Build、来源、模型设置和证据预算。Bonus 未获得事实质量晋级证据，本次不加入付费候选。

四个 Build 合计 1,237 Memory、884 个被引用 Source Turn、22,691 条关系。准备同时验证完整导出契约与明确 Build pin；没有重建 Build、发布版本或调用 Query。

| 对话 | Build |
| --- | --- |
| conv-26 | 367c901b300440649bdc0bfba2af8010 |
| conv-30 | b8f34a05c8ef4585a1fc3c917745aa53 |
| conv-41 | 8d459492549b4a3e88005211f036addf |
| conv-42 | c892596ac8884f43b4cf2098349a7fa5 |

## 身份和隔离

- 历史 Run：`a2abe1fb49be45ccba291728e1f6b3c9`。
- 历史源库主文件 SHA：`ffa299c36ba1d15a6148826dd14430dca6e4ebfa27069d7a141021987cda060c`。
- 固定 question 输入 SHA：`0816f9f2f60acc068a7a6bf3562c603db6545ea85920d1d6cfcfe2ba0ae7c9f0`。
- Settings SHA：`b879a9ea09a86760605b6d75c87377e0e33a68c7d5c54538bfc08e89c532ba0f`。
- 唯一候选 plan SHA：`e7caed32203c567f5fb3ee7fb3a10250400a6da9a9ad453dbfb101eb4f03cf76`。
- `tools/m5/level_c.py` SHA：`3d8cb571f727099db8a0f171527052b2354449b9f9194e499e8c7e78f9d53ee0`。

生成输入通过 SQLite `json_extract` 投影题目和身份，SQL 中显式限定四个开发对话；不加载完整 evaluation Run，不读取 answer、evidence、Gold 或历史 predictions。独立数据库只复制 14 类构建必需表的四开发 Build/来源行，不复制任何历史 evaluation 数据或 import annotations；生产 Database 初始化时只新建空 import_artifacts 表。未复制 holdout 行。

源库保持只读。独立审阅发现仅冻结 SQLite 主文件无法检测已提交 WAL 中的 Gold 变化，现已修复为**主文件与 -wal 的存在性和字节 SHA**；不读取 Gold SQL、不包括易变 shm。准备前后比较，评分在全部生成冻结检查之后、打开参考答案之前比较，投影后再次比较。WAL checkpoint 造成字节身份改变时会保守拒绝；本工具不主动 checkpoint 或 vacuum。

## 费用与执行边界

模型 `deepseek-flash`；query analysis thinking disabled，resolution low，answer disabled。保留既有 settings 的 temperature 0、max_tokens 32,768、内部重试 2。

- Hybrid 最多 2 个生成操作/题；Dynamic 最多 3 个生成操作/题。
- 100 × (2+3) × (1+2) = **1,500 次物理请求**。
- 每次实际 messages JSON 最多 **160,000 UTF-8 字节**，输出最多 **32,768 tokens**。
- 按 2026-11-04 官方峰价 cache-miss input 0.30 / output 1.20 USD 每百万：每请求预约上界 `(160000×0.30 + 32768×1.20)/1000000 = 0.0873216 USD`。
- 总硬上界：**130.9824 USD**。已在执行前重新读取官方价格，峰价匹配本政策，并取得本阶段明确授权。

BudgetTransport 使用独立、不可静默改策略的 SQLite ledger，所有内部重试共享上限；HTTPTransport retries=0。超字节/输出/模型约束时本地拒绝，不截断 payload，不切换策略。缺失 usage/transport unknown 保留预约。现有关系阶段授权不覆盖本实验。

执行必须同时匹配精确授权、plan/inputs/sample/settings/生产模块 SHA、准备数据库与 ledger 快照；持有 backend ownership 后落一次性 marker。不提供自动重启、自动扩大预算或补跑。

## 新增入口

- `tools/m5/level_c.py`：prepare、execute-authorized、review-units、score。
- `tools/m5/level_c_embedding_preflight.py`：仅本地实际 MiniLM question 编码。
- `tests/test_m5_level_c.py`：独立 synthetic 验证。

准备命令（本轮已实际执行；目标必须不存在）：

```sh
PYTHONPATH=tools/integration/offline_guard:src:. /home/kenqia/my_folder/locomo-dynamic-memory/.venv/bin/python -m tools.m5.level_c prepare --output var/m5-development/level-c-preparation-v1/final/final-v2
```

在授权未落文件时 `execute-authorized` 默认报错，且不会产生 marker 或请求。真实 execute 已按授权终结；原执行 marker 保留，禁止重复执行。脚本不生成任何授权文件；`expected_authorization()` 仅返回审阅时可核对的所需结构。

生成阶段每个计划 item 都保留成功/失败状态和原始 trace。只有全部 200 个 item 的身份、状态、文件 SHA 都被冻结后，独立 score 命令才能打开开发 Gold；不完整或篡改的 generation-freeze 会提前拒绝。Gold 缺失的题目单列不计零；可评分运行失败计零，同时输出仅成功题分数。普通题与诊断题分别汇总，每题差值、每对话/类别差值及固定 seed 配对 bootstrap；四个暴露开发对话仅支持探索性结论。

`review-units` 只在相同完整生成冻结之后导出 question、answer/citations 与完整 conversation 来源，供独立语义核查；其标签默认为 null，不声称已审阅。Answer source support、正确/错误拒答、人物/事件/时间错误、列表遗漏在独立复核前明确为 not_measured。

## 新鲜验证

运行：

```sh
PYTHONPATH=tools/integration/offline_guard:src:. /home/kenqia/my_folder/locomo-dynamic-memory/.venv/bin/python -m pytest tests/test_m5_level_c.py -q
```

结果：**5 passed，34.39 秒**；1 条既有 Starlette/httpx deprecation warning。全部使用 synthetic conversation、mock HTTP 和受控测试 embedding，不是真实模型质量证据。测试覆盖实际四个 synthetic 完整 Build、200 个计划回答、502 次 mock 物理请求（首项 schema/citation 三次失败计入分母）、Gold/evidence 哨兵零泄漏、200 个冻结结果后的独立评分、缺失 Gold、review units、授权缺失、准备状态篡改、结果篡改、不完整 freeze。另覆盖主 SHA 不变且 WAL 已提交 Gold 改动时，必须在参考查询之前拒绝；准备过程中并发 WAL 写同样拒绝且不产生 plan。

独立审阅者已复现原主文件 SHA 漏检 WAL 的 P2，并在修复后独立重跑 **5 passed / 36.60 秒**；当前明确审阅范围无剩余阻断 finding。这是代码复核结果，不是付费授权或整个 M5 的完成验收。

本轮对真实固定 100 道 question 运行了缓存的 pinned MiniLM：全部成功得到 100×384 有限归一化向量，CPU，最大输入 256 tokens、超长拒绝；真实 provider calls=0、generation=False、Gold=False。最新候选预检耗时 **3.1600 秒 wall / 4.9429 秒 CPU**，进程峰值 RSS **632,940 KiB**，详见 `final/final-v2/embedding-preflight.json`。这是本地编码可用性证据，不是 QA 得分。

## 未完成与剩余限制

已完成真实生成、评分、延迟/token/预约汇总和独立AI来源审阅，详见结果报告；没有实际账户账单或人工/教师语义真值，未晋级 Bonus 或 Level D/E。用户随后已确认最终评测使用DeepSeek-V4.1-Flash-1017且禁止thinking，见[模型要求](MODEL_REQUIREMENTS.md)。本次resolution low结果保留为开发诊断，不算全链disabled最终成绩。

未修改 src 或冻结历史数据库。准备工具与测试已在本地提交323917c；没有远端写入、push、PR 或 Notion 更新。
