# M2 本地制作验证记录

日期：2026-10-06。验证对象为本轮报告、简化图和过程包，不包括未来系统实现与实验效果。

## 文档环境

当前会话未提供 `load_workspace_dependencies`，本轮以本机已有 Python、python-docx、Pillow、LibreOffice 7.3 与 Poppler 作为替代。标准文档渲染脚本缺少 pdf2image，因此在 `/tmp/locomo-m2-docs-20261006` 创建临时隔离环境，使用既有包并仅补充 pdf2image 1.17.0。没有修改系统配置或项目生产依赖。

图示使用 Noto Sans CJK SC，保留可编辑 SVG 与高分辨率 PNG。Word 正文使用 11 pt 中文字体；表格按内容使用 9.5–10 pt。PDF 从 Word 渲染导出，避免分别制作而产生内容漂移。

## 实际命令

```sh
/tmp/locomo-m2-docs-20261006/bin/python scripts/build_m2_report.py

/tmp/locomo-m2-docs-20261006/bin/python \
  /mnt/c/Users/26960/.codex/plugins/cache/openai-primary-runtime/documents/26.909.11814/skills/documents/render_docx.py \
  docs/requirements/vision-and-scope.docx \
  --output_dir /tmp/locomo-m2-docs-20261006/render-v3 --emit_pdf

pdfinfo docs/requirements/vision-and-scope.pdf
git diff --check
```

临时环境和渲染目录不进入交付包。制作脚本可在具备 python-docx、Pillow 和指定字体的环境重用；渲染脚本需要 pdf2image、LibreOffice 与 Poppler。工具路径是本次环境记录，不是项目运行环境要求。

## 已完成的文档检查

- 报告 PDF 为 5 页 A4，符合本轮不超过 5 页的目标。
- 已逐页打开最终渲染的五张页图，检查正文、表格、页码、两张图及引用说明。未发现缺字、裁切、重叠、断表或多余空白页。
- 已打开两张简化图检查流程和箭头，修正多行文字贴边。
- 逐项比较 Markdown 正文和表格单元与 Word 内容，未发现遗漏。
- Word 中嵌入图数量为 2，DOCX 压缩包、相关 XML 和两张 SVG 可解析。
- PDF 可提取预期章节、Recall@K 与 CONFLICT 等关键文字，未出现替换字符。
- 制作脚本语法可解析，已实际运行并完成文档构建与渲染。
- `git diff --check` 通过。

## 打包检查

打包脚本对显式文件清单操作，不收集整个工作区。按组长提供的 M1 ZIP 调整留档方式后，包内保留仓库相对路径，全部文件与仓库文件逐字节一致，不再改写报告源稿的图引用。阅读页、文件清单与校验值先写入仓库，再打包。报告 Word/PDF 独立交付，ZIP 保留其 Markdown 作为迭代过程材料。

过程 ZIP 与文件清单的逐项完整性、SHA-256、相对链接、Markdown 图引用、PNG/SVG 可读取性，以及导出的 10 条 M2 任务是否保留原状态，由 `scripts/package_m2_materials.py` 构建时检查，命令结果另存 `deliverables/m2/package-check.json`。包内附带清单与校验文件，避免将初稿、旧快照或参考图片误作当前成果。

首次制作的过程包为 33 个文件。后续依据 M1 ZIP 调整为保留仓库原始路径，移除包内重复报告 Word/PDF，并加入真实已有会议 Word 和历史快照 Word/PDF，调整后的清单共 34 个文件。运行 `/tmp/locomo-m2-docs-20261006/bin/python scripts/package_m2_materials.py` 检查 ZIP CRC、文件清单、校验值、相对路径、离线 HTML 链接、Markdown 图引用、PNG/SVG 读取及仓库对应内容；实际结果见交付目录的 `package-check.json`。

10 条 M2 任务与原始导出逐字段相同；独立报告副本与仓库报告一致，PDF 保持 5 页。文本类包内文件的常见凭据模式检查不打印匹配值；该检查不替代截图共享范围核对。组长提供的 M1 包中 19 个文件也与仓库对应原件逐字节相同。

## 未验证与未完成事项

尚未进行系统功能测试、模型调用或对照实验；这些属于 M3–M5 后续工作。此记录只证明文档与打包检查。

当前 M2 文件未取得成员非作者复核记录，未合并或推送，未更新 Notion，未正式提交。包内的成员清单未勾选。实际展示安排及最新文件命名、收件渠道仍由负责人核对；本轮未制作汇报文件。
