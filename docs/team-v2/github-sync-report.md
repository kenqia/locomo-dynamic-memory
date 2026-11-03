# GitHub 同步审查记录

核验日期：2026-11-03，仓库 `kenqia/locomo-dynamic-memory` 为 PUBLIC，默认 main 未改动。此提交先记录本地审查；最终远端 SHA、CI 和干净 clone 结果将在推送后写入本页及 remote-verification.json，不据本页的本地结果宣称远端已通过。

## 安全基线与原历史

原 Production `915fac02f6b9296e331f913a1e78717cfa7e2df1` 与 Research `f41c94b79d0d59a81a1a26ac343ac82420560898` 包含封存作者映射，禁止直接 push。Production 安全根快照 `f4d36c7aacf74c8a58d69fb2c14231f019f813bf`；Research 安全子快照 `18b03904d1d8878c29f07f8c5ea66300f3c101a9`。它们仅导出白名单代码及必要文本，不继承未发布的受控历史。

原 main 与所有旧分支保留；安全根与旧 main 无共同祖先，本轮不强推、不合入 main。集成时基于安全 Production 分支审查实际 feature commits，必要时只 cherry-pick 经审查的增量，不合并原研究历史。代码来源和 SHA256 见 source-manifest.json。

## 已审范围与 HOLD/DENY

允许发布：`src/`、测试代码及合成 fixture、工具源码、必要 app/agent/ADR 文本、锁文件与无凭据示例、经过审查的任务书文本、协作文档、脱敏聚合。新增协作文件仅限 `README.md`、`.github/`、`docs/team-v2/`、`tools/team_v2/`。

DENY：真实凭据、原始 provider wire、sealed/author-only 评审映射、私有会话。HOLD：运行时 SQLite/缓存/账本/活动报告、未审历史实验输出、课程原件/ZIP/媒体、个人资料和版权不明内容。原公开 main 中的历史课程资产未在本轮再次发布或清理，可见性保持 PUBLIC；不能认为已有 PUBLIC 等于已完成许可复核。

已导出文件经高置信凭据格式、字面 key、禁止资产路径和 2 MB 大小闸门扫描，未发现阻断项。扫描只能提供有限证据，不代替成员内容复核。原 ZIP 保留本地；公开任务书只替换本机路径，并记录用户分配覆盖自由认领规则。

## 本地保护与恢复

受控归档 ID：`20261103-six-day-kickoff`。已存可恢复 Git bundle、三工作树 status/patch、2,856 个未提交文件归档与逐文件 SHA256；归档成员重新读取校验，0 哈希不符。22 个运行时/敏感路径单列保留，未复制 live DB。原 `20261101-pre-v2-cleanup` 和 Phase3 归档保留。不要将这些备份上传 PUBLIC。

恢复必须在新目录执行：先 `git clone <受控目录>/refs-before.bundle <新恢复目录>`，检出所需 source SHA，再将对应 `*-changes.tar` 解包到新的隔离目录检查；严禁直接覆盖现有工作树。`working-files-manifest.json` 与 `BACKUP_SHA256SUMS` 验证内容。受控路径和运行时原件不在 Git bundle 内，不宣称完整磁盘备份。

## 验证与限制

Production 公开离线套件：583 passed /6 deselected；三个依赖官方语料/历史计划的测试模块未收集，不计通过；真实模型和本地模型检查禁用。Research 套件仍在执行。原完整套件首次发现缺少受控资料后中断，不能记为通过。公开入口 `uv run --locked python tools/team_v2/check.py -q --tb=short` 明确列出排除项。

离线合成 fixture 已生成完整 Build；API/UI 健康检查通过。Streamlit AppTest 经真实本机 HTTP API 验证当前/历史/冲突/不足四案例，异常为零，真实 provider 请求为零。不是完整浏览器验收或真实 QA 改善证明。完整浏览器 E2E、正式媒体打开/播放、两个成员的非作者复核仍待 D4–D6。

任务：#23/#24/#25 三父任务，#26–#37 十二子任务，原生子关联已核验；Owner 分别为 @Thorns-06/@xiaozhuozi39/@VanadisssSSS。milestone `v2-6day-demo` 为 11/08，具体冻结时刻看 Issue 正文。

未同步：Notion 无关联任务和可用访问工具，需负责人补录；微信仅准备私有通知稿，当前无发送接口。成员本人响应、非作者 Reviewer 与成员成果 PR 均待落实。
