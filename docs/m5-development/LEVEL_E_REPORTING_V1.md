# Level E 冻结后报告与独立来源审阅

`tools/m5/level_e_reporting.py` 为已冻结的 Level E 结果提供免费后处理。它复用现有 Level C 的 ledger、usage、延迟分布与来源审阅校验，不修改生成入口、82 个冻结 producer、执行 stage 或参考库，不发起模型调用。真实结果必须等根代理确认全部生成冻结后再处理。

先使用 `level_e.frozen_items` 验证全部计划输出、授权、marker、账本、Build 与实现身份。冻结门禁通过后，工具才汇总 ledger 并投影审阅所需的原始来源。门禁内部沿用已锁入口的 Build 与 ledger 完整性核验。后处理只使用冻结 item 中的已保存 trace，以及两份 conversation-only 执行库的明确 Source Turn 字段；不读取 Gold、`scores.json` 或参考数据库。

`audit` 输出分臂、分对话的成功/失败/Unknown、usage、重试、失败请求与失败项的成本，以及已保存的 item、stage 和 adapter 延迟 p50/p95。全局费用以独立 ledger 为准。只有全部已完成 adapter 记录按冻结 producer 的串行操作顺序与 ledger 数量、usage、响应状态完整对应时，才分摊物理预约；任何记录缺失、usage 不一致或 Unknown item 都保留全局预约，并把分臂预约和费用比标为 `not_measured`。缺失 usage 不补零；已报告 usage 的峰价上界不是实际账单。

生成入口没有保存过程 CPU/RSS/GPU 采样。这些指标默认 `not_measured`。可通过 `--process-resources` 提供根代理在凭据外层采集、绑定 plan 与启动 marker 的 `m5-level-e-process-resource-v1` 侧车。该数据只表示 whole launcher children 的累计 CPU 与进程生命周期峰值 RSS，不分摊到两臂，不表示瞬时采样。存储只报告冻结后文件大小；token 效率只报告已有 usage 对成功项的比值，并保留缺失范围，事实收益/token 仍未测量。

将以下示例中的绝对路径替换为已冻结 stage 和新的输出路径。输出必须位于 stage 外。

```sh
PYTHONPATH=src:. /home/kenqia/my_folder/locomo-dynamic-memory/.venv/bin/python \
  -m tools.m5.level_e_reporting audit \
  --stage /absolute/path/to/frozen-stage \
  --output /absolute/path/to/new-runtime-report.json
```

`prepare-review` 为全部计划项创建来源审阅包；真实范围为 800 项，不筛选失败或 Unknown。包只包含问题、最终回答、引用、执行 outcome 与两段完整原始对话，不包含 arm、问题 ordinal、Gold、F1、resolver 决策或模型 trace。稳定 unit ID 与臂身份的对应只保存在私有 mapping 中。输出目录为 0700，包、模板与 mapping 为 0600，不提交 Git。

```sh
PYTHONPATH=src:. /home/kenqia/my_folder/locomo-dynamic-memory/.venv/bin/python \
  -m tools.m5.level_e_reporting prepare-review \
  --stage /absolute/path/to/frozen-stage \
  --output /absolute/path/to/new-private-review-directory
```

独立审阅者填写模板时，逐项检查全部事实断言、引用与拒答，提供同一对话的逐字 Source 引文和判定用途。正确拒答还必须明确检查完整对话并记录证据缺口。失败和 Unknown 适用未生成有效答案的 `not_applicable` 契约，执行 outcome 仍分别保留。引用 ID 的存在不能代替语义支持。

使用 `validate-review` 核查部分审阅覆盖；只有全部单位有明确独立审阅后，`score-review` 才汇总来源支持、引用支持、正确/错误拒答、人物/事件/时间错误和列表遗漏。所有输出绑定 generation freeze、review manifest 与后处理源码 SHA。审阅不包含教师真值，也不能把类别 5 的字面拒答得分解释为事实正确性。

```sh
PYTHONPATH=src:. /home/kenqia/my_folder/locomo-dynamic-memory/.venv/bin/python \
  -m tools.m5.level_e_reporting score-review \
  --stage /absolute/path/to/frozen-stage \
  --review-dir /absolute/path/to/private-review-directory \
  --reviews /absolute/path/to/completed-private-reviews.json \
  --output /absolute/path/to/new-public-semantic-summary.json
```

验证命令为 `./tools/integration/check.sh tests/test_m5_level_e_reporting.py -q --maxfail=1`。测试仅使用合成 item、ledger、Source 和六份合成 Build，并覆盖完整冻结门禁、预约归属歧义、canonical JSON 排序后的失败 trace、Unknown、来源引文与拒答契约。本页不报告真实 Level E 后处理成绩。

回滚时停止引用新后处理工具，保留 generation freeze、账本、原始输出、审阅包与已有报告，不重跑或改写生成。
