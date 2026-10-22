# 关系输出的小范围修复

2026-10-20，Asia/Shanghai。本次依据 v5 新 Build 的已持久化错误修复请求指导和内部重试。
没有新增真实模型调用，没有重启完整构建。真实改善幅度尚未验证。

## 证据与修复

[v5 实验报告](issue-15-live-continuation/README.md) 记录 12 个任务连续 3 次在 4096 tokens
上限以 `length` 结束，另 2 个任务连续 3 次因 `verbatim_support_required` 失败。
旧重试循环重复发送相同请求，模型看不到校验器发现的具体错误。这是本次可确定的实现缺口；
没有响应原文，不能断言截断一定由某些默认字段引起，也不能重建错误引用的原貌。

`relations-v6` 增加紧凑输出指导，要求省略无证据的可选字段、缩短理由，并保留完整候选覆盖
及已知日期、条件和来源。引用指导明确要求单条来源中的连续原文片段。
JSON Schema 和领域规则没有变化。

仅当上一次关系调用为 `length` 或 `verbatim_support_required` 时，下一次内部重试
携带 `retry_feedback`，包含错误 code、输出字段路径与静态纠错指导。字段路径不解释为
输入候选位置。不回传被拒绝输出或异常文本，不累积历史反馈，不自动改写关系标签。
候选数、4096 输出上限和现有重试上限保持不变。

该改动局限于现有 DeepSeek adapter。没有新增依赖、数据库迁移、配置项或通用纠错框架。
HTTP 请求错误的具体状态与安全分型仍待后续处理，此次未推断其原因。

## 版本与回退

v5 的实现身份和实验结果保留在原报告，新 Prompt 改为 `relations-v6`。
修复后的生产实现 SHA-256 为
`93c2a407dc7e635906ccfe2e5c69bf20cf8fa9bd23e731691b500c4ce17be29f`。
恢复接口会拒绝用新契约原地重试旧 Build。后续真实验证需要独立回放或新构建，
不能把 v6 结果拼接到 v5 Build。

本次修复前的文件副本保存在本机 `/tmp/issue15-before-output-fix-sdqi2wk4`。
回退时只恢复本次改动对应的文件差异，保留此前尚未提交的 v5 修复及实验产物，
不删除或回退数据库、调用预算库和调用历史。

## 受控验证

新增测试在公开 `DeepSeekModel.generate()` 边界使用合成 HTTP，覆盖 20 个完整候选、
截断与逐字引用错误、0/1/2 次重试配置、完整校验、反馈替换与不泄漏响应原文。
另验证 regex 请求估算包含纠错内容，以及非关系调用维持现有行为。
新增回归在实现前出现 5 项预期失败，实现后 9 项通过。

关系任务 API 的已有测试继续核对逐次诊断、用量去重、显式重试和重启后的历史。
旧有“所有重试请求相同”断言改为检查仅截断后的请求增加反馈，其他输入保持一致。

```sh
.venv/bin/python -m pytest tests/test_relation_output_recovery.py \
  tests/test_model_diagnostics.py tests/test_relation_diagnostics.py \
  tests/test_relations.py tests/test_contract_recovery.py -q --tb=short
```

最终结果为 133 passed，耗时 85.61 秒。未重跑全套非真实测试。

受控成功仅证明代码传递反馈并保留约束，不证明真实模型会按指导生成，也不作为
原始 29 个历史失败任务的根因统计。

预算自检通过，新增真实调用为 0。本轮调用数仍为 313/1,000，v5 Build 仍为
`interrupted`，旧基线数据库 SHA-256 保持不变。`git diff --check` 和文档链接检查通过。
