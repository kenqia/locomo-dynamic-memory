# M5 Final Submission

项目：面向长期对话的动态记忆系统：设计、实现与评测

团队：第三组「在阴雨天游泳」

仓库：https://github.com/kenqia/locomo-dynamic-memory

## 提交内容

- 01_Report：5 页课程版主报告（PDF/DOCX/Markdown）；Full_Report 内保留原 14 页报告及 39 页研究附录。
- 02_Presentation：10 页 PPTX/PDF、演讲备注和 Q&A。
- 03_Demo：291 秒配音视频、匹配字幕、旁白稿、脚本和分镜。
- 04_Process：需求、架构、ADR、会议纪要与过程索引。
- 05_Reproduction：源码快照、逐文件版本清单、复现指南。
- figures：报告图、可编辑 DOT/SVG 与生成脚本。

## 运行

先解压 05_Reproduction/source-code.tar.gz 到新目录，再进入源码目录：

    uv sync --locked --python 3.12
    uv run --locked python tools/team_v2/demo.py replay

打开 http://127.0.0.1:18501。这是离线合成演示，不需要 API key，不调用模型。

## 数据与隐私

提交包不包含 LoCoMo 原始对话、标准答案、六份真实 MemoryExport 原件、凭据或本地密钥。六份 MemoryExport v2 保存在单独的本地受控目录；来源许可为 CC-BY-NC-4.0，课程接收渠道和再分发授权需单独确认。不要上传 GitHub 或 Notion。

## 验收边界

本地完整离线回归 1,201 项通过；解包后 52 项专项、Chromium 六类场景、视频全片解码和包内 SHA-256 校验通过。视频为 291 秒、1920×1080、30 fps、H.264/AAC。自动化通过不替代非作者真人全片观看、文件签收和课程提交回执。

Product 与 Sidecar 已合入 main。交付 PR #43 中包含之前的 14 页报告版本；本包已按课程 5 页要求本地生成新主报告，尚未推送更新。远端 CI 仍需在修复提交推送后复验。

主报告严格排为 5 页。原 14 页报告及 39 页研究附录保留在 01_Report/Full_Report/，供助教按需深入查阅。
