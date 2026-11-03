# DYN-03 conv30四题A/D

日期：2026-10-28

## 当时问题与假设

同Build动态处理能否改善证据选择与正确性？

## 方法与输入

4题×A/D，无自动重试，独立副本

## 配置

按来源版本与冻结配置；本归档未修改或执行历史配置

## 执行代码身份

以来源记录中的执行 commit / implementation SHA 为准；source_commit 是证据文件版本，不能替代执行身份

## Run ID

证据缺失或本项不适用；不补造。

## Build ID

5abd7718841d417ebd71a1db896be39f

## 统计分母

8

## 实际结果

6成功/2D解析失败；14请求392178token；3accept/3correct；correct=需改；2解释判断受制包缺源限制

## 失败与unknown

见 observed_result；未明确报告的失败、unknown 与用量为证据缺失，不推定为零

## 结论与采用状态

两对完整答案不足以证明总体增益；D两例16→2Memory不等于降总成本

## 局限

开发诊断/已知题结果不能推断隐藏集；结构、引用 ID 与 scorer 不等于语义正确；未复跑历史实验

## 人类参与

用户提出问题、范围取舍及授权见原记录；未将助手实现或实验执行归为用户亲手完成

## AI参与

原记录中的实现、运行、分析或 AI 复核；本次另由 AI 只读归档

## 复核类型

原记录称收到成员B的6答案独立盲审；本次未另核实身份/过程；解盲后制包审计为作者检查

## 源码与测试

现有安全分支 src/、tests/、tools/；历史特定源码/测试若未在白名单中则 HOLD，不能声称新检出可重现原 Run

## 报告和数据

公开指标见 metrics.json；原表/Trace/数据/盲审原件保留在本地，按证据 SHA 定位

## 费用口径

provider token/峰时价格估算/未知预约/实际扣款分开；实际账单未核对；各轮额度和重复报告不累加

## 证据入口

- [S132](../evidence/S132.md)：experiments/conv30-ad-mini-20261028/COURSE-REPORT.md；SHA256 617d47010ba61dabb99dab536f6276ba7495623ce0b66afd4783a2e5458fd78d
- [S133](../evidence/S133.md)：experiments/conv30-ad-mini-20261028/EXECUTION.md；SHA256 a5fd6d09d34c6894f2e3fc1f0421d42c2323a25b9dedd857c9c810014bfec560
- [S134](../evidence/S134.md)：experiments/conv30-ad-mini-20261028/README.md；SHA256 23aaf8935db2ad2936d0cd05e7b7f8f5c58a68ea7a2e280f073d727f07f79ead
- [S135](../evidence/S135.md)：experiments/conv30-ad-mini-20261028/REVIEWED-RESULTS.md；SHA256 f30c6e8a9f1268b7db7aa52864cb8713c234150262d36a99bbcd418e0fc84072
- [S136](../evidence/S136.md)：experiments/conv30-ad-mini-20261028/execution-v1/RESULTS.md；SHA256 359091d6affd1d2ac459b4626a43303991292234fae06419d5b32282570625f2
- [S137](../evidence/S137.md)：experiments/conv30-ad-mini-20261028/execution-v1/TRACE-ASSESSMENT.md；SHA256 9b7ac7d9f6b9847475157cbc229cc0e5749bf1beb894d653eaff2f85d1fb689c

完整配置身份原文摘记见 [机器索引](../experiments.json)。来源版本不是执行代码身份。

[返回研究问题](../questions.md)
