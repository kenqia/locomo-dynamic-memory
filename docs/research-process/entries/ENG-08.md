# ENG-08 浏览器/CI与安全复盘

日期：2026-10-19

## 当时问题与假设

能否以真实UI识别受控夹具和环境缺陷？

## 方法与输入

Playwright/HTTP/SQLite/受控provider；临时环境

## 配置

按来源版本与冻结配置；本归档未修改或执行历史配置

## 执行代码身份

以来源记录中的执行 commit / implementation SHA 为准；source_commit 是证据文件版本，不能替代执行身份

## Run ID

证据缺失或本项不适用；不补造。

## Build ID

证据缺失或本项不适用；不补造。

## 统计分母

证据缺失或本项不适用；不补造。

## 实际结果

112 passed/4 skipped；故障注入预期失败；浏览器exit0；早期独立审查含安全问题

## 失败与unknown

见 observed_result；未明确报告的失败、unknown 与用量为证据缺失，不推定为零

## 结论与采用状态

采用工程改进；旧报告中的未push是当时状态

## 局限

开发诊断/已知题结果不能推断隐藏集；结构、引用 ID 与 scorer 不等于语义正确；未复跑历史实验

## 人类参与

用户提出问题、范围取舍及授权见原记录；未将助手实现或实验执行归为用户亲手完成

## AI参与

原记录中的实现、运行、分析或 AI 复核；本次另由 AI 只读归档

## 复核类型

未发现独立人工验收；原记录中的 AI 审查/作者检查与工程测试分别保留

## 源码与测试

现有安全分支 src/、tests/、tools/；历史特定源码/测试若未在白名单中则 HOLD，不能声称新检出可重现原 Run

## 报告和数据

公开指标见 metrics.json；原表/Trace/数据/盲审原件保留在本地，按证据 SHA 定位

## 费用口径

provider token/峰时价格估算/未知预约/实际扣款分开；实际账单未核对；各轮额度和重复报告不累加

## 证据入口

- [S008](../evidence/S008.md)：experiments/issue-12-integration-validation.md；SHA256 1970baf887316efb33f5f45722284843e508ef9aa8466f67806c9fe39dcee127
- [S051](../evidence/S051.md)：experiments/issue-4-implementation.md；SHA256 969dc02fa3e71c3463cbe7d294d27a384d32972828dae85b906a4aeb3f078655
- [S052](../evidence/S052.md)：experiments/issue-4-review-fixes.md；SHA256 e6a698ea2535ce8b88572980d5bafe984a874fdb03e6844d97b04bbf17fda92e
- [S053](../evidence/S053.md)：experiments/issue-4-review.md；SHA256 94e885cd39e095ab8dc22da27e5fd11f6362fbc8f02b014642921456044af2f8
- [S059](../evidence/S059.md)：experiments/retro-validation-guardrails.md；SHA256 81c9f53e9226b26667e274d0a8c236368d8671f3b9b88280ebb946bf46e9e71b

完整配置身份原文摘记见 [机器索引](../experiments.json)。来源版本不是执行代码身份。

[返回研究问题](../questions.md)
