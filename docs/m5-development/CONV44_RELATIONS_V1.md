# conv-44 本地索引与全 disabled 关系阶段 v1

2026-11-04。本阶段先在新scratch完成本地索引与关系任务准备，再单独申请付费关系执行。真实离线index与prepare已完成；用户已批准1,152次物理请求/USD100.5944832，执行现已终结为374成功/10失败，417次请求；终态完整性审计通过但尚非complete，见[真实结果](CONV44_RELATIONS_V1_RESULTS.md)，见[授权记录](../../experiments/m5-development/conv44-relations-authorization-v1.json)和[当前交接](../../M5_CONV44_RELATIONS_V1_HANDOFF.md)。下文0请求、缺少授权的检查保留准备时点。原[successor v3抽取](CONV44_SUCCESSOR_V3_RESULTS.md)已成功并冻结为34/34片段、392 Memory；本方案不追加抽取请求，不读取留出QA、evidence或answers。

## 契约与保护范围

复用现有 `BuildService`、`RetrievalService`、已缓存 `MiniLMEmbedder`、`RelationService` 和 `BudgetTransport`，不引入新依赖或生产schema。只处理明确的新Build `d9fb61417bb740e4b8eb34acb8652a46`，不能遍历旧Build或调用conv-43专用的high模式门禁。

新scratch保留原settings.db_path及完整fingerprint，存储位置通过显式Database对象路由。父库只读backup，不改原stage或ledger。继承sidecar继续记录33个旧producer片段与9条新生成Memory的来源边界，不能宣称全部由v5重新生成。

索引阶段仅允许新Build状态与索引记录变化；来源、全部Memory、片段和其他Build保持相等。关系准备仅创建新Build任务；实际执行保护全部Memory、片段、index和其他Build，保留抽取calls前缀及inheritance metadata。新关系attempts使用独立ledger，不重复计费已完成的抽取调用。

准备及执行入口冻结核心producer、实际helper与脚本、settings、source终态/索引摘要、sidecar、任务身份与selection、原记录保护摘要。执行还需要精确新授权、数据库锁和单次marker；工具最多运行到related，失败不自动追加尝试或改变预算。

终态审计分别核对逻辑attempt与物理请求：任务必须具有一次已关闭的逻辑attempt，其状态、错误和时间对应；provider SQL身份必须与metadata及连续请求编号对应。Build、phase、Prompt/schema与任务总状态一致，related必须无失败任务。允许本地政策拒绝产生failed逻辑attempt但零物理请求，transport Unknown保留完整预约；不能把两类计数混为一谈。

## 免费准备命令

在工作树 `/home/kenqia/my_folder/locomo-worktrees/m5-final-conv44-relations-20261104` 中运行。先完成代码与合成验证及非作者复核；不得覆盖已有输出目录。

```sh
umask 077
env -u DEEPSEEK_API_KEY -u OPENAI_API_KEY -u CODEX_ACCESS_TOKEN \
  HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false \
  PYTHONPATH=tools/integration/offline_guard:src:. \
  /home/kenqia/my_folder/locomo-dynamic-memory/.venv/bin/python \
  -m tools.m5.conv44_relations index \
  --source /home/kenqia/my_folder/locomo-worktrees/m5-final-conv44-recovery-v3-20261104/var/m5-development/conv44-successor-v3 \
  --source-terminal /home/kenqia/my_folder/locomo-worktrees/m5-final-conv44-recovery-v3-20261104/experiments/m5-development/conv44-successor-v3-terminal-v1.json \
  --output var/m5-development/conv44-index-v1
```

以下记录索引前的encoder预检：固定MiniLM revision `c9745ed1d9f207416be6d2e6f8de32d1f16199bf`、384维、CPU，392条Memory的完整索引文本最大41tokens，低于256上限，超限0。该预检本身不保存索引；随后本轮实际索引已保存392×384维finite、normalized向量，且只属于新Build。证据为[缓存身份](../../experiments/m5-development/conv44-cached-embedding-preflight-v1.json)和[输入预检](../../experiments/m5-development/conv44-embedding-input-preflight-v1.json)。

索引实际通过后准备关系任务：

```sh
umask 077
env -u DEEPSEEK_API_KEY -u OPENAI_API_KEY -u CODEX_ACCESS_TOKEN \
  HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
  PYTHONPATH=tools/integration/offline_guard:src:. \
  /home/kenqia/my_folder/locomo-dynamic-memory/.venv/bin/python \
  -m tools.m5.conv44_relations prepare \
  --source var/m5-development/conv44-index-v1 \
  --output var/m5-development/conv44-relations-v1
```

预期输出包含实际任务数、固定任务摘要、独立空ledger和未批准授权模板。任何准备异常都保留首次scratch，修复后使用新目录；不能覆盖旧结果或跳过保护校验。

## 只读任务预检

不创建index或任务记录的[纯规划预检](../../experiments/m5-development/conv44-relations-readonly-preflight-v1.json)得到384个任务、7,134次比较；初次完整messages最大38,182 UTF-8字节，超过160,000的任务为0。该预检保留源码的source_order/m.rowid排序、实体历史和selection算法，提供任务选择摘要供真实prepare后核对。预检不代表任务DB已准备、反馈重试一定成功或关系语义正确。

实际prepare确认384任务、7,134比较，与纯规划预检的计数及输入极值一致。根代理还从冻结Memory重新逐项核对完整任务身份与selection。最终硬上界为1,152请求/USD100.5944832；非作者实际准备复核8组通过；现可申请精确授权，尚未批准或执行。

## 实际准备工件

实现已本地提交 `82a9d25`。主代理针对性验证96 passed，非作者代码复核27 passed；1条既有Starlette warning，无生产src改动或新依赖。修前[v1验证](../../experiments/m5-development/conv44-relations-verification-v1.json)保留为历史；[v2验证](../../experiments/m5-development/conv44-relations-verification-v2.json)绑定最终代码。见[非作者代码复核](CONV44_RELATIONS_V1_REVIEW.md)。

私有index为 `var/m5-development/conv44-index-v1`，关系stage为 `var/m5-development/conv44-relations-v1`。源库及抽取ledger摘要不变；新stage为queued/relations、384任务全部pending，392 Memory、281引用Source，关系、attempt、provider、query均为0。独立ledger为空，无authorization或execution marker，真实缺少授权入口已拒绝且两库不变。目录0700、文件0600。[根代理实际准备检查](../../experiments/m5-development/conv44-relations-preparation-v1.json)共21项通过。[非作者准备复核](CONV44_RELATIONS_V1_PREPARATION_REVIEW.md)独立核验8组通过，安全数值见[独立准备检查](../../experiments/m5-development/conv44-relations-independent-preparation-v1.json)。独立审计未重新编码encoder、重拼完整wire messages或审阅关系语义；38,182字节为根代理实际重算值。

精确plan SHA为 `0920823b2c04d5d632df481df24ca60348b182fc760da8bb3a28f02cc5eb94cf`。此SHA绑定实际任务与selection、settings、producer、source/index、继承血缘、准备schema和空ledger；准备完成不等于关系完成或付费授权。

## 独立费用与授权

设实际任务数为T，每任务最多3次物理请求。单请求最多160,000 UTF-8字节、32,768输出tokens；按峰价input USD0.30/M、output USD1.20/M，以每字节一个代理token的保守上界计算：

```text
单请求预约上界 = (160000 × 0.30 + 32768 × 1.20) / 1000000
               = USD 0.0873216
物理请求上界 = 3T
阶段预约硬上界 = USD 0.2619648 × T
```

schema/transport重试均计入独立账本，Unknown保留全部预约；旧阶段剩余额度不转移。实际任务数为384，精确预算为1,152请求/USD100.5944832；须经独立metadata复核并提交用户批准。初次输入能容纳不保证响应或反馈重试成功，硬字节上限会拒绝超限请求。

模型为`deepseek-flash`（当日公布DeepSeek-V4.1-Flash-1017），全部新生成thinking disabled，不发送reasoning_effort。执行前复核官方价格与alias身份；可变alias不是不可变服务端版本pin。仅明确批准精确plan后，通过`with_deepseek_env.py`调用`execute-authorized`；准备不自动创建批准文件。

## 完成标准与后续顺序

本阶段关系成功停止于related，独立验证来源和关系schema、投影、任务/调用/账本、保护快照及Unknown。通过后才在新的本地副本完整化和严格导出第六份`memory-export-v2`，另附绑定导出SHA的混合producer sidecar。索引或关系准备都不等于complete，也不自动授权QA。

六份JSON齐备后锁定最终系统配置，再为一次独立Level E准备新计划和预算。前五份JSON的历史关系high模式如实保留，不把本轮disabled描述成全部历史构建均disabled。没有远端写入、push、PR或main合并。未识别关联Notion记录，未同步或标记总任务完成。

回滚保留独立scratch、计划和账本，不引用新副本即可；无需更改冻结源。后续清理或生产迁移另行处理。
