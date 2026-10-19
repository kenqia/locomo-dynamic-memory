## Summary

实现 Issue #4 及 #5–#12 的本地动态记忆应用。

```text
Streamlit → FastAPI → SQLite
  来源导入 → 原子 Memory → 混合检索 → 关系与状态投影
  完整版本固定 → 有效证据问答与 Trace → JSON 导出
  独立评测 → FullText / Vector / Hybrid / Dynamic 比较
```

Refs #4, #5, #6, #7, #8, #9, #10, #11, #12。
票据关闭需等待非作者复核及合并验证。

## Evidence

- **Before:** 已有批准的规格、票据和上游数据，缺少应用及测试入口。
  **After:** 来源、构建、检索、关系、问答、恢复、导出和评测均已实现；
  实际验证命令及结果见 `experiments/issue-4-implementation.md`。
- 真实离线 MiniLM 已验证编码、长度拒绝、混合检索和旧版本编码器选择。
  Chromium 已验证完整页面流程、失败重试、冲突、证据不足、下载和四策略评测。
- 未执行真实 DeepSeek 请求。课程六段对话、4/2 划分、动态真值未提供，
  正式指标保持 unavailable。未关联 M3/M4 Notion 任务，未宣称同步。

## Merge Danger

**Door:** two-way

回滚应用代码前停止 FastAPI 与 Streamlit，保留 SQLite 和导出文件。
旧完整版本继续通过其固定配置和编码器读取；本次不部署服务。

**Blast Radius:** local

显式构建和问答会调用生成模型。真实模型质量与课程验收需要另行验证。
