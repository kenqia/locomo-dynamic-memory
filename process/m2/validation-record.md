# M2 文档与过程包验证

日期：2026-10-06。验证范围为报告、图示和过程包。

## 文档构建与检查

使用 Python、python-docx、Pillow、LibreOffice 7.3 和 Poppler 构建及检查文档。没有改变项目生产依赖。图示保留 PNG 和 SVG，报告以 Word 导出 PDF。

```sh
python scripts/build_m2_report.py
python scripts/build_m1_report.py
libreoffice --headless --convert-to pdf --outdir output docs/requirements/vision-and-scope.docx
pdfinfo docs/requirements/vision-and-scope.pdf
python scripts/package_m2_materials.py
python scripts/package_m1_materials.py
git diff --check
```

正文修订后，两份 PDF 均为 5 页 A4；已检查渲染页面、表格、图示、页码和文字边界。Markdown 正文与 Word 内容逐项对应，DOCX XML、PNG 与 SVG 可解析。本轮只优化过程材料，报告 PDF 保持上一轮已检查的版本。修改后的任务快照和 M1 反馈记录另行导出 Word/PDF。

## 打包与校验

打包采用显式文件清单，包内路径与仓库一致。脚本检查 ZIP CRC、文件大小、SHA-256、安全相对路径、离线链接、图源可读取性和报告副本一致性；原历史任务 CSV 保持原字节。

本次检查结果保存在包内 process/m2/package-check.json。最终文件数以该文件为准；file-manifest.csv 覆盖清单和校验文件以外的全部载荷，file-sha256sums.txt 另包含 manifest 的校验，不计算自身。版本记录仅说明版本演进，不再保存另一份哈希表。

历史过程包依次为 33、34、36、39 个文件；这些数字表示当时的迭代，不表示本轮数量。

## 任务与成员检查

本轮读取现有 Notion 任务表，将已有 M2 产物的相关任务按实际进度送入待复核，并重新读取导出快照。历史 W09 的“进行中 / 验收通过”仅保留为旧记录，当前 Notion 已为“已完成”。最新快照附在过程包中，不改写历史 CSV。

M1 原执行流程和此前全员核对事实保留。M2 文件尚缺真实成员复核记录，检查范围及填写位置见 member-review-record.md。文档生成和自动检查不能替代成员复核。

尚未执行系统功能测试、模型调用、对照实验、合并、推送、正式提交或课堂展示。Issue/PR 尚未建立，不编造其链接；本轮本地修订也没有可用的远端交付地址。
