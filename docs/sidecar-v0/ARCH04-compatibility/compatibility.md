# 两个合成完整Build的兼容检查

Two synthetic complete Build fixtures, not two real historical research Builds. No real QA quality evaluation.

| Fixture | Memory | Source | 多来源Memory | 所有检查 |
| --- | --- | --- | --- | --- |
| single-source-temporal | 2 | 2 | False | True |
| multi-source-preference | 2 | 2 | True | True |

由实际公开API与SQLite构建，生成和Embedding均受控；没有真实模型调用。
诊断前后原数据库及导出字节摘要相同，Build身份保留，开启/关闭不改写原响应。
数据库仅在新临时目录创建并删除，报告不包含数据库或模型wire。真实成员复核仍待完成。
