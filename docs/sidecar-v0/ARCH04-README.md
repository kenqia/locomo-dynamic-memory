# ARCH04 / #33：兼容性、ADR 与交接

这是第四个增量包。先保留 ARCH01、ARCH02、ARCH03，再将本包 tools、tests、docs 合并复制到项目根目录；不要用整个目录替换已有目录。本包不修改生产代码、默认配置或旧测试。

## Windows 本地验证
在包含 pyproject.toml 的项目根目录执行：

```bat
uv run --locked python -m pytest tests/test_sidecar_schema.py tests/test_sidecar_core.py tests/test_sidecar_io.py tests/test_sidecar_research.py tests/test_sidecar_compare.py tests/test_sidecar_release.py -q --tb=short
uv run --locked python -m tools.research_v2.sidecar_compatibility --output var/sidecar-arch04/compat-v1
```

输出目录必须不存在。重跑请改为 compat-v2，避免覆盖证据。兼容脚本只新建临时测试数据库并清理，不读取活动数据库；构建与嵌入均为受控模拟，无真实模型调用。

## 应观察到
测试数量参考145，若本地有不同结果保留实际输出。CLI应显示 fixtures=2、all_passed=true、external_provider_calls=0、real_historical_builds_checked=0、temporary_databases_removed=true。打开新目录中的 compatibility.md 与 compatibility.json 检查两份 Build 各项检查，不能只看汇总。

## 交付与未完成项
ADR 见 docs/adr/0003-temporal-event-sidecar.md；算法、验证记录、复核清单和 PR 草稿与本文件同目录。所有案例和兼容证据均为合成诊断，不能称真实模型成绩。真实历史 Build 验证、负责人语义确认、真实成员复核与 PR 尚待完成，不能据此宣称 #33 已验收。

## 产品交接与回滚
A 可读取 ARCH02-example 或本目录 PRODUCT-EXAMPLE.json，在独立诊断区展示来源、时间、unknown；保持正式答案与原证据字段不变。示例不是前端已接入证明。
回滚时先移除调用方的显式 enabled=True 或关闭研究开关；原回答路径不变。独立诊断输出可删除。若要撤销整个增量，只移除交付清单列出的新增文件，不删除已有仓库文件，不迁移或回写活动数据库。
