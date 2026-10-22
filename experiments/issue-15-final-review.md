# Issue #15 最终复核

实现冻结点为 `6a2918383aa10c906a2e3d350a9ccb495fe7bd1f`，修复比较基点为 `0d2ddc5`。

## Standards

审查固定差异：`git diff 0d2ddc5...6a2918383aa10c906a2e3d350a9ccb495fe7bd1f`。依据 `AGENTS.md`、`CONTEXT.md`、`docs/agents/domain.md`、ADR 0001/0002，以及 `.agents/skills/code-review/SKILL.md` 的完整 smell baseline。已检查全部修复差异及相关调用上下文，包括 SQLite 唯一约束、孤立执行项恢复、创建结果发现和显式接纳、公共 API 测试与操作文档。

未发现文档硬性规范违反，也没有需要提出的新增 smell 判断性建议。原 Standards 审查中的 P3 Duplicated Code 已消除：Run 身份与 preflight 现在共同调用 `implementation_identity.implementation_sha256()`，避免两处算法日后分歧。

修复继续沿用已有 FastAPI、SQLite 和模型适配器；没有引入生产依赖、任务队列或新供应商抽象。恢复流程保留不确定记录，通过关联标识和执行身份核对后显式接纳；无法核实旧记录时拒绝自动重建。行为变化与公开 API 同步写入使用文档。新增测试从公共 API 观察结果；SQLite 触发器仅用于注入真实持久化边界故障，没有直接断言私有存储结构。

`git diff --check` 通过，集成工作区干净。本次为只读静态复核，未重复执行测试；未读取凭据、调用真实模型或执行远端写操作。

Standards：0 项硬性违反，0 项判断性建议。


# Spec re-review

冻结比较：`git diff 0d2ddc5...6a2918383aa10c906a2e3d350a9ccb495fe7bd1f`，diff 非空。对照父规格 `docs/specs/issue-15-real-deepseek-baseline.md`、tickets #16–#21 以及原 `spec-review.md`。本轮只核查复核修复及关联调用方，没有重新执行真实实验。

无新增可报告缺陷，原两项已修复：

- 原 P1：`evaluation_execution.py:258–292` 在独占执行所有权下将仍为 `running` 的项目和尝试标成 `unknown`；启动恢复也检查已标为 `interrupted` 的 Run。保留先前未知尝试，只有显式 `retry_unknown` 才重新调用，符合规格 Implementation Decisions 14–18。
- 原 P2：`experiment.py:75–113` 提供只读发现和显式接纳；核对关联 token、隔离数据库、配置/实现/适配器身份及资源对应数据/计划/固定版本。没有关联 token 的旧未知记录拒绝猜测认领。Build/Run 各自的 SQLite 非空 token 唯一索引阻止相同创建 token 再建资源；发现不自动接纳，接续使用原资源，符合规格 Implementation Decisions 16、29–30。未发现实质范围扩张。

独立运行四项公开 API 行为测试：结果提交失败变为未知及显式重试；Build 响应丢失后的发现/错误认领拒绝/接纳；Run 响应丢失后的发现/接纳/不重复调用；旧未知记录保持证据。结果 **4 passed，11.94s**。状态断言通过公开 API 和 provider 调用记录，SQLite trigger 仅用于注入真实提交失败，不通过私有 SQL 断言结果。

真实 DeepSeek 与全量实验的实际验收不在本轮复核中；本报告不将 #20/#21 的实验义务标为完成。未读取凭据、未调用真实服务、未远端写入。

本轮 Spec findings：**0**。
