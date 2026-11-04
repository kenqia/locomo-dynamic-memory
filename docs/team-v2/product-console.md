# Product Console：导航与 API 映射

关联：[#26](https://github.com/kenqia/locomo-dynamic-memory/issues/26)，并提供 #27 的只读入口。
基准：`3ba1954bd0c188ad84d80dd4a4f94618857b0109`。

## 使用场景与导航

展示者从 Overview 检查数据、对话和冻结 Build，依次进入 Memory、Query/Evidence、Experiments、Demo。
评审者使用相同导航，并打开“评审者”视图核对版本、来源和原始字段。
Console 只使用 GET 和仓库内已审查的冻结 JSON，不提供构建、重试或评测运行按钮。
“五阶段工作流”开关返回原有上传、对话、构建、问答、评测流程；其中显式执行操作保留原行为。

| 页面/对象 | 数据来源 | 实际字段与显示规则 |
| --- | --- | --- |
| 连接状态 | `GET /health` | `status`；连接失败明确报错，冻结报告仍可查看 |
| 数据选择 | `GET /datasets` | `items[].dataset_id/version/license/conversation_count/turn_count`；空列表提示尚无数据集 |
| 对话选择 | `GET /datasets/{dataset_id}/conversations` | `items[].sample_id/speaker_a/speaker_b`；对话作用域不跨数据集 |
| Build 选择/身份 | `GET /builds?dataset_id=…&sample_id=…` | `build_id/fingerprint/source_sha256/status/phase/query_ready/created_at/updated_at/progress`；未完整版本也能检查，不伪称完整 |
| Memory 入口 | `GET /builds/{build_id}/memories` | 分页展示原始 `Memory` 对象；时间、计划、否定、来源等字段原样保留 |
| Query/Evidence 入口 | `GET /queries/{trace_id}` | 校验 `build_id` 与当前 Build 一致；展示 outcome、answer/error 及原始 Trace；没有 Trace 时不发起生成 |
| 后端 Run 列表 | `GET /evaluation-runs` | `run_id/status/plan_id`；列表按 API 的 ID 顺序，不能冒称时间顺序 |
| 保存的报告 | `GET /evaluation-runs/{run_id}` | 显式读取已保存结果；显示 `completed_at`、`status` 和报告 JSON；未记录的时间显示 unknown |
| 冻结真实报告 | `docs/team-v2/research-evidence.json` | `source_commit/run_id/original_baseline`；与本机 Build、后端 Run 分开标识 |
| 原 Run 状态 | 同上 | 757 QA、3028 组合；2969 succeeded、56 failed、3 unknown；缺测不填零 |
| 实验策略摘要 | 同上 `original_baseline.groups.strategy` | `planned/states/execution_success_rate/qa_successful_scorable/full_denominator_qa_score`；null 显示 unknown |
| Demo | 启动器与合成 fixture | 固定问题、启动方式、Replay 说明；不宣称真实模型质量 |

列表使用分页控件，不把当前页数量当作全部数量。
完整 Timeline、引用跳转、四类失败/成功冻结案例属于 #27；多维实验比较与完整 3–5 分钟 Demo 属于 #28；浏览器全流程验收属于 #29。

## 启动

在自己的 clone 中安装 uv，然后运行：

```sh
uv sync --locked
uv run --locked python tools/team_v2/check.py -q --tb=short
uv run --locked python tools/team_v2/demo.py prepare
```

`prepare` 只创建本 clone 下新的 `var/team-v2-demo/`。已存在时不得覆盖，改用新的
`--output var/<new-name>`，后续 api/ui 使用同一个 output。

分别在两个终端运行：

```sh
uv run --locked python tools/team_v2/demo.py api
```

```sh
uv run --locked python tools/team_v2/demo.py ui
```

访问 `http://127.0.0.1:18501`，确认显示 `OFFLINE SYNTHETIC DEMO`。
没有 uv 命令但已有项目环境时，可将 `uv run --locked python` 替换为
Windows 的 `.venv\Scripts\python.exe`。普通生产环境可用
`uv run --locked streamlit run src/locomo_memory/console_ui.py` 打开 Console，
使用与 API 相同的 `LOCOMO_CONFIG`；合成演示始终使用上述隔离启动器。

## 验证与回滚

先运行 `tools/team_v2/check.py tests/test_console_ui.py -q --tb=short`，再运行完整离线检查。
截图和本机实际结果见 [Product 验证记录](product-validation.md)。
不把 API/AppTest 通过当成非作者人工验收；Reviewer 未确认时保持 pending。
撤销本 PR 的功能提交即可回到基准 UI，无生产数据库迁移，无默认 Build/Query/模型参数修改。
