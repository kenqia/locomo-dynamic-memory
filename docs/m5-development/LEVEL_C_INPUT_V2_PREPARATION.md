# Level C input v2 准备结果

2026-11-04。**已完成真实 prepare，状态为 `prepared_not_authorized`。** 新阶段尚未获得付费批准，没有创建 `authorization.json` 或 `execution-started.json`，物理请求为 0。本页提供可审阅的独立提案，不追认旧 QA 补跑，也不复用旧阶段剩余额度。

## 实验范围

工作树为 `/home/kenqia/my_folder/locomo-worktrees/m5-final-input-v2-20261104`，分支为 `codex/m5-final-input-v2-20261104`，基线为 `3335862dba1e9658f4d5c515b602c98049826d7c`。代码、测试及准备工件将在本提案提交中本地 commit；`src/`、生产配置、旧实验工作树和原 conv-43 关系进程未修改。旧 QA 仍由旧工作树中的冻结工具审计。

新 stage 为 `var/m5-development/level-c-input-v2-preparation-v1`，使用独立 `memory.sqlite3` 和 `physical-requests.sqlite3`。固定沿用既有 80 普通题、20 诊断题，每个开发对话为 20+5 题，Hybrid/Dynamic 两臂合计 200 项。Bonus 全部关闭；不读取留出，不重新抽取或建立关系，不重建、发布四份开发 Build。

| 对话 | 固定 Build |
| --- | --- |
| conv-26 | `367c901b300440649bdc0bfba2af8010` |
| conv-30 | `b8f34a05c8ef4585a1fc3c917745aa53` |
| conv-41 | `8d459492549b4a3e88005211f036addf` |
| conv-42 | `c892596ac8884f43b4cf2098349a7fa5` |

严格导出验证的四份 Build 合计 1,237 Memory、884 个引用 Source Turn、22,691 条关系。历史构建的模型血缘原样保留；新 settings 的全 disabled 不表示这些历史 Build 被重建为全 disabled。

## 新旧设置与授权边界

用户已明确要求最终模型为 DeepSeek-V4.1-Flash-1017，禁止开启 thinking；本次新的所有生成操作显式设置 `thinking={"type":"disabled"}`，不发送 `reasoning_effort`。`thinking_enabled=false`，extraction、relation、query analysis、resolution、answer 的五个 effort 均为 `disabled`，不接受 `low` 或 `high`。本阶段只运行三个 Query 操作，extraction/relation 的拟执行次数为 0。

| 设置 | 旧 Level C | input v2 提案 |
| --- | --- | --- |
| messages UTF-8 字节上限 | 160,000 | 640,000 |
| 完整 resolution 正则 token 预算 | 96,000 | 192,000 |
| query analysis / resolution / answer | disabled / low / disabled | disabled / disabled / disabled |
| relation effort 设置 | high | disabled；本阶段不运行 relation |
| 最大输出 tokens | 32,768 | 32,768 |
| 每操作内部重试 | 2，最多 3 次尝试 | 2，最多 3 次尝试 |
| 物理请求硬限 | 1,500 | 新独立 1,500 |
| 峰价最大预约 USD | 130.9824 | 新独立 346.9824 |

用户明确请求 192,000 token 预算；640,000 bytes 是对“再翻倍字节”问题形成的具体待批方案。该讨论和准备行为均不等于本阶段费用批准。

`proposal_version=m5-level-c-input-v2`、独立 scope、plan SHA、settings SHA、生产模块 SHA 与初始数据库/ledger 快照共同限定该阶段。执行入口要求精确匹配新的授权结构；旧 scope、旧 plan SHA、旧授权或旧 ledger 均在 HTTP 前拒绝。原授权不适用于新阶段；不清除或重用旧 marker。

## 请求与费用上界

按固定 100 题计算，各操作最多尝试 3 次。失败项仍保留，不截断输入、不切换策略、不在阶段结束后自动补跑。

| 策略与操作 | 逻辑操作上限 | 物理请求上限 |
| --- | ---: | ---: |
| Hybrid query analysis | 100 | 300 |
| Hybrid answer | 100 | 300 |
| Dynamic query analysis | 100 | 300 |
| Dynamic resolution | 100 | 300 |
| Dynamic answer | 100 | 300 |
| 合计 | 500 | 1,500 |

根代理于 2026-11-04T07:53:34.814476+00:00 重新读取 DeepSeek 官方定价页，确认 `deepseek-flash` 当日映射为 `DeepSeek-V4.1-Flash-1017`、公开 context 为 1M、峰时 cache-miss 输入 USD0.30/百万及输出 USD1.20/百万。公开记录为 [pricing-input-v2-20261104.json](../../experiments/m5-development/pricing-input-v2-20261104.json)；公开页面原件与 JSON 已分别复制至新 stage 的 `pricing-recheck.md` 和 `pricing-recheck.json`。本子代理没有重复联网。

```text
每请求最大预约 = (640000 × 0.30 + 32768 × 1.20) / 1000000
               = USD0.2313216
阶段最大预约   = 1500 × USD0.2313216 = USD346.9824
```

输入字节是保守 token 上界，不是实际 tokenizer 用量。所有 schema/transport 内部重试共享独立次数和金额硬限；底层 HTTP retries=0。Unknown/部分 usage 保留全预约。预约上界不是预计消费或账户账单；准备阶段没有产生 Provider 费用。

API 请求仍使用可变 alias `deepseek-flash`。官方映射和实际响应 model 应分别记录；没有不可变服务端版本 pin 证明，不发明日期版请求 ID。

## 初始输入门槛的证据边界

旧实验工作树的公共 `experiments/m5-development/level-c-input-diagnostics-final-v2.json` 经入口/出口完整审计后，重建全部 100 项初次 resolve：最大 480,456 messages bytes、145,670 正则 tokens。在原始完整 payload、没有空白压缩或可逆分组的前提下，640,000/192,000 两道本地门槛全部满足；320,000/192,000 仅 87/100 满足。

该公共报告 SHA 为 `e129ae0caec789b640533c3a863aa20646213b45859278770c34f6f0721f14af`。它是旧运行初次请求的离线重建，未捕获原始 wire，不覆盖重试反馈、新 query analysis 输出、服务端 tokenizer/context 接纳、schema 成功或 QA 质量。**100/100 通过初始本地阈值不等于 100/100 新运行成功。** v2 未产生答案、分数或模型质量结论。

## 实际准备和完整性检查

本次在新工作树使用既有 Python 环境、离线网络守卫、清除凭据环境后实际调用 `tools.m5.level_c.prepare`，随后运行 `verify_plan`。常规准备命令如下；本目标已存在，禁止重复执行或覆盖。

```sh
PYTHONPATH=tools/integration/offline_guard:src:. /home/kenqia/my_folder/locomo-dynamic-memory/.venv/bin/python -m tools.m5.level_c prepare --output var/m5-development/level-c-input-v2-preparation-v1
```

生成前从历史 Run 仅通过 SQL 投影读取 config、Build pins、dataset ID、question 和身份，不在 Python 中加载完整 Run、答案或 evidence。源库使用只读连接；独立库只复制开发 Build 所需表，不含历史 evaluation 或 import annotations。生成冻结完整性校验仍先于后续独立评分的 Gold 访问。

`preparation-verification.json` 实际确认：四份 Build、100 question、200 planned items；五个 effort disabled；192,000 resolution budget；物理 ledger 为 0；query 表为空；evaluation 表不存在；import annotations 为空；无授权文件或执行标记。源库 main 和 WAL 的存在性与字节 SHA 在准备前后完全相同：

| 源存储 | SHA-256，准备前后相同 |
| --- | --- |
| main | `ffa299c36ba1d15a6148826dd14430dca6e4ebfa27069d7a141021987cda060c` |
| WAL，存在且为空 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |

私有 inputs 和 Memory 保留在 Git 忽略的 stage，不提交原文。公共文档只记录身份、数值和 SHA。

## 已运行验证

根代理在最终四个代码/测试文件上实际执行：

```sh
./tools/integration/check.sh tests/test_m5_level_c.py tests/test_m5_level_c_audit.py -q
```

结果为 **52 passed、1 warning、136.09 秒**。原日志 `/tmp/m5-input-v2-tests.txt` 已原样复制为 [level-c-input-v2-targeted-root.txt](../../experiments/m5-development/test-results/level-c-input-v2-targeted-root.txt)。测试使用 synthetic conversation、mock HTTP、受控 embedding 和外部网络守卫；没有使用真实 Provider，不是模型质量证据。本子代理此前一轮为 51 passed、1 warning、183.81 秒，未包含最后新增的 audit 严格禁用回归；最终以根代理的 52 项结果为准，没有再次无意义重跑。

覆盖实际五种操作 HTTP body 的 thinking disabled、不发送 reasoning_effort；五个 effort 的 low/high 拒绝；640,000 bytes 和 32,768 output 的精确边界；1,500 次及 USD346.9824 的次数/金额边界；Unknown 预约不退款；旧授权、旧 plan SHA、旧 scope 和旧 ledger 拒绝；全部 200 synthetic 项冻结后的评分；Gold/evidence 哨兵、缺失 Gold、WAL 改变、结果篡改和不完整 freeze 的拒绝。audit 同时要求 `thinking.disabled` 与 `reasoning_effort=None`，不能用 enabled thinking 配上 disabled 字符串绕过。

本次没有重新运行全仓测试。非作者已独立复核并完成 24 项定向测试，未发现 P0/P1/P2；见 [LEVEL_C_INPUT_V2_REVIEW_V1.md](LEVEL_C_INPUT_V2_REVIEW_V1.md)。这些验证不等于最终 Release 批准。

## 冻结身份

| 工件 | SHA-256 |
| --- | --- |
| stage `plan.json` | `3c9adc27b22d1b1da0175a508636ba51e8cdb2fd744a6faed566a963c2a79af6` |
| stage `settings.json` | `08af05ac9e8bf9555b628af8ed28d9739493693155faa7000f7f171119669ebb` |
| stage `inputs.json` | `0816f9f2f60acc068a7a6bf3562c603db6545ea85920d1d6cfcfe2ba0ae7c9f0` |
| stage `sample.json` | `f5be6536b105b78d7dc0eca44f7eecaa4b9b6a71d9d3662f115d361c6e707aeb` |
| stage `build-identities.json` | `050a345fe246a10e0dd8b069b5269bfb952f139c2f5c572c35e26f4c9f6787f2` |
| stage `preparation-verification.json` | `975e6853263ee20d62fd635f13fff8f3994dedd8997732f72d16b6e6e168cef6` |
| stage `pricing-recheck.md` | `45396c395f2bbe150317331dcd9e4d0b485456432e0d891af7d0c9028f6abc9d` |
| stage `pricing-recheck.json` | `098d020a08cf63f9ceb12a6304b0e7beea60dbe2b7bcfc0afafc9a10b6a5b8d7` |
| `tools/m5/level_c.py` | `def5898c6afe2c6e9a5c5cf419bd9e2e12b11bf2878300929f305b04917e5334` |
| `tools/m5/level_c_audit.py` | `c8823a95c1c5a52212fb7a9b7138da50ac30efeef2218d28510feee03c2085ab` |
| `tests/test_m5_level_c.py` | `57a5997207a7b7094dac20e2bce714d1777c8bf5bc7c1bdc00c001c439e90303` |
| `tests/test_m5_level_c_audit.py` | `8957cd0ee403d57fe7a82e31b6249688a8b7692605621ae2a23303d1d047b8c7` |

准备后没有更改 plan/settings 或被 plan 绑定的生产模块。放弃本提案时保留此未授权 stage 作为实验记录即可；旧工作树、原数据库和原关系阶段不需要回滚。

非作者复核已完成；下一步仅在具体费用批准完成后，由负责人决定是否建立绑定本 plan SHA 的新授权并执行；本页没有创建授权或发起新调用。没有识别关联 Notion 任务，本次未同步、未标记完成。
