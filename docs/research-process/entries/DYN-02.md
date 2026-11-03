# DYN-02 时间锚点因子与反馈探针

日期：2026-10-28

## 当时问题与假设

引用锚点/源句表示能否解决conv41失败？

## 方法与输入

四组有限对照阶段1最多12请求；阶段2有复核门槛

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

8可用输出/4不可用，48事实判断待审；后续反馈3次仍失败；不启动完整重建

## 失败与unknown

见 observed_result；未明确报告的失败、unknown 与用量为证据缺失，不推定为零

## 结论与采用状态

阶段2未获得证据支持；保留抽取8份待审

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

- [S140](../evidence/S140.md)：experiments/dynamic-validation/results/anchor-factorial-20261028/RUNBOOK.md；SHA256 6dcab7bd28340fc1dc67df6a4ae48a3c3c4336a2c7233168df4adc844bba19f5
- [S141](../evidence/S141.md)：experiments/dynamic-validation/results/anchor-factorial-20261028/design.md；SHA256 8d2b1ac984aa0a102488c6aff8dc898f2b221f2bc48f62833bd7f5725acbfb64
- [S142](../evidence/S142.md)：experiments/dynamic-validation/results/anchor-factorial-20261028/source-review-package/README.md；SHA256 f98236f1950f5a898b771210eddcf671e28753ef1b37c1e0e150895dc7d84963
- [S143](../evidence/S143.md)：experiments/dynamic-validation/results/anchor-factorial-20261028/stage1-output-review-package/README.md；SHA256 a0e84d3ea4d7250fcf0dd36b808dd24496213f7185ccd43d9a92a12e5bacef46
- [S144](../evidence/S144.md)：experiments/dynamic-validation/results/anchor-factorial-20261028/stage1-results.md；SHA256 18d11123c359c7f48961d8b957295d386a433d697d51281a0e344f2ab8452aa6
- [S145](../evidence/S145.md)：experiments/dynamic-validation/results/anchor-feedback-probe-proposal-20261028.md；SHA256 22c12d51411f54b3f2ad2dd5679ef155ae0a34c68474a18e19dcba6a791e0083

完整配置身份原文摘记见 [机器索引](../experiments.json)。来源版本不是执行代码身份。

[返回研究问题](../questions.md)
