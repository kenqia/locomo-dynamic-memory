# 留出本地索引与独立关系阶段

用户已明确授权本次USD104.78592/1,200次关系阶段，官方价格复核匹配，阶段已终结为related并通过终态审计。原抽取及恢复授权均已终结，本阶段使用新的独立批准和账本。留出QA、evidence和answers仍保持未读。下文“批准后”步骤保留操作协议，不授权重复执行。

## 已验证结果

holdout_index.py保留冻结Settings，通过显式Database对象把写入路由到独立SQLite副本，不修改原Build指纹。SQLite backup包含已提交WAL。db_path也是生产契约的一部分，不能改写后继续原Build。首次v1因此被正确拒绝；v3已修正工具，不放宽生产校验。

holdout-local-index-v3：真实缓存MiniLM固定revision c9745ed1d9f207416be6d2e6f8de32d1f16199bf，384维、CPU、拒绝超长输入，禁止网络下载。conv-43的402条Memory全部索引，逐条验证向量长度、有限性及单位范数，共617,472bytes，耗时9.53秒。原抽取库逻辑快照不变，Provider请求0。

conv-44失败Build拒绝索引；conv-43的pin仍返回no_complete_version，不能进行完整版本导出或查询。完整工件见experiments/m5-development/holdout-local-index-v3.json。

从M5工作树以PYTHONPATH=tools/integration/offline_guard:src:.、HF_HUB_OFFLINE=1、TRANSFORMERS_OFFLINE=1运行既有虚拟环境Python模块tools.m5.holdout_index。参数--stage指向holdout-extraction-proposal-final-v2，--output必须使用未存在目录。已有v1/v2/v3不覆盖。

## 已准备的关系提案

var/m5-development/conv43-relation-proposal-v1是一次性的独立副本。只有conv-43进入queued/relations；conv-44仍failed。工具复用RelationService.start生成400任务、7,620对比较，不调用模型。

冻结deepseek-flash、relation thinking high、最多3次物理尝试/任务，每请求最大160,000输入消息UTF-8 bytes及32,768输出tokens。按2026-11-04官方峰时cache-miss输入USD0.30/百万、输出USD1.20/百万：

    1200 × (160000 × 0.30 + 32768 × 1.20) / 1000000 = USD104.7859200

这是保守硬上界，不是预期账单。重试反馈也受输入上限限制；超限拒绝，不截断证据。未知网络请求保留预约，不自动退款。所有任务共享独立SQLite ledger。旧抽取ledger保持78请求及历史预约，不与本阶段混用。启动前重新核对官方价格；费率上涨则重新准备并取得匹配预算。

准备入口为tools.m5.holdout_relations，参数--index-stage指向holdout-local-index-v3，--output使用未存在目录。v1已准备，不覆盖。准备核对源库前后逻辑快照，记录计划、代码、设置、任务身份及副本/账本SHA；原索引和抽取库均不写入。

## 批准后执行

先取得用户对conv-43关系阶段、USD104.7859200/1,200次上界的明确批准，再保存聊天凭据并创建authorization.json。精确结构由holdout_relations.authorization(output)返回，绑定scope、Build ID、policy和plan SHA；函数不写文件，也不代表批准。

准备时v1没有authorization.json或execution-started.json，真实快照缺失授权拒绝验证通过。用户批准后已记录明确授权、核对完整性并创建一次性执行标记；已执行完成，不得再次execute。

获批并完成记录后，从M5工作树通过scripts/with_deepseek_env.py launcher运行既有虚拟环境Python模块tools.m5.holdout_relations，参数为--output var/m5-development/conv43-relation-proposal-v1 --execute-authorized，设置PYTHONPATH=src:.。禁止打印环境和凭据。

入口先核对匹配授权、代码和配置SHA、数据库/ledger逻辑快照及任务身份，取得副本后端独占锁，再写一次性启动标记。成功只到related；不发布、不读取留出题目、不执行QA或修改原抽取库。失败或崩溃保留账本、检查点及启动标记，不删除标记重跑。恢复须另行检查及批准。代码可通过revert撤回；已经发生的请求和账本不能通过代码回滚。

## 验证范围

实际运行命令：./tools/integration/check.sh tests/test_m5_holdout_relations.py tests/test_m5_budget.py tests/test_relation_diagnostics.py -q。

28 passed。另显式启用local_embedding运行tests/test_local_embedding.py，2 passed。测试使用synthetic输出验证控制与隔离；真实MiniLM检查验证本地适配器。均不证明真实关系语义质量或holdout泛化效果。既有全仓664/4回归覆盖此前生产代码；本次新增工具有上述定向验证，非作者RELATION_STAGE_REVIEW_V1已实际交付，范围内无P0/P1/P2，另跑28项通过；不替代费用授权或Release验收。

## 终态只读审计

tools.m5.relation_audit读取副本、原索引库、冻结计划和独立ledger，不读取标准答案、不发送请求。原索引库的逻辑快照必须匹配冻结plan；ledger policy经Decimal规范化后必须精确匹配批准计划。Memory、来源、抽取片段、索引等保护表逐行摘要保持一致，其他Build逐列不变。

审计器重新验证每条关系的端点、来源、引文和schema；成功related时重新计算投影并核对保存结果。它检查真实生产query_traces及其他查询/评测表为空，版本未发布；终态还核对物理请求与provider检查点计数。输出标签分布不是真实关系准确率，峰价usage上界不是账户账单。

实际命令：

    PYTHONPATH=tools/integration/offline_guard:src:. /home/kenqia/my_folder/locomo-dynamic-memory/.venv/bin/python -m tools.m5.relation_audit --stage var/m5-development/conv43-relation-proposal-v1 --output var/m5-development/NEW-AUDIT.json

输出路径必须未存在。运行中审计会包含在途请求的未知用量，不能将其当成终态网络失败。终态结果另存，禁止覆盖运行中及历史审计。

新增审计器经独立复核发现三项P2：查询表名漏检、policy只与自身比较、源与副本可能共同改变而漏检。三项均已修复并保留复现记录，独立14项测试通过，见RELATION_AUDIT_REVIEW_V1.md。它不覆盖掉电级持久性或真实语义真值。

## 本次关系终态

400/400任务成功，7,620条标签为undetermined 7,465、RETAIN 60、UPDATE 94、SUPERSEDE 1。标签分布不是真实语义准确率，来源/schema及投影检查不替代独立真值。实际408请求：401 response_received、7 transport_unknown；400次成功输出之外有5次timeout、2次HTTP错误及1次known_source_required拒绝，均保留原尝试历史。

[公共终态审计](../../experiments/m5-development/conv43-relations-terminal-v1.json)确认终态related、Memory/Source/抽取片段/索引保护、其他Build和投影契约均通过；未publish，查询/评测表为空，留出QA未读。根代理已实际运行只读审计并exit 0；非作者已独立重跑并核对完整审计对象一致，见[独立终态复核](RELATION_TERMINAL_REVIEW_V1.md)。原抽取库仍extracted，独立副本related均非complete；conv-44仍failed。

保守预约USD20.2028820、已知usage峰价上界USD3.9199638，7项未知用量保留预约USD0.3500316。剩余792请求/USD84.5830380不授权重跑、publish或其他阶段。三阶段终态共907请求、预约USD42.9743136、已知usage峰价上界USD5.3163252，见[终态费用汇总](../../experiments/m5-development/cost-ledger-terminal-v1.json)。旧cost-ledger.json保留为运行中历史快照；实际账单未访问。冻结relation high不是用户要求的最终全disabled实验，新v2仍待独立付费批准、0次调用。

归档说明见[关系终态私有归档v2](../../experiments/m5-development/conv43-relations-raw-archive-v2.json)：13个成员逐项回读验证，私有gzip为3,015,384 bytes，SHA-256为 `22d9cb655a975c9bc931dbd6ecbea8628ba44d5f26f1a76b6aaeda36e31d01d5`，源逻辑快照前后不变。v2以明确白名单排除运行时WAL/SHM；v1及其误含空WAL/SHM的限制说明保留，不覆盖原件。归档含私有原文和Memory，原件不提交；两次归档均无Provider调用。
