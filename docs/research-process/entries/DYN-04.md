# DYN-04 解析契约修复及六题提前停止

日期：2026-10-28—2026-10-29

## 当时问题与假设

澄清现有契约是否能通过原两题门槛？

## 方法与输入

修复两题与后续六题效果实验分开

## 配置

按来源版本与冻结配置；本归档未修改或执行历史配置

## 执行代码身份

以来源记录中的执行 commit / implementation SHA 为准；source_commit 是证据文件版本，不能替代执行身份

## Run ID

证据缺失或本项不适用；不补造。

## Build ID

证据缺失或本项不适用；不补造。

## 统计分母

12

## 实际结果

修复4请求214263token；效果4成功/1失败/7未尝试，10请求129252token；第二对话未运行

## 失败与unknown

见 observed_result；未明确报告的失败、unknown 与用量为证据缺失，不推定为零

## 结论与采用状态

保留停止；mini03-A具体违约未知；非总体可靠性收益

## 局限

开发诊断/已知题结果不能推断隐藏集；结构、引用 ID 与 scorer 不等于语义正确；未复跑历史实验

## 人类参与

用户提出问题、范围取舍及授权见原记录；未将助手实现或实验执行归为用户亲手完成

## AI参与

原记录中的实现、运行、分析或 AI 复核；本次另由 AI 只读归档

## 复核类型

用户提交成员B的4份盲审：A1accept/1correct、D2accept；未另核实过程；不替改答案

## 源码与测试

现有安全分支 src/、tests/、tools/；历史特定源码/测试若未在白名单中则 HOLD，不能声称新检出可重现原 Run

## 报告和数据

公开指标见 metrics.json；原表/Trace/数据/盲审原件保留在本地，按证据 SHA 定位

## 费用口径

provider token/峰时价格估算/未知预约/实际扣款分开；实际账单未核对；各轮额度和重复报告不累加

## 证据入口

- [S125](../evidence/S125.md)：experiments/resolution-contract-20261028/README.md；SHA256 1dcb8a135a8e6af3417d0fd3874a7f7189c61d54e2fa04ec2aa5722aaf908090
- [S126](../evidence/S126.md)：experiments/resolution-contract-20261028/RESULTS.md；SHA256 7b1399873de8a610a12787e0cba984a8ab993ea0fbd7e3bb93b8ea8a1d0e8cfa
- [S127](../evidence/S127.md)：experiments/resolution-contract-20261028/STATUS.md；SHA256 6106ace26c94505c016fb7c4d9903cdb27754784fbf5b445711940b0f552b786
- [S128](../evidence/S128.md)：experiments/two-conversation-mini-20261028/CURRENT.md；SHA256 ee6b87dbfbcf7dc0884e6e69b589f993b1e0b077928b606a5a81154775a51918
- [S129](../evidence/S129.md)：experiments/two-conversation-mini-20261028/FAILURE.md；SHA256 e7fae767ad83b0a97f4f878cb8ba38321293bc436ebbaa4a67360ed05911b5ce
- [S130](../evidence/S130.md)：experiments/two-conversation-mini-20261028/README.md；SHA256 0ccca50a19b295d660cca851a367cb5c11e003736aa04611bf953279fd6758d4
- [S131](../evidence/S131.md)：experiments/two-conversation-mini-20261028/review/README.md；SHA256 85c9554fa456c6ee9db19a171c86d3f4dfb662df9ae7c25d7661142829ec596e

完整配置身份原文摘记见 [机器索引](../experiments.json)。来源版本不是执行代码身份。

[返回研究问题](../questions.md)
