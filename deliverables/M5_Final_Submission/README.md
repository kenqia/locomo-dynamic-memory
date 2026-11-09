# M5 Final Submission

**Project:** 面向长期对话的动态记忆系统：设计、实现与评测

**Team:** 第三组「在阴雨天游泳」

**Repository:** https://github.com/kenqia/locomo-dynamic-memory

## 提交内容

| 部分 | 文件 / 位置 | 用途 |
|---|---|---|
| 产品 | `05_Reproduction/source-code.tar.gz` | 应用源代码、配置、测试、合成演示数据与运行文档 |
| 研究 | `01_Report/Final_Technical_Report.pdf` | 最终技术报告；DOCX 与 Markdown 同目录 |
| 研究补充 | `01_Report/Research_Supplement.pdf` | 完整实验过程、失败记录与详细分析 |
| 展示 | `02_Presentation/Final_Presentation.pdf` | 10 页展示 PDF；可编辑 PPTX 与演讲备注同目录 |
| 演示 | `03_Demo/PROJECT-MILESTONE5-3-在阴雨天游泳-演示视频-配音版.mp4` | 4 分 51 秒配音演示；同目录附匹配字幕与旁白稿 |
| 过程 | `04_Process/` | 需求、设计、决策与会议纪要 |
| 复现 | `05_Reproduction/REPRODUCE.md` | 环境准备、离线演示、测试与实验复核说明 |
| 图表 | `figures/` | 报告 Markdown 引用的图片、可编辑 DOT 与生成脚本 |

正式归档入口为 `deliverables/m5-final/m5-final.zip`，解压后顶层目录为 `M5_Final_Submission/`。在该目录运行 `sha256sum -c SHA256SUMS.txt` 核对完整性。

## 运行

先解压 `05_Reproduction/source-code.tar.gz` 到新的源码目录，再进入该目录。使用 Python 3.12 + uv：

```bash
uv sync --locked --python 3.12
uv run --locked python tools/team_v2/demo.py replay
```

打开 `http://127.0.0.1:18501`。这是离线合成演示，不需要 API key，不调用模型。

## 数据与隐私

提交包不包含 LoCoMo 原始对话、标准答案、真实记忆导出原件、凭据或本地密钥。请勿将受控数据复制到公开提交渠道。

## 视频状态

配音视频、对应字幕及旁白稿已纳入本包。视频全片解码通过；自动检查不能代替非作者全片观看、听音与签收。实际观看结论记录在 `03_Demo/Recording_Checklist.md`，未取得的签名保持空白。`VIDEO_STATUS.md` 记录本次检查范围。

当前技术报告为 14 页，汇报为 10 页，研究附录为 39 页。负责人已告知课程要求有后续更正，具体页数与提交口径仍待补充。六份完整 Memory JSON 通过获准的受控渠道另交，本公开材料包不包含原件；其渠道与回执尚未核实。课程提交由负责人执行。

## 版本说明

主项目 Product 基准为 `5519dd2`；Sidecar 离线诊断后续通过 PR #42 合入 main（合并提交 `51d994f`）。报告中的 E25 成绩仍来自冻结实验，不因后续 Sidecar 合入而改变。

源码版本和逐文件哈希见 `05_Reproduction/SOURCE_VERSION.json`。2026-11-09 新增的四周会议纪要已整合；历史材料保留原记录，不作为本次真人复核签名。
