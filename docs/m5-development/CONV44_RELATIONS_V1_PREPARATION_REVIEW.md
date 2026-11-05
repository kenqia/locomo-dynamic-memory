# conv-44 关系阶段 v1 实际准备独立复核

2026-11-04。**结论：实际本地索引与关系准备的8组独立检查全部通过，可以提交精确关系预算供用户审批；尚未获得或执行新付费授权。** 当前384个任务全部pending，物理请求0。此结论只覆盖准备工件，不代表关系已完成、Build已complete、第六份严格导出完成或Level E已启动。

复核者为非作者代理 `/root/final_actual_review`。工作树为 `/home/kenqia/my_folder/locomo-worktrees/m5-final-conv44-relations-20261104`，基点为 `aed4634deb6c873ef1620d0a80bd023e2541d1a2`，实现本地提交为 `82a9d25`。本次没有修改实现、重新运行index/prepare或创建授权文件。之前的[独立代码复核](CONV44_RELATIONS_V1_REVIEW.md)保留其历史快照及27项新鲜验证；本次没有重新运行该测试集。

安全数值与摘要保存在[独立准备检查JSON](../../experiments/m5-development/conv44-relations-independent-preparation-v1.json)，SHA-256为 `f2e283765f3f0d2faeac295dc56d201b86dc4919b06cffbf00889d9b5283d334`。

## 复核方法与范围

检查脚本通过项目现有Python环境从stdin执行。其运行环境为：

```sh
env -u DEEPSEEK_API_KEY -u OPENAI_API_KEY -u CODEX_ACCESS_TOKEN \
  HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
  PYTHONPATH=tools/integration/offline_guard:src:. \
  /home/kenqia/my_folder/locomo-dynamic-memory/.venv/bin/python -
```

所有SQLite检查连接均使用 `mode=ro`、`query_only=ON` 和读事务。脚本只输出安全计数、摘要及检查结果；8组断言全部通过后才以独占创建方式写入新JSON。缺少授权检查向真实 `execute` 入口注入MockTransport，provider调用次数必须为0。

检查没有读取凭据、raw provider日志或留出QA/evidence/answers。Memory结构仅在内存中参与索引文本契约、指纹和既定任务选择算法重算；未人工审阅或输出conversation正文。source、index与prepared数据库采用逐行保护比较，检查输出不包含记录正文。

本次独立检查的8组结果如下。根代理的21项检查与96项测试是另外的验证范围，不能计为本复核者执行。

| 检查组 | 独立检查内容与结果 |
| --- | --- |
| 1. 来源与终态身份 | source/index/relations分别符合8/11/17表精确白名单。source database、ledger、plan、settings、inheritance身份与源公共终态、索引摘要和关系计划一致；源授权及outcome摘要保持冻结身份。评测annotations和candidate_queries为空。 |
| 2. Producer、配置与血缘 | 独立枚举85个producer文件并核对两个计划及工具清单。工具SHA、index-summary SHA、settings和inheritance一致；新生成thinking disabled、local files only、32768输出tokens、2次重试、resolution输入预算192000。保留原settings.db_path和混合producer sidecar，实际存储显式路由到scratch。 |
| 3. 副本与保护摘要 | source→index、index→prepared基础表按 `rowid,*` 逐行相等，仅允许目标Build的status/phase/updated_at按阶段变化。索引表在第二次复制中完全保留，schema只增加既定阶段表。目标状态依次为extracted/extraction、indexed/indexed、queued/relations；当前契约、保护摘要、抽取metadata前缀及1次历史抽取调用均保留。其他Build与来源记录未变。 |
| 4. 向量与索引身份 | 唯一索引属于明确目标Build且为ready，保存392条384维float32向量，全部finite且归一化；最大norm绝对误差为 `1.1920928955078125e-07`。固定MiniLM revision、CPU、256 token上限、reject策略与配置一致。索引文本符合 `indexing_text(memory)`，重新计算的index fingerprint一致。 |
| 5. 准备状态与空生成表 | 仅一目标relation phase为queued，Prompt/schema为当前身份且无错误。384 tasks全部pending、attempts为0、metadata为空、error为空。关系、投影、逻辑attempt、provider记录和candidate_queries全部为0，外键检查无失败。 |
| 6. 任务选择重算 | 从index按production的 `MIN(source.position), m.rowid` 排序，使用既有 `select_history` 重算实体历史。逐项比较task_id、build_id、ordinal、new_memory_id、history_ids_json、truncated_count和selection_json，全部相等，任务摘要一致：384任务、7,134比较、28,644次省略历史比较。 |
| 7. 账本、预算与权限 | 新ledger为空，policy与实际384任务一致。最多1,152物理请求；每次160000输入字节、32768输出tokens、预约上界USD0.0873216，总预约硬上界USD100.5944832。批准模板为false，没有authorization、execution marker或outcome；index阶段无独立请求ledger。两个目录均0700，现存私有文件均0600。 |
| 8. 缺少授权门禁与不变性 | 向真实执行入口注入MockTransport后立即得到缺少授权文件拒绝，Mock调用0；没有创建execution marker。前后重算prepared DB/ledger、index及源身份均不变。复核者新增live请求0。 |

## 冻结身份

明确目标Build为 `d9fb61417bb740e4b8eb34acb8652a46`。源阶段为冻结的successor v3；索引为 `var/m5-development/conv44-index-v1`，准备阶段为 `var/m5-development/conv44-relations-v1`。

| 工件或逻辑身份 | SHA-256 |
| --- | --- |
| 实际关系plan | `0920823b2c04d5d632df481df24ca60348b182fc760da8bb3a28f02cc5eb94cf` |
| index-summary | `05ae7194dc4b5b9edf619ba8dc103cc9c1de1216f5e720fe150f75d7afd2ca13` |
| 源database逻辑快照 | `07ce1ee6d2a32c9b4c310e520c328134fea00cb7fc041776425770e618034e79` |
| 源ledger逻辑快照 | `ece4a12e1128428da2aaee99fadf13272457fa1fb4e7df8c01a527b37bcfddf0` |
| index database逻辑快照 | `0663f0548e5be21a4cef1d468e47d26d00210fd430293c99eec1bb12d99a1f3f` |
| prepared database逻辑快照 | `fa172ab2c9767c95779c4201e589ed1d9ebe32d315131963303c253ae225fb14` |
| prepared ledger逻辑快照 | `39ca67cadbeda22aa6ce7372d5802a6dd175787529eca1961a42c816c0afeda0` |
| 完整任务身份摘要 | `4deafd6608923998538cffc0c04183fc62ef301b92422d9c573a3696443d6d7a` |
| `tools/m5/conv44_relations.py` | `d82f8fc0bd0bc0562700a37d1c168a3276b8762936ead2d188c888f79b7bde7a` |
| `tests/test_m5_conv44_relations.py` | `eef56ec88f6972a8239c5dfd18a6dbce292a58b580257641dd152ba9d8b7f4d6` |

## 文档一致性

已复核下列6份公共文档的当前conv-44状态与边界，无阻断问题：已真实indexed/prepared、384任务、7,134比较、预算1,152请求/USD100.5944832、0请求且未获新授权。总任务、完整导出和Level E仍未完成；旧交接保留历史正文并在顶部链接当前交接。历史测试和其他阶段数字仅按既有证据引用，本次没有重新验证其全部结论。

| 文档 | 复核时SHA-256 |
| --- | --- |
| [阶段方案](CONV44_RELATIONS_V1.md) | `e74be014c839edd9e7ccb5a8882a8dfce1a01502bf69aa4cc623db4673106ae1` |
| [当前交接](../../M5_CONV44_RELATIONS_V1_HANDOFF.md) | `ac60cfd236ea1cf39baa84a32fd147a3164dffcee7ec60fba388088b02b87650` |
| [Level E准入](LEVEL_E_GATE.md) | `059b5d073085e1951eebfc98f74ef05e44300222957644d1137d0f90a5626e77` |
| [导出就绪状态](EXPORT_READINESS.md) | `1e397dc7e2ee525a627385081b2bbd8a51560d376534cec58604dbb149a88ea6` |
| [最终交付清单](FINAL_DELIVERY_CHECKLIST.md) | `7150b413f3bb66eac785b9a89f3636491510b5d4a5f977ee92192b5a366e3af7` |
| [历史交接及当前指针](HANDOFF.md) | `e280b33a5a45aa481b0c4a61c1a083d4db3f591089635f5b0163dc1a9f13cf16` |

## 未验证项与后续边界

本次没有重新加载encoder或重编码向量；向量数值检查、配置身份与fingerprint不能替代重新编码一致性验证。没有重新拼装包含conversation原文的wire messages，未独立重算38,182字节输入极值；该值在阶段方案中明确归于根代理实际重算及既有公共预检。

本次没有重新审查继承或新增Memory的事实语义，也没有评价关系语义、响应成功率或反馈重试可行性。源抽取身份与逐行保留检查仅证明准备阶段没有改变既有结果。关系尚未生成，不能据此宣称关系质量通过。

后续执行须由用户明确批准上述精确plan与新关系预算。抽取或历史关系额度不转移；本报告不创建或替代授权。执行完成后仍需独立终态审计，再在新副本完整化和严格导出第六份JSON；最终配置锁定及Level E另按各自准入条件处理。
