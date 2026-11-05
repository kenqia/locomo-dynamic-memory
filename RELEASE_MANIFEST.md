# M5 Personal Core Release — pending team integration

日期：2026-11-05（北京时间）。个人核心交付候选，独立于队友Product、Architecture、Delivery及课程平台提交。

当前结论：**PERSONAL_READY（仅本地个人交付候选，pending team integration）**。固定应用截点全仓991项、独立公开包937项均通过，普通Web与无凭据Replay浏览器验收通过；没有未解决P0。最终封包身份和非作者核验绑定在staging的`FINAL_ACCEPTANCE_RECEIPT.json`。没有新增付费请求、重新评分或覆盖历史实验。

## 版本身份与范围

- 分支：`codex/m5-release-integration-20261105`，工作树：`/home/kenqia/my_folder/locomo-worktrees/m5-release-integration-20261105`。
- M5基础：`28ce63d73d6736c7812aa0be4425a0d9650dd09e`；其祖先生产基线：`915fac02f6b9296e331f913a1e78717cfa7e2df1`。
- 最终可执行代码/测试截点：`c7eae7a2f4ed667e83f2520e000e33aee7314e2b`。随后文档/验证记录提交不替换此测试身份；封装commit见交付manifest，最终Git HEAD由提交后回执给出。
- 附录：只导入`docs/experiment-supplement@3392faf:docs/supplement/**`，保留原字节，独立勘误。
- 来源与文件SHA：[血缘](RELEASE_CODE_LINEAGE.md)、[提交映射](RELEASE_COMMIT_MAP.json)、[组件覆盖表](RELEASE_COMPONENT_MATRIX.md)。未整体搬入主仓36项dirty，未修改main或合并PR38/39。

## 运行与交付入口

在本工作树根目录执行：

```sh
uv sync --locked --python 3.12
scripts/personal-release doctor
scripts/personal-release start
# 无key演示单独执行：
scripts/personal-release replay-offline-demo
```

普通API/UI：8000/8501；独立只读Replay：18010/18510，均绑定127.0.0.1。具体路径、健康、导入、Build、Memory、Source、Trace、评测、下载和故障处理见[README](README.md)及[RUNBOOK](docs/release/RUNBOOK.md)。启动器安全停止自有服务，保留数据库。

公共QA默认Hybrid；Dynamic显式可选。历史关系/版本保留。Graph浏览可选，Graph两跳、compression wire、adaptive及temporal新增软优先默认关闭。[默认变更与回滚](docs/release/DEFAULTS_AND_ROLLBACK.md)包含实际修改和恢复方式。四类Bonus均有实现与工程测试，不能据此宣称QA收益已证实。

## 数据、实验与归档

- 六份完整MemoryExport v2：2,031 Memory、37,445关系、1,465引用Source Turn、39,771,212bytes，SHA/Build/Index/Projection/来源/时间校验见[six manifest](six-memory-exports-manifest.json)与[实际结果](experiments/personal-release/six-exports-validation.json)。完整副本仅本机受控`/home/kenqia/my_folder/locomo-private-delivery/m5-personal-candidate-20261105/memory-exports/`。
- 公开包只含代码、锁、Schema/清单/哈希、合成Replay、公共汇总、附录和测试；许可、受控接收者及课程渠道未确认，完整原文/Memory不公开。
- Level E完整400双臂、失败保留：类1–4每臂301题，H=.402606、D=.409151，差值区间跨零。类别5是字面拒答。新Release修复没有新的模型成绩。见[个人摘要](PERSONAL_EXPERIMENT_SUMMARY.md)。
- 37页附录实际重建、文本一致、20图和字体/版面检查；原PDF保留，元数据差异及数值/措辞勘误见[附录核验](docs/release/SUPPLEMENT_ERRATA.md)。非作者282数值核对0差异，历史原始真值不补造。
- E0–E25可定位索引：[实验档案](EXPERIMENT_ARCHIVE_INDEX.md)。主档2,301,324,861bytes/35,440成员；源码补档5,880,956bytes/2,446成员，完整逐成员SHA和恢复验证受控保存。[归档与清理计划](LOCAL_ARCHIVE_AND_CLEANUP_PLAN.md)记录排除边界，历史删除0。

## 验收及尚存团队依赖

实际通过/失败/跳过/未测量边界见[验收](docs/release/ACCEPTANCE.md)及[16项对抗审查](docs/release/ADVERSARIAL_REVIEW.md)。公开包位置、体积、SHA和封装source commit见`deliverables/m5-personal-candidate/public-package-manifest.json`；tar仅本地，不进入Git。原冻结结果producer与Release工程身份严格分开。

没有推送个人分支或创建Draft PR：既有Git历史含受控原文，当前公开tar扫描不证明整条分支可公开。保留本地可审查增量commit。远端发布和数据披露仍需确认目标/渠道；没有自动合main、提交课程平台或变更队友Issue。

Product仍需完成/提供#26–29页面与浏览器证据；Architecture PR38语义阻塞解决前不进入默认链，后续只允许opt-in Sidecar；Delivery仍需正式PPTX、MP4、团队总报告和单包规范核对。详见[团队接入契约](TEAM_INTEGRATION_HANDOFF.md)。缺本次Release关联Notion记录，未声称已同步，由负责人补录。
