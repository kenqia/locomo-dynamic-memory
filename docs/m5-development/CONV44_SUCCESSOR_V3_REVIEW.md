# conv-44 successor v3 非作者代码复核

2026-11-04。最终 Standards 与 Spec 两轴均通过，未解决发现均为 0。当前代码可进入独立离线准备与准备工件复核；本报告不授权真实 provider 调用、索引、关系构建、发布或 Level E，也不保证真实恢复成功。

## 范围与方法

工作树为 `/home/kenqia/my_folder/locomo-worktrees/m5-final-conv44-recovery-v3-20261104`，固定基点为 `3f8929839e30cd085b105504ca1a6fe11fcf216f`。基点至 HEAD 没有新提交，`git diff <base>...HEAD` 为空；按明确要求，实际审查使用 `git diff <base>` 加 `git ls-files --others --exclude-standard`，包含下表全部代码、测试与文档。实现方完成修改，复核方未修改实现、测试或提交代码；唯一写入为本报告。

按仓库 `.agents/skills/code-review/SKILL.md` 分离 Standards 与 Spec 轴。受并发槽位限制，两名独立子代理顺序执行，两轴未互换初始结论；主审另行阅读最终实现、复查修复并运行合成测试。文档使用 `google-developer-docs` 技能整理。

Standards 来源为用户工作约定、项目 `AGENTS.md`、`CONTEXT.md`、相关 ADR 和技能的 Fowler smell baseline。Spec 来源为本次明确恢复要求：独立新 Build 继承成功片段，仅恢复原完整失败片段；保留冻结源库、账本和旧 Build；全部新 thinking disabled；严格 schema 不放宽；真实混合血缘与独立计费；精确授权、预算、锁和单次 marker；Unknown 保留全额预约；成功最多到 `extracted`。

未读取真实 stage、留出 QA、evidence、answers、凭据或原始 provider 日志；未执行真实准备或 live 调用。历史数量和结果沿用已复核的公共记录，本次不重新审计其正文。

## Standards

最终未解决发现：0。没有值得报告的启发式 smell。

初审发现一项 P2：新增 CLI、v5 prompt 与安全诊断缺少配套文档，不满足“修改行为、setup、命令或架构时，同步更新相关 README、docs 或项目 AGENTS.md”的约定。实现方新增 `CONV44_SUCCESSOR_V3.md`，并更新 `LEVEL_E_GATE.md`；独立 Standards 子代理确认其覆盖命令、授权范围、预算、继承血缘、诊断限制、后续顺序与回滚，且与代码一致。该项关闭。

## Spec

最终未解决发现：0。

初审发现一项 P2：计划的 producer 摘要缺少当前工作树 `isolated_extraction_recovery.py`，但新工具实际依赖其只读与隔离 helper；旧工作树同名脚本的校验不能冻结当前 helper。实现方新增局部 `producer_hashes()`，显式纳入 `prior.__file__`，并在准备和执行时使用同一清单。新增合成测试证明 helper 摘要变化在写执行 marker 和调用 provider 前以 `successor_producer_changed` 拒绝。主审和独立 Spec 子代理均复核该修复，问题关闭。

其余要求的实现与验证一致：

- 新 Build 保留旧记录，仅原失败 ordinal 为 pending；继承 Memory 除身份外保持相等，并重新执行严格验证及 source links、session times 检查。
- 源库与源账本保持只读；原 rowid 范围和继承记录分别由摘要保护。合成测试覆盖网络期间修改继承记录后的拒绝。
- 新阶段 calls 为空，历史调用另存来源 metadata；新请求使用独立账本，不转移旧预算。计划、配置、sidecar、父终态、核心 producer、当前 helper 和入口脚本均冻结。
- 全部 thinking disabled；精确授权、数据库锁与单次 marker 限制执行。Unknown 测试保留三次请求的全部预约。
- 运行入口只调用抽取服务，成功停止于 `extracted`；无 index、relation、publish 或 QA 入口。
- `memory_schemas.py` 相对基点无变化。v5 prompt 与三个合成例强化原文时间引用；安全诊断只返回固定路径、类别和布尔值，其异常不改变严格失败、重试反馈、usage 或预算。

## 新鲜验证

主审在最终代码上运行：

```sh
./tools/integration/check.sh tests/test_m5_conv44_successor.py tests/test_extraction_time_diagnostics.py tests/test_extraction_examples.py -q
```

结果：**44 passed，20.19 秒**。其中 successor 为 14 个 case。出现一条既有 `StarletteDeprecationWarning`。入口移除真实凭据变量并启用离线守卫；测试只使用合成资料与 `httpx.MockTransport`。测试前后代码摘要一致。

本报告不重复全仓测试；实现方另行运行的全仓检查不作为此处的新鲜验证结论。合成 fixture 的继承数量为 1 片段、1 Memory，不能替代真实准备后对预期 33 片段、383 Memory 的独立 metadata 核对。

## 最终审查身份

以下 SHA-256 对应最终审查内容；报告自身不纳入此表。

| 文件 | SHA-256 |
| --- | --- |
| `tools/m5/conv44_successor.py` | `8d2aba66c44c77844d7c597e11c3027f586b47a128d475ab25b2c2652b2b0c6a` |
| `tests/test_m5_conv44_successor.py` | `c62a1b851976183bb18cbd6b44d90eafd853abe6aa9a9834e228cf3c27065f08` |
| `src/locomo_memory/model.py` | `3eb285d6283e09decda40635af842eeb40d31f993e5c9a6d3db7cedddb2bb368` |
| `src/locomo_memory/extraction_examples.py` | `7d90f6d6031571b5f1d0108c5b3016dab36a02339c0808967f555b2b1553ee95` |
| `tests/test_extraction_examples.py` | `2598132f6487981034d95f0bb42610038ec049f8df77f15dad86361888971149` |
| `src/locomo_memory/extraction_time_diagnostics.py` | `bf2b5055cb4b78a395929395a60b0a91a4f1ec46eca7472b9271c1bdbd3534f9` |
| `tests/test_extraction_time_diagnostics.py` | `a681107ba22ce0b70354ae6731329731d387b6f00fa172da05e6a98eaef9d263` |
| `docs/m5-development/CONV44_SUCCESSOR_V3.md` | `2af6003b43ddb15ae6b48039cab14569cb54984af3b7b2e490ef29f32f4fbb71` |
| `docs/m5-development/LEVEL_E_GATE.md` | `a996be4b1e7d7ab58fffab0228e2e06537c5874674d22e2cdfc2569c56eda3c6` |

Standards：0 未解决，1 项 P2 已关闭；Spec：0 未解决，1 项 P2 已关闭。
