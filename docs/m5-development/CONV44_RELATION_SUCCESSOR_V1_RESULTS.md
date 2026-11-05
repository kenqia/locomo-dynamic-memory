# conv-44 单任务恢复与第六份导出

2026-11-05（Asia/Shanghai）。用户批准的单任务logical3恢复在首请求成功。全部384个关系任务成功，保存7,134条合法关系；根代理和非作者独立终态审计通过，392条Memory的CurrentState投影精确重算一致。随后在新本地副本complete/pin，严格导出第六份 `memory-export-v2` JSON，原付费源仍为related。

目标Build为 `d9fb61417bb740e4b8eb34acb8652a46`。仅ordinal163的20次比较被恢复；383个旧成功任务、7,114条旧关系、394条旧logical1/2、429条旧Provider及430条旧Build调用前缀逐行保留。旧Memory、Source、片段、索引、配置、继承、其他Build和三代关系账本均未改写。新增逐候选标签前提只解释现有校验器，不强改响应或放宽schema。严格关系与来源检查不等同语义准确率。

本阶段硬限3请求/USD0.2619648，实际1请求，预约USD0.0537564；已报告输入14,745、输出2,368 tokens，按峰价折算上界USD0.0072651，Unknown0。新请求为deepseek-flash、thinking disabled，无reasoning_effort。官方当时映射Flash-1017；返回alias不证明不可变权重pin。实际账单未访问。九个已批准阶段累计1,863请求、预约USD92.1592080、已知usage峰价上界USD10.3702023；历史7 Unknown保留USD0.3500316预约，旧余额不转移。

实际导出为 `var/m5-development/conv44-sixth-export-successor-v1/exports/conv-44.json`，SHA-256 `1006ce3d855ffb496cb8a2c029276511707427bb7129474013f4b1768639611f`。sidecar绑定抽取继承和三个关系阶段的plan、终态、独立ledger及wire producer；末尾重新验证源终态与递归父身份。导出0模型请求，无QA或新embedding。

证据包含[根终态](../../experiments/m5-development/conv44-relation-successor-terminal-v1.json)、[独立终态](../../experiments/m5-development/conv44-relation-successor-independent-terminal-v1.json)、[归档清单](../../experiments/m5-development/conv44-relation-successor-terminal-archive-v1.json)、[第六份导出](../../experiments/m5-development/conv44-sixth-export-successor-v1.json)、[六份身份](../../experiments/m5-development/six-build-exports-v1.json)和[累计费用](../../experiments/m5-development/cost-ledger-including-conv44-relation-successor-terminal-v1.json)。私有归档使用只读SQLite backup并核逻辑身份，排除执行stdout/stderr。

实际导出的非作者复核独立保存，不以代码测试替代。六份核验后才锁最终配置并投影全部留出问题；全部生成冻结后才读Gold。该恢复授权不包含Level E或QA。无远端写入，未识别关联Notion，未标记总任务完成。
