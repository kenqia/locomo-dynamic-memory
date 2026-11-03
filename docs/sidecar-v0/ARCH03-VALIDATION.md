# ARCH-03 实际验证记录

日期：2026-11-03。环境：Linux / Python 3.12.14，现有项目uv.lock；没有新增依赖。

实际命令：

```text
uv run --locked python -m pytest tests/test_sidecar_schema.py tests/test_sidecar_core.py tests/test_sidecar_io.py tests/test_sidecar_research.py tests/test_sidecar_compare.py -q --tb=short
```

最终结果：144 passed、1 warning、2.14s。原ARCH01/02的107项和新增37项均在该次执行；警告为项目已有Starlette/httpx弃用提示。Windows本机结果待卓新烨执行，尚无真实非作者Reviewer结论。

新增可观察验证：默认关闭即使收到非法快照也不调用规则；off/on/off保持原响应同一对象且字节不变；开启失败或版本不匹配不覆盖原答案；不新增来源ID；预期标签攻击不影响两种对照；重复次数有限，冻结摘要变化或输出目录已存在则拒绝。

另以真实FastAPI、SQLite、检索与受控生成/Embedding建立合成Build并生成当前问答Trace，对其进行off/on/off；原答案、引用、预算与完整Trace不变，存储的Current State、关系及导出一致，SQLite字节不变，注释前后生成适配器调用数量不变。此验证不是新的付费模型实验，也不证明真实模型语义质量。

对照实际运行：

```text
uv run --locked python -m tools.research_v2.sidecar_compare --output var/sidecar-arch03/compare-v1 --repeats 20
```

结果：16个输入，15个对照，1个重复来源契约拒绝；输入SHA不变，来源/Memory闭合，off/on/off原响应不变，provider_calls=0。完整输入及两种输出、额外CPU/wall与运行环境见ARCH03-example/comparison.json；可读摘要见同目录comparison.md。具体本机时间不是质量指标，也不是其他机器的验收阈值。

规则与fixture未改：ARCH01案例SHA仍为429b0e0d95f18fbfbaac7b5fcbc83ef8ef740ce521d8f04ab4b2d073daaa140a；ARCH02核心未改。新增代码不引入fcntl/resource等Unix专用模块。

阶段边界：仅独立diagnostic_only注释和两种诊断对照，生产Query未接入；没有新增真实课程样本、独立语义gold或QA质量收益。原Build已由前阶段合成Export路径验证，本轮仅补注释前后不变验证；更多合法历史Build兼容留给ARCH04。

远端操作与人工验收：未执行；Issue/Notion未更新，任务未正式关闭。不要把机器验证或AI检查填为真实成员Reviewer。
