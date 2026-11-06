# ARCH-02 确定性时间与事件诊断

日期：2026-11-03。父任务 #24，子任务 #31。状态：实现与Linux定向验证完成，Windows与真实非作者复核待完成。

本包是ARCH-01之后的增量：Schema与16个冻结案例不改动。它实现独立诊断，不接生产Query，不调用模型，不连接活动数据库，不把诊断当作最终答案或独立gold。

## 本地安装

前提：已安装Sidecar-ARCH01.zip并在本机通过42项Schema检查。将本包的tools、tests、docs目录合并进现有项目根目录。目录层级与pyproject.toml同级，不替换整个项目。本包不包含旧Schema、旧案例和旧验证记录，避免覆盖你补写的Windows结果。

Windows CMD或PowerShell，在项目根目录运行：

```text
uv run --locked python -m pytest tests/test_sidecar_schema.py tests/test_sidecar_core.py tests/test_sidecar_io.py -q --tb=short
```

本次Linux实际结果为107 passed、1 warning；Windows结果须以你执行输出为准。唯一警告为原有Starlette/httpx弃用提示，不为本模块新增依赖。

生成启用与关闭两份独立文件：

```text
uv run --locked python -m tools.research_v2.sidecar_cli cases --enabled --output var/sidecar-arch02/cases-on-v1.json
uv run --locked python -m tools.research_v2.sidecar_cli cases --output var/sidecar-arch02/cases-off-v1.json
```

输出目录自动创建。重复运行必须换新文件名，例如cases-on-v2.json；既有输出拒绝覆盖。冻结案例的换行或字节发生变化会导致SHA检查失败，不能为通过检查静默重算预期。原CLI输出16 cases、1 rejected：第15例为重复source身份，契约要求拒绝，不是隐藏失败。

开启结果包含各Claim的reported_at/event_time、completed/attended、EventLink正/负/unknown理由和有限问题诊断。关闭结果不计算诊断。原始来源、Memory与所有历史保留在record.snapshot，global_mutation为false。

## 文件与职责

- tools/research_v2/sidecar_core.py：纯诊断函数diagnose(SidecarInput, enabled=False)，不接收manifest或expected_behavior；显式开启后计算独立结果。
- tools/research_v2/sidecar_io.py：只读JSON快照或项目MemoryExport，校验引用和完整版本，输出新的JSON；输入前后SHA核对，拒绝覆盖输入或已有输出。
- tools/research_v2/sidecar_cli.py：独立离线入口；cases只把各case.input传给核心，不传case_id、类别或预期；snapshot读取一个明确输入文件。
- tests/test_sidecar_core.py：冻结案例语义与额外反例，防误连、误拆、日期错用、计划/否定、未知、输入顺序及副作用。
- tests/test_sidecar_io.py：输入哈希、输出隔离、篡改拒绝、预期泄漏反例、实际项目合成Export兼容。

## 支持的规则与限制

1. 复用已有temporal.py的英文月份定义，时间锚定SourceEvidence.reported_at日历日期；不读系统时钟。区分报告与事件日期。支持ISO日期、英文完整月份日期、年月范围、yesterday、本/上周、last weekday。周为周一至周日，last weekday严格早于报告日。
2. 英文日期省略年份时，当前有限语法使用来源报告年份并在basis说明；这是一项解释约定，不证明所有无年份原文都属于同一年。带last/next year或多日期等歧义保留unknown。recently/next month不强转精确日期，范围不伪造某一天。
3. 时间只从相符的窄谓词与同人物第一人称来源推导；引用合法不等于语义支持。引号、不同说话人、条件/模态、多事实句或不支持句式保留unknown。不进行通用指代消解或通用英文理解。
4. EventLink只在明确same-event引用、相同命名会议及可匹配日期下输出same_event；明确第二次同目的地旅行且日期分离输出different_event。仅同人/同主题/同名/不同日期不构成连接或拆分的充分理由；其他输出unknown。
5. 事实、计划、否定仍保留原性质；完成仅支持明确搬家完成断言，否定参加不转成参加，未报告完成保持unknown。不是覆盖所有动词的通用事件完成判定器。
6. 问题诊断仅支持明确单实体的有限住所与出生年句式。住所根据明确日期和from/to链，在已知截止范围内沿用最后有支持的住所；输出assumptions说明“未报告变化”的连续性假设，不把它当成全局RETAIN关系。历史问题可使用后来报告的过去事实；问题时间不是报告知晓时间。超截止日期不足，模糊或断链unknown。出生年互斥值保留冲突，不按新旧选一条。
7. 日期、实体与状态键的规范化来自所给快照，不跨对话合并。所有EventLink来源来自端点，推断不生成新Source/Memory ID。事件对比较有上限，超限显示links_truncated。

这些规则针对冻结人工合成边界做确定性检查，不代表真实模型质量或通用QA收益。unknown表示当前规则不确定，不能直接等同于问答的“现实中没有事实”。

## 读取一个固定JSON

自建输入必须满足ARCH-01 SidecarInput（不包含expected_behavior）：

```text
uv run --locked python -m tools.research_v2.sidecar_cli snapshot --input var/my-snapshot.json --output var/sidecar-arch02/my-result-v1.json --enabled
```

已有合法完整Build导出可选：

```text
uv run --locked python -m tools.research_v2.sidecar_cli snapshot --format export --origin synthetic --input var/demo-export.json --output var/sidecar-arch02/export-v1.json --enabled --question "Where does Alex live?"
```

synthetic仅用于合成导出；获准使用的真实来源应标source_snapshot。文件须由你合法取得；本模块不下载、不自动读取任何研究工作树。导出格式使用现有MemoryExport校验（Memory、Relation、Source及版本引用）；旧关系作为结构校验对象，不当成语义gold。诊断不改存储关系标签。

导入Export时复制其Build fingerprint；输入字节SHA另外记录。核心输出顶层rule_version是此次规则版本；record.snapshot.provenance保留输入身份，其rule_version可能是输入契约版本，不能冒充本次规则版本。真实数据库从未被此适配器打开；仅JSON文件被只读打开。

## 交付边界与回滚

仅提供纯函数／独立CLI的关闭与开启结果，不宣称已经完成ARCH-03生产查询默认路径等价或消融实验。ARCH-03再补对照报告与性能测量；ARCH-04补正式ADR、两个历史Build/fixture兼容与Reviewer实测。

本轮只在合成真实生产格式Export上验证兼容与DB文件未改动，没有运行受限制真实Build、活动数据库或付费模型。正式公开提交不要包含var/、.venv/、真实原文导出或私密模型wire。包内只提供合成输出示例。

回滚：删除本包新增的3个Python模块、2个测试和ARCH02文档/示例即可；保留ARCH-01文件。没有生产schema迁移或生产默认配置改动。
