# Demo 环境与模式说明（交 @VanadisssSSS，Issue #36）

版本：main `5519dd2`（PR #41 合并后，CI run 42582449214 success）。录制前请在自己的 clone 执行 `git rev-parse HEAD` 并把结果填入 `Recording_Checklist.md`。若负责人之后打最终 tag，以 tag 指向的 SHA 为准重新确认。

## 1. 推荐模式：OFFLINE SYNTHETIC REPLAY（主体）

```bash
git fetch origin && git checkout 5519dd2
uv sync --locked --python 3.12
uv run --locked python tools/team_v2/demo.py replay --ui-port 18501
```

浏览器打开 `http://127.0.0.1:18501`。
- 读取 `demo_fixture/product-v1/` 中经 SHA 校验的公开合成快照；**无 API、无数据库、无模型调用、无需 key**。
- 2 个 Build、6 个案例：当前事实 / 历史日期 / 证据冲突 / 证据不足 / 引用异常 / 预算失败。
- 数据是项目原创的合成对话（Alex、Sam），CC0；不含 LoCoMo 原文。
- Experiments 页显示的是 **E12 历史 757 题 Run**（Run `a2abe1fb…`，3,028 组合），**不是** E25 留出结果。旁白必须这样说。
- 本机已在 1920×1080 下实际跑通并截图（`var/m5-final-screens-1920/`），五个页面均正常渲染。

Windows：`.\.venv\Scripts\python.exe tools/team_v2/demo.py replay`（README 原文命令）。

## 2. 可选：原五阶段工作流（合成 API，仍为离线）

```bash
uv run --locked python tools/team_v2/demo.py prepare --output var/demo-rec-01
uv run --locked python tools/team_v2/demo.py api --output var/demo-rec-01     # 终端 1
uv run --locked python tools/team_v2/demo.py ui  --output var/demo-rec-01     # 终端 2
```

使用 MockTransport 合成模型，0 次 provider 调用。可展示"导入→构建→问答"的真实界面操作，但回答是预设合成结果，**仍属于 OFFLINE**，不可称 LIVE。每次录制换新的 `--output` 目录。

## 3. LIVE MODEL CALL（不推荐今晚录）

Console 本身是只读的：Query 页只读取已保存的 Trace，**不会发起新问答**。真实模型问答只能通过顶部"五阶段工作流"开关进入原 `ui.py`，需要：
- 本机 DeepSeek key（按 `docs/agents/local-credentials.md`，不得出现在画面里），
- 一个用合法数据完成的真实 Build（需本地 MiniLM 缓存；构建本身会收费），
- 负责人对付费调用的明确授权。

如果确实要录 LIVE 片段：只录 1 次 Hybrid 问答，画面角标 "LIVE MODEL CALL · deepseek-flash"，并把 Trace ID 与时间记入检查表。否则全片只用 OFFLINE，并在片头和角标上写明。

## 4. 技术限制（录制时要注意）

| 限制 | 影响 | 处理 |
|---|---|---|
| Streamlit 每次点击后会重新渲染，约 1–2 s | 画面短暂变灰 | 等右上角运行指示消失后再进行下一步操作 |
| 来源原文是英文，界面是中文 | 观众可能看不清 | 鼠标停在原文上 2 s，字幕给中文意思 |
| "视图设置 → 评审者"会展开全部字段 | 画面过长 | 主体用"展示者"，只在 Trace 段切到"评审者"一次 |
| 预算失败案例显示错误 | 这是预期行为 | 旁白说明"失败被保留，而不是当成空结果" |
| Experiments 页是 E12 历史数据 | 容易误说成最终结果 | 旁白照脚本读；E25 结果用报告图 F7（标注"报告图表"） |
| 端口占用 | 启动失败 | 改 `--ui-port 18511` |
