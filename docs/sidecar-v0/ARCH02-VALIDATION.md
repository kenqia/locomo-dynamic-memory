# ARCH-02 实际验证记录

日期：2026-11-03。环境：Linux，Python 3.12.14，项目原有uv.lock。

命令：

```text
uv run --locked python -m pytest tests/test_sidecar_schema.py tests/test_sidecar_core.py tests/test_sidecar_io.py -q --tb=short
```

最终结果：107 passed，1 warning，0.82s。包含原Schema的42项、核心规则55项和文件/导出10项。警告为既有Starlette/httpx弃用提示。Windows原生运行待成员执行；不把Linux测试作为Windows证明。

案例文件与ARCH-01字节一致，SHA：429b0e0d95f18fbfbaac7b5fcbc83ef8ef740ce521d8f04ab4b2d073daaa140a。

16个冻结输入中15个合法、1个重复来源按契约拒绝；语义预期仅由测试断言读取，不传入diagnose。另有测试把全部expected_behavior和案例名称替换为攻击内容，重新校验摘要后，实际诊断完全一致，证明规则不依赖这些预期字段。

两次独立CLI实际运行：

```text
uv run --locked python -m tools.research_v2.sidecar_cli cases --enabled --output var/sidecar-arch02/cases-on-v1.json
uv run --locked python -m tools.research_v2.sidecar_cli cases --output var/sidecar-arch02/cases-off-v1.json
```

均输出cases=16、rejected=1、input_unchanged=true、provider_calls=0；开关对应enabled=true/false。历史Memory和来源保留，未知与冲突不伪造答案。静态合成运行结果见ARCH02-SYNTHETIC-RESULT.json，不冒充真实模型成绩。

只读性验证：测试先以项目FastAPI公开接口、真实SQLite及受控外部适配器建立完整合成Build并导出，关闭服务后保存数据库与导出的字节；运行本模块Export适配和诊断后，原SQLite及导出字节均相同，Build fingerprint保持原值，Memory身份保持。混入其他Build身份的导出被拒绝。没有运行付费调用。

覆盖：当前/历史交叉顺序不变、后来报告的过去事实、计划不替代当前事实、否定与不足、矛盾不选更新值、相对日期与闰年、误导的派生时间、不同人物/事件、逆序输入、重复身份、空输入、事件对预算、文件禁止覆盖、运行中输入变更与manifest篡改。

边界：读取前后摘要检测不能保证最后检查之后仍无人并发修改；必须使用冻结副本。存储关系通过现有Export契约检查，但没有独立证明其语义。通用语言、真实课程质量、完整生产Query开关等价、Windows实测、跨两个真实历史Build兼容与真实成员Review仍待后续。

未发布Issue评论、PR、推送或Notion更新；未标记#31正式验收完成。真实成员Reviewer与项目负责人语义复核待记录。
