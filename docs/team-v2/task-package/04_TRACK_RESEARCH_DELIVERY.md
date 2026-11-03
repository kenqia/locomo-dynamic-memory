# Track C｜Research Communication & Delivery：六天交付全部展示材料

**建议父 Issue**：`[v2][Delivery] 6-day Presentation, Technical Report & Demo Release`
**Owner**：一位队员自由认领，D1 确认；**Reviewer**：组长检查数字真实性，另一队员实际检查文件。
**分支**：`team/research-delivery-v2-6d`。**完成日**：D5 视频/文件齐备，D6 正式打包。

## 成功定义（不是“PPT 初稿”）

第六天交付一套评审者可以直接打开和观看的材料：**中文技术说明 + 有证据来源的研究报告 + 可编辑 PPTX + 全页核验 PDF + 3–5 分钟可播放 MP4 + 有声/字幕脚本 + 架构图 + 发布清单和答辩材料**。正式课程格式按最新要求核对，不得用旧 M4 的页数/形式臆测 v2 规定。

已知：`presentations/proposal-outline.md` 是旧提纲；`docs/design/m4-midterm-report.md` 是旧 M4 状态；`deliverables/m4/` 已有报告、汇报 PDF 和本地主仓尚未审查的 MP4。必须先核实这些材料，不覆盖原件，也不能说“完全没有视频”。

## 四个子 Issue

### DEL-01｜D1–D2 研究叙事和数字证据台账（P0）

- 冻结 10–12 句项目核心论断：问题、已有系统、技术创新、真实基线、成本、证据/严重错误边界、失败与 v2 新架构。
- 建立 `claim → Run/Build/commit → report/table → reviewer type` 台账；区分实际、AI 研究审查、真实人工评审、概念方案。
- 必须包含原 3,028 组合 **2,969 成功 / 56 失败 / 3 unknown**，Dynamic 709/757 技术成功、完整分母 QA 0.515133，以及 Dynamic/Hybrid 完成率与成本差异的正确口径。后续补充/修复不拼进原 Run。
- E1 Router v1 是负例，E5 缓存只证明本地 CPU 收益；Sidecar 仅展示候选。
- 验收：所有重要表格带身份证据指针，Reviewer 能反查；不能把“教师隐藏测试最佳”写入材料。

### DEL-02｜D1–D3 正式可编辑 PPTX + PDF 初稿（P0）

- 以真实当前架构与实验结果制作 **12–15 页**（需服从课程最终规则）中文高质量可编辑 PPTX，包含 Presenter Notes；D2 展示至少 6 页，D3 交付全套初稿。
- 建议顺序：问题→用户价值→Build/Memory→Query/Evidence→时间状态→实验设计→四策略结果→完整分母与成本→失败案例→正在研究的 E2→产品演示→局限与下一步。
- 统一样式，不用密集堆字；图表由真实数据生成且带来源；PDF 每页渲染检查字体、图、数字和注脚。
- 验收：可编辑原件、可打开 PDF、文字/图表与证据台账吻合，不能用漂亮图代替可追溯结果。

### DEL-03｜D2–D5 Demo 剧本、实录 MP4、字幕（P0）

- D2 完成完整 3–5 分钟分镜、操作脚本与录屏环境准备；与 Product Track 对齐 Demo Fixture。
- D4 用固定脱敏/获许可的演示环境录制粗剪；D5 输出正式 MP4、字幕（可 SRT）、旁白/逐字稿和 30 秒备用演示片段。
- 镜头建议：问题→选择冻结 Build→Memory/Time→发起/回放 QA→来源点击→Trace→实验结果→局限与下一步。
- 画面明确标注 LIVE / OFFLINE REPLAY / PROTOTYPE，不能用预录画面冒充实时模型调用。
- 禁止出现私密账号、环境变量、token、原始受控模型 wire/评审密钥、未获许可的对话或个人信息。
- 验收：无声播放能靠字幕看懂，带声音正常、无黑屏和跳帧，另有人实际观看全片记录问题。

### DEL-04｜D3–D6 技术报告、图示、课程交付包与答辩（P0）

- 写 v2 Current Architecture + 研究实验摘要 + 当前限制 + 复现说明。概念 Sidecar 明确标 `proposed/opt-in`，不能冒充已入生产。
- 输出 SVG 可编辑架构图、Build/Query 流程图、事实/时间/成本数据图及必要封面。不要不必要地重写所有历史文档。
- D5 生成初步 deliverables/v2 包：报告、PPTX/PDF、MP4、字幕/脚本、图、SHA256、授权/来源与版本清单、README；完成交叉复核。
- D6 提供可直接用于提交的最终包和现场答辩 Q&A，附准确 GitHub URLs/commit SHA、真实性声明、展示操作与备份方案。课程正式提交需用户最后确认。
- 验收：使用干净目录逐个打开、打印/预览全部页面、播放 MP4、验证包内 SHA；别的队员能照 README 找到所有材料。

## 六天内的内容优先级

| 必须做 P0 | 资源允许 P1 | 本轮不做 P2 |
|---|---|---|
| 技术摘要与证据台账、可编辑 PPTX/PDF、3–5 分钟 MP4、脚本/字幕、完整交付包 | 海报、精致动画、双语 PPT、可打印项目卡片 | 新宣传网站、复杂 3D 动画、长篇未核实学术论文、外部公众推广 |

D4 18:00 后不再增加新章节，只修真实错误和必要图表；D5 18:00 后冻结数字和素材，D6 只做发布与阻断修复。

**文件组织**：`docs/team-v2/`、`presentations/v2/`、`deliverables/v2/`、`process/v2/`。对于 PUBLIC 仓库，授权不明的媒体先保留本地并只公开脱敏摘要/manifest，不能因为 D6 截止越过隐私闸门。
