# 报告排版

```bash
pandoc Final_Technical_Report.md -s --self-contained --resource-path=.:../figures -c report.css -o report.html --metadata lang=zh-CN
python html_to_pdf.py "$PWD/report.html" "$PWD/Final_Technical_Report.pdf"   # Playwright Chromium, A4
pandoc Final_Technical_Report.md -o Final_Technical_Report.docx --reference-doc=<样式模板> --resource-path=.:../figures
```
