## Summary

汇集 #15 及 #16–#21 的工程实现、查询质量迭代和实验记录，目标分支为 `main`。保留既有提交、失败记录及已撤回优化的 Revert，不恢复已撤回行为。

```text
公开评测入口
  固定开发计划、完整 Build 与运行身份
  Full Text / Vector / Hybrid / Dynamic / Dynamic + 原文兜底
  逐项持久化、显式恢复、失败分母及全部尝试用量
查询
  核心 Memory + 原始来源优先交付
  必要冲突端点保留、来源会话时间优先
  有界原文补查、先前支持保护、结构化失败备用
Streamlit
  简短答案、来源与解释、历史关系、保存的 Trace
```

#15 已 Superseded，#21 本轮全量实验取消，均以 not planned 关闭；原定757题、四策略3,028项未执行，不宣称原验收全部完成。#16–#19已分别工程结案；#20原固定预检仍有形式缺口，保持低优先级延期开放。本 PR 不自动关闭 #20。详见[范围结案](../../experiments/issue-15-closure/README.md)。

## Evidence

- **Before:** 正确 Memory 可因同键完整组超预算而未交付；原文补查可丢失先前支持，派生时间可覆盖原始表达。
  **After:** 预算边界、冲突双方、部分答案保留、有证据纠正、引用身份及相对时间回归覆盖这些路径；[修复与真实复验](../../experiments/issue-15-query-reliability/followup.md)保留成功与失败结果。
- **Before:** 评测整轮结束后保存、Full Text 受短预算截断，失败分母及未知结果不可充分核查。
  **After:** 固定版本的逐项保存与显式恢复，完整全文交付或明确超限失败，分类分母和全部可追溯尝试用量；见 [#17](../../experiments/issue-17-recovery-validation.md)、[#18](../../experiments/issue-18-full-text-validation.md)、[#19](../../experiments/issue-19-failure-report-validation.md)验证记录。
- 本次合并前全量非live回归 **405 passed、4 skipped**，361.51秒，1条既有Starlette/httpx弃用警告。编译`src tests experiments scripts`、浏览器runner语法、`git diff --check origin/main`通过；现有Chromium浏览器回归退出0，无pageerror/console error。见 [本次验证记录](issue-15-checks.json)。未新增付费调用。
- 为通过整个PR范围的CI空白检查，仅将3份历史CSV的CRLF改为LF、移除2份报告末尾空行；逐单元格与字节变换核对通过，实验内容及数值未变。
- [五策略展示](../../experiments/current-showcase/results/analysis.md)：20题×5策略100项均运行成功；16题F1依次为0.3490 / 0.4911 / 0.5124 / 0.5100 / 0.3997；4道对抗题各策略均拒答匹配。Dynamic有2题实际触发原文备用，不能作为关闭备用的纯消融。原文兜底未总体胜出。
- 同轮40题Recall@5/10/20为64.17% / 72.92% / 77.92%；10个动态场景、20条来源语义核验、5个真实Trace只读Web回放与截图已保存。新增307/420次调用，复用272条Memory和4,902条关系，Build未变。作者来源审阅不作为独立动态真值或泛化结论。

## Merge Danger

**Door:** two-way

建议以 merge commit 合并，保留本轮提交和 Revert 历史。回滚代码时保留实验数据库与报告，必要时恢复合并前数据库备份；旧版不承诺继续执行新版运行记录。新增表及唯一索引为增量初始化，无清库或重抽任务。

**Blast Radius:** pipeline

影响评测 API 的默认异步行为、持久化恢复、查询证据打包、Prompt/schema、时间解释、模型参数和现有 Streamlit 页面。默认最大输出8192，关系思考强度high、解析low，调用成本可能变化；没有把全部操作切到high。大部分文件增量是保留的实验材料，不新增生产依赖。

作者合并前检查不替代非作者复核。当前没有关联的可更新Notion记录或可用Notion工具，Notion未同步；不标为完成。
