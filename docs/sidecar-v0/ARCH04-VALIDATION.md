# ARCH04 验证记录

日期：2026-11-03。

## 已观察证据
- 用户 Windows ARCH01：42 passed，0.14s。
- 用户 Windows ARCH02：107 passed，1.81s；16 cases、1 rejected、input_unchanged=true、provider_calls=0。
- 用户 Windows ARCH03：144 passed，2.58s；15 compared、1 contract_rejected，response_unchanged_all、references_valid_all、input_unchanged 均为 true，provider_calls=0。
- 本次 Linux Python 3.12 环境运行六个 Sidecar 测试文件：145 passed，1 warning。最终重新运行：145 passed，1 warning，1.12s。
- ARCH04 CLI：2个合成完整 Build，所有检查通过，无外部模型调用；数据库与导出摘要不变、原响应身份不变、关闭恢复、来源/Build身份保留。详见 ARCH04-compatibility/。

警告为现有 Starlette TestClient/httpx 弃用提示，不作为已修复项。没有运行整个仓库全量测试，没有新增付费模型实验，没有确认真实历史 Build 兼容性或真实模型准确率。Windows 原提交定向测试 145 passed，1 warning，2.48s；两个合成 Build 兼容检查通过，外部模型调用 0，临时数据库已清理。

## 复核问题修复（2026-11-06）

- 对照复核记录 HEAD `0f470a3b3aac782b42b082b199e2fa81a12cf837`、merge-base `4d1d072f2c7075ebcac10879269bdcfd736e683b`，在本地交付快照上验证修订。远端修订后的 HEAD 和 CI 待上传后确认。
- 规则版本 `deterministic-sidecar-v0.3`。新增 14 个回归参数用例，覆盖事件对象、极性、阶段和日期错配，时间限定词丢失、历史日期回退，以及搬家正反来源顺序。原 16 个冻结案例及其校验值保留。
- Linux / Python 3.12.14，六个 Sidecar 定向测试文件：159 passed，1 warning。
- 同一环境运行公开离线入口 `tools/team_v2/check.py -q --tb=short`：1 failed, 906 passed, 8 deselected, 1 warning in 131.63s (0:02:11)。按入口规则排除了受限历史材料和 live/local embedding 等用例。首次失败项为既有 Streamlit 界面测试超过 3 秒时限。同一用例单独复跑：1 passed, 1 warning in 1.13s。
- 兼容 CLI：两个合成 Build 通过，外部模型调用 0，临时数据库已清理。合成对照：16 个案例，15 个完成比较，1 个按契约拒绝；原响应、来源引用和输入检查通过，外部模型调用 0。
- ARCH01–03 示例与历史测试记录为原交付结果。ARCH02 文件摘要中的代码和测试条目已刷新为修订版本。
- 继续保留 Draft，等待真实成员复核修订后的 HEAD、负责人确认 ADR 和真实历史 Build 验证。本轮核验真实历史 Build 数量为 0。
