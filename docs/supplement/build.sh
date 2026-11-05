#!/usr/bin/env bash
# 重新生成全部图表并导出 PDF。需要 uv、graphviz（dot）、pandoc、xelatex 和 Noto CJK 字体。
set -euo pipefail
cd "$(dirname "$0")"
(cd scripts && uv run --with matplotlib python charts.py && uv run --with matplotlib python extra.py && python3 diagrams.py)
pandoc supplement.md -o supplement.pdf \
  --pdf-engine=xelatex --columns=30 --toc --toc-depth=3 \
  -V CJKmainfont="Noto Serif CJK SC" -V CJKsansfont="Noto Sans CJK SC" \
  -V mainfont="Noto Serif CJK SC" -V sansfont="Noto Sans CJK SC" -V monofont="DejaVu Sans Mono" \
  -V geometry:a4paper,margin=2.2cm -V fontsize=10pt -V linestretch=1.25 \
  -V colorlinks=true -V toc-title="目录" \
  -H latex-header.tex
echo "wrote supplement.pdf"
