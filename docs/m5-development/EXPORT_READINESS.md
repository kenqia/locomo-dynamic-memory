# 六段数据完整导出就绪状态

2026-11-04。**总体状态：blocked，六段完整导出尚未齐备。** 本页仅汇总现有公共证据，没有重新打开私有数据库、原文或导出，也没有运行新的严格导出校验。四开发及conv-43共五份严格完整导出已在独立scratch中完成；conv-44抽取已恢复成功，当前第六份仍待关系执行及完整化。详见[五份导出验收](FIVE_BUILD_EXPORT_V1.md)。

六段conversation已完成导入和身份核查。下表把完整Build、索引和导出分别列出；本地索引成功不代表Build已complete，抽取结果也不能代替`memory-export-v2`完整导出。

| 对话 | Build ID | Build与抽取状态 | 索引与关系状态 | 严格完整导出 | 公共证据 |
| --- | --- | --- | --- | --- | --- |
| conv-26 | `367c901b300440649bdc0bfba2af8010` | 既有冻结complete；259 Memory、190引用Source、4,740关系 | 既有索引ready，索引/投影身份已记录 | 已有严格`memory-export-v2`校验及export SHA | [开发Build身份](../../experiments/m5-development/replay-v1/build-identities.json)、[准备时契约核查](LEVEL_C_PREPARATION.md) |
| conv-30 | `b8f34a05c8ef4585a1fc3c917745aa53` | 既有冻结complete；244 Memory、154引用Source、4,460关系 | 既有索引ready，索引/投影身份已记录 | 已有严格`memory-export-v2`校验及export SHA | [开发Build身份](../../experiments/m5-development/replay-v1/build-identities.json)、[准备时契约核查](LEVEL_C_PREPARATION.md) |
| conv-41 | `8d459492549b4a3e88005211f036addf` | 既有冻结complete；321 Memory、243引用Source、5,767关系 | 既有索引ready，索引/投影身份已记录 | 已有严格`memory-export-v2`校验及export SHA | [开发Build身份](../../experiments/m5-development/replay-v1/build-identities.json)、[准备时契约核查](LEVEL_C_PREPARATION.md) |
| conv-42 | `c892596ac8884f43b4cf2098349a7fa5` | 既有冻结complete；413 Memory、297引用Source、7,724关系 | 既有索引ready，索引/投影身份已记录 | 已有严格`memory-export-v2`校验及export SHA | [开发Build身份](../../experiments/m5-development/replay-v1/build-identities.json)、[准备时契约核查](LEVEL_C_PREPARATION.md) |
| conv-43 | `b19ae777b6e642c9855ea278ebd4cd81` | 独立scratch complete；34/34片段、402 Memory、300引用Source；原关系库仍related | 索引已验证；400/400关系任务、7,620标签；副本完成化已通过独立审计 | 已严格导出与roundtrip，SHA及来源身份已记录；无query/QA | [五份导出](FIVE_BUILD_EXPORT_V1.md)、[独立检查](../../experiments/m5-development/five-build-export-v1-independent-check.json) |
| conv-44 | `d9fb61417bb740e4b8eb34acb8652a46` | 新successor extracted；34/34片段、392 Memory、281引用Source；旧failed Build保留 | 新Build本地索引ready，392×384维；384关系任务、独立空ledger已准备，待新增授权；不能复用旧身份 | blocked；尚未完整化和严格导出第六份JSON | [v3真实终态](CONV44_SUCCESSOR_V3_RESULTS.md)、[关系准备](CONV44_RELATIONS_V1.md) |

四开发Build合计1,237 Memory、884引用Source、22,691关系。完整原文导出保存在Git忽略的私有目录，公共Build身份只提供摘要与计数；克隆仓库不会自动取得这些导出。SHA证明工件身份，不证明事实语义准确率或最终模型要求合规。

## 后续核查清单

以下项目尚未全部完成。按已有授权与[交接边界](HANDOFF.md)执行，不把本页当作新的调用、恢复或发布授权。

- [x] conv-43关系已终结，根代理[终态只读审计](../../experiments/m5-development/conv43-relations-terminal-v1.json)通过保护快照、来源/关系契约、索引/投影、未发布、查询/评测表为空及物理账本核对。非作者已独立重跑并核对完整审计对象一致，见[独立终态复核](RELATION_TERMINAL_REVIEW_V1.md)。
- [x] conv-44新继承方案已独立获批并抽取成功；旧失败/恢复记录保留，严格时间契约不变。
- [x] conv-43已在新本地scratch完成化并严格导出；原关系库和原账本保持不变。
- [ ] conv-44恢复后完成本地索引、单独获批的disabled关系阶段、完整化和严格导出；本清单不授权付费调用或远端发布。
- [ ] 对最终获授权的每份complete Build核对明确Build pin、严格`memory-export-v2`契约、完整导出SHA、索引/投影身份和来源归属；新增结果另存，不覆盖既有历史工件。
- [ ] 将最终六份工件身份、计数、严格校验结果和本地可取得性写入公共清单；私有原文和导出继续留在忽略目录。新生成操作遵守[全disabled模型要求](MODEL_REQUIREMENTS.md)，历史low/high结果如实保留。

六段导出齐备也不自动满足独立测试条件；另须通过[Level E准入核查](LEVEL_E_GATE.md)。
