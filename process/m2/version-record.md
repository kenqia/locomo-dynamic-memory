# M2 本地版本记录

整理日期：2026-10-06。

制作基准为本地 HEAD：1799d549649741829fce7250e7a91cb0f6f6fb3b。
本轮产物在首次制作时属于该基准上的未提交工作区文件；不宣称它们已包含在基准 commit 内。组长随后要求材料存入 repo，本轮在 `codex/m2-proposal-materials` 分支留档，实际提交以本地 Git 记录为准；未合并到 main 或更新远程。

## 报告与图示校验

| 仓库路径 | SHA-256 |
| --- | --- |
| docs/requirements/vision-and-scope.md | 30c88e6574fbfbe6256be0b6575bcc35af5aa18043470dda17c0afb74ed5051a |
| docs/requirements/vision-and-scope.docx | 495c8dcc1c0f69846d70d1528d5fb905af700b259acea26e453affe4ec3da81b |
| docs/requirements/vision-and-scope.pdf | 061b1ced842d0f1a18014fd5eda7ccb674ce29612cbaa30c05894962f7e32a72 |
| docs/requirements/assets/m2/recording-retrieval-flow.png | b851fddedcdd844b0dad17ce806f58ff455d88ed53a9a7e2dcddb810f6123348 |
| docs/requirements/assets/m2/recording-retrieval-flow.svg | cd228bf48c00b8ee5720ee02772c7fbb96ffae47a179e2a335d31dfd16f8d1db |
| docs/requirements/assets/m2/system-architecture.png | 43e863ad74408645444d4633eaeb743fb005517ac93ebefa68b860c02f14b472 |
| docs/requirements/assets/m2/system-architecture.svg | 1bb79a1c9041e744ec902266611637f102aa9d071baa4f4c811ceb38153d40e7 |

包内文件校验值见 `process/m2/file-sha256sums.txt`，文件清单见 `process/m2/file-manifest.csv`。这些文件先生成并保存在仓库，再与原始材料一起打包，包内路径及内容与仓库一致。外层报告、Word 和 ZIP 的校验值另存于交付目录。
正式提交、成员复核、合并与推送后，应补录实际 commit/tag 和回执，不用本轮基准替代。

## 联网修订版本

本轮修订基于本地 `bfda541`，此前 `729e2cc` 留档首版、`bfda541` 统一 CSV 换行。新增联网笔记、调研前稿与参考链接，更新报告与过程包；当前文件校验见上表及包内清单。新增提交的实际编号以本地 Git 为准，不把远端同步或成员复核写成已完成。
