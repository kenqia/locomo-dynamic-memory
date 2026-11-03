# ARCH-03 固定合成案例的诊断对照

两种方式：control仅检查输入已有字段；sidecar执行ARCH-02的时间、事件和有限问题诊断。control不是生产QA基线；本次不评模型质量，不生成最终答案。

环境：Linux / Python 3.12.14。案例16个，比较15个，契约拒绝1个。

输入未变：True；回滚原响应未变：True；引用闭合：True；provider calls：0。

每个有效案例每方式重复20次，先各预热1次，交替顺序。

本机平均额外wall：196770.78 ns；平均额外CPU：197069.72333333333 ns。

只测函数体；校验、序列化、文件I/O和哈希在计时外。不等同用户请求时延，不承诺其他机器同数值；负差值保留，不解释为稳定提速。

| 案例 | control | sidecar | 额外wall中位差 ns |
| --- | --- | --- | --- |
| ARCH01-01 | 保留输入字段；无新增推断 | links=same_event | 198811.5 |
| ARCH01-02 | 保留输入字段；无新增推断 | links=different_event | 342613.0 |
| ARCH01-03 | 保留输入字段；无新增推断 | time=known | 95480.0 |
| ARCH01-04 | 保留输入字段；无新增推断 | time=known | 64180.5 |
| ARCH01-05 | 保留输入字段；无新增推断 | time=unknown | 57079.5 |
| ARCH01-06 | 保留输入字段；无新增推断 | time=range | 51764.5 |
| ARCH01-07 | 保留输入字段；无新增推断 | time=unknown | 48197.5 |
| ARCH01-08 | 保留输入字段；无新增推断 | time=known | 60987.0 |
| ARCH01-09 | 保留输入字段；无新增推断 | time=unknown | 41699.0 |
| ARCH01-10 | 保留输入字段；无新增推断 | time=unknown | 54881.0 |
| ARCH01-11 | 保留输入字段；无新增推断 | query=sufficient / Rome | 206090.5 |
| ARCH01-12 | 保留输入字段；无新增推断 | query=sufficient / Paris | 204677.0 |
| ARCH01-13 | 保留输入字段；无新增推断 | query=conflict | 239823.5 |
| ARCH01-14 | 保留输入字段；无新增推断 | query=insufficient | 9893.5 |
| ARCH01-15 | 输入非法 | 按契约拒绝 | 不计时 |
| ARCH01-16 | 保留输入字段；无新增推断 | links=unknown | 236399.0 |

完整输入、两种输出、source/memory身份、逐例CPU/wall与off→on→off记录见同目录comparison.json。
未把冻结预期当作推断输入，也未计算正确率；先前ARCH-02语义测试另行报告。非作者成员复核与生产Query接入仍未完成。
