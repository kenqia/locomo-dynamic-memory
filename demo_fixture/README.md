# Product Console 固定快照 Replay

本目录包含团队编写的合成来源与受控适配器实际生成的应用记录，以及已审查的真实实验聚合副本。
合成 Build、Trace 和来源**不代表真实模型成绩**。真实聚合有独立 Run ID 与来源 commit，界面明确分开。
无密钥、原始模型 wire、活动数据库或课程/个人素材。

## 干净 clone 启动

```sh
uv sync --locked
uv run --locked python tools/team_v2/demo.py replay
```

打开 `http://127.0.0.1:18501`，确认 `OFFLINE SYNTHETIC DEMO · REPLAY` 和“无 API / 数据库”。
只需一个 Streamlit 进程；无需 `prepare`、API、SQLite、Embedding 下载或模型凭据。
已有项目环境的 Windows 可直接用 `.venv\Scripts\python.exe` 替换 `uv run --locked python`。
Ctrl+C 停止服务。其他演示占用端口时，追加 `--ui-port 18502`。

`product-v1/manifest.json` 固定两个 JSON 的 SHA-256；启动时检查一致性和来源/Memory/Build 作用域。
这验证包内一致性，不是第三方签名认证。文件损坏时恢复已审查版本，不自动补造数据。
`snapshot.json` 包含两个历史 Build、七个合成 SourceTurn、每个 Build 六条 Memory 和六个保存的 Trace。
`research-evidence.json` 是 `docs/team-v2/research-evidence.json` 的冻结副本，原 757 QA / 3028 组合分母不变。

## 3–5 分钟演示路径

| 时间 | 操作 | 讲解重点 |
| --- | --- | --- |
| 0:00–0:30 | Overview：查看 Build 指纹和真实报告卡片 | 当前应用是合成 Replay；真实报告属于另一个固定 Run，2969 成功、56 失败、3 unknown |
| 0:30–1:20 | Memory：展开数据选择，切换历史 Build 后返回；选一条 Memory，点“查看完整原文” | Build 不混用；报告时间、事件时间、有效区间分开；未知日期保持 unknown |
| 1:20–1:50 | 选择 Tokyo 计划和否定 car 记忆 | plan 不当成已发生事实，negative 不丢失；来源 ID 必须与完整原文一致 |
| 1:50–2:40 | Query/Evidence：依次载入 success、insufficient、citation_anomaly、budget_failure | 切换 initial → expanded → effective/delivered → answer/citations；打开答案引用原文；失败保留阶段和错误码，预算失败不当作成功或“无证据” |
| 2:40–3:40 | Experiments：依次选策略、对话、题型；查看配对子集与历史成本；切到补充/修复 Run | 单维聚合不伪造交叉明细；705 个双方成功配对与全量失败并列；估算非实扣；未提供补充结果就明确显示未提供 |
| 3:40–4:00 | Demo：核对案例和运行模式 | 展示可追溯应用链路；不宣称 Sidecar 接入或模型质量提升，说明缺测与人工复核待办 |

`historical` 保留显式请求日期 2023-05-01 的 Paris 答案；`conflict` 保留 1990/1992 双方证据。
`citation_anomaly` 是受控错误引用被真实答案校验拒绝的失败 Trace；诊断为
`answer_memory_citation_scope_required`，对外错误 `answer / invalid_output`。
`budget_failure` 是隔离查询预算为 1 时的真实 `conflict_evidence_budget_exceeded`；未修改生产默认预算。
exact wire、event_ref 未记录时界面显示“未记录”。

## 重建与检查

```sh
uv run --locked python tools/team_v2/freeze_demo.py --output var/new-freeze
uv run --locked python tools/team_v2/check.py -q --tb=short tests/test_console_replay.py tests/test_console_evidence_ui.py tests/test_console_experiments_ui.py
```

重建器只接受本 clone 下新建的 `var/` 目录，用新的合成 SQLite 和显式 MockTransport 完成应用链路；
已存在目录拒绝覆盖。只审查并复制 `bundle/` 中三个 JSON，不上传数据库或日志。
重新生成的 ID/时间和哈希会变化，须重新核对后再更新公共固定快照。

浏览器验证与录屏命令见 [后续验证记录](../docs/team-v2/product-followup-validation.md)。
当前维护的是可供成员复现的候选版本；非作者真人复核、集成和正式验收仍为 pending。
