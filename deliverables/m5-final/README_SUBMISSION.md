# M5 Final Submission

**Project:** 面向长期对话的动态记忆系统：设计、实现与评测  
**Team:** 第三组「在阴雨天游泳」  
**Repository:** https://github.com/kenqia/locomo-dynamic-memory

## 提交内容

| 部分 | 文件 / 位置 | 用途 |
|---|---|---|
| 产品 | `source-code.tar.gz` | 应用源代码、配置、测试、合成演示数据与运行文档 |
| 研究 | `01_Report/Final_Technical_Report.pdf` | 最终技术报告；DOCX 与 Markdown 同目录 |
| 研究补充 | `Research_Supplement.pdf` | 完整实验过程、失败记录与详细分析 |
| 展示 | `02_Presentation/Final_Presentation.pdf` | 10 页展示 PDF；可编辑 PPTX 与演讲备注同目录 |
| 演示 | `03_Demo/` | 演示脚本、镜头清单、字幕与录制验收清单 |
| 过程 | `PROCESS.md` | 需求、设计、开发与验收过程的精简索引 |
| 复现 | `REPRODUCE.md` | 环境准备、离线演示、测试与实验复核说明 |

## 运行

Python 3.12 + uv：

```bash
uv sync --locked --python 3.12
uv run --locked python tools/team_v2/demo.py replay
```

打开 `http://127.0.0.1:18501`。这是离线合成演示，不需要 API key，不调用模型。

## 数据与隐私

提交包不包含 LoCoMo 原始对话、标准答案、真实记忆导出原件、凭据或本地密钥。请勿将受控数据复制到公开提交渠道。

## 视频状态

最终 Console 操作演示视频由田亦洁录制。视频文件到位并完成验收后，放入 `03_Demo/`，再重建最终 ZIP 与 SHA-256 清单。未放入视频的包不应被标记为最终完整包。

## 版本说明

主项目 Product 基准为 `5519dd2`；Sidecar 离线诊断后续通过 PR #42 合入 main（合并提交 `51d994f`）。报告中的 E25 成绩仍来自冻结实验，不因后续 Sidecar 合入而改变。
