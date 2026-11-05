# conv-44 关系恢复 v1 的实际准备

2026-11-05（Asia/Shanghai）。免费实际准备已成功，根代理13项、非作者独立6组检查通过；新阶段尚未获付费授权，物理请求0。目标仅为原阶段10个失败任务的161次比较，不重跑374个成功任务，不增加抽取、索引、QA或远端发布范围。代码本地提交为 `443d16b`，工具及最终39项测试身份见[代码验证](../../experiments/m5-development/conv44-relation-recovery-verification-v1.json)。

## 冻结计划

工作树为 `/home/kenqia/my_folder/locomo-worktrees/m5-final-conv44-relations-20261104`，新stage为 `var/m5-development/conv44-relation-recovery-v1`。目标Build仍为 `d9fb61417bb740e4b8eb34acb8652a46`；只在新副本重排原失败任务。原阶段已通过[根终态审计](../../experiments/m5-development/conv44-relations-terminal-v1.json)及[非作者终态审计](../../experiments/m5-development/conv44-relations-independent-terminal-v1.json)，原数据库、独立账本、诊断和终态链已归档。

新plan SHA-256为 `82251c43a541f86a089dd649337930c501dcb00717debeb6786651f04b93529b`，绑定完整失败任务、旧calls前缀、源终态与数据库/ledger逻辑身份、设置、继承血缘、producer、包装器SHA、新输入契约和初始副本摘要。原logical attempt 1与provider记录、已成功任务整行、6,973条旧关系、Memory/Source/片段/索引和其他Build均保持原样。新调用只能记入logical attempt 2及新账本。

独立policy为30次物理请求、USD2.6196480硬限；每任务最多3次。单请求上限160,000 UTF-8字节、32,768输出tokens，`deepseek-flash`，全部thinking disabled，不发送reasoning_effort。[当日价格复核](../../experiments/m5-development/conv44-relation-recovery-pricing-v1.json)以零缓存年龄请求重新读取官方页面，确认当前alias公告版本及峰价input USD0.30/M、output USD1.20/M。alias不能证明不可变服务端权重pin，执行前仍需核对价格；原阶段余量不转移。

## 根代理实际验证

[准备审计](../../experiments/m5-development/conv44-relation-recovery-preparation-v1.json)的13项检查核对源终态与旧历史、精确新policy、原记录保护、完整失败任务队列、producer与设置、初始DB/ledger快照以及未批准模板。现无 `authorization.json` 或一次启动marker；注入MockTransport调用缺少授权入口，确认零请求拒绝且两库与marker保持不变。

对每个失败任务按生产顺序重建完整context，在内存中使用实际DeepSeekModel与新包装器、MockTransport和合成占位凭据，检查初次及截断反馈请求。30次合成dispatch均未经过真实Provider或新账本；完整endpoint来源映射、disabled设置和输出上限符合要求，最大messages为40,058 UTF-8字节，低于160,000。该检查覆盖初次和length反馈路径，不冒称捕获真实wire或覆盖所有未来反馈；运行时硬限继续生效。

源阶段和新账本均未产生额外真实模型费用。根审计脚本副本保存在私有stage，SHA绑定于公共审计；不读取私有运行stdout/stderr、原始provider响应或留出QA/evidence/answers。

## 审批与后续

[独立准备审计](../../experiments/m5-development/conv44-relation-recovery-independent-preparation-v1.json)6组通过，确认全部旧记录、10个待恢复任务、新policy及缺少授权的零请求拒绝，可提交精确30次/USD2.6196480恢复授权申请。任务书第10节要求新增付费阶段单独批准；旧关系授权及额度余量不覆盖本阶段。缺少批准时只暂停付费入口。

成功后另做恢复终态审计，保留两次logical attempt与双ledger历史；在新本地副本完整化并严格导出第六份JSON，sidecar绑定抽取混合血缘及两阶段关系输入producer。若再次失败，不自动追加请求。六份JSON齐备后才锁最终配置，再另行准备并审批一次独立Level E；当前仅完成Level E入口代码，未读取真实问题、未建立最终锁、未执行评测。

当前主仓及冻结父树保持原样；没有push、PR、main合并或部署。未识别关联Notion，未同步或标记总任务完成。回滚时停止引用新scratch，保留全部历史和账本。
