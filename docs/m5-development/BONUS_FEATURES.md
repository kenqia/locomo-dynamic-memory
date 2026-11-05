# Bonus 能力状态

各列含义独立：实现不等于收益，演示就绪不等于生产采用。当前均未合并main。

| Bonus | IMPLEMENTED | TESTED | EXPERIMENTALLY_BENEFICIAL | DEMO_READY | PRODUCTION_ELIGIBLE |
| --- | --- | --- | --- | --- | --- |
| A 复杂状态/版本/来源 | 生产基础+新增只读timeline | 原关系/时间测试与Browser | 新QA收益未测 | 合成边界与真实conv-26 Browser均通过 | 既有生产能力保持；新面板待最终验收 |
| B Graph浏览 | 是，来源/边/Build可追溯 | HTTP+Browser+契约 | 不以QA收益验收浏览 | 合成及真实conv-26 Browser通过 | 可作为可关闭展示候选 |
| B 多跳检索 | 是，真实两跳路径及后续Resolution接口 | 合成端到端+757离线 | 否；最终来源覆盖无增益 | 可演示机制，不能宣称有效推理 | 默认关闭 |
| C 可逆分组 | 文件包与真实wire可选适配器 | 全字段roundtrip、HTTP、757消息回放 | 仅极小token代理节省；QA未测 | 适合展开/来源演示 | 默认关闭 |
| D 自适应 | 现有候选优先级+按问题关系扩展 | 合成端到端+757 | 否；来源交付退化 | 研究接口可运行 | 拒绝默认启用 |
| D 时间增强 | 单日/相对时间/未知区间软优先 | 合成+原解析回归+757 | 无新增来源代理收益 | 工程机制可展示 | 默认关闭，保留原时间能力 |

Graph/压缩API由显式bonus URL访问，Streamlit图浏览checkbox默认false。问答策略默认仍为原Dynamic，不自动调用研究入口。JSON统一导出契约没有新增Bonus字段，图/压缩另有命名空间工件。
