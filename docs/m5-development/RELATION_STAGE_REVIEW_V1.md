# 留出索引与关系阶段独立代码复核 v1

结论：本次明确审查范围内 **P0/P1/P2 findings 均为 0**。未发现授权检查、预算硬限制、冻结契约、副本隔离或禁止自动重复执行的阻断问题。新鲜离线定向验证 `28 passed`。此结论仅为工具代码复核，不代表已批准付费阶段、真实关系质量、发布或总目标验收。

审查日期：2026-11-04。审查者：`final_code_review_v6` 非作者子代理。工作树为 `/home/kenqia/my_folder/locomo-worktrees/m5-final-development-20261104`，审查时 HEAD 为 `6044b709636e6860e295991a568229b87b698590`，新增工具及测试尚未提交。报告沿用已读取的 `google-developer-docs` 技能。

## 范围与代码身份

实际逐行读取：`tools/m5/holdout_index.py`、`tools/m5/holdout_relations.py`、`tests/test_m5_holdout_relations.py`。同时读取相关 `Settings`、`BuildService`、`RetrievalService`、`MiniLMEmbedder`、`VersionsService`、`RelationService`、`RelationAttempts`、`BudgetTransport`、数据库后端独占锁、逻辑快照及排他写入实现，并核对 `docs/m5-development/HOLDOUT_RELATIONS.md` 和公开准备摘要。

| 文件 | 审查时 SHA256 |
| --- | --- |
| `tools/m5/holdout_index.py` | `344b320970bd947f217189820c9bd421999775618dc083daf42b53e339e3c9c2` |
| `tools/m5/holdout_relations.py` | `960de2683e341966e13217a1a07ef4ef5a1b1e0dada840822f0d32e2865ae5d7` |
| `tests/test_m5_holdout_relations.py` | `33e67116766730d4d139d9a26eeca4325bf36a5287a1c1d02330476c78b30a24` |
| `src/locomo_memory/m5_budget.py` | `1734357d07b1fc932e078ca1f5a15cf3f08fddd02a588b2bf55d93d9ac13f0ee` |
| `src/locomo_memory/model.py` | `394f1bb436620bf9e63311dca4d83f6dd6e33ee12f28d0e7caf084490c1818de` |
| `src/locomo_memory/relations.py` | `7f909ce169756c70d9f4415811e1436518a5e6c61b4e47e4fe50f9b63b9ac7a6` |
| `src/locomo_memory/relation_diagnostics.py` | `1778028ded92529eb6501e8ef49bd21aca6a99187097094f5d647f0e701bf4ea` |
| `src/locomo_memory/retrieval.py` | `743adc94ce4458eaaf2398419df7b8978cbe0931e84e0302532cecafe364efd1` |
| `src/locomo_memory/builds.py` | `7279575b2c5aaedd6a716f3f20fa07b3d1adb5c596cc917916f30b74dcc89b53` |
| `src/locomo_memory/database.py` | `79669243905c25ce724c8b361a2289fb18dcb3db79644b19fd7197468a6a9086` |
| `tools/m5/extraction_recovery.py` | `439ade803fc1894c6c48ae4b20df3032b2fa44a6e7c823dc950ec959a1641260` |
| `tools/m5/offline.py` | `e1f7914d7ad764668259bdc520eb7ddff7401c0243bd437a57990fd00eb1ec63` |

## 行为核对

**授权。** `holdout_relations.execute` 在建立 HTTP transport 之前读取明确授权文件，精确匹配 `approved`、scope、Build ID、完整 policy 与计划 SHA。`authorization(output)` 只返回所需结构，不创建授权文件，也不证明聊天批准。缺少文件和错误授权均在创建启动标记前拒绝。实际人工授权仍是外部前提，不能由当前或历史抽取授权推断。

**冻结契约。** `prepare` 复制源 SQLite，保留冻结 Settings 的 `db_path`，用显式 `Database(target)` 路由本阶段存储。索引与关系准备均继续调用生产 `require_current_contract`，未重写 Build 指纹。关系执行核对 Settings SHA、本脚本 SHA、所有本地顶层生产 Python 模块及快照依赖脚本的 SHA，核对准备数据库/账本的逻辑快照，然后检查目标 Build 的 `conv-43/queued/relations` 状态、任务数量及任务内容摘要。生产模块集合新增、缺失或内容变化也会使字典比较失败。

**隔离。** SQLite 源通过 `mode=ro` 打开，backup 包含已提交 WAL。写入限定于新建输出目录的副本；源 Settings 中的路径只作为冻结契约保留。所审调用方的持久操作均使用显式传入的 Database，未按 `settings.db_path` 重新打开原库。关系准备限定副本内两份 Build 分别为 `conv-43/indexed` 和 `conv-44/failed`；执行只运行计划绑定的 conv-43。成功结果只到 `related`，没有调用 publish 或 query。索引完成仍显式验证版本 pin 拒绝未完成 Build。

**预算。** policy 要求 `deepseek-flash`、relation thinking `high`、每任务 3 次尝试、每请求 160,000 输入消息 UTF-8 bytes 和 32,768 输出 tokens。预算计算使用 Decimal，400 任务对应 1,200 次、USD104.7859200 的保守预约上界。生产 transport 在 SQLite `BEGIN IMMEDIATE` 内检查并预约共享次数和金额，再调用 delegate；重试反馈也经过相同输入上限检查。底层 `HTTPTransport(retries=0)`，未知传输保留预约，不自动退款。此次独立账本不修改或复用旧抽取账本。该金额上界依赖计划声明的价格假设，启动前价格核对属于文档明确的外部执行步骤，本复核未验证实时价格。

**禁止自动重复与失败持久化。** 执行取得目标数据库的后端独占锁后，使用 `open('x')` 创建一次性标记。两次竞争执行不能都通过该标记；进程崩溃后标记仍在，工具拒绝自动重跑。普通无效输出由生产关系路径保存 task、logical attempt、provider 检查点和 Build 失败，工具写 `outcome.json` 后以 `relation_stage_incomplete_no_automatic_retry` 报错。致命退出可能没有 outcome，但已有账本、检查点及启动标记保留；本工具不自动调用恢复。明确本地预算拒绝会清除未发送的临时检查点，先前真实物理调用不被删除。

## 新鲜验证

实际运行已有离线入口：

```sh
./tools/integration/check.sh tests/test_m5_holdout_relations.py tests/test_relation_diagnostics.py tests/test_m5_budget.py -q
```

结果：`28 passed, 1 warning in 26.97s`。唯一 warning 为既有 Starlette/TestClient 使用 `httpx` 的弃用提示。

实际测试覆盖：synthetic 副本关系成功及 conv-44/源库不变、无发布、重复执行拒绝、全部输出无效时恰好耗尽 6 次上界且持久失败、缺失/不匹配授权、数据库/账本/配置/producer 变化、竞争后端、共享预算并发争用、未知费用保守保留，以及关系检查点在发送前/响应后/先失败再退出等崩溃点的重启行为。新阶段测试全部使用 synthetic 数据和 MockTransport，未使用真实 holdout 数据执行 execute。

## 限制与剩余验证范围

本次没有运行真实 `holdout_relations.execute`、真实模型请求、真实关系评分、holdout QA、索引/关系发布或远端写入。没有读取密钥、留出 QA/evidence/answers；没有修改源码、工具、授权文件或冻结计划，仅新增本报告。

`holdout_index.run` 经过源码及生产调用方审查，但本次未重新运行真实 MiniLM，也没有新增其专用测试。公开已有真实缓存索引结果属于父任务证据，不能写成本审查者独立复跑。当前默认 Settings 的 `embedding_local_files_only=True`；文档要求相同离线环境，不将任意外部改写 Settings 下的行为外推为已验证。

现有崩溃测试覆盖生产关系诊断；新增阶段自身尚无单独 subprocess 崩溃注入测试。其“一次性标记先于付费请求”的顺序已实际阅读源码，正常重复和竞争锁由定向测试覆盖。未验证掉电级文件系统持久性、跨磁盘事务或所有不遵守后端锁协议的外部 SQLite 写入者。

真实阶段仍为准备状态，执行需要用户对该阶段范围与上界的明确批准。代码复核不能替代该批准，也不能证明真实关系语义正确或总任务已完成。
