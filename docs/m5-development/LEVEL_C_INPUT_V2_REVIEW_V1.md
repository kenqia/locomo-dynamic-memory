# Level C 输入 v2 付费脚本边界独立复核 v1

结论：指定4文件未发现P0/P1/P2。独立新鲜定向验证为24 passed；v2计划将输入门槛设为640,000 messages UTF-8 bytes与192,000完整输入regex tokens，保留最多1,500次物理请求，统一峰价预约上界为USD346.9824。此复核不授权付费执行，也不替代预算确认或全项目验收。

2026-11-04。非作者审查者 `final_code_review_v6`，未参与实现。隔离工作树 `/home/kenqia/my_folder/locomo-worktrees/m5-final-input-v2-20261104`，HEAD `3335862dba1e9658f4d5c515b602c98049826d7c`。审阅指定实现与tests相对该HEAD的完整diff及相关授权/执行路径。报告沿用已读取的 `google-developer-docs` 技能。

| 文件 | SHA256 |
| --- | --- |
| `tools/m5/level_c.py` | `def5898c6afe2c6e9a5c5cf419bd9e2e12b11bf2878300929f305b04917e5334` |
| `tools/m5/level_c_audit.py` | `c8823a95c1c5a52212fb7a9b7138da50ac30efeef2218d28510feee03c2085ab` |
| `tests/test_m5_level_c.py` | `57a5997207a7b7094dac20e2bce714d1777c8bf5bc7c1bdc00c001c439e90303` |
| `tests/test_m5_level_c_audit.py` | `8957cd0ee403d57fe7a82e31b6249688a8b7692605621ae2a23303d1d047b8c7` |

## 授权、门槛与费用

`proposal_version=m5-level-c-input-v2`及独立scope进入plan和expected_authorization；授权同时绑定精确plan SHA与policy。verify_plan拒绝v1 proposal/scope、producer或设置/输入/样本身份变化和不匹配的policy。execute在创建execution marker或HTTP请求前检查授权、prepared数据库及ledger snapshot；旧ledger的policy也由既有BudgetTransport拒绝，不能沿用v1额度。

policy固定100题、两臂、32,768最大输出tokens、2次内部重试上限。当前两臂每题最多2＋3次逻辑generate，每次最多3次物理尝试，因此物理请求上限仍为100×5×3＝1,500；新增设置不引入raw策略或其他恢复路径。

独立Decimal核算：每请求上界为 `(640000×0.30 + 32768×1.20)/1000000 = USD0.2313216`，1,500次合计 **USD346.9824**。这是统一峰时cache-miss费率下的保守预约边界，未按192,000的regex估计降低预约，亦不是实际账单。边界测试覆盖640,000 bytes恰好通过、再多1 byte本地拒绝、输出超限、最后一个请求槽、请求数耗尽及请求槽未耗尽时金额先耗尽，拒绝均在发送前发生。

## 全部thinking disabled

prepare从原设置快照显式覆盖 `thinking_enabled=False`、192,000输入预算及extract、relate、query_analysis、resolve、answer五类effort为disabled，逐项记录settings_changes。policy拒绝任一effort为low/high，或全局thinking开关及输入预算不符。

测试通过实际DeepSeekModel＋BudgetTransport＋MockTransport检查五种operation的HTTP body：`thinking={"type":"disabled"}`，不发送reasoning_effort。全200项synthetic流水线同样核对真实请求body。终态audit要求所有保存的完成尝试都具有同一disabled结构且reasoning_effort为None；不能用enabled thinking配合字符串disabled混过核对。

请求模型仍为 `deepseek-flash` alias，plan记录当时公布映射 `DeepSeek-V4.1-Flash-1017`，同时明确 `immutable_provider_pin_verified=False` 与执行前重查alias。代码和离线测试不能证明未来服务端的不可变模型身份；执行前版本映射核验仍需按方案完成，不能将alias等同于不可变pin。

## 新鲜验证

实际独立执行：

```sh
./tools/integration/check.sh tests/test_m5_level_c.py tests/test_m5_level_c_audit.py -q -k 'v2 or synthetic_full_pipeline'
```

结果：`24 passed, 28 deselected, 1 warning in 90.10s`。warning为既有Starlette/TestClient的httpx弃用提示。此次选择新增v2边界测试和完整synthetic生成/冻结/评分流程，不重复剩余28项既有测试；其他代理提供的52项通过记录不计作本审查者实际复跑结果。tests全部使用synthetic来源与MockTransport，真实provider请求为0。

`git diff --name-only 3335862dba1e9658f4d5c515b602c98049826d7c -- src`无输出，未修改src生产实现。原tree及旧v1冻结源码不在本次修改范围。

## 已准备计划的受限核对

按作者ready通知，仅对新隔离tree的 `var/m5-development/level-c-input-v2-preparation-v1/plan.json` 做文件SHA核对，结果为 `3c9adc27b22d1b1da0175a508636ba51e8cdb2fd744a6faed566a963c2a79af6`，与作者提供身份相同。通过文件存在性核对，authorization.json、execution-started.json、generation-freeze.json均不存在。本审查者未读取该stage中的真实问题、来源、items或数据库，也没有为其写入授权或执行命令；未独立验证作者报告的真实prepare数据库内容或请求数。

本报告只复核本地付费脚本边界及synthetic行为。输入门槛可容纳不保证provider接受、校验重试成功、答案正确或质量提升；尚未发生的真实v2结果不得预先宣称。没有读取原tree真实items、Gold、holdout或凭据，未干预关系session85918，没有commit、远端写入或费用支出。
