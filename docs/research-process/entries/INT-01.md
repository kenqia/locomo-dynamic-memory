# INT-01 安全集成RC1/RC2与后续修复

日期：2026-10-31—2026-11-01

## 当时问题与假设

哪些窄改动可进入生产候选？

## 方法与输入

先审查26项集成候选，RC1/RC2独立保留；后续INT-FOLLOWUP-20261101-v1为28题（12已曝光开发+12合成+4旧回归）×2重复×3 arms，每pipeline初答+一次通用复核。

## 配置

RC2完整解析输入预算24,000；后续三臂wide-original/wide-guided/selective-guided；单阶段最多1HTTP，单并发；计划、执行、后处理分别冻结。

## 执行代码身份

RC2基准5fc33a9611565711ba175a807f19881d0ae748fb；后续真实执行冻结aea7ed9；后处理修复178e121；并非同一个执行版本。

## Run ID

后续实验身份INT-FOLLOWUP-20261101-v1；RC1/RC2其他运行身份见原记录，未合并为一个Run。

## Build ID

证据缺失或本项不适用；不补造。

## 统计分母

后续168 pipelines/336逻辑输出槽；实际334HTTP=168初答+166复核。原版2次初答被严格拒绝，其复核未发送；4 null输出保留。RC1/RC2其他分母不相加。

## 实际结果

后续已曝光开发24输出，原版17/24→复核17/24，两guided各24/24→24/24；合成24输出原版20/24→20/24、wide-guided23/24→23/24、selective22/24→22/24；旧回归8输出依次6/8→7/8、6/8→8/8、7/8→7/8。选择性总token节省15.7594%，低于20%门槛。

## 失败与unknown

后续原版2初答严格拒绝，4 null槽保留；全部334请求settled，未知用量0。逐事实仍有过推断与必要细节遗漏；相同HTTP输入仍产生输出差异，不把差异归因于上下文选择。首次离线导入环境错误invalid-import-*不计成绩；178e121修复3项后处理P2，不改模型输入/结果。

## 结论与采用状态

RC1/RC2采用矩阵另存；后续F01四包可逆但估算32,859–59,291均超24K，0真实解析请求，本实现不采用；F02指导留研究候选，F03未验收，未加入默认路径。

## 局限

开发诊断/已知题结果不能推断隐藏集；结构、引用 ID 与 scorer 不等于语义正确；未复跑历史实验

## 人类参与

用户提出问题、范围取舍及授权见原记录；未将助手实现或实验执行归为用户亲手完成

## AI参与

原记录中的实现、运行、分析或 AI 复核；本次另由 AI 只读归档

## 复核类型

后续非作者AI预审及336输出盲审，31 fail/uncertain交叉复核；评审有既有曝光，不是人工真值。未发现新增独立人工验收。

## 源码与测试

现有安全分支 src/、tests/、tools/；历史特定源码/测试若未在白名单中则 HOLD，不能声称新检出可重现原 Run

## 报告和数据

公开指标见 metrics.json；原表/Trace/数据/盲审原件保留在本地，按证据 SHA 定位

## 费用口径

后续646,438 provider tokens，高峰cache-miss估算上界1.463288元；连上一轮估算2.094828元不是实际扣费。Codex评审用量不可得，不能宣称全项目成本。

## 证据入口

- [S146](../evidence/S146.md)：docs/integration/20261031/AUDIT.md；SHA256 178bb16ad9442757da525b1d5fbb21ff99da912ce30219234cc33997e3e72745
- [S147](../evidence/S147.md)：docs/integration/20261031/CODE_REVIEW.md；SHA256 cf1e1daf47bf39a35bf92a06ce5ba42eed6b0b8f93f0edd40d471481051858e7
- [S148](../evidence/S148.md)：docs/integration/20261031/INVENTORY.md；SHA256 19c56675b1155f3c93194a4d9149f64f6372087f8bd2e7274d79aea14c86152e
- [S149](../evidence/S149.md)：docs/integration/20261031/REPORT.md；SHA256 406c31d3db7648f29807eefb7368d2da741b9c71e20a7cf16abe5d9c59eab8ae
- [S150](../evidence/S150.md)：docs/integration/20261101/ACCEPTANCE_REPORT.md；SHA256 cbd745b49a086f15950d094424706890f543b8b389e703533356cb70da9fff5f
- [S151](../evidence/S151.md)：docs/integration/20261101/NEXT_EXPERIMENTS.md；SHA256 17d394f18b9290889aac0c5f18da8fe2a38ec8f072a5da89a9a168698d906af8
- [S152](../evidence/S152.md)：docs/integration/20261101-followup/REPORT.md；SHA256 5f8816dba9aba2fa637543f98601d1fc2dba27e42a0bfc4383c175b25bfa886d
- [S110](../evidence/S110.md)：experiments/integration-acceptance-20261101/README.md；SHA256 be85ea1155fbb069256efb43e4ee66cd299ce0d61b283904c851c93d4204b14f

完整配置身份原文摘记见 [机器索引](../experiments.json)。来源版本不是执行代码身份。

[返回研究问题](../questions.md)
