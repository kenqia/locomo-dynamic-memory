# ARCH04 算法与接口说明

## 输入、输出与身份
输入为 SidecarInput 或经现有 MemoryExport 校验转换的 JSON。保留 dataset/sample/build/fingerprint/rule_version、Memory ID、Source ID 与来源锚点；缺失或悬空引用拒绝。输出为独立诊断记录，不是替换答案。四类契约、字段与约束见 ARCH01 schema；实现为 tools/research_v2/sidecar_schema.py。

## 规则路径
1. 输入校验：唯一 ID、来源闭合、有效时间区间、来源锚点；冻结案例期望标签不参与推理。
2. 默认关闭直接跳过。开启后在纯函数内处理来源支持的时间与事实状态。
3. 时间：区分报告时间与事件时间；明确日期/受支持相对日期解析，月份保留区间；不支持或含糊表达为 unknown，不使用系统今天补全。
4. 完成/出席：只接受支持的显式来源表达；计划、条件、引用他人或含糊多事实表达不得自动升级为已完成。
5. 事件配对：受配置上界限制；明确同事件引用才 same_event，明确第二次事件可 different_event，其余 unknown。事件与状态不能混并。
6. 状态查询：仅对受支持的英语居住地/出生年份表达诊断。使用问题 as_of 与来源支持的事件时间；保留全部原 Memory ID。最后已知状态连续性属于显式假设，不构成全局写回。
7. 输出：保留诊断、unknown、冲突与证据引用；所有原响应、输入与来源均不变。失败由研究包装器独立报告，不污染原响应。

## 关键边界
| 输入情况 | 必须保留的语义 |
| --- | --- |
| 5月1日住巴黎，5月2日搬罗马 | 当前与5月1日历史查询分别处理，巴黎记忆仍保留 |
| 计划搬家 | 不能证明已经搬家 |
| 两条不同出生年份的明确事实 | 保留冲突与两侧来源，不能任挑一个 |
| 没有出席记录 | unknown，不能生成未出席事实 |
| 最近参加活动，无可靠日期 | 不生成确定日期 |

## 研究适配
research_view(original_response, snapshot, enabled=False) 返回包含原 response 的研究视图。开启诊断应放在独立字段/面板；调用方继续使用原 response 展示正式回答。off_on_off 是诊断开关检查，不是生产 QA 质量基线。

## 成本与复现
时间处理按输入事实扫描，事件候选配对最坏二次增长且受 max_event_pairs 限制。输入字节与重复次数另有有界检查。比较脚本记录受控输入字段视图与规则诊断的 CPU/wall 原始样本，不比较模型成绩。具体参数属于实现/研究配置，不是质量门槛。

## 文件
sidecar_core.py：规则；sidecar_io.py：只读导出适配；sidecar_research.py：研究视图；sidecar_compare.py：合成成本；sidecar_compatibility.py：两个临时合成完整 Build 检查。兼容脚本依赖仓库已有 tests.helpers、test_queries、test_versions，因此需在完整开发仓库执行，不是独立生产依赖。
