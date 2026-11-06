# ARCH-03 独立诊断开关、回滚与对照

日期：2026-11-03。父任务#24，子任务#32。状态：独立diagnostic_only入口与Linux定向验证完成；Windows及真实成员复核待完成。

## 安装和运行

先保留已通过测试的ARCH01、ARCH02。将本增量包的tools、tests、docs合并到项目根目录，与pyproject.toml同级。本包只新增文件，不覆盖原Schema、冻结案例或你补充的Windows记录。

Windows CMD和PowerShell均可执行：

```text
uv run --locked python -m pytest tests/test_sidecar_schema.py tests/test_sidecar_core.py tests/test_sidecar_io.py tests/test_sidecar_research.py tests/test_sidecar_compare.py -q --tb=short
```

Linux本轮实际结果144 passed、1 warning；你的Windows结果另记，不自动宣称相同。

生成可读对照报告及完整JSON：

```text
uv run --locked python -m tools.research_v2.sidecar_compare --output var/sidecar-arch03/compare-v1 --repeats 20
```

输出目录必须是新目录，重复运行换compare-v2，禁止覆盖既有结果。打开：

```text
var/sidecar-arch03/compare-v1/comparison.md
var/sidecar-arch03/compare-v1/comparison.json
```

预期摘要：cases=16、compared=15、contract_rejected=1、response_unchanged_all=true、references_valid_all=true、input_unchanged=true、provider_calls=0。第15例因重复来源身份被拒绝，属于契约案例，不删除。若某项实际不同，保留输出并调查，不把失败改成通过。

## 两种对照的含义

control（supplied_fields_only）只展示输入已有的报告时间、提取时间、性质及来源，不新增事件连接或问题答案。sidecar执行ARCH02规则，输出事件、时间与有限问题诊断。两者使用同一冻结输入和相同旧Build身份，不读取expected_behavior。完整输入、两种输出、source/memory ID及原始unknown保存在comparison.json。

这个control不是组长真实Full Text/Vector/Dynamic的生产QA基线；该对照也不是付费模型配对实验或正确率提升证据。本轮未计算准确率，不把“无诊断”和“有诊断”的差别写成QA收益。

## 独立研究开关

sidecar_research.research_view接收一个已经取得的原响应，以及同版本SidecarInput：

```python
from tools.research_v2.sidecar_research import research_view

# original_response：已有结果，不在这里调用Query/模型。
# snapshot：已固定且经过校验的输入，不含预期标签。
view = research_view(original_response, snapshot)                 # 默认关闭
view = research_view(original_response, snapshot, enabled=True)   # 显式诊断
view = research_view(original_response, snapshot, enabled=False)  # 关闭回退
assert view.response is original_response
```

返回ResearchView.response仍是原对象；diagnostic在外部独立字段中，不插入或替换原HTTP响应。enabled=False在校验快照、执行规则之前返回；开启失败时保留原对象，状态diagnostic_failed，错误码不包含私密详情。若原响应带build_id/dataset_id/sample_id/build_fingerprint，则必须与快照匹配才附诊断。

这是独立研究入口，生产代码没有导入它，未新增生产API、配置开关或数据库迁移。不开启等价性只证明本入口原响应不变，不伪称已接入并验证所有生产Query路径。若未来需要A线展示，读取独立diagnostic字段并标候选；不得拿query.answer覆盖原答案。

## 回滚证明与额外开销

每个合法冻结案例运行off→on→off，核对原响应对象身份与规范化JSON摘要、关闭后无诊断。案例对照中的原响应是明确标记SYNTHETIC_INPUT_ECHO_NOT_QA的输入回显，不冒充模型回答。另有真实项目FastAPI合成Trace测试，验证原答案、引用、预算、Trace、全局状态、关系、导出及SQLite字节不因注释改变；生成/Embedding均受控，wrapper前后无新增外部调用。

性能测量每个有效案例先各预热一次，然后各重复指定次数，交替执行顺序。wall使用perf_counter_ns，CPU使用process_time_ns，测量函数体；校验、序列化、文件I/O及哈希在计时外。报告逐例中位数、最小/最大值及额外开销，保留负差值；不据此承诺时延门槛、稳定提速、网络开销或账单金额。

## 文件和交付边界

- tools/research_v2/sidecar_research.py：原响应外部注释、默认关闭、范围检查与失败回退。
- tools/research_v2/sidecar_compare.py：固定案例的两种诊断、开关回滚、CPU/wall及报告入口。
- tests/test_sidecar_research.py、tests/test_sidecar_compare.py：开关、范围、来源、不可变、预算、摘要、预期泄漏和实际API合成Trace检查。
- docs/sidecar-v0/ARCH03-example/：本机本轮实际生成的合成JSON和Markdown报告，供阅读，不代替Windows实测。

回滚代码：先停止调用research_view或传enabled=False；如需移除本次功能，只移除本包新增的两个模块、两个测试及ARCH03文档/示例。保留ARCH01/02，无需数据库恢复。不开启时不读取快照或运行规则；如果调用者自己在调用前读取文件，那部分开销不属于开关保证。

限制：不支持通用语义，不改动旧Build，不证明真实QA提升，不替成员签署Reviewer记录。ARCH04仍需正式ADR、更多合法Build/fixture兼容、演示交接、非作者实测及PR。没有发布Issue评论、推送、PR或Notion更新。
