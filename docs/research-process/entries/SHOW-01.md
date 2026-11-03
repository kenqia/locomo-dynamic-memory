# SHOW-01 五策略展示

日期：2026-10-21

## 当时问题与假设

原文兜底在分层题上是否总体更好？

## 方法与输入

conv26同Build；20题×5；40Recall；10真实动态；20来源审阅

## 配置

按来源版本与冻结配置；本归档未修改或执行历史配置

## 执行代码身份

以来源记录中的执行 commit / implementation SHA 为准；source_commit 是证据文件版本，不能替代执行身份

## Run ID

证据缺失或本项不适用；不补造。

## Build ID

证据缺失或本项不适用；不补造。

## 统计分母

100

## 实际结果

100/100执行成功；16可回答题F1：full.3490/vector.4911/hybrid.5124/dynamic.5100/raw.3997；Recall@5/10/20=.6417/.7292/.7792

## 失败与unknown

见 observed_result；未明确报告的失败、unknown 与用量为证据缺失，不推定为零

## 结论与采用状态

否定raw总体更优；Dynamic实际含2题备用路径；来源审阅为开发助手自查

## 局限

开发诊断/已知题结果不能推断隐藏集；结构、引用 ID 与 scorer 不等于语义正确；未复跑历史实验

## 人类参与

用户提出问题、范围取舍及授权见原记录；未将助手实现或实验执行归为用户亲手完成

## AI参与

原记录中的实现、运行、分析或 AI 复核；本次另由 AI 只读归档

## 复核类型

开发助手来源语义自查；非独立人工gold

## 源码与测试

现有安全分支 src/、tests/、tools/；历史特定源码/测试若未在白名单中则 HOLD，不能声称新检出可重现原 Run

## 报告和数据

公开指标见 metrics.json；原表/Trace/数据/盲审原件保留在本地，按证据 SHA 定位

## 费用口径

provider token/峰时价格估算/未知预约/实际扣款分开；实际账单未核对；各轮额度和重复报告不累加

## 证据入口

- [S001](../evidence/S001.md)：experiments/current-showcase/README.md；SHA256 97278c783509c71596b3c2763c3e187485bd2f4a180e214ba7f963a4461f54c6
- [S002](../evidence/S002.md)：experiments/current-showcase/results/analysis.md；SHA256 32fba0108eb1065d1a63784ed8079f63eaba34e45ccae08d20fb2758fc61d08a
- [S003](../evidence/S003.md)：experiments/current-showcase/results/answer-source-review.md；SHA256 e2750923e682710147fa124489b5889d624058edb24ea93502a7fddf4be012e0
- [S004](../evidence/S004.md)：experiments/current-showcase/results/dynamic-review.md；SHA256 ef115e1430357aa08c1344d889e05283aff1a0a7707a651101a842c416964d5e
- [S005](../evidence/S005.md)：experiments/current-showcase/results/report.md；SHA256 815099c0ee26a0ad2b6913e57698347984aae45195f249b22b9d6877ab8cf3d6

完整配置身份原文摘记见 [机器索引](../experiments.json)。来源版本不是执行代码身份。

[返回研究问题](../questions.md)
