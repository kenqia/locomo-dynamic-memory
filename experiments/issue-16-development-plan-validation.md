# Issue #16 开发集计划预览验证

2026-10-20。只验证离线计划与公开接口行为，未调用真实生成模型、下载模型或执行本地测试集评测。未产生真实 QA 成绩。

## 输入与范围

使用仓库固定官方原件，经 `POST /imports/official` 校验并导入真实 SQLite。原件 SHA256 为 `79fa87e90f04081343b8c8debecb80a9a6842b76a7aa537dc9fdf651ea698ff4`，upstream commit 为 `3eb6f2c585f5e1699204e3c3bdf7adc5c28cb376`。

开发集为 `conv-26`、`conv-30`、`conv-41`、`conv-42`，只生成其独立评测输入。本地测试为 `conv-43`、`conv-44`，不读取或产生其模型成绩。教师隐藏评分集未公开。

## TDD 与 API 验证

新增公开 FastAPI 测试先验证全量预览，初次返回 404，添加入口后通过。随后 smoke 测试先发现返回 `conv-26` 全部 199 题，添加按原始顺序取每类别首题后通过。

在工作树根目录运行：

```sh
PYTHONPATH=src /home/kenqia/my_folder/locomo-dynamic-memory/.venv/bin/python -m pytest tests/test_evaluation_plans.py tests/test_evaluation.py tests/test_imports.py -q
```

结果为 22 passed，仅有现有 Starlette/httpx 弃用警告。测试通过公开接口检查以下结果：

- 官方全量预览为 757 题、四策略、3,028 组合；同一输入与范围重复请求返回同一已保存 Plan。
- 官方 smoke 为五题、20 组合，原始 QA 位置为 `0`、`2`、`3`、`82`、`152`，类别按原始顺序为 `2`、`3`、`1`、`4`、`5`。
- 预览前没有完整构建，受控 provider 未收到调用。
- 缺少必要类别明确拒绝；重复问题文本保留独立身份；指定新 QA 原件不会改写旧计划。
- 来源 API 不含独立答案、证据和辅助摘要；计划保留来源及原件身份；重启后可以读取计划和对应 Input。
- 不支持 `scope: "test"`，不存在的原件明确拒绝。

## 页面 smoke

以临时 SQLite、受控 provider 和 ControlledEmbedder 启动真实 Uvicorn HTTP 后端，使用 Streamlit `AppTest` 执行 `render_evaluation`。选择 `smoke` 并点击“生成开发集计划预览”后，页面无异常，表格显示五题、20 组合，自动填入对应 Input ID，并显示 JSON 下载控件。没有 provider 调用。

该检查验证页面交互和 HTTP 接入，未进行浏览器截图或布局验收。计划预览不固定执行用 BuildVersion；运行时版本固定、逐项进度与恢复由后续票实现。
