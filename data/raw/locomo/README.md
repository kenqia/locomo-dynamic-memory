# LoCoMo 本地原始数据

官方数据位于 [locomo10.json](locomo10.json)。来源为 [snap-research/locomo](https://github.com/snap-research/locomo)，2026-10-19 下载，上游 commit 为 `3eb6f2c585f5e1699204e3c3bdf7adc5c28cb376`。

文件保留上游原文，没有清洗或改写。许可证原件为 [LICENSE.txt](LICENSE.txt)，标明 CC-BY-NC-4.0。逐文件 SHA-256、上游路径、对话统计及证据异常位置见 [provenance.json](provenance.json)。

## 内容和边界

数据包含 10 段对话、5,882 个轮次和 1,986 条 QA。每段对话内的 `dia_id` 无重复；跨对话定位证据需要同时使用 `sample_id`。

- `conversation`：原始对话，作为本项目记忆构建输入。
- `observation`、`session_summary`：官方生成的观察与会话摘要。
- `event_summary`：事件摘要任务标注。
- `qa`：问题、类别、证据以及答案或对抗答案，供评测使用。

课程指定的 6 段对话及开发/测试划分尚未确定，本目录保留全部官方数据，不擅自指定测试集。课程动态状态关系、有效 Memory 标注未包含在下载文件中。

## 证据 ID 检查

共发现 9 个 evidence 列表元素不能直接匹配所在对话的单个 `dia_id`，位置见 provenance。部分元素包含以空格或分号分隔的多个 ID；另有 `D`、`D:11:26`、`D30:05` 及找不到对应轮次的 ID。后续评测需区分可解析的组合引用、格式问题和缺失引用。

当前只报告异常，不自动修复原始数据，也不把异常样本静默删除。证据解析与计分政策需要在评测实现前确定。

## 上游评测参考

[官方 README](upstream/README.MD) 说明数据结构和运行方式；[evaluation.py](upstream/task_eval/evaluation.py) 与 [evaluate_qa.py](upstream/task_eval/evaluate_qa.py) 保留官方 QA 评测实现供阅读。这些文件只是参考副本，不构成可独立运行的上游环境，未安装其依赖或执行模型调用。

官方实现包含答案规范化、词干化和类别相关的计分分支，不能未经对齐就用普通 token F1 替代。课程 Recall@K 与动态状态准确率仍需本项目实现并核对口径。
