# Level E 实际questions-only准备独立复核

2026-11-05。**结论：6组独立实际准备检查全部通过；400题、两臂800项准备完整，新账本0请求，尚未获费用授权或执行。** 获准的question正文仅在内存比较，未输出；category、answer、evidence和Gold均未读取。6000物理请求/USD1387.9296为待审批硬上限，不是费用授权。

复核者为非作者代理 `/root/final_actual_review`，工作树为 `/home/kenqia/my_folder/locomo-worktrees/m5-final-conv44-relations-20261104`。实际准备stage为 `var/m5-development/level-e-preparation-v1`，实现commit锁为 `0dbd98e7b296ef29d9998fa55d88d512f8ec85f1`。本复核没有运行prepare、execute、score或live，没有实例化写服务、backup参考库、写库、修改锁/producer或运行模型测试。

[独立准备JSON](../../experiments/m5-development/level-e-preparation-independent-v1.json) SHA-256为 `4e8a9d1a031b3a0dc2a79efade8546d46094907890b32c40b30837593d7069b8`。脚本 `/tmp/level_e_independent_preparation_audit.py` SHA为 `6b5892f1d2b944baf09804c2794caa9d02f1a4ada1aa8adf35be50bcffe365b0`。实际运行使用项目venv、撤销DEEPSEEK_API_KEY/OPENAI_API_KEY/CODEX_ACCESS_TOKEN、启用HF/Transformers离线及offline_guard，执行该Python脚本。

| 独立检查组 | 结果 |
| --- | --- |
| 1. 实际plan、锁和SQL gate | plan、私有锁及公共锁身份一致。新两份执行库和两份Build来源先通过允许表集合、无非空annotations、无queries/evaluation记录、外键及SQLite完整性检查。参考库仅检查byte身份和之后获准的question投影，不做backup或全表逻辑快照。 |
| 2. verify_plan与独立范围 | 实际verify_plan通过。conv-43原ordinal 0–241共242题，conv-44原ordinal 0–157共158题，共400个唯一question_id。inputs每条仅question_id/sample_id/qa_index/question；Hybrid和Dynamic两臂800项，无Bonus。新生成全disabled，输入640000字节、resolution代理tokens192000、输出32768、重试2。独立Decimal核算6000请求/USD1387.9296000。 |
| 3. 独立question-only SQL | 精确dataset/artifact/sample及唯一QA数组形状匹配锁。在SQLite中只返回原ordinal与question两列，未返回QA对象、annotations_json、category、answer或evidence。全部400条投影与inputs逐项相等，无筛题、重排或正文输出。 |
| 4. 六exports及两执行库 | 六份锁定JSON均重新核SHA并通过strict memory-export-v2及roundtrip。两份执行库所有原行含rowid与各自来源相同，新增query/evaluation表仅为空；complete状态及明确pin保持。使用纯只读read_bundle重新导出，与锁定JSON逐字段相等；独立保护摘要等于plan，未通过写服务导出。 |
| 5. Producer与真实commit | 实现commit实际存在。82个producer的当前SHA、锁定SHA及该commit的Git blob完全相等；pyproject.toml、uv.lock也匹配其blob。检查后producer未变。 |
| 6. 空账本、无授权和末尾不变性 | 新ledger仅policy/physical_requests两表，精确policy且0请求，main/WAL身份符合plan。无authorization、执行marker、generation-freeze、execution-aborted、items或scores。两构建源、参考源main/WAL和执行库、plan/inputs/锁前后身份未变；私有目录0700、文件0600。 |

根代理[准备检查JSON](../../experiments/m5-development/level-e-preparation-root-v1.json) SHA为 `6fc08d17a720764851f7f20f10ab59386ea7a633d02c4cc0493ddf6d2f241fff`，其25项检查全true、findings0；8个公共身份/范围/预算字段与独立证据相同。其缺授权Mock检查属于根代理，本复核遵守不运行execute的范围。根代理随后新增的authorization-template已独立核对精确plan/policy且approved=false，它不是authorization。

首跑在根实际审计仍进行时停于六export/执行库保护组，未写公共工件；随后原样重跑完整通过，未修改审计代码、产品或stage，未复现具体阻塞断言。本报告保留这一观察，不将其推断为产品缺陷或编造原因。

| 冻结工件 | SHA-256 |
| --- | --- |
| 实际plan | `5d99378868a5aed92889ff3995ae7771270b91d8effb373fb6d7e85672484c92` |
| final-system-lock | `3b6e3fbcad1670226f1f9d8e1c9fa96436b104893a875527d078dc4948671ac6` |
| questions-only inputs | `ced0d3c79e0009de49394544a61d6d4478d9d0c7ce400a5e8aade3adabd06718` |

本复核不评价题目、答案、关系或Memory语义质量，不读取实际账单或原始provider日志。问题字段获准读取不能概括为“未读任何QA字段”；准确边界是questions-only，答案/证据/类别和Gold未读。后续须用户明确批准此精确plan及独立预算；历史额度不可转移。全部800项生成结果、成功/失败/Unknown状态与工件身份冻结并通过准入核查后，才可进入另行获准的Gold评分阶段。准备通过不代表Level E已执行、质量达标或Release完成。
