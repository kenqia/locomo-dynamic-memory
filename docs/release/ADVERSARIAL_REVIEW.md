# 个人Release对抗性审查

审查日2026-11-05，代码/测试截点c7eae7a。证据根目录`experiments/personal-release/`；非作者双轴原记录为independent-spec-review.json与independent-standards-review.json。PASS表示所述可验证边界通过；PARTIAL保留未具备的团队/隐私/测量条件，不能解释为教师验收。

| # | 严格问题 | 结论 | 证据、复现与限制 |
|---|---|---|---|
| 1 | 按文档能否启动？ | PASS | normal-startup.json与普通Browser双health/完整流程通过；cold-start-sanitized-final.json记录公开包独立安装/启动/浏览器与TERM通过。README的uv sync、doctor、start可复制 |
| 2 | 无模型key能否演示？ | PASS | browser-offline/browser-result.json：provider0/external0、仅GET；`scripts/personal-release replay-offline-demo`，无SQLite/模型实例 |
| 3 | 六JSON是否六完整Build？ | PASS | six-exports-validation.json和根manifest逐份身份/SHA/源时间/index/projection，2031/37445；`validate-six-exports` |
| 4 | Graph关系是否有来源？ | PASS | 同Build MemoryRelation的source/support/reason与结构边分别标明，Graph截图及API测试；合法source ID不等于教师语义真值 |
| 5 | H/D是否区分实验身份？ | PASS | PERSONAL_EXPERIMENT_SUMMARY、freeze/producer与E0–E25索引；757/C100两配置/E400不合并成绩；Release无新分数 |
| 6 | 是否删失败题分母？ | PASS | E800项，17失败记0；每臂类1–4=301、类5=99；independent-spec-review独立聚合。旧成功子集仅诊断，不能替换主分母 |
| 7 | 类5是否冒称事实F1？ | PASS | 明确literal refusal .858586/.808081，单列；附录勘误优先于旧措辞，不称纯400事实F1 |
| 8 | 关系Accuracy是否隐去真值不足？ | PASS | 50/60为AI诊断，无SUPERSEDE/CONFLICT真值覆盖；四标签真实准确率NOT_MEASURED |
| 9 | Bonus是否只通过代码就宣称QA增益？ | PASS | COMPONENT_MATRIX明确A保留、B浏览可选、多跳/C/D默认关；代理来源/packing非新QA实证 |
| 10 | PDF能否由数据重建？ | PARTIAL | build.sh已重建37页/20图、布局文本一致；282数值核对0差异，原PDF保留；matplotlib未全锁，历史raw未全部重评分，独立勘误 |
| 11 | 干净环境测试能复现？ | PASS | 独立uv sync成功，全仓991/公开包937均通过（0失败/错误/跳过），见ACCEPTANCE；公开数据排除测试明示，真实Embedding借既有环境 |
| 12 | 公开文件是否泄漏原文/Gold/key？ | PARTIAL | 显式allowlist排除原数据、原Memory/Gold/var/敏感日志，已知长Source/官方问题/Python与credential形状扫描；不读取私有Gold、不保证未知形状或语义匿名化，Git旧历史不得直接视为公开包 |
| 13 | 个人与队友成果能否区分？ | PASS | CODE_LINEAGE、TEAM_INTEGRATION_HANDOFF，未合PR38/39，未伪造队友PPTX/MP4/总报告，主仓36项不搬运 |
| 14 | 有无未授权付费/历史覆盖？ | PASS | 新命令只有只读/Mock/离线；所有历史runner未execute，新provider请求0，旧结果/SHA保留，旧预算不是授权 |
| 15 | 能否安全回滚？ | PASS | DEFAULTS_AND_ROLLBACK，独立分支增量commit、配置快照/新DB、自有服务停止；历史目录删除0，不reset/stash/clean/prune |
| 16 | 是否具备团队最终单包基础？ | PARTIAL | 个人代码/附录/JSON受控候选/演示可供合流，团队Product/Architecture/Delivery仍须review/验证；许可与提交渠道确认后集成并获最终课程提交批准 |

结论：PERSONAL_READY（仅本地个人候选）。13项PASS、3项PARTIAL，无FAIL和未解决P0；PARTIAL限于历史研究可重算性、未知语义隐私风险和团队交付条件。最终tar的外部回执另绑定来源commit、包SHA和非作者核验，不扩大上述通过边界。教师动态真值、隐藏评分、实际账单和未做的Bonus模型收益均NOT_MEASURED，不以AI非作者审查代替。
