# 个人Release代码血缘

生产基线915fac02f6b9296e331f913a1e78717cfa7e2df1是最终M5 28ce63d73d6736c7812aa0be4425a0d9650dd09e的祖先；本Release沿用已有codex/m5-release-integration-20261105，未新建worktree/修改main/重写历史。

RELEASE_COMMIT_MAP.json逐一列出生产→M5全部commit、当前src/tools每文件最后M5来源commit及Release改动标记/SHA，包含各开发分支HEAD。与当前最终HEAD的差异可用`git log --reverse 28ce63d..HEAD`及`git diff --stat 28ce63d HEAD`核验。

| 层 | 来源 | 集成范围 | 最终默认 |
|---|---|---|---|
| 核心导入/Build/检索/关系/QA/API/UI/评测 | production915fac0→M5完整祖先链→28ce63d | src/locomo_memory；逐文件源commit见JSON | 既有能力，公共Hybrid默认适配单列 |
| 四类Bonus/开发与E工具 | M5 development/input/build/completion/conv44 branches，最终已汇入28ce63d | m5_*.py、tools/m5、tests/test_m5_*、experiments/m5-development、docs/m5-development | A保留；其余可选展示/研究，QA新机制默认关 |
| 个人研究附录 | docs/experiment-supplement@3392faf | 仅docs/supplement/**，Git对象逐文件拷贝 | 文档，无运行副作用 |
| 历史研究E0–E19 | research-process-archive@3e64811、research-next@97bfaaa及本地未提交证据 | 公开索引/附录/安全汇总；原始证据受控本地归档 | Hindsight/CE/PropMem未接默认 |
| Release增量 | codex/m5-release-integration-20261105增量提交 | public Hybrid adapter、只读viewer/replay、启动/验证/打包/归档工具、README及验收文档 | 明确公开默认与无key演示 |

冻结实验producer不是当前Release：E=0dbd98e7b296ef29d9998fa55d88d512f8ec85f1，82文件锁；原结果保持。Release公开请求默认/日期/Trace等修复只作工程回归，没有重评分、调参或新收费生成。数值仍绑定原Run/Build/锁，不用新commit冒充原实验代码。

未导入主仓36项dirty、未合PR38/39、未更改队友分支。新增源码默认不联网、不安装外部研究后端。uv.lock未改依赖；pytest加pythonpath和controlled_data标记以支持直接入口及公开包数据边界。
