# ARCH-01 初测记录

日期：2026-11-03。
范围：新增Schema与冻结合成输入；未运行推断核心、付费模型、数据库构建或网页自动化。

执行环境：Linux，Python 3.12.14；使用B分支ZIP的uv.lock安装项目环境。
实际命令（项目根目录）：

```text
uv run --locked python -m pytest tests/test_sidecar_schema.py -q --tb=short
```

实际结果：42 passed，1 warning，0.14s。警告为项目已有FastAPI/Starlette的httpx弃用提示。
Windows原生环境未在本机运行；新增代码与测试没有fcntl/resource等Unix专用导入，仍需卓新烨在本机执行上述定向命令并保存实际结果。不得将本次Linux通过写成Windows通过。

测试内容：16个案例输入的有效／预期拒绝检查，manifest摘要与编号，默认关闭，JSON往返，时间范围及锚点，外部来源、重复Memory、错误指纹、空陈述、自连接、重复事件对及无理由拒绝；开启契约时输入未改变。

边界：此处的42个检查不是42个真实动态语义案例；16个合成案例的语义预期尚未由推断核心计算。没有核验旧活动Build磁盘哈希，没有端到端证明enabled=False旧路径等价，没有真实模型质量或性能结果。后续由ARCH-02/03补齐。

团队审阅：待真实非作者Reviewer执行与反馈；尚未发布GitHub评论、PR或更新Notion，未标记任务完成。
