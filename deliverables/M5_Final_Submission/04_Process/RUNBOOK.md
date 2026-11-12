# 个人Release运行与验真

先在根目录执行README的`uv sync --locked --python 3.12`。doctor输出Python/锁定包/Embedding缓存和现有DB quick_check，不读凭据；损坏DB返回非零且不修复覆盖。

## 正常应用操作

1. 启动`scripts/personal-release start`，等两个health通过后打开8501。启动器将打印准确API/UI/日志路径。
2. 上传LoCoMo原始conversation格式JSON，填写真实版本和许可；`tests/browser/sample.json`为公开合成输入。原始QA不会进入抽取输入。
3. 选择对话，显式创建Build。真实Build需要准备好的Embedding缓存及自己授权的DeepSeek；本次不提供免费真实生成承诺。
4. 完成抽取、Index、关系、Projection和publish后选择固定Build。未complete的版本可检查进度，不能作为完整QA库。
5. 查看Memory/source、历史状态、可选Graph。Graph结构边仅表示归属/来源，四类关系边保留理由、源轮次及适用条件。
6. 提交英文Question；默认Hybrid，Dynamic显式选择。日期不代表观测超出对话结束后的现实。
7. 展开citation读取原Source Turn；通过Trace ID取成功/失败记录。不要把运行失败解释为没有证据。
8. 下载`memory-export-v2`；评测页读取已有Run/报告。新增评测是显式收费操作，本次验收不执行。

HTTP合约在`/docs`；常用只读路由：`GET /health`、`/datasets`、`/builds`、`/builds/{id}/memories`、`/builds/{id}/current-state`、`/builds/{id}/relations`、`/builds/{id}/export`、`/queries/{trace_id}`、`/evaluation-runs/{id}`（准确命名以OpenAPI为准）。`POST /queries`是真实生成入口，切勿用它做免费离线演练。

## 独立只读演示

`scripts/personal-release replay-offline-demo`使用独立FastAPI和Streamlit，完全不创建Database、DeepSeekModel或Embedder。页面所有控件只读取本地固定fixture；GET API和download不产生生成任务。默认不访问互联网，Browser实测拦截外域、无外域请求。

固定顺序：Build → Memory → Projection/历史/关系 → Graph checkbox → Source Turn → Current/Historical/Failed Trace → 冻结E汇总 → 可逆分组 → JSON下载。
Synthetic回答来自MockTransport冻结fixture，不是模型分数。Real Experimental Result表明确绑定旧producer，当前Release修复没有新QA测量。

真实六份导出使用README的`--manifest/--directory`；API `/catalog`和UI共用同目录与SHA校验。不会导入SQLite或更改Build。没有预录问答时显示“不会创建新回答”。

## 验收命令与数据边界

```sh
uv run --locked python -m compileall -q src tools scripts tests
uv lock --check
bash -n scripts/personal-release tests/browser/run.sh
git diff --check
scripts/personal-release run-tests
uv run --locked pytest -q tests/release tests/test_m5_*.py -m 'not live_model and not local_embedding'
```

工程全仓适用测试在合法含数据工作树运行；默认不付费。标记`live_model`和`local_embedding`的4项显式排除，不冒充运行。
公开包不含官方conversation/QA，受控数据依赖测试需明确标记并在公开包运行`scripts/personal-release run-tests --public`（明确排除controlled_data）；其数量和结果见ACCEPTANCE，不能用公开子集替代工作树全仓结果。

真实MiniLM opt-in（本地不联网，无收费模型）：`LOCOMO_LOCAL_EMBEDDING=1 HF_HUB_OFFLINE=1 uv run --locked --extra embedding pytest -q -m local_embedding`。未运行就标未运行。
浏览器单独环境安装Playwright，使用自己的`playwright install chromium`或`LOCOMO_CHROMIUM_EXECUTABLE`显式指向已安装Chromium，不使用个人登录profile。新增离线脚本：`<browser-python> tests/browser/personal_replay.py --output /absolute/path/to/evidence`；正常App的合成全流程：`bash tests/browser/run.sh <browser-python>`。均为受控合成外部适配器，不是真模型成绩。

## 故障与恢复

- 端口占用：使用另一组端口；不自动kill未知进程。服务任一退出会停止另一服务并返回非零。
- 缺Embedding：doctor报告未安装/未缓存；只读Replay仍可运行。
- 缺/损坏JSON、错误SHA/Build/Source/time：只读入口拒绝，保留原件。不要修写旧SHA。
- 缺数据：官方导入明确返回invalid_official_data；可上传合成或合法副本。
- 错来源ID：404/422，失败Trace可检查；不猜测修复来源。
- SQLite异常：用另一个新DB做演练或恢复用户确认的备份；不删除研究SQLite。
- 历史一次性实验仅验SHA/结构，绝不调用execute/prepare/runner；预算余量不是授权。
