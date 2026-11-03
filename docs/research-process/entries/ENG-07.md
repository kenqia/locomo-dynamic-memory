# ENG-07 评测、完整全文与运行分母

日期：2026-10-19—2026-10-20

## 当时问题与假设

得分是否保留失败/unknown和Full Text身份？

## 方法与输入

官方类别scorer、持久Run、全文超限失败、显式恢复

## 配置

按来源版本与冻结配置；本归档未修改或执行历史配置

## 执行代码身份

以来源记录中的执行 commit / implementation SHA 为准；source_commit 是证据文件版本，不能替代执行身份

## Run ID

证据缺失或本项不适用；不补造。

## Build ID

证据缺失或本项不适用；不补造。

## 统计分母

757QA/3028只是当时计划；各工程测试不叠加

## 实际结果

分别见工程票；未执行模型的计划预览不是成绩；unknown不自动重发

## 失败与unknown

见 observed_result；未明确报告的失败、unknown 与用量为证据缺失，不推定为零

## 结论与采用状态

采用分母及恢复机制

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

- [S007](../evidence/S007.md)：experiments/issue-11-evaluation-validation.md；SHA256 87152915955c180eecbe26ee8223158b53366ed1c33ab43edc2b068ff8e332e5
- [S046](../evidence/S046.md)：experiments/issue-16-development-plan-validation.md；SHA256 8634cbf8c0238f0ae711fef40f899a39f0d93e5a5b649618fc55dc75ac620236
- [S047](../evidence/S047.md)：experiments/issue-17-recovery-validation.md；SHA256 9e33f0591373d89d843f19f7803d89d621887f8234d0f11cc91e81fc1054d95e
- [S048](../evidence/S048.md)：experiments/issue-18-full-text-validation.md；SHA256 140fc8de85e26e7063007b11a9f476ba80576a86535e2d5ee6c10b9e2456a828
- [S049](../evidence/S049.md)：experiments/issue-19-failure-report-validation.md；SHA256 3180c7e6c99c7b8b0a14ec06a4711f2c794d9be71e6f7355c212036cc05f1371
- [S050](../evidence/S050.md)：experiments/issue-20-runner-validation.md；SHA256 db0044aef7afba3ee204ad18ce1867b3ccad3cd16be17a0c6293c5b3fe73a488
- [S037](../evidence/S037.md)：experiments/issue-15-review-fixes.md；SHA256 82beb7a7d34a4490c43d9c57880ba0b53b1ff7486accf260ef7295154e098239

完整配置身份原文摘记见 [机器索引](../experiments.json)。来源版本不是执行代码身份。

[返回研究问题](../questions.md)
