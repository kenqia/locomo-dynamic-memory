## Summary

补齐 M5 配音演示视频，修复旧源码包缺文件导致的测试收集失败，形成可解压复现的交付候选。关联 #25、#34、#35、#36、#37；保留待非作者验收状态。

```text
M5_Final_Submission/
├── 01_Report/         14页报告、DOCX/Markdown、39页研究附录
├── 02_Presentation/   10页PPTX/PDF、演讲备注、Q&A
├── 03_Demo/           291秒配音MP4、匹配字幕、旁白、操作脚本
├── 04_Process/        需求、架构、ADR及四周补录会议纪要
├── 05_Reproduction/   源码、逐文件版本清单、复现指南
└── figures/           报告图片、DOT/SVG、聚合数据与脚本
```

生产应用代码、默认 Hybrid、默认关闭的 Sidecar 和冻结实验结果保持原版本。唯一测试修正为 Sidecar 保真测试显式请求 Dynamic，并断言状态解析执行，避免默认 Hybrid 的候选排序导致偶发失败。含原文摘录的 12 份研究输出不随包分发，证据损失图改读同值聚合摘要。

## Evidence

- **Before:** 旧源码包仅含 404 个成员，缺少 685 个声明的证据文件，测试收集发生 2 个文件缺失错误；旧 ZIP 不含视频。
  **After:** 源码清单覆盖 1,078 个文件，逐项哈希核验通过；干净目录按锁文件离线安装可运行，视频全片解码成功。最终 SHA-256：`f6908e677cb61d9a47e31d9ceb260d0fba66530183eb3ce396baeef933c31bf3`。最终测试与包哈希记录在 `PRE_SUBMISSION_CHECK.md` 和 `package-verification-20261109.json`。
- **Before:** Sidecar 测试遗漏策略参数，完整套件出现 1 failed / 1200 passed；重复运行可时过时不过。
  **After:** 显式 Dynamic 后相关 45 项通过；撤回参数的反向验证失败，保留原有回答/Trace/数据库/调用数保真断言。完整重跑 1201 passed，0 failed（531 + 670；JUnit 集合与全量收集逐项一致）。
- Chromium：六类 Replay、历史 Build、来源跳转、Trace 与导出通过，0 模型调用、0 外网请求。报告与汇报全部 24 页成功渲染；Office 容器 CRC 通过；字幕 46 条时轴合法。
- 负责人后续处理：课程更正口径、六份完整 JSON 受控交付、非作者全片/文件签收和课程提交回执。此 PR 不声称这些事项已完成。

远端 main@4baa981 的最新 CI 当前因同一条旧测试失败；本 PR 含修正，PR43已创建，新的CI结论见PR最新head；不借本地通过宣称远端已通过。

## Merge Danger

**Door:** two-way

可用标准 revert 撤回交付材料与测试修正；旧预览原件已保留在本地交付备份，Git 历史也保留旧版本。无模型费用、数据库迁移或新增运行依赖。

**Blast Radius:** delivery

只涉及交付文件、图表输入分发、证据清单及一条测试，不修改生产请求路径。文件签收后再决定合并及关闭 Delivery Issues；历史延期 Issue #20 保持开放。
