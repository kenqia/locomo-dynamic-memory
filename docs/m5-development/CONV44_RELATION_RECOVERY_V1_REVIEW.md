# conv-44 失败关系恢复 v1 独立代码复核

2026-11-05。**结论：Standards 0项、Spec 0项未决；审查中发现的两项P2均已修复并独立验证。** 本报告只确认代码审查范围内通过，不代表真实恢复已准备、付费获批、恢复成功或第六份严格JSON已导出。真实原阶段仍为[已独立审计的失败终态](CONV44_RELATIONS_V1_TERMINAL_REVIEW.md)：374成功、10失败。

主审为非作者代理 `/root/final_actual_review`。Standards与Spec分别由独立子代理 `/root/final_actual_review/recovery_standards` 和 `/root/final_actual_review/recovery_spec` 复核，未共享两轴结论。受并发槽位限制，两轴分批执行。最终局部修补由主审续核，并运行与改动对应的新鲜合成验证。

固定基点为 `7cd6723fbfcfabbe3e90f0b74c3868347d87a25f`。初审时以下两文件为untracked新增，已通过 `git diff --no-index /dev/null <file>` 审阅全部新增全文，并核对 `git diff 7cd6723...HEAD -- <files>`。最终冻结身份如下：

| 文件 | SHA-256 |
| --- | --- |
| `tools/m5/conv44_relation_recovery.py` | `77cc554f9ebc94c70cb2f0f1e4674aeffdd3b659efaf997dcc5740371ac5120a` |
| `tests/test_m5_conv44_relation_recovery.py` | `18c803c1441a9be2bd3df58c76fb29eedd37e0e9d5d8d4f2f44f0825fa01412d` |

## 需求与范围

依据用户要求及[关系阶段边界](CONV44_RELATIONS_V1.md)，只允许在原失败终态冻结后，复制到全新scratch并重排原有全部F个failed任务；成功任务、原logical attempt 1、历史provider记录、关系和Memory保持不变。失败任务只新增logical attempt 2，最多3F次物理请求，使用独立ledger、精确计划、另行授权和单次marker；旧余额不转移。

恢复wrapper继续使用全disabled设置与原严格证据校验，增加完整endpoint source IDs及经过白名单过滤的反馈，不改core、endpoint或Build fingerprint。额外输入契约和wrapper SHA记录在新call metadata及provenance中。只有新恢复阶段达到related并冻结审计通过，才能再在另一新副本完整化、pin及严格导出第六份 `memory-export-v2`。导出sidecar须绑定导出SHA、抽取继承血缘以及两次关系输入producer与独立ledger；原失败库和恢复related库均保持原状态。

已静态对照根终态生成脚本及实际公共终态schema：父阶段 `version=m5-conv44-relations-terminal-v1`、`status=relations_failed_not_complete`，包含build_id、全true的checks、plan/settings/inheritance/authorization/outcome SHA及最终database/ledger逻辑快照。恢复成功终态使用同组身份字段与 `version=m5-conv44-relation-recovery-terminal-v1`、`status=related_not_complete`。合成fixtures使用这些字段通过各入口；本复核没有运行真实恢复prepare。

## Standards

**0项问题。**

Standards子代理只读核对AGENTS、CONTEXT、domain约定、ADR 0001/0002、`pyproject.toml` 及既有阶段工具，未发现可操作的硬标准违反或smell baseline问题。实现复用复制、关系服务、预算门禁和严格导出接口；恢复专用审计有独立职责，没有因此引入抽象或风格调整。

子代理初次终核基于 `e4fa3f...` / `2494515...` 身份。主审对后续局部修补继续核对相同规则：预约合法性计算、固定same_state反馈、对应测试和合法测试seed均保持原职责与最小范围。最终未修改85个冻结producer、生产schema、现有验证规则或Build fingerprint，未增加依赖或远端写入。

## Spec

**最终0项未决。** 审查中发现2项P2，修复见下一节。

失败任务范围、logical attempt 2、独立授权与账本、严格证据校验、历史记录保护和混合provenance未发现其余实质偏差；scope creep 0项。Spec子代理已确认预约P2关闭及末尾终态绑定修复。主审续核最终same_state指导：只保留白名单诊断并强调现有 `allowed_labels_by_old_memory`；RETAIN、SUPERSEDE、CONFLICT要求相同state_key，不改UPDATE规则，不重写端点或强迫标签，证据不足可保持undetermined。

## 发现与关闭证据

| 发现 | 复现、修复与独立验证 |
| --- | --- |
| P2：导出结束时未重新核对源outcome绑定 | 在纯合成stage的 `VersionsService.publish` 回调中改写源 `outcome.json`，原 `complete_export` 仍返回成功并创建summary。独立fault先为1 failed / 3.85s。作者补导出结束时完整 `terminal_check`，同一fault变为1 passed / 3.44s；当前会拒绝终态链失配，不创建成功summary。 |
| P2：正数低报预约能通过审计 | Spec子代理用临时ledger复现，主审再按实际32768输出上限独立确认：输出预约下限USD0.0393216时，USD0.0000001的Unknown预约仍可通过。作者改为先扣policy锁定的完整输出预约，再验证反推输入字节数是1..max_input_bytes的整数，补低报、分数字节及合法Unknown回归。主审独立fault与受影响流程新鲜通过。 |

预约修复验证的是金额能否对应合法整数字节数及完整输出预约。现有ledger不保存实际wire bytes，本复核没有捕获或重拼真实请求，因此不能据此宣称已将预约逐条与真实wire长度重算相等。运行时 `BudgetTransport` 按实际编码messages预约，Unknown保留原预约；终态快照、后续SHA及独立ledger继续保护身份。

最终还修正了一处测试基础数据：旧负例seed `.00001` 在8输出tokens、USD1.20/M输出与USD0.30/M输入policy下本身反推为分数字节，可能掩盖model/output/thinking等检查分支失效。现改为合法9字节预约 `.0000123`，对应7个负例重新通过；此项未列为新增实现finding。

## 新鲜验证与限制

所有主审合成验证在 `/home/kenqia/my_folder/locomo-worktrees/m5-final-conv44-relations-20261104` 使用offline guard并移除进程中的模型凭据变量。阶段性结果分别绑定当时实现，不冒称在最终身份上重跑全部测试：

| 实现阶段 | 主审独立结果 |
| --- | --- |
| 首项P2修复后，预约P2修复前 | 35个新增tests + `/tmp/test_conv44_recovery_review_fault.py`：36 passed / 55.39s |
| `a7b3fa...` / `b274a0...` 预约修复后 | accounting、低报/分数字节、合法Unknown、logical 2三种结果，以及两份独立fault：17 passed / 9.89s |
| 最终 `77cc554f...` / `18c803c1...` | 新same_state反馈1项 + 修正合法seed的accounting负例7项：8 passed / 0.87s |

最终最小验证的实际命令为：

```sh
env -u DEEPSEEK_API_KEY -u OPENAI_API_KEY -u CODEX_ACCESS_TOKEN \
  HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
  PYTHONPATH=tools/integration/offline_guard:src:.:tests \
  /home/kenqia/my_folder/locomo-dynamic-memory/.venv/bin/python -m pytest -q \
  tests/test_m5_conv44_relation_recovery.py::test_wrapper_preserves_dimension_failure_feedback_without_rewriting_cross_dimension_endpoints \
  tests/test_m5_conv44_relation_recovery.py::test_accounting_rejects_policy_model_output_thinking_and_reservation_corruption
```

各次仅有既有Starlette/httpx弃用提示。作者另报告预约修复后的完整38项通过；新增same_state指导后共39项，根代理在最终冻结身份另行新鲜运行完整39项，结果39 passed / 56.19s。本主审没有在最终身份重跑全部39项或全仓测试，不把根代理运行计为自己的验证。临时fault均只使用合成SQLite，不属于仓库生产工具。

本次代码审查未读取活跃真实数据库、raw provider响应、私有stdout、凭据或留出QA/evidence/answers；未运行真实恢复prepare/live、真实完整化或导出，未commit。另行完成的原真实阶段只读终态审计见[失败终态独立报告](CONV44_RELATIONS_V1_TERMINAL_REVIEW.md)，不与本合成代码验证混计。

后续实际准备须重新核对原终态、F个失败任务、输入上限、所有保护摘要和零请求门禁，并生成精确新计划供用户批准。代码审查通过不授权付费恢复，不保证新增反馈能够使生成成功。

两轴汇总：Standards 0项；Spec初始2项P2均关闭，最终0项未决。
