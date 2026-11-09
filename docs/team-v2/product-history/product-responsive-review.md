# Product Console：页面适配与文案调整

> 历史记录：以下行为、命令、截图与结果仅对应文内注明的版本。复现历史命令请使用当时的 Git 提交；当前送审入口见 [Product 复核说明](../product-review.md)。

日期：2026-11-09。对应 #23、#26–#29 / Draft PR #39。本轮依据负责人在工作区提出的页面修改意见；改动基准 `739888347e5651036a1c42040f75dbe0d8f6f456`，页面代码 `8b40d23f882568565fb637004e9fce16797dbf94`。

## 可见变化

- 页面使用黑色文字、白色面板与浅蓝背景，阅读区最大宽度从 1260 增至 1840 像素，正文、说明与指标字号分别调整。
- 删除顶端 Replay 小字和品牌副标题。宽屏品牌在最左侧，与 Overview / Memory / Query / Experiments / Demo 导航同一行；窄屏品牌在上、导航在下。
- 导航使用横向栏目、浅蓝选中背景与蓝色底线。仍支持键盘切换，当前选中状态可供辅助工具识别。
- 手机端任务卡片、问答操作和 Memory 详情纵向排列，四项指标按两列排列。实验汇总表可换行，原始 JSON 在详情内部滚动。
- 单个选项直接展示；2–6 个选项直接切换；更多选项保留可搜索下拉框并限制宽度。适用于数据/对话/Build、案例、来源、报告和实验分组。

## 页面说明与注释审查

范围为 Console 五页、版本/视图设置、原文与 Trace 详情、冻结实验报告和离线启动入口中的可见说明；代码中的注释也核对其与实际行为一致。原始问题、答案、来源原文及冻结数字不作为说明文案改写。

| 位置 | 必要性与准确性判断 | 处理 |
| --- | --- | --- |
| 顶部品牌、Replay 标语 | 重复页面身份，占用顶部空间 | 删除副标题和顶端小字；保留品牌图标、名称 |
| 数据与版本 | 需要知道所选构建及其完整身份 | 版本选择放入弹层；正文保留合成/只读模式及构建状态；完整 ID、指纹和发布状态可查 |
| Overview | 需要理解从哪里开始、两类数据的区别 | 保留三个任务入口与简短作用说明；明确合成案例与独立历史真实报告的区别 |
| Memory | 时间、计划、否定、来源与关系会影响判断 | 保留这些字段；删除中文后重复的英文枚举；列表说明改为“按记录顺序展示，未按事件时间排序” |
| 原文检查 | 来源身份不一致不能展示其他对话内容 | 保留身份校验与错误；缩短连接/映射失败说明；保留来源身份详情 |
| Query | 已有记录、证据不足、冲突和执行失败必须区分 | 简化载入提示；保留回答状态、失败阶段/代码、日期、引用及可恢复的无效 ID 提示 |
| 阶段 Trace | 有效选择不等同于实际送达 | 保留阶段区分和未记录送达的说明；原始 wire 不展示的代码注释仍符合白名单输出行为 |
| 实验说明 | 成功子集不能推导全量提升 | 保留可比配对、完整分母、失败和 unknown；删除重复提示，精度/完成率定义放到明细 |
| 成本 | 历史价格估算不是账户实扣 | 保留估算与缺测说明、共享构建成本；没有的对话/题型成本不补零 |
| Demo | 必须区分流程演示与真实模型成绩 | 保留一次醒目的合成说明和约 4 分钟路线；删除重复 Replay 文案和卡片上的机器 ID，身份仍可展开 |
| 启动/空态/错误 | 用户需要恢复路径 | 保留本地命令、空数据、快照校验失败和异常提示，删去与操作无关的实现描述 |

## 本地审查方式

```powershell
.\.venv\Scripts\python.exe tools/team_v2/demo.py replay
```

打开 `http://127.0.0.1:18501`。浏览器缩放先设为 100%，依次检查五页；把窗口从宽屏缩到手机宽度，确认品牌/导航换行、文字和卡片布局。Memory 打开原文，Query 切换六类案例，Experiments 切换分组并下载报告。

定向自动检查：

```powershell
.\.venv\Scripts\python.exe tools/team_v2/check.py -q --tb=short tests/test_console_ui.py tests/test_console_experiments_ui.py tests/test_console_replay.py tests/test_console_evidence_ui.py
.\.venv\Scripts\python.exe tools/team_v2/verify_replay.py --browser-python var/console-browser/Scripts/python.exe --output var/new-responsive-check --browser-script browser_console_responsive.py
```

输出目录必须是新目录；浏览器命令需要安装 Playwright 的独立 Python 环境和本机 Edge。安装依赖需要网络，Replay 运行读取本地固定快照。

## 验证与交接

本轮定向离线检查 22 passed / 1 条现有依赖弃用 warning。独立 main 候选检查通过：基于 `0ebb2b8f832e306c37389881b9b7187129e5311a` 添加六个 Product 模块，五页可打开，原 Hybrid 默认和五个核心文件字节哈希保持不变。此检查不是合并或 main 全量回归。

实际浏览器检查通过 25 个页面/尺寸场景（390、768、1024、1280、1920 像素宽），包括宽屏同排、窄屏两行、主页面无横向溢出、键盘导航、手机端原文打开、失败案例恢复、实验切换和下载 JSON 与冻结源整体相等。页面脚本错误 0、外部请求 0、真实模型请求 0。

随后在 `66b6f9e` 补跑六案例完整浏览器回放通过，包括历史 Build 切换、来源跳转、四阶段 Trace、404/非法路径输入恢复。该提交只修正浏览器脚本，页面代码仍与 `8b40d23` 相同。过程中的失败记录保留于 ignored `var/responsive-*`，不计为通过结果。

| 查看内容 | 实际截图 |
| --- | --- |
| 桌面 Overview，1920×1080 | [查看](../assets/product-responsive/overview-1920.png) |
| 桌面 Overview，1280×900 | [查看](../assets/product-responsive/overview-1280.png) |
| 平板 Overview，768×1024 | [查看](../assets/product-responsive/overview-768.png) |
| 手机 Overview，390×844 | [查看](../assets/product-responsive/overview-390.png) |
| 桌面 / 手机 Memory | [桌面](../assets/product-responsive/memory-1920.png) · [手机](../assets/product-responsive/memory-390.png) |
| 桌面 / 手机 Query | [桌面](../assets/product-responsive/query-1280.png) · [手机](../assets/product-responsive/query-390.png) |
| 桌面 / 手机 Experiments | [桌面](../assets/product-responsive/experiments-1280.png) · [手机](../assets/product-responsive/experiments-390.png) |
| 桌面 / 手机 Demo | [桌面](../assets/product-responsive/demo-1280.png) · [手机](../assets/product-responsive/demo-390.png) |

[证据与 SHA-256 清单](../assets/product-responsive/manifest.json)、[25 场景原始结果](../assets/product-responsive/responsive-result.json)、[main 候选结果](../assets/product-responsive/main-compatibility.json)、[六案例结果](../assets/product-responsive/six-case-result.json)。环境为 Python 3.12.12、Streamlit 1.66.0、Edge 157.0.4341.42。本轮没有将自动化浏览器录制宣称为正式 MP4。

`b91d74f` 的 [API Console / 旧入口检查](../assets/product-responsive/api-legacy-result.json) 也通过：在全新 ignored 目录生成合成数据、启动本地 API/UI，四案例与原五阶段入口往返成功，服务端口占用错误正确透传。真实模型调用 0；该检查产生的合成数据库未上传。

清单中 JSON 的 SHA-256 和字节数按 UTF-8 / LF 计算，PNG 按原始字节计算；Windows checkout 的 CRLF 需先规范为 LF。这与 Git 中保存的材料一致。

本轮没有调用真实模型、修改冻结数据或生产逻辑。最终非作者成员验收仍待基于新版本补录；保持 Draft PR，未合并、未关闭 Issue。Notion 当前缺少可用连接工具，本轮更新需负责人补录。

回滚：停止本地 Demo，使用独立 checkout 打开基准 `7398883`；若撤销已提交改动，按提交做普通 revert，不改写共享分支历史。旧截图与验证记录保留在 [上一轮交接](product-final-handoff.md)。
