# conv-44 单任务关系successor v1 实际准备独立复核

2026-11-05。**结论：实际准备工件的5组独立检查全部通过；可提交精确plan及3次请求/USD0.2619648预算审批，尚未获得或执行新付费授权。** 仅task163的20次比较为pending，attempts仍为2，无logical3记录。Build为queued/relations，尚非complete，第六份严格JSON和Level E仍未完成。

复核者为非作者代理 `/root/final_actual_review`，工作树为 `/home/kenqia/my_folder/locomo-worktrees/m5-final-conv44-relations-20261104`。本复核没有修改实现、配置、既有报告或stage，没有创建授权/marker，也没有重新prepare、运行合成测试或发起live调用。代码两轴复核由其他代理进行，本报告仅覆盖实际准备工件。

[独立检查JSON](../../experiments/m5-development/conv44-relation-successor-independent-preparation-v1.json) SHA-256为 `32565c063892a0392fecd293cfc9a96e30b7f199cf8d473ea9ad985bbc39583b`。一次性审计脚本 `/tmp/conv44_relation_successor_independent_preparation_audit.py` SHA为 `48935b636d6f07ed96ca00b157512d31951e0ac1b82091ef88d98102212a9f1d`，运行命令：

```sh
env -u DEEPSEEK_API_KEY -u OPENAI_API_KEY -u CODEX_ACCESS_TOKEN \
  HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
  PYTHONPATH=tools/integration/offline_guard:src:. \
  /home/kenqia/my_folder/locomo-dynamic-memory/.venv/bin/python \
  /tmp/conv44_relation_successor_independent_preparation_audit.py
```

独立SQLite连接均为mode=ro、query_only及读事务。在计算快照或读取记录前，对新stage、原恢复stage及其原关系祖先先执行精确17表白名单、空candidate_queries、无非空评测annotations和外键检查。快照包括已提交WAL，逐行保护比较包含rowid。未读取凭据、raw provider日志、私有stdout/stderr、Gold或留出QA/evidence/answers；记录仅在内存校验，不输出正文或calls私有metadata。

| 独立检查组 | 结果 |
| --- | --- |
| 1. SQL gate与递归父身份 | 原恢复公共失败终态、DB/ledger、原关系祖先及其公共终态均保持冻结，production递归parent检查作为补充通过。新88文件manifest逐文件匹配，其中原87和原85子集完全保留。完整settings、inheritance和Build fingerprint契约保持不变；额外wire输入契约单独记录。 |
| 2. 全部旧行及精确排队 | schema完全一致。基础/索引/Memory/Source/片段/其他Build全部保留；383成功task、7114旧关系、394旧attempt（384 logical1+10 logical2）及429旧provider（417+12）逐行含rowid相同。430条Build calls历史完全保留。仅原task163变为pending/error=null，attempts仍2且旧metadata保留；无logical3。目标Build及phase仅改变允许的排队状态和时间字段。384任务选择摘要未变，投影仍0。 |
| 3. 内存输入包装 | 使用Capture模型调用实际EndpointModel，完整endpoint来源映射与Memory.source_ids精确一致，原Memory/history/context未变。20个逐ID标签前置矩阵与现有relation_label_error重算相同：15个仅undetermined、4个UPDATE/undetermined、1个RETAIN/UPDATE/CONFLICT/undetermined。安全反馈保持code/path，明确UPDATE证据及不得修复旧响应；observer最终记录successor输入契约与wrapper SHA。未拼wire、未调用provider。 |
| 4. 新ledger、门禁及不变性 | policy精确为3请求/USD0.2619648，每次160000输入字节和32768输出tokens，单次预约上限USD0.0873216；ledger请求0。模板approved=false，无authorization、execution-started、outcome。真实execute入口缺授权即拒绝，Mock dispatch为0；新DB/ledger/计划配置及原源、祖先账本和冻结文件前后身份不变。目录0700、私有文件0600。 |
| 5. 根准备交叉核对 | 根代理[准备JSON](../../experiments/m5-development/conv44-relation-successor-preparation-v1.json)的13项检查全true，与独立结果11个公共状态/身份/预算字段相同。根代理的3次内存synthetic dispatch、初次及length反馈最大48876字节归于其验证，不算本复核者执行，也不代表所有反馈路径。 |

明确Build为 `d9fb61417bb740e4b8eb34acb8652a46`，新stage为 `var/m5-development/conv44-relation-successor-v1`。

| 工件 | SHA-256 |
| --- | --- |
| 实际plan | `699934d373556a353f837322322931cd8aec3adc76b87feada2c97a5fb9bd8a4` |
| 准备database逻辑快照 | `6396308ad64757ea84decf437281cca41e5eff8b613814665c3a8949c62b29ca` |
| 准备ledger逻辑快照 | `9c25527a302bd5ae0a37bb3f4ba432acf909d04a85d6de76260c4edad9a8c88b` |
| 工具 | `6afe3fb5a1094b4cb521fa6f05bcc3fa9d75a6173ec4fee46a28a8f375687464` |
| tests | `21fe123ba9aedb8e4a6371b90574542a864c64515e559cde6acce399a44882e2` |
| 根准备JSON | `21292e1b72e27dcd0cb5c4c3c461d9c90c6c8bd99f8ba0cceab2c41cb215e1c6` |

本复核未重编码向量、重拼wire或评价事实/关系语义，不保证下一次响应成功。历史调用和余额不转移；本报告不替代新费用授权。后续执行必须匹配上述精确plan与独立预算，完成后须独立终态审计；只有related成功且审计通过后，才能在另一个新副本complete/pin/export。
