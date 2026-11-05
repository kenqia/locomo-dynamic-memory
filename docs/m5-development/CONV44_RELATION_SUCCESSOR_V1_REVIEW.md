# conv-44 单任务恢复代码复核

2026-11-05（Asia/Shanghai）。两名非作者代理完成独立代码复核：Standards 0 项未决，Spec 0 项未决。根代理对冻结源码新鲜运行原恢复与新入口测试，54 passed，仅既有 Starlette 弃用提示。该结论不授权真实请求，也不证明剩余任务一定成功。

基线为 `dd0bb18014c87a2506773e987581f57a2dba8128`。新增实现为 `tools/m5/conv44_relation_successor.py`，SHA-256 `6afe3fb5a1094b4cb521fa6f05bcc3fa9d75a6173ec4fee46a28a8f375687464`；新增测试为 `tests/test_m5_conv44_relation_successor.py`，SHA-256 `21fe123ba9aedb8e4a6371b90574542a864c64515e559cde6acce399a44882e2`。旧阶段全部 producer 未修改，原关系85文件、恢复87文件及新入口88文件的实际 SHA 均匹配各自冻结计划。

## Standards

非作者 `/root/final_code_review_v6` 核验明确授权与排他 marker、目标数据库锁、SQL annotation gate 先于全库快照、所有旧行与调用前缀保护、独立硬限及 Unknown 完整预约、全部新生成 disabled、原 schema 和证据校验，以及只在另一副本完整化与三代来源记录。未发现已证实 P0–P2 问题。

该代理独立初跑新测试得到14 passed/1 fixture失败。失败因合成来源缺少 `text`，尚未进入预期 UPDATE 证据校验；作者补充合成文本后，代理只重跑该项，1 passed（0.03s）。此问题已关闭，不把该次重跑称为全15项新鲜通过。未修改作者代码、读取真实 QA/raw、实调或提交。

## Spec

非作者 `/root/level_e_spec` 静态核验任务书3.1/10及单任务恢复约束：只重试剩余logical2失败任务，logical3保留历史；独立3请求/USD0.2619648、旧额度不转移；逐标签矩阵直接调用原 `relation_label_error`，不修改响应、不放宽UPDATE或其他证据；副本严格导出绑定三代ledger/terminal/plan/wire及抽取继承，末尾再核源终态。未发现必要P级问题。

该代理未重复54项测试，未读取真实阶段数据库、QA或raw，未prepare、调用或修改文件。两轴均终读并确认上述最终源码和测试SHA。

## 验证

作者最终15项新鲜通过（37.56s）。根代理执行以下命令，54 passed（88.23s）：

```sh
./tools/integration/check.sh \
  tests/test_m5_conv44_relation_recovery.py \
  tests/test_m5_conv44_relation_successor.py -q
```

`git diff --check` 通过。测试均使用合成数据库与 MockTransport；真实计划另做零调用准备和非作者实际准备复核。未获新阶段授权前不得创建授权文件或启动模型；六份完整JSON、最终配置锁和Level E仍未完成。
