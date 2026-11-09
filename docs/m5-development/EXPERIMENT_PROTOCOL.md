# M5 统一实验协议与复现

开发集固定 conv-26/30/41/42，757 题；本地留出conv-43/44先只检查原conversation；后来经18USD/204次单独授权执行抽取，一段extracted、一段failed，未完成Build或评分，始终未读QA/evidence。教师隐藏集未知。

历史 Run a2abe1fb49be45ccba291728e1f6b3c9 的四策略 F1 为 Full Text 0.464869、Vector 0.519714、Hybrid 0.521886、Dynamic 0.515133。这些分数不属于 M5 新答案。原失败、Unknown 和账本不改写。

## 实验层级

Level A 运行既有全仓离线测试、新 Bonus 契约及合成边界测试。Browser 使用受控模型完成真实 HTTP/UI/SQLite，不作为真实模型质量证据。

Level B 分两次保留原件。replay-v1 为候选排序/可逆包探索，使用共享完整 Memory JSON 预算；其自适应优先作用于扩展后列表，与在线包装器位置不同，只作为早期探索。delivery-v1 直接复用 BonusRetrieval、BonusExpansion、生产 ExpansionService 和 QueryService.generate_answer，止于模型前。它比较同题冻结输入及相同证据预算下的 would-be Answer 包，不执行 Resolution，也不冒称 Dynamic 端到端。

H 使用冻结 Hybrid query；D/B1–B4 使用冻结 Dynamic query。缺失 query 的 arm 显式失败并保留分母，不用另一策略输入代替。B1 开启两跳图，B2 使用完整 messages 的可逆分组与解码提示，B3 使用问题/analysis 路由，B4 使用有效时间优先级。B5/B6 因单模块无独立正面证据不执行。

每题先完成全部 arm，之后才读取 evidence mapping 作评分。Recall@5/10/20 的 K 单位为 Memory 排名，映射为 Source Turn 集合覆盖。expanded/delivered 全集另报，不混称同一个 Recall@K。753题证据映射适用，4题不可评分；失败的可评分 arm 记零。来源代理不是独立原子事实召回或答案支持率。

配对题差、每对话和类别差及2,000次 bootstrap 保留。仅四个已曝光开发对话，所有筛选是探索性，题级区间不能证明跨对话泛化。

Level C 固定80普通+20诊断题身份存于 replay-v1/fixed-live-sample.json，按SHA顺序各对话20+5。未根据候选表现选题；这是新 M5 样本，不冒称既有 Phase7/8 注册方案。付费调用前仍须锁定实现、模型、Prompt、预算和原始输出独占目录。

Level D 仅在单模块有独立事实增益、无严重人物/事件/时间错误且预算获批后运行。Level E 在最终候选与成本政策锁定后一次性运行；当前两层均未启动。

## 复现命令

在独立 M5 工作树执行；输出 label 必须未存在。

    ./tools/integration/check.sh tests -q
    PYTHONPATH=tools/integration/offline_guard:src:. /home/kenqia/my_folder/locomo-dynamic-memory/.venv/bin/python -m tools.m5.offline --label new-candidate-replay
    PYTHONPATH=tools/integration/offline_guard:src:. /home/kenqia/my_folder/locomo-dynamic-memory/.venv/bin/python -m tools.m5.delivery_replay --label new-delivery-replay
    PYTHONPATH=tools/integration/offline_guard:src /home/kenqia/my_folder/locomo-dynamic-memory/.venv/bin/python tools/production/smoke.py --output /absolute/new/private/browser-output --browser-python /home/kenqia/my_folder/locomo-worktrees/browser-env/bin/python

delivery_replay 读取本轮 replay-v1 的已校验导出与历史只读SQLite，在新 var 子目录建立过滤 scratch SQLite。新增查询/expansion 不写历史库。聚合、SHA和运行身份在 experiments/m5-development，原文、完整导出、来源审阅在忽略的 var/m5-development。


## 实际审核、真实数据演示与预算准备

以下命令需要既有本地私有工件，缺失时明确失败；它们不从远端自动取私有数据。

    PYTHONPATH=tools/integration/offline_guard:src:. /home/kenqia/my_folder/locomo-dynamic-memory/.venv/bin/python -m tools.m5.score_review --review var/m5-development/review-independent-a.json --review var/m5-development/replay-v1/review-independent-b.json --label new-reviewed-score
    PYTHONPATH=tools/integration/offline_guard:src:. /home/kenqia/my_folder/locomo-dynamic-memory/.venv/bin/python -m tools.m5.demo_smoke --output /absolute/new/private/real-demo --browser-python /home/kenqia/my_folder/locomo-worktrees/browser-env/bin/python
    PYTHONPATH=tools/integration/offline_guard:src:. /home/kenqia/my_folder/locomo-dynamic-memory/.venv/bin/python -m tools.m5.holdout_extraction --output /absolute/new/private/extraction-proposal

最后一条只导入conversation并准备政策，不发模型请求。审批对象为COST_ANALYSIS的18USD/204次extract-only阶段。授权后执行必须使用已准备目录；脚本核对设置与实现SHA，失败或Unknown不自动重跑。若修改代码需重新准备并复核审批范围。不能用prepare成功宣称完整Build完成。

experiments中的gzip详细回放含模型派生适用条件，仅保留本地、由.gitignore排除；SHA和压缩往返校验清单可提交。完整原文、Memory导出、独立引用标签和真实截图留在var。提交的逐题紧凑指标不含原文/QA答案。synthetic Browser截图可用于报告，但须明确其性质。


## 关系阶段只读预估复现

在已执行的抽取快照上执行以下命令，输出路径必须未存在。不会建立索引、生成关系或读取留出QA；conv-44恢复后必须重新运行，旧估计不得用于新快照。

    PYTHONPATH=tools/integration/offline_guard:src:. /home/kenqia/my_folder/locomo-dynamic-memory/.venv/bin/python -m tools.m5.relation_preflight --stage var/m5-development/holdout-extraction-proposal-final-v2 --output /absolute/new/relation-preflight.json

该工具逐项复用生产Memory排序、select_history、allowed_labels、wire payload和完整messages；记录任务身份SHA、首次请求bytes及重试上界。它只计算上界，不授权费用。当前快照预估为2,325请求/USD203.02272；此值不是实际账单，且不包含索引、查询或评测。历史producer顺序parity在relation-preflight-producer-parity.json中，四开发Build共1,219任务完全一致。

合成课程边界的针对性验证：

    ./tools/integration/check.sh tests/test_m5_course_boundaries.py -q

6项测试使用MockTransport覆盖计划取消、共同参与者和三个查询配置；它们验证来源及类型不丢失，不评价真实模型选择准确率。实际课程案例候选身份在course-case-inventory.json，只含开发Memory/来源ID与存储预测关系，未独立确认其语义标签。


单片段恢复入口已准备，范围为原失败片段最多新增3请求/USD0.2619648，原全局上限同时保留。具体前提、prepare、授权记录和执行命令见EXTRACTION_RECOVERY.md；后来已获明确恢复授权并执行3次，仍失败；不能再次执行该恢复目录。恢复测试只用synthetic SQLite/MockTransport；真实阶段的prepare与缺少授权拒绝均没有发出Provider请求，旧抽取结果不变。


问题相关有效选择历史审核的完整协议与命令见DYNAMIC_TRUTH_PROTOCOL.md。query-applicability-v1的40份参考已真实完成，25可评分、15不确定；该历史有效选择诊断未生成新答案。另行Level C固定100题真实QA已完成，见[Level C真实结果](LEVEL_C_RESULTS.md)；其resolution low配置不是最终全disabled成绩，全disabled新v2仍待付费授权。额外无原文集合差分析可在新输出目录复现：

    PYTHONPATH=tools/integration/offline_guard:src:. /home/kenqia/my_folder/locomo-dynamic-memory/.venv/bin/python -m tools.m5.query_review_analysis --label query-applicability-v1 --output /absolute/new/query-analysis

原始准备/评分失败记录保留在var；首次结构校验发现两条确定缺证据参考没有代表性逐字引文，审核者补充最近相关原文并明确其只用于定位缺口；状态、选择未变。两位审核者在预测打开前统一unresolvable仅指参考无法评分，明确缺证据的insufficient仍进分母。正式评分以reference-freeze.json所冻结的最终文件为准，不据预测修改参考。


后恢复审计与只读关系预估已用新输出路径保存；旧75次审计不覆盖。当前accepted Memory数未变化，关系预估仍只是现有785条的部分快照，不是完整Build费用批准。完整回归最终以full-offline-final-v7的664/4为准。
