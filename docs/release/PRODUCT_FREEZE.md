# Product 冻结记录

日期：2026-11-09，Asia/Shanghai。负责人接受最新真人复核，并授权更新、整合 main、最终验证、同步 Notion 和冻结 Product。

## 冻结身份

| 对象 | 版本或记录 |
| --- | --- |
| 作者交付 | Thorns-06，PR #39，`0401155aa2c270c48b942e4b410a9f4b390156b3` |
| main 整合基准 | `ba349cf7a8b784ff6c739767ee392802055feff5` |
| 运行代码整合 | `4081ece0afecdc00c37c620140cf984963665ad6`；后续提交补文档、验证材料及 CI 解释器选择 |
| 真人非作者复核 | xiaozhuozi39，绑定0401155的[逐项记录](product-integration-20261109/Product-Human-Review-PR39.md)、[原回执](https://github.com/kenqia/locomo-dynamic-memory/pull/39#issuecomment-6734327474) |
| main 合并与 CI | [整合 PR #41](https://github.com/kenqia/locomo-dynamic-memory/pull/41)；以最新 head 的成功 checks 和 merged 状态确认 |
| 冻结标签 | `product-v2-final-20261109`，收尾时指向实际 main 整合提交；不移动既有标签 |

解析最终交付版本：

```sh
git fetch origin tag product-v2-final-20261109
git rev-parse 'product-v2-final-20261109^{commit}'
```

## 验证结果

- 本地完整公开回归：**1018 passed、28 deselected**，899.01秒；1条既有依赖弃用 warning。排除 live_model、local_embedding、controlled_data，排除项不计通过。
- Product 与 main 入口专项：27 passed；与完整回归有重叠，不累加为独立测试总量。
- Chromium：六案例/历史 Build/来源/异常 ID 恢复、完整分母/unknown/成本和实际无损导出通过。
- 布局：五页 × 两角色 × 三宽度共30场景通过；来源反复显示、字段默认折叠与实际滚轮11场景通过。
- 正常 Release 启动器：新合成数据库、四个已有 Trace 和原五阶段往返通过，实际模型调用0。
- 作者16份材料SHA匹配；公开清单校验通过。main六个核心入口/查询文件与ba349cf字节一致；两轴AI复查无未解决高可信问题，AI结论与真人记录分开。

新鲜聚合结果及代码指纹见[验证目录](product-integration-20261109/latest-validation/provenance.json)，详细过程及失败尝试见[整合验收](PRODUCT_INTEGRATION.md)。前两次CI因下载固定Python补丁版遇504，尚未进入测试；后续使用runner缓存Python 3.12，并记录实际版本，锁定依赖和全部质量门槛保留。

## 冻结范围

冻结六个Product模块、公开合成Replay及其测试/工具、正常启动器Console入口和对应证据。main最新时间范围/上下文/证据回归、公共Hybrid默认、原五阶段、M5/Bonus及独立MemoryExport Replay均保留。

Product冻结不表示Sidecar、Delivery正式PPTX/MP4、统一课程包或课程提交已验收完成。冻结后新增功能另开任务；发现阻断问题时用新提交修复、重验并建立新标签，不改写本标签身份。需要恢复旧入口可直接运行原`ui.py`；完整回滚采用本次整合提交的`git revert`，无数据库回迁。
