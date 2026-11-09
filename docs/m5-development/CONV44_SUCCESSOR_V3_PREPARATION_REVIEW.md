# conv-44 successor v3 准备工件独立复核

2026-11-04。**通过：7 组独立只读检查，未发现 metadata 问题。** 新阶段已准备，尚未授权。新 Build `d9fb61417bb740e4b8eb34acb8652a46` 保持 `queued` / `extraction`，33 个成功片段及 383 条 Memory 已继承；ordinal 18 的完整 20 条 source 为唯一 pending 片段。

本结论只确认准备工件与已审代码、父终态及预算契约一致，不授权付费调用，不保证真实恢复成功。当前仍未生成第六份完整 JSON，Level E 继续 blocked。

## 范围与方法

工作树：`/home/kenqia/my_folder/locomo-worktrees/m5-final-conv44-recovery-v3-20261104`。

准备阶段：`var/m5-development/conv44-successor-v3`。复核时 HEAD 为 `fe455f5182e04f5b20fc0d9ae89424a680968dc5`；入口脚本、v5 prompt 和安全诊断 SHA 与[非作者代码复核](CONV44_SUCCESSOR_V3_REVIEW.md)一致。

复核方使用 `env -u DEEPSEEK_API_KEY -u OPENAI_API_KEY -u CODEX_ACCESS_TOKEN`、项目 `offline_guard` 及已有虚拟环境运行独立 Python 检查。SQLite 连接均为 `mode=ro`、`query_only=ON`，检查以提交可见逻辑行核对数据库和账本身份，包含 WAL。为避免构造器写入数据库，当前 Build 契约检查只调用无数据库写入的 fingerprint/config 校验。

source 与继承 Memory 的正文只在内存中用于严格验证和等价比较，没有输出正文、表达式或 source ID。未读取留出 QA、evidence、answers、凭据或原始 provider 日志；未发起 live 请求。官方价格网页缓存只核文件 SHA，没有打印正文。唯一新建工件为本报告与[安全检查 JSON](../../experiments/m5-development/conv44-successor-v3-independent-check.json)，均未覆盖既有文件。

## 七组检查结果

| 组 | 独立检查 | 结果 |
| --- | --- | --- |
| 1. 范围与父终态 | 先以 SQL 检查 conversation-only 表集与空评测 annotations，再核父库、父账本、plan、settings 和终态 manifest | 全部匹配；父库与父账本逻辑身份与冻结终态一致 |
| 2. Producer 与新契约 | 独立枚举 82 个 producer 文件，包含当前 recovery helper；核入口脚本、settings、继承 sidecar、父 producer 和新 fingerprint/config | 全部 SHA 匹配；新 Build 为当前 v5 契约；所有新 thinking 字段 disabled，resolution input budget 为 192,000 |
| 3. 父记录保留 | 将源库每张表的全部原 rowid 行与新库对应范围逐行比较，并比较 schema | 原记录完全相等；旧 Build 仍为 failed/extraction；原库未被修改 |
| 4. 继承等价性 | 对 33 片段、383 Memory 核身份映射；对除 memory_id/build_id 外的 JSON、关系列、source links、session times、历史 metadata 及 payload 摘要逐项比较；重跑严格 Memory/MemoryDraft 校验 | 全部相等；新 calls 和 returned_models 为空；历史调用独立保存；混合 producer 声明及 sidecar 摘要一致 |
| 5. 唯一失败片段与输入 | 比较旧失败 ordinal 18 与新 pending 片段的 source 顺序，并核对完整 position 范围；构造实际首请求 messages 但不调用模型 | 正好 20 条 source，无新增 Memory；首请求为 20,217 UTF-8 字节，小于 160,000 字节上限；外键检查通过 |
| 6. 账本、门禁、权限与费用 | 核独立账本 policy/0 请求、未批准模板、无 authorization/marker/outcome、目录文件权限、峰价与保守费用上界 | 全部通过；stage 为 0700，全部现存私有文件（含 WAL/SHM）为 0600；无旧预算转移 |
| 7. 检查后不变性与公共工件 | 重新核父库/账本/plan/settings 及新库/新账本快照，生成只含安全计数、布尔值、身份和摘要的独立 JSON | 检查前后均未变；独立工件成功新建 |

“继承等价”表示继承内容在允许的身份变换后相等，并通过现行严格 schema；它不替代事实准确率评价。父片段仍来自旧 prompt，不能宣称全部由 v5 重新生成。后续严格导出须另附绑定导出 SHA 的混合来源 sidecar。

本轮未重复合成测试或全仓测试。代码复核已有独立 44 项合成验证；实现方另外报告全仓 `842 passed, 1 skipped, 4 deselected`，以及最后 helper 修改后的 14 项新鲜 successor 验证，这些结果不冒称本轮独立重跑。

## 预算与模型限制

独立 policy 最多 3 次物理请求，单请求最多 160,000 UTF-8 字节、32,768 输出 tokens。按 input USD 0.30/M、output USD 1.20/M，并以每字节一个代理 token 的保守上界计算：

```text
单请求上界 = (160000 × 0.30 + 32768 × 1.20) / 1000000
           = USD 0.0873216
三次请求上界 = USD 0.2619648
```

账本当前物理请求为 0。schema 与 transport 重试共用上述请求和金额封顶；Unknown 保留全部预约，旧阶段余额不转移。当前检查只确认门禁文件不存在，未调用执行入口或创建授权。

价格依据为旧树当日公共记录 `experiments/m5-development/conv44-isolated-recovery-v2-pricing.json`，日期 2026-11-04，来源为 [DeepSeek 官方价格页](https://api-docs.deepseek.com/quick_start/pricing/)。其峰价字段与 policy 相等；公共网页缓存 `var/m5-development/recovery-v2-pricing-official.json` 的 SHA 与记录相等。本轮未重新访问官网。记录公布版本为 `DeepSeek-V4.1-Flash-1017`，实际请求 alias 为 `deepseek-flash`；不可变服务端版本 pin 未获证明。

`EXPORT_READINESS.md` 的新增状态与准备工件一致：五份严格完整导出已完成，conv-44 和第六份导出仍 blocked。准备成功不改变该边界。

## 工件身份

| 工件 | SHA-256 |
| --- | --- |
| 新 plan | `27fbb376bbd493c7911b55124c3a6e71930428fe86e10d65f1533af208114bbd` |
| 新 settings | `3e2bd434a1c75f263a35dd5f28be50d858ff8047e0e540390a68b8fce0eafe28` |
| 继承 sidecar | `b5e312b5c54bde04f57c1d6961e6dd108a1c9594c6a6ffa8526b0ce2969cdf1e` |
| 82 文件 producer 清单的 canonical 摘要 | `e5ef399482f6bce1114577f92deac4135fd9e5277a283aaeac33c2337012ca18` |
| 入口脚本 | `8d2aba66c44c77844d7c597e11c3027f586b47a128d475ab25b2c2652b2b0c6a` |
| 父终态 JSON | `18e8b9d61a7b14e6904b282f4e8fb4025182065187aab2fee7e9f7714d2d9e80` |
| 官方价格公共记录 | `ae1cb4884b36d241d8fc04704c0a7785a4eb78212770fb9b5846ab2d6f3a5d0e` |
| 官方价格原网页缓存 | `1274fca04ca89edff81c866ac0abbbbcea3d69f1b5f2496047e7f49ce8ab11ed` |
| 本轮独立安全检查 JSON | `a60ea7417070418455e458ac39e6b3b8e9fa74f4e3239161679ffb29bae7dce1` |

准备复核通过；付费执行仍待用户对精确 plan 的明确批准。
