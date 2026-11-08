# Product 真人独立操作记录模板

此文件是空模板，不是已执行或通过的验收记录。由非作者成员独立操作后填写实际结果，未执行项保持“未执行”。
依据 [负责人安排](https://github.com/kenqia/locomo-dynamic-memory/issues/23#issuecomment-6703489480)；交付入口和范围见 [收尾记录](product-closeout.md)。

## 实际环境

- 执行人 GitHub：待本人填写（负责人指派 xiaozhuozi39）。
- 实际操作日期/时间（北京时间）：待填写。
- 独立目录/clone：待填写；不必在公共记录披露个人绝对路径。
- 分支与 `git rev-parse HEAD`：待填写。
- OS、Python、浏览器版本：待填写。
- 安装/启动命令与结果：待填写。
- 是否使用模型凭据、活动数据库或付费调用：待实际核对；本次应为无凭据离线/合成操作。

```powershell
git branch --show-current
git rev-parse HEAD
uv sync --locked
uv run --locked python tools/team_v2/demo.py replay
```

已有锁定环境可直接运行 `.\.venv\Scripts\python.exe tools/team_v2/demo.py replay`。
打开 `http://127.0.0.1:18501`。全新安装需要下载依赖；Replay 运行阶段只读本地固定快照。

## 逐项实际操作

| 场景 | 操作与预期 | 实际结果 / 证据 |
| --- | --- | --- |
| 安装/启动 | 按 README 独立启动，核对实际 SHA 与合成标识 | 未执行 |
| 版本切换 | 两个 Build 切换，内容与来源不混用 | 未执行 |
| Memory/来源 | 选择记忆，打开原文，核对来源身份与内容 | 未执行 |
| 时间/计划/否定 | 报告/事件/有效时间分开；Tokyo 是计划；car 否定保留；未知不补造 | 未执行 |
| success | 载入后当前居住地为 Rome；引用可打开原文 | 未执行 |
| historical | 请求日期 2023-05-01，对应 Paris | 未执行 |
| conflict | 保留出生年 1990/1992 双方证据，明确冲突 | 未执行 |
| insufficient | 护照号码证据不足，不编造答案 | 未执行 |
| citation_anomaly | 显示 answer / invalid_output，失败保持失败 | 未执行 |
| budget_failure | 显示 conflict_evidence_budget_exceeded，不当成证据不足或成功 | 未执行 |
| Trace | 展开评审详情，逐一操作四阶段，检查原文、错误与预算 | 未执行 |
| 手输 ID 恢复 | 不存在 ID、../health 给出提示，再载入 success 可恢复 | 未执行 |
| 实验 | 能找到 3028 分母、2969 成功、56 失败、3 unknown、705 配对子集与估算成本 | 未执行 |
| 补充 Run | 明确未提供，不借用原 Run 成绩 | 未执行 |
| 1280px 可读性 | 核心内容无需横向滚动；与同视口旧截图比较 | 未执行 |
| 旧五阶段 | 按 README 的合成 prepare/api/ui 入口检查；只用新演示目录，不连接研究 DB/真实模型 | 未执行 |
| 连续演示 | 按 3–5 分钟路线连贯操作，记录卡点 | 未执行 |

截图/日志标注实际提交与对应场景，不上传密钥、原始 wire、活动数据库或未授权素材。旧五阶段入口属于合成 API/UI 模式，独立静态 Replay 不启动它的 API。

## 问题与结论

- 环境阻塞：待填写。
- 功能问题：待填写。
- UI 可读性问题：待填写。
- 未执行项及原因：待填写。
- 总体结论（通过 / 需修改 / 阻塞）：待本人填写，不默认通过。
- 修复后复验版本、场景和结果：如适用，由本人填写。

将实际记录留在 #23 / PR #39。组长的第一步方向确认、成员独立验收、CI、合并后集成验证分别记录；互相不替代。
Overview/Experiments 等第二步视觉返工当前仍待方向确认，不能仅凭两页改善就记录为全 Product 返工验收通过。
