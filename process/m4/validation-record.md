# M4 导出、打包与校验

本文只说明重建方法和机器检查；成绩口径见[来源说明](source-notes.md)，人工意见见[复核登记](member-review-record.md)。

## 重建

使用独立文档环境：Pillow、python-docx、ReportLab、PyMuPDF，不加入应用依赖。

```sh
python scripts/build_m4_report.py
python scripts/package_m4_materials.py
```

报告正文改变时依次运行两条命令；仅整理过程文件时运行打包命令。构建以 Markdown 为源，默认使用 Windows 宋体／黑体；其他系统用 --font、--bold-font 指定中文 TrueType 字体。

## 检查结果与文件用途

| 文件 | 检查及用途 |
| --- | --- |
| [pdf-validation.json](pdf-validation.json) | 实际 PDF 页数、源稿和 PDF 摘要；含索引共 5 页。Word 分页未独立渲染，单独编辑 Word 后需另导出并核页数 |
| [source-validation.json](source-validation.json) | 从保存行重算 F1、Recall、查询 token 及 Dynamic／Hybrid 比值；核对真实案例 Trace、原文片段和报告本地链接 |
| [package-check.json](package-check.json) | DOCX XML、JSON/CSV、PNG/SVG、ZIP CRC、安全路径、离线链接、载荷与工作区原件一致性；只读检查 M3 与截图原件未变 |
| [file-manifest.csv](file-manifest.csv)、[file-sha256sums.txt](file-sha256sums.txt) | 清单记录路径、类别、大小与 SHA-256；清单排除自身及哈希文件，哈希文件覆盖除自身外的包内文件 |
| [report-sha256sums.txt](report-sha256sums.txt)、deliverables/m4/sha256sums.txt | 前者记录源稿及报告导出，后者记录独立交付的 PDF、Word 和 ZIP |

包内源文件保留仓库路径和原字节，Word/PDF 在 ZIP 外独立交付。预览图和提取正文由本目录 .gitignore 忽略，可随构建重建；历史稿由 Git 对象读取并校验，不覆盖其内容。

脚本不调用模型或重跑业务测试。自动检查不代替[成员复核与正式交付](member-review-record.md)。
