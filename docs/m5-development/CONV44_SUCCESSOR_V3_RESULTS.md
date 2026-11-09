# conv-44 successor v3 抽取终态

2026-11-04。用户回复“是”批准精确 plan 后，本阶段一次执行成功：首个请求通过严格抽取校验，ordinal 18 新增 9 条 Memory。新 Build `d9fb61417bb740e4b8eb34acb8652a46` 为 `extracted/extraction`，34/34 片段成功，共 392 条 Memory，其中 383 条继承、9 条新增。尚未索引、构建关系或完整导出，不能称第六份完整 JSON 已完成。

## 授权与执行

[明确授权](../../experiments/m5-development/conv44-successor-v3-authorization-v1.json)绑定 plan SHA `27fbb376bbd493c7911b55124c3a6e71930428fe86e10d65f1533af208114bbd`。执行前核对82个producer、入口、settings、继承sidecar、父终态及独立空账本。通过 Firecrawl 重新只读访问[官方价格页](https://api-docs.deepseek.com/quick_start/pricing/)，模型公布版本仍为 DeepSeek-V4.1-Flash-1017，峰价input USD0.30/M、output USD1.20/M，与获批上界一致；[价格核查](../../experiments/m5-development/conv44-successor-v3-pricing-v1.json)绑定新网页缓存SHA。

实际执行命令如下，进程退出码为0：

```sh
umask 077
PYTHONPATH=src:. python3 scripts/with_deepseek_env.py -- \
  /home/kenqia/my_folder/locomo-dynamic-memory/.venv/bin/python \
  -m tools.m5.conv44_successor \
  --output var/m5-development/conv44-successor-v3 --execute-authorized \
  > var/m5-development/conv44-successor-v3/live-process-output.txt 2>&1
```

只有 launcher 为该进程载入凭据；没有打印凭据或读取私有进程输出。结果来自结构化 outcome、SQL安全metadata和独立账本。唯一请求/返回alias均为`deepseek-flash`，thinking disabled、reasoning_effort null，HTTP200、finish_reason stop、outcome succeeded。可变alias仍不是不可变服务版本pin。

## 费用与诊断边界

| 项目 | 记录 |
| --- | ---: |
| 物理请求 | 1 |
| 新增 / 继承 Memory | 9 / 383 |
| prompt / completion tokens | 5,679 / 1,245 |
| 预约费用 | USD 0.0453867 |
| usage 峰价上界 | USD 0.0031977 |
| Unknown 请求 / 预约 | 0 / USD 0 |

独立获批上限为3请求/USD0.2619648。阶段已成功终结，剩余2次及金额容量不授权额外调用，也不转移到关系或Level E。六个历史付费阶段累计1433请求、预约USD70.9596105、known usage峰价上界USD7.9158096；既有7项transport Unknown继续保留USD0.3500316预约。以上均不是实际账单。

此次新Prompt及示例下首请求成功，只证明本次恢复完成。历史被拒原始输出未保存，本次没有时间错误诊断；不能据此确定历史失败是session timestamp误用、错误anchor还是表达改写，也不能声称经过控制实验证明某一项修改有效。

## 独立审计与归档

[根代理终态检查](../../experiments/m5-development/conv44-successor-v3-terminal-v1.json)20项全部通过，并严格验证数据库全部1177条Memory及其MemoryDraft、source links、session times、SQL列与外键。新Build引用281条source。父记录和原库、继承片段、producer、配置及sidecar均保持不变。Build及fragment calls与独立ledger usage一致。实际MockTransport重复进入口在provider前拒绝，终态数据库及账本不变。

[非作者终态复核](CONV44_SUCCESSOR_V3_TERMINAL_REVIEW.md)独立检查新Build全部392条Memory、保护摘要、精确授权、模型模式、账本及未扩展执行范围。新库仅原conversation-only八表，没有index、relation、publish、query或QA。

[私有归档记录](../../experiments/m5-development/conv44-successor-v3-archive-v1.json)对应`var/m5-development/conv44-successor-v3-terminal-v1.tar.gz`，484067bytes、8成员、0600，SHA `a240fcf7b78f1af07ddd1aa7379aea0ecd2ba74f34dee24d877cad088598db0e`。归档使用SQLite backup，逻辑摘要与终态一致；两个主文件通过immutable读取与integrity检查，不依赖WAL。所有成员SHA回读相等，排除私有进程输出。

本轮未修改producer或Prompt，因此不重复全仓测试；代码已在执行前通过842项全仓测试、最终14项successor回归及非作者44项合成检查。本轮新增的验收为真实终态与归档检查，不替代事实语义准确率或QA质量评价。

## 后续顺序

在新独立scratch复用已缓存MiniLM，仅为当前新Build建立本地索引；离线准备全部thinking disabled的关系任务，并依据实际任务数另批关系请求与费用。原conv-44 failed Build及33个历史片段仍保留；不得复制旧index/relations/projection或把继承片段冒称v5新生成。

关系终结后再完整化，严格生成第六份`memory-export-v2`并附绑定JSON SHA的混合producer sidecar。六份导出齐备后才锁定最终配置并准备一次独立Level E。conv-43/44的QA、evidence与answers仍未读。没有push、PR、main合并、远端发布或生产写入；未识别关联Notion记录，未同步或标记总任务完成。
