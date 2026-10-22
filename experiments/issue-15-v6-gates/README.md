# v6 关系可靠性与完整构建关卡

后续按用户要求，将默认 `model_max_tokens` 从4096提高到8192，示例配置同步更新。
这是共用输出上限，适用于抽取、关系与QA；未进行新的真实调用。下文源码身份和
关卡结果属于调整前的验证记录，不能作为修改后身份已冻结的依据。第五关仍未通过。

2026-10-20，Asia/Shanghai。当前停在第五关，未创建新完整 Build、发布或运行 QA。
`relations-v6.2` 改善了两项定向语义问题，但 `relation:172` 仍把同一已完成事件的
详述判成 UPDATE。结构成功、逐字引用合法均不足以通过语义关卡。

当前保留的生产源码身份为
`c3207ffd535a6337705377dd413ed35b9f7196bec5a050c493a55b3d52cc6a13`，
Prompt `relations-v6.2`、Schema `relation-v1`，尚未冻结为完整构建身份。
最新状态见 [current-outcome.json](current-outcome.json)。

## 关卡结果

| 关卡 | 已验证结果 | 结论 |
| --- | --- | --- |
| 1. HTTP 分类与预算 | v6.2受控定向117项，全套283项通过、4项排除 | 通过 |
| 2. 两个固定长度失败输入 | 73、91在v6/v6.1/v6.2下，4096与8192均stop、各20/20覆盖 | 通过，不能归因于提高上限 |
| 3. 条件性确定分批 | 固定输入8192未截断 | 未触发实施条件 |
| 4. 148、172逐字证据 | 各版真实输出均通过严格引用与完整覆盖 | 通过，语义另审 |
| 5. 关系语义 | 73恢复UPDATE；148改RETAIN；172仍误判UPDATE | 未通过，停止真实调用 |
| 6. 冻结、完整conv-26、20项QA | 前一关未通过 | 未进入 |

本阶段累计25次调用，继承此前313次，总计 **338/1,000**，剩余662次。
25次中24次结构成功、1次HTTP402；结构成功不等于语义正确。
本阶段已知266,248 tokens，402没有usage，仍按已预留调用计数。
更早HTTP调用另有未知usage，不声称未计费。原始29个旧失败任务的根因仍不能统一归因。

## HTTP分类与持久预算

`DeepSeekModel.generate()`增加安全HTTP分类：408/500/502/503/504为临时服务错误，
429为限流，允许既有上限内重试；400/422无效请求、401认证、402余额、403权限、其他
HTTP错误及上下文拒绝停止。HTTP失败不混入JSON、Schema或领域校验错误。
只保留实际状态码和白名单类别，不保存错误响应正文、headers或异常字符串。

[Campaign](v6_campaign.py)在每次请求前持久预留额度。失败、重试和未知usage均计数。
账本继承v5预算库的304条调用及更早9次验证，固定该账本SHA-256；历史改变、预算缺失、
未知未结束调用、上限耗尽或执行时源码身份改变均停止。各Prompt版本共用同一账本。

```sh
.venv/bin/python -m pytest tests/test_http_diagnostics.py tests/test_v6_campaign.py -q --tb=short
```

HTTP和预算定向21项通过。v6.2全套验证为283 passed、4 deselected，231.60秒：

```sh
.venv/bin/python -m pytest -m 'not live_model and not local_embedding' -q --tb=short
```

v6.1初次回归282通过、1失败。失败是过时的完整Prompt文本快照，已改为验证稳定的
Schema、原始payload及provider参数，定向75项通过，随后v6.2全套通过。
上述受控结果不能证明真实模型语义正确。

## 固定长度与证据输入

[关卡运行器](gates.py)使用`source_snapshot()`和`comparison()`，只读重建v5 Build
`23f0459c5b3b47269dc1497cfc066810`的73、91。两项历史上各有三次4096的length失败。
每个版本分别比较4096和8192，retries=0，发送前离线捕获请求，去掉max_tokens后精确相等。
Memory、候选顺序、原文、模型、温度、Prompt及Schema在各版内部对照均相同。

首个v6请求返回HTTP402并停止。用户补充余额后才继续同一账本，原402记录保留。
v6之后四次对照均通过；v6.1与v6.2各四次也通过。没有8192仍截断的证据，因此未实施分批。

通过后才调用148、172，均8192、retries=0，保留各20候选。
[QuoteAuditTransport](evidence.py)不改请求或响应，仅在内存检查来源与连续逐字引用，
持久化白名单布尔诊断。v6的两段引用分别101、84字符；后续版本也逐字合法。
这些检查不能判断引用是否足以支持所选标签。

## 独立语义审计与更正

先冻结每个任务6项未确定比较，共24项，按同键优先、词面重合降序、稳定SHA-256排序。
实际24项均跨键。另审两项确定关系对照。这是定向风险抽样，不能给总体错误率，
也不是人工真值或课程标签。

[首次逐项审计](semantic-v6-audit.md)发现73漏判和172误判；
[复核更正](controls-reassessment.md)进一步撤回148的UPDATE接受结论。
旧报告原样保留，修正后的结论为23项合理undetermined、1项遗漏UPDATE、2项无支持UPDATE。

| 比较 | 来源与含义 | 预先接受的标签 |
| --- | --- | --- |
| 73 | D5:4报名陶艺课→D5:8在该课做出作品，跨键同过程推进 | UPDATE |
| 148 | D10:3已加入组织→D10:5补充组织名称，未见新阶段 | 有明确复证理由的RETAIN，或保守undetermined |
| 172 | D12:2项目已完成→D12:6描述同件作品动机与外观，未见新阶段 | 有明确复证理由的RETAIN，或保守undetermined |

使用原文邻接D5:2–9、D12:1–7核对指代。148与172的接受标签集合在下一轮完整输出审核前
落盘，不按待评模型结果改标准。不能把来源相关、同键或event/state编码差异当新阶段。

补充31与76的四项同键对照。独立预审先于真实输出，期望为2项undetermined和2项RETAIN。
[semantics.py](semantics.py)完整运行这两个任务，不裁候选。v6.1符合四项预审，但30项完整
[后续审计](v6.1/semantic-audit.md)仍有148、172两项无支持UPDATE，第五关未通过。

## 最小修复、诊断与回退

- v6.1澄清跨键具体过程推进与已完成事件详述的区别。73恢复UPDATE；148、172仍误判。
- v6.2区分现实阶段与叙述顺序，明确补充名称、属性或表示形式不等于推进。148改RETAIN，
  172仍UPDATE，理由却承认同一完成阶段。
- [单候选诊断](single_pair.py)只用于定位，不能使完整候选关卡过关。v6.2把73和172分别
  降为一个历史端点及双方来源，保持Prompt、8192及retries=0，172仍误判。候选负担与长度
  因此不是该案例的充分解释。
- v6.3/relation-v1.1仅在Schema的label字段同步操作定义，受控确认描述进入实际请求，
  定向140项通过。预先封顶两次隔离调用，73正例通过，172仍UPDATE且理由否认推进。
  [实验处理](v6.3/experiment-treatment.json)保留确切描述与身份。按停止条件结束真实调用，
  回退该Schema描述与版本实验，当前保留v6.2/relation-v1。

没有通过硬编码Memory ID、读取reason强改标签、删除候选、放宽证据或类型约束来过关。
剩余问题需要能检验标签与阶段证据一致性的输出契约方案及独立验证，不能靠继续堆叠Prompt
宣称已解决。此处未引入新字段、强制新语义接口或新的生产依赖。

修改前副本：v6.1前`/tmp/issue15-v6-before-semantic-s2i6kcpi/model.py`；
v6.2前`/tmp/issue15-v61-before-stage-hpv8a3yk/model.py`；Schema实验前
`/tmp/issue15-v62-before-schema-guidance-l_bnogyw/`。回滚保留实验、预算账本及早先修复。

## 产物与边界

外部权威目录为`/home/kenqia/my_folder/locomo-worktrees/real-baseline-issue15-relations-v6`。
`campaign.sqlite3`是调用账本，父目录保存原v6报告，`v6.1/`、`v6.2/`、`v6.3/`各自保存观察，
不覆盖或合并版本。仓库复制JSON/Markdown公开实验记录，不复制凭据或SQLite。
`gates.json`表示各版关卡，不以进程exit0替代语义验收。

没有创建该目录的memory.sqlite3，未启动完整Build、发布或QA。未做远端写入或Notion状态更新，
不宣称Issue15及子票已验收。旧v5保持interrupted，未用新代码原地恢复。
更早基线DB SHA-256保持`13497e43f418275585532d7d8a3a2bb326035662ed6eef67f41a05b6e8f46116`；
v5源DB保持`12410a8a857e91a9e23b97280b4cbcb647278daef83200cb9907c748cd238e2d`。
