# Sidecar 研究复现与交接

先读REPORT.md，再看PROTOCOL.md、AMENDMENT-V2.md、freeze.json与freeze-v2.json。实际PR输入为3e0b217，merge-base4d1d072；修复e330834，首冻f03f413，安全修复12c20d0，二次冻结398122e。代码/锁没有新增依赖。本轮复用已有Python3.12项目环境，包版本在process/sidecar-20261107/environment.json，不冒充新冷安装。

## 无凭据工程复验

在独立clone或明确隔离的目录，使用既有锁定环境：

```sh
PYTHONPATH=src:. python -m pytest -q tests/test_sidecar*.py
python tools/team_v2/check.py -q --tb=short
```

公开离线入口排除受控历史数据模块及live_model/local_embedding；具体排除见tools/team_v2/check.py。不能将其计为无排除全套通过。默认关闭/包装器不导入生产查询，不需要模型Key，也不启动API或SQLite。

## 真实数据复验

需要负责人合法提供六导出manifest及conv-26.json、conv-30.json；不需要原始QA/Gold或活动数据库。实际原件和全量诊断/参考只在受控目录，公开Git没有复制真实原文。首先在已有Release环境使用现有ExportCatalog严格校验；本轮实际结果在process/sidecar-20261107/real-export-preflight.json。不要仅凭文件名或普通JSON解析跳过该校验。

新建独立输出目录后准备相同样本：

```sh
python research/sidecar-20261107/prepare.py --exports /absolute/controlled/exports --private /absolute/new/sidecar-repro
```

该命令拒绝覆盖输出目录；冻结manifest/数据SHA必须完全匹配。68条已独立标注的参考文件由负责人通过受控渠道提供，按公开reference_label_hashes校验，不重新请求模型标注。Source text与模型标签不上传Notion或Git。

使用V2的原冻结文件（脚本拒绝源码SHA变化、拒绝覆盖run-v2）：

```sh
PYTHONPATH=src:. python research/sidecar-20261107/run.py --private /absolute/new/sidecar-repro --run-id run-v2 --freeze freeze-v2.json
python research/sidecar-20261107/analyze.py --private /absolute/new/sidecar-repro --run-id run-v2
```

不要在已完成的原受控目录重跑。主研究只允许一次推断；重复复现必须用新目录、明确标为复现，不挑最好一次。外部预算0、独立超时和禁止网络/SQLite护栏保持。退出或失败要保留日志，不覆盖成功/失败记录。

## 产物与限制

- run-summary.json与analysis-summary.json：V1原结果；run-v2-summary.json与run-v2-analysis.json：V2安全回归。
- v1-v2-comparison.json：相同68预测、受控文件大小/SHA索引；不包含原文或答案。
- frozen-input-plan.json：两Build身份、抽样规则/ID和参考包SHA。
- grammar-failure-analysis.json：真实适配失败原因，502语法外/1无合格来源。
- process/sidecar-20261107/：测试XML/输出、源身份、旧反例、初次失败及各版本实际运行日志。
- 受控原件：两原导出、68标注输入与输出、两次逐项预测和完整诊断，按manifest逐文件验真。

本轮没有新QA分数、教师隐藏集、人工真值、实际账单或冷环境复现证明。一次AI参考、范围有限、数据已曝光；低错误确定化来自全unknown，并非高质量。推荐拒绝当前真实接入；研究闭环不等于#24/#30–#33验收完成。

真实非作者复核请求见REVIEW-REQUEST.md，拟请Thorns-06；负责人未确认/消息未发布前不宣称已指派或已验收。源作者xiaozhuozi39不自验Sidecar。远端发布与Notion同步的实际结果单独记入publication-receipt.json；文件不存在时仅为本地研究交付。

回滚：关闭研究开关；本轮未改生产默认或DB。代码可在新修复分支通过revert本轮研究提交恢复PR38基线，不重写远端历史，不删除历史实验或受控原件。
