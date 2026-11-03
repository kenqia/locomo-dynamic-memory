# ARCH04 验证记录

日期：2026-11-03。

## 已观察证据
- 用户 Windows ARCH01：42 passed，0.14s。
- 用户 Windows ARCH02：107 passed，1.81s；16 cases、1 rejected、input_unchanged=true、provider_calls=0。
- 用户 Windows ARCH03：144 passed，2.58s；15 compared、1 contract_rejected，response_unchanged_all、references_valid_all、input_unchanged 均为 true，provider_calls=0。
- 本次 Linux Python 3.12 环境运行六个 Sidecar 测试文件：145 passed，1 warning。最终重新运行：145 passed，1 warning，1.12s。
- ARCH04 CLI：2个合成完整 Build，所有检查通过，无外部模型调用；数据库与导出摘要不变、原响应身份不变、关闭恢复、来源/Build身份保留。详见 ARCH04-compatibility/。

警告为现有 Starlette TestClient/httpx 弃用提示，不作为已修复项。没有运行整个仓库全量测试，没有新增付费模型实验，没有确认真实历史 Build 兼容性或真实模型准确率。

## ARCH04 Windows 本地验证

日期：2026-11-03。

- 六个 Sidecar 测试文件：145 passed，1 warning，2.48s。
- 兼容检查：fixtures=2，all_passed=true。
- external_provider_calls=0。
- temporary_databases_removed=true。
- real_historical_builds_checked=0。

以上为两个合成完整 Build 的兼容性验证，不代表真实历史
Build 已验收，也不代表真实模型问答质量提升。
真实成员复核与负责人确认仍待完成。