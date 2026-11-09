# ARCH-01 Sidecar Schema 与冻结边界案例

日期：2026-11-03。负责人：卓新烨。父任务 #24，子任务 #30。
状态：数据契约与初测完成；人类Reviewer待确认／复核。不是ARCH-02推断核心的完成证明。

## 如何放入你的项目

将补丁包中的 tools、tests、docs 三个目录合并复制到现有项目根目录（与pyproject.toml同级），保留目录结构。仅新增本包文件，不替换已有业务文件。不要把整个补丁文件夹当成项目运行。

在项目根目录运行（Windows CMD和PowerShell均可）：

```text
uv run --locked python -m pytest tests/test_sidecar_schema.py -q --tb=short
```

只运行这个文件，不运行包含Unix研究模块的全套check。若导入失败，先确认sidecar_schema.py位于tools/research_v2/，终端当前目录包含pyproject.toml。

## 交付内容

- tools/research_v2/sidecar_schema.py：SidecarRecord、EventLink、StateClaim、TimeInterval，以及Provenance、SourceEvidence、SidecarInput。
- docs/sidecar-v0/sidecar-record.schema.json：Pydantic生成的静态JSON Schema，供审阅与后续工具使用。
- tests/fixtures/sidecar_cases.json：16个合成案例，预期与输入分开。
- tests/fixtures/sidecar_cases.sha256：案例文件字节摘要，初次冻结后修改须新版本及理由。
- tests/test_sidecar_schema.py：数据契约、非法引用、时间边界、默认关闭及输入不改写测试。
- docs/sidecar-v0/ARCH01-VALIDATION.md：本次实际执行结果与边界。

## 契约约定

SidecarInput的provenance将所有嵌套Source、Claim及Link绑定到同一dataset/sample/build及build_fingerprint；单条记录不得脱离该容器跨版本复用。输入须由调用者从可信快照显式提供；当前仅校验摘要格式与容器内引用，不读取数据库验证来源真伪。实际旧Build内容哈希及磁盘只读保证由ARCH-02接入检查，本包不声称已经实现。

SourceEvidence.reported_at为报告时间；StateClaim.event_time为事件适用日期或范围。已知时间必须有上下界、原始表达、来源锚点与依据；模糊表达可保留unknown，不填精确日期。Schema只验证结构、时间区间与引用，不能证明文本蕴含或规则语义正确。

EventLink只表达same_event、different_event、unknown，不取代已有RETAIN/UPDATE/SUPERSEDE/CONFLICT关系。计划、事实、意愿、不确定及否定保存在Claim中，不因相同实体或state_dimension就建立事件等价。判断算法尚未实现，不能把手填预期冒充自动判定。

SidecarRecord默认enabled=False，mode固定diagnostic_only。关闭时不允许携带计算出的EventLink；这是输出契约，不代表已经完成生产开关接入。生产API、配置、schema和数据库均未改动。

frozen=True阻止模型属性赋值，序列字段使用tuple；处理后的新结果须新建对象。此机制不能替代文件只读权限或外部Build哈希核查。

## 案例清单

| ID | 边界 | 冻结预期 |
| --- | --- | --- |
| 01 | 明确同一事件后续 | same_event |
| 02 | 两次明确独立旅行 | different_event |
| 03 | 报告日期与发生日期不同 | 事件日期不取报告日期 |
| 04 | yesterday与明确锚点 | 保留原词、锚点、可核查日期 |
| 05 | recently | unknown，不伪造精确日期 |
| 06 | 明确月份 | 范围，不伪造某一天 |
| 07 | 计划搬家 | 完成情况unknown |
| 08 | 明确完成搬家 | 完成有来源支持 |
| 09 | 未参加 | 保留否定 |
| 10 | 未报告完成 | 不推断确定未完成 |
| 11 | 截止时间的当前住所 | Rome，保留历史 |
| 12 | 搬家前的历史住所 | Paris，不写回全局 |
| 13 | 无法消解的出生年矛盾 | conflict，双方来源保留 |
| 14 | 空快照 | insufficient，不是conflict |
| 15 | 重复来源身份 | 契约拒绝；不静默合并 |
| 16 | 同人物与泛化计划表述 | unknown，不自动合并事件 |

全部为明确标记的合成数据，不含真实课程材料、活动DB或封存评审映射。synthetic Build摘要是人工测试身份，不是真实数据库摘要。预期由开发者根据任务规则制定，尚待真实非作者成员审阅，不属于课程gold。

输入中的source_id、Memory身份只用于当前合成快照的闭合引用；必须连同provenance使用。expected_behavior仅存在manifest中，不属于SidecarInput，禁止进入后续推断函数。ARCH-02应使用case.input运行规则后与expected_behavior比较。

## 下一步与回滚

ARCH-02实现确定性规则、旧Build只读核查和实际预期行为断言；ARCH-03提供独立opt-in/回滚入口和对照；ARCH-04补ADR、跨fixture兼容及真实成员复核。本包没有付费模型调用、没有改最终答案、没有证明QA质量提高。

回滚：移除本包新增的Schema、测试、fixture、文档与静态schema文件即可，不需要生产数据库迁移。若已有其他成员新增同名文件，先比较再处理，不直接覆盖。
