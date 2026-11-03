# DYN-01 五组动态机制验证与16K/32K恢复

日期：2026-10-27—2026-10-29

## 当时问题与假设

固定抽取能否识别扩展/解析/关系复用贡献？

## 方法与输入

conv30/41/42，ABCDE×3最多1080；16K和32K不同campaign

## 配置

按来源版本与冻结配置；本归档未修改或执行历史配置

## 执行代码身份

以来源记录中的执行 commit / implementation SHA 为准；source_commit 是证据文件版本，不能替代执行身份

## Run ID

证据缺失或本项不适用；不补造。

## Build ID

conv30 5abd7718841d417ebd71a1db896be39f; conv41 e45e688ea9ec467eae7f052df0dd0ae2

## 统计分母

最多1080计划；QA完成数见原件，未完成

## 实际结果

16K第107调用结果用量未知；32K多次transport恢复后conv30完整；conv41抽取33/34，重复失败；正式1080未完成

## 失败与unknown

见 observed_result；未明确报告的失败、unknown 与用量为证据缺失，不推定为零

## 结论与采用状态

停止；不从完整conv30外推全部机制收益

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

- [S113](../evidence/S113.md)：experiments/dynamic-validation/README.md；SHA256 f04a82bcff80a16923e5df268c170ed706ac481c8af47255def9ee11683be469
- [S115](../evidence/S115.md)：experiments/dynamic-validation/results/32k-conv41-diagnostic-proposal-20261028.md；SHA256 cc2b72a3efd8102651d360a19f9b1822c4e850c84618368a4db2354c87bbe09a
- [S116](../evidence/S116.md)：experiments/dynamic-validation/results/32k-conv41-extraction-recovery-20261028.md；SHA256 b4afb8714abfa7bd22576b102b706d1ea7ccba0f98a3bf806c31645c31754f83
- [S117](../evidence/S117.md)：experiments/dynamic-validation/results/32k-second-recovery-proposal-20261028.md；SHA256 3cf33fe08439fd87ca932533542ff7ca1e0bdc81cf35f582a9ccfd013234f26d
- [S118](../evidence/S118.md)：experiments/dynamic-validation/results/32k-transport-recovery-20261028.md；SHA256 471693850bc1a56885f9955ba785ddfaa0c2e3678a45ebdcd1852dcbb26c8491
- [S121](../evidence/S121.md)：experiments/dynamic-validation/results/recovery-107-proposal-20261028.md；SHA256 10cf70d8e9629cdf341af5370ce89f6341272911aefe8670e30c962c75a55a2e
- [S122](../evidence/S122.md)：experiments/dynamic-validation/results/recovery-20261028.md；SHA256 904f36ef7ae529eeab93c76087a1ab4e54d42a1998aa20c8774090b1c086a62a
- [S123](../evidence/S123.md)：experiments/dynamic-validation/results/relation-budget-32768-20261028.md；SHA256 7b9cd6d270412600049d42a11e8e1ff7cb5f20b2271d48c469b94d64869baffd
- [S124](../evidence/S124.md)：experiments/dynamic-validation/results/run-start.md；SHA256 a67c51cefc55bb0766aa09361d321ba993dea606d97ed173d53def940776ded7
- [S139](../evidence/S139.md)：experiments/dynamic-validation/README.md；SHA256 6ab6911943d1981e86c7571f06bd6d63f3b79d1e18ed5f51eec45c883faff000
- [S156](../evidence/S156.md)：experiments/dynamic-validation/README.md；SHA256 d27e87b804c28ddbbef75d2fe068a02bb27e25f0108a8ae65d1462780c713f51

完整配置身份原文摘记见 [机器索引](../experiments.json)。来源版本不是执行代码身份。

[返回研究问题](../questions.md)
