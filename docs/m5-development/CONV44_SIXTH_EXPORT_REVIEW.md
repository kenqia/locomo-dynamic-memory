# conv-44 第六份严格导出工具独立代码复核

2026-11-04。**结论：Standards与Spec两轴各0项问题；独立新鲜合成验证12 passed。** 此结论覆盖新增离线导出工具与测试，不代表真实关系阶段已成功或第六份JSON已导出。工具只接受已冻结且审计通过的 `related_not_complete` 终态；`relations_failed_not_complete` 必须拒绝。

主审为非作者代理 `/root/final_actual_review`，两轴分别由独立子代理 `/root/final_actual_review/sixth_export_standards` 与 `/root/final_actual_review/sixth_export_spec` 并行完成。未读取运行中的stage、真实数据库、凭据、raw provider日志或留出QA/evidence/answers，未运行真实导出、调用provider或修改实现。

固定基点为 `a795be451b662d482b62fb89508d7f24db2359ae`。`git log a795be4..HEAD --oneline` 和两文件的 `git diff a795be4...HEAD` 为空；本轮明确审查基点后的两个untracked新增文件，以 `git diff --no-index /dev/null <file>` 核对新增全文。复核时身份如下：

| 新增文件 | SHA-256 |
| --- | --- |
| `tools/m5/complete_conv44_export.py` | `01dbcd6c5afbde0b13fe33e4b84279d4dcb485b709df922162a8d00445df733f` |
| `tests/test_m5_complete_conv44_export.py` | `75979eace55c0783eedfd0edbb0a8b0cde79247c80180307f69c47c28aadea91` |

需求依据为用户先完成conv-44第六份完整JSON的授权，以及[关系阶段方案](CONV44_RELATIONS_V1.md)和[当前交接](../../M5_CONV44_RELATIONS_V1_HANDOFF.md)的完成标准：关系成功后在新本地副本完整化并严格导出 `memory-export-v2`，用绑定导出SHA的sidecar保留混合producer与恢复继承血缘；保护原source/ledger、其他Build和前五份导出，不读取留出参考或追加生成。

## Standards

**0项问题。**

已按 `git diff --no-index /dev/null` 审阅两个新增文件全文，冻结SHA均匹配；固定基点至HEAD无提交或已跟踪差异。

- `tools/m5/complete_conv44_export.py`：复用现有校验、发布、pin、严格导出和独占写入接口；源库使用只读连接，服务写入明确路由到新副本；未新增依赖、凭据读取或远端操作。未发现违反所列AGENTS、领域文档及ADR的可操作问题。
- `tests/test_m5_complete_conv44_export.py`：复用合成fixtures与MockTransport，覆盖源身份变更、SQL注解隔离、越界修改及严格roundtrip；未访问真实阶段数据。

Smell baseline为判断性启发规则，0项需报告。未将格式偏好或阶段工具沿用的命名风格视为缺陷。Standards子代理只做静态只读审查，没有重跑测试或开展Spec轴复核。

## Spec

**0项实质问题。**

(a) 未发现缺失或部分实现的要求。工具先核验冻结且审计通过的related终态，在全新scratch完整化和pin目标Build，经现有服务验证来源、索引和投影，再严格导出 `memory-export-v2` 并核对roundtrip。混合producer sidecar绑定导出SHA，保留恢复继承血缘；源数据库、ledger、其他Build和其余表均做不变性检查。

(b) 未发现scope creep。未增加模型调用、QA、远端写入或前五份JSON的重导出；`VersionsService.publish` 仅作用于新本地副本。

(c) 未发现可操作的实质实现错误。

已确认固定基点及两个新增文件SHA与任务给定值一致。Spec子代理仅做静态只读审查，未读取真实数据库或敏感内容，未执行真实导出或重复主审合成测试。

## 独立新鲜验证

主审在 `/home/kenqia/my_folder/locomo-worktrees/m5-final-conv44-relations-20261104` 执行：

```sh
env -u DEEPSEEK_API_KEY -u OPENAI_API_KEY -u CODEX_ACCESS_TOKEN \
  HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
  PYTHONPATH=tools/integration/offline_guard:src:. \
  /home/kenqia/my_folder/locomo-dynamic-memory/.venv/bin/python \
  -m pytest -q tests/test_m5_complete_conv44_export.py
```

结果为 **12 passed、1条既有Starlette/httpx弃用提示，18.71秒**。范围仅新增合成导出tests；没有重新运行已经通过的旧关系代码测试或全仓测试。检查覆盖副本局部complete/pin、严格导出与sidecar、拒绝覆盖、来源DB/ledger/终态/config/授权/producer改变、SQL先拒绝注解、其他Build/表意外修改和额外导出字段拒绝。

## 实际运行边界

根代理在关系阶段执行期间报告已有任务失败，最终结果仍待终态独立审计。本代码复核不改变正在执行的预算或重试政策，也不允许从失败终态继续完整化。若最终为 `relations_failed`，应保存全部合法部分关系、失败逻辑attempt与闭合物理账本，第六份完整导出继续blocked；本工具必须在创建输出目录前拒绝该终态。

真实成功终态后的导出仍须核对实际新副本、严格JSON、血缘sidecar及原库/ledger不变性。代码复核与合成测试不能证明真实工件完整、关系语义准确率或Level E就绪。

两轴汇总：Standards 0项、Spec 0项；两轴均无最高优先级问题。
