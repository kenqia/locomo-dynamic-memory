# Track A｜Product Experience：六天交付可演示 Research Console

**建议父 Issue**：`[v2][Product] 6-day Research Console + Evidence Demo`
**Owner**：三位队员自由认领；必须 D1 确认。**Reviewer**：另一个真实成员。
**分支**：`team/product-console-v2-6d`。**交付日**：D5 完成、D6 只修阻断。

## 成功定义（不是 UI 原型）

评审者打开一套离线可运行的 UI，可以完整体验：选择对话/冻结 Build → 查看 Memory 时间线/关系 → 查询结果与证据 → 引用来源 → 检索/解析 Trace → 查看真实评测与成本（必要时 read-only replay）。流程可录屏、可复现，不要真实模型密钥或 live DB。

**复用基础**：现有 FastAPI + Streamlit，`src/locomo_memory/ui.py`、`query_ui.py`、`evaluation_ui.py`、`version_ui.py`、`ui_theme.py`。不要把六天浪费在 React/Next 全量重写；要新前端必须先保证原 Streamlit 仍能交付。既有 5 阶段功能必须保持可用。

## 只有四个子 Issue（按 D1—D5 完成）

### PROD-01｜D1–D2 统一信息架构 + 可运行 Overview（P0）

- 明确展示者、评审者两种主要场景，固定菜单：Overview、Memory、Query/Evidence、Experiments、Demo。
- 展示真实 Build/Run 身份、运行成功/失败/unknown、最近报告、已有 API/fixture 字段；不能凭空新增真实分数。
- 交付：可运行页面、样式统一、无凭据离线启动、一张截图、API 字段映射。
- 验收：新机器按 README 能启动；前后端连接失败/空数据有正确提示；不发生成请求。

### PROD-02｜D2–D3 Memory Timeline + Evidence Inspector（P0）

- 复用已有 Memory/SourceTurn/relations/time/QueryTrace 显示时间、状态、来源和冲突。
- 在 Query 页面并列或可切换显示 initial → expanded → effective/delivered → answer/citations、每阶段错误与预算。
- 点击引用跳回完整原文；如果 event_ref 不存在不能虚构；如果 exact wire 未记录显示“未记录”。
- 交付：两页实作、至少四个冻结案例（成功、证据不足、引用异常、预算失败）、对应截图/测试。
- 验收：来源 ID 与 source 文本一致；未知日期、计划、否定不被渲染为确定事实。

### PROD-03｜D3–D4 实验比较与离线 Demo（P0）

- 只读接入已有 757 QA / 3,028 组合结果；按对话、类型和策略呈现完成率、成功子集得分、完整分母、成本及缺测。
- 必须把原 Run 与补充/修复 Run 分开，不把 unknown 填零；`dynamic` 可比子集优势与总运行失败并列展示。
- 构建 `demo_fixture/` 的脱敏、授权可公开**固定快照**；离线演示不依赖正在运行的 DB、不触发 DeepSeek；标记 Replay。
- 交付：演示命令 + Demo 操作路径 + ≥4 张真实 UI 截图。
- 验收：一个 3–5 分钟连续演示脚本可以从头到尾走完，无中途配置/联网障碍。

### PROD-04｜D4–D5 E2E / 浏览器验收 + 发布（P0）

- 提供 pytest/Streamlit AppTest/浏览器冒烟，覆盖至少：导入或选择、历史 Build 查看、Memory→Source、QA Trace、失败状态、Run 对比、Demo 不付费。
- 检查 1280px 桌面布局，字号和引用可读；优先修功能缺陷，不花时间在动画。
- 交付：PR、测试记录、使用说明、已录真实 Demo 素材片段；D5 附实际可运行版本。
- 验收：Reviewer 从干净 clone/明确环境可运行；旧 API/生产默认契约不退化。

## D4 冻结后的裁剪次序

1. 必须保留：已有五阶段流程、Query Evidence、可追原文、真实指标、离线演示。
2. 时间不足：用简洁 Timeline 表格代替图形；用可展开关系表代替复杂 Graph；先桌面端，不做移动端复杂适配。
3. 首先砍掉：3D Graph、动画、全新前端框架、耗费 API 的实时“AI 分析”按钮。

## 禁止事项

不得修改默认 `builds.py`、`queries.py`、Prompt 或 Model 参数；不得使用新架构未验证字段冒充真实数据；不得读取/提交原始敏感 wire、封存评审密钥、教师隐藏测试；不得启动收费 Build。接口确实缺失时用可审查的**只读 adapter 或 fixture**，新增生产接口需负责人批准。
