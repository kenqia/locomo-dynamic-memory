# 多项目覆盖、短答案与解析备用策略

2026-10-21，基线提交 `fb8b497`。修复上一轮真实复验发现的三个问题，不重建现有 Build，
不引入新的模型、评估器、依赖或工作流。

## 行为变化

多项目查询在构造安全证据组前对原子 Memory 排序。对 activities、hobbies、events 等
宽泛名词使用少量通用动词与维度词扩展，避免把问题的泛称当成唯一匹配词。
同一人物且相关的候选中，结合不同状态维度、state_value 的词干 Jaccard 相似度，
优先交付不同项目。已有候选顺序用于相同得分的决胜，不调用模型重排。
已参与的 events 优先事实与直接参与陈述，计划、意愿仍交给 Resolution 核对。
事实排序不决定有效性，不合并或删除 Memory。

CONFLICT／SUPERSEDE 必要双方仍由现有不可分证据组保护，遗漏端点继续显式交付不确定性。
首次支持的联合打包优先级不变。没有恢复完整组排序，也没有强制所有枚举题补查。

Answer 指令要求列出紧凑、去重的项目名称，问题未问时间时把日期和相对时间计算放入
explanation。新增合成示例只说明格式，不包含开发题答案。需要改变项目含义的否定和
不确定性仍保留。未对模型答案做字符截断或删除引用。

Dynamic 解析仍按原 Schema 校验；有限重试结束为 invalid_output 时，使用同一 Build 的
固定原文快照，转入既有有界 dynamic_raw_fallback。原失败响应不能作为有效证据使用。
备用解析及其原文增量仍执行引用、人物、冲突和预算检查，备用失败仍返回失败。
网络／服务错误、账户额度错误和 Answer 失败不触发这条备用路径。

Trace 保留 requested dynamic 和 strategy_recovery.executed_strategy，保存失败调用及总用量，
查询指纹包含备用版本与实际恢复信息。Streamlit 提示备用路径。评测按实际混合证据
记录来源覆盖，不将混合证据强行当作纯 Memory 动态真值。历史 Dynamic 成绩属于旧行为，
比较时必须同时检查是否执行备用策略，不能仅看 strategy 标签。

## 离线复查

沿用此前确认的公开查询 API、评测 API、预算打包入口和 Streamlit AppTest。
先复现重复项目挤掉不同项目，以及 Dynamic 校验失败直接报错，再实现修复。
另复现评测把备用原文来源误计为空的问题，修正为实际交付的来源。

已通过的针对性边界包括不同活动与事件覆盖、不可分冲突双方、部分支持保留、
Dynamic 备用成功、备用自身输出无效、服务不可用不扩大重试、失败调用用量、混合来源
评测和页面解释。完整回归与最终检查结果见下方更新。

对上一轮固定实验 SQLite 的只读重放显示，QA 15 首次送达 D8:6 的 painting 来源，
QA 32 首次送达 D1:3 的 support group，以及会议、学校活动、志愿活动、工作坊、
骄傲游行、倡议小组的证据。20/20 联合打包保留历史首次支持，均在 12,000 预算内。
这证明输入覆盖变化，不证明模型一定生成完整短答案。

最终检查结果：

- `LOCOMO_LIVE_MODEL=0 LOCOMO_LOCAL_EMBEDDING=0 .venv/bin/python -m pytest -q --tb=short`：404 passed、4 skipped，387.78秒，既有弃用警告1项。
- 查询、原文、预算、回答及页面的针对性联合复查：76 passed。
- `LOCOMO_LOCAL_EMBEDDING=1 HF_HUB_OFFLINE=1 .venv/bin/python -m pytest tests/test_local_embedding.py -q --tb=short`：2 passed，未下载模型。
- `.venv/bin/python -m compileall -q src tests experiments/issue-15-query-reliability`：通过。项目未提供单独类型检查入口。
- `bash tests/browser/run.sh /home/kenqia/my_folder/locomo-worktrees/browser-env/bin/python`：退出0，Chromium 156.0.8078.4，无页面或控制台错误。
- `git diff --check`：通过。

浏览器使用既有脚本，在临时独立环境安装锁定依赖及构建合成库；不修改根虚拟环境和真实
Build。浏览器结果见 [followup-browser-result.json](followup-browser-result.json)，
截图与完整产物位于 `/tmp/locomo-browser-smoke.7si2nX/artifacts`。
预算重放见 [followup-delivery.json](followup-delivery.json)，额外逐项检查6道固定题的关键
来源及20题联合保留/预算条件均通过，不产生模型调用。

## 下一轮真实复验方案

`followup.py` 复用既有 live.py、Campaign 与公开 evaluation API。
题单固定为 raw_fallback QA 15、32、18、53、60、136，以及 Dynamic QA 3，共7项。
保留原模型参数、预算、每项单轮；失败及重试共用32次新调用硬限。
历史账本1141次保留，新累计硬上限1173。不得用旧轮未用额度自动扩大新轮授权。

先 prepare 冻结实现摘要、题目、参数及来源快照，再获得这轮调用授权才可 execute。
原 Build 272条 Memory 与4902条关系不变。复验应核对原文和首次／最终来源，分别报告
成功项评分、运行失败及失败计0的补充分数。对照使用上一轮已保存结果。

已执行 prepare，冻结目录为
`/home/kenqia/my_folder/locomo-worktrees/real-baseline-issue15-query-followup-frozen`，
计划及校验和副本为 [followup-plan.json](followup-plan.json) 与
[followup-plan.sha256](followup-plan.sha256)。状态 `frozen_pending_authorization`，尚未真实调用。

获得这轮32次授权后执行以下固定命令；不能自动继承旧轮64次授权。

```sh
python3 scripts/with_deepseek_env.py -- .venv/bin/python \
  experiments/issue-15-query-reliability/followup.py execute \
  --directory /home/kenqia/my_folder/locomo-worktrees/real-baseline-issue15-query-followup-frozen \
  --authorized-call-limit 32
```

## 作者复核与回滚

遵从用户不使用多 Agent 工作流的要求，按 code-review 的 Standards 与 Spec 两轴自审，
不能当作独立审核。固定比较点为 fb8b497，规格为本轮用户三项缺口及原验收约束。
Standards：核查全量输入、来源、版本、调用账本与失败记录；修正备用证据在评测中漏计
和潜在重复计入失败调用的问题，没有新增依赖或放松 Schema，未发现剩余可操作违规。
Spec：本地实现覆盖三项缺口，安全与展示回归通过；真实生成完整性、长度及备用策略的
实际表现仍待获授权的固定题复验，不宣称模型语义验收完成。
本轮可通过回滚本地提交移除；不改持久化 Memory、关系或全局 CurrentState。
尚未推送远端、创建 PR 或变更任务完成状态。
