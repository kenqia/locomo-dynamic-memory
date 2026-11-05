# Level E 实际准备

2026-11-05（Asia/Shanghai）。最终系统配置在读取留出问题正文前已提交于 `191349f`。随后 questions-only 准备正常退出，未调用 Provider，未读取类别、答案或证据。实际准备的独立复核已通过，等待新的付费阶段明确批准。

## 范围与身份

- 实现 commit：`0dbd98e7b296ef29d9998fa55d88d512f8ec85f1`；82 个 producer 与该 commit 匹配。
- 配置锁 SHA-256：`3b6e3fbcad1670226f1f9d8e1c9fa96436b104893a875527d078dc4948671ac6`。
- 计划 SHA-256：`5d99378868a5aed92889ff3995ae7771270b91d8effb373fb6d7e85672484c92`。
- 私有 stage：`var/m5-development/level-e-preparation-v1`，目录权限 `0700`；问题、执行数据库和账本为 `0600`，不提交原文。
- 两段完整 400 题（242+158），保留原始 ordinal；Hybrid/Dynamic 共 800 项，Bonus 全关。
- 独立上限：6,000 物理请求、USD 1,387.9296。全部新生成 disabled，640,000 字节、resolve 192,000 代理 tokens。该金额是保守预约硬上界，不是预计消费。

完整参数、评分分母、失败/Unknown 和 Gold 政策见[最终配置](LEVEL_E_FINAL_CONFIGURATION_V1.md)。不重建 Build；只使用两份无标注 complete 副本。配置中的原 `db_path` 保留开发快照，实际服务通过 `model_copy` 指向各自副本。

## 实际验证

[根代理审计](../../experiments/m5-development/level-e-preparation-root-v1.json)的 25 项检查通过：实际 `verify_plan`、完整四字段问题投影、六份 strict SHA、两份 complete Build 再导出精确相等、数据库 quick/FK check、82 个真实 Git blob、所有源 main/WAL 不变、精确账本政策和 0 请求。

对真实 `execute` 传入 Mock：缺少 `authorization.json` 时抛出对应 `FileNotFoundError`，0 dispatch，未创建 marker/abort/freeze/items/scores，执行库与账本身份保持不变。`authorization-template.json` 的 `approved=false`；它不是可执行授权，不会自动复制成授权文件。检查脚本为 `/tmp/m5_level_e_root_preparation_audit.py`，只读取问题，不打印问题正文。

实际准备命令：

```sh
env -u DEEPSEEK_API_KEY -u OPENAI_API_KEY -u CODEX_ACCESS_TOKEN \
  HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
  PYTHONPATH=tools/integration/offline_guard:src:. \
  /home/kenqia/my_folder/locomo-dynamic-memory/.venv/bin/python -m tools.m5.level_e prepare \
  --final-lock var/m5-development/level-e-final-lock-v1/final-system-lock.json \
  --output var/m5-development/level-e-preparation-v1
```

该目录已经存在，不能重跑此命令覆盖准备。源码未改变，沿用此前 Level E 定向 21 项及非作者修复 5 项验证；本轮运行实际准备与审计，不冒称重新运行全仓测试。[非作者实际准备复核](LEVEL_E_PREPARATION_REVIEW_V1.md)的 6 组检查全部通过，0 项未决发现；独立 SQL 仅投影 question+ordinal 与 400 输入精确相等，两执行库旧行与 rowid 保留，六导出、82 个真实 producer blob、所有源与私有准备载荷不变。准备 manifest 绑定两份实际审计与空账本身份。

## 后续执行

获批前不写 `authorization.json` 或执行生成。获批后须复核当日官方价格和模型映射，使用已有凭据 launcher 单次启动；保留私有 stdout/stderr，不打印原始响应。全部 800 项生成冻结后再评分，失败和 Unknown 不筛除。

停止使用此 stage 即可回滚准备。参考库、Build 源、历史账本和生产默认均保留；不删除历史或转移旧余额。Level E、来源事实/拒答审阅和最终交付仍未完成。未识别关联 Notion，未同步或标记总任务完成。
