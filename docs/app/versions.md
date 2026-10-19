# 恢复构建与导出完整版本

通过 FastAPI 显式恢复失败或中断阶段，再发布完整版本。Streamlit 的“恢复与完整版本导出”区使用相同接口。导出始终使用页面选择的 `build_id`，不会改成当前活动版本。

## 恢复失败或中断阶段

1. 请求 `GET /builds/{build_id}`，确认 `status` 和 `phase`。
2. 用 `GET /builds/{build_id}/fragments` 检查抽取结果。关系任务使用 `GET /builds/{build_id}/relation-tasks`。
3. 请求 `POST /builds/{build_id}/retry-phase`。抽取仅重试失败或中断片段；索引从已有 Memory 重建；关系仅重试未成功比较，并重算投影。成功片段及比较的尝试次数不变。
4. 刷新构建状态。抽取结束后显式建立索引，索引结束后显式构建关系，最后调用 `POST /builds/{build_id}/publish`。

已有 `/retry`、`/index` 和 `/relations` 控制继续可用。没有自动续跑或外部任务队列。全局最多一个等待或运行的构建任务，包含抽取、索引和关系阶段。索引重试同步执行；抽取和关系由当前 FastAPI 进程中的后台任务执行。

后端重启将等待或运行的构建标记为 `interrupted`，不重复处理已成功片段。启动锁阻止两个后端同时使用同一数据库。改动配置后，旧的不完整构建拒绝重试并返回 `build_configuration_changed`；创建新版本继续。

## 固定完整版本

`GET /versions/pin?dataset_id=...&sample_id=...` 返回当前活动完整版本。传入 `build_id` 可固定指定完整版本。没有匹配完整版本时返回 HTTP 409 `no_complete_version`。候选检查接口仍允许检查已有索引的部分版本，不能将它称为完整记忆库回答。

发布事务校验抽取、关系任务、投影、Memory 与索引集合、索引文本和指纹、向量形状及归一化、来源及版本引用后，同时设置 `complete` 和活动指针。失败保留原活动版本。完整版本的构建产物不可重写；修正产物需创建新版本。

查询使用所选索引持久化的 Embedding identity。生产 MiniLM 从本地缓存加载该 revision 和长度设置，不先加载当前配置中的新模型。旧 revision 缓存不存在时明确报错，不用新模型编码旧向量。查询预算使用并记录当前查询配置，构建配置快照保留不变。

## 下载 JSON

调用 `GET /builds/{build_id}/export`，或在页面选中完整版本后点击“准备所选版本 JSON”，再点击“下载完整 Memory JSON”。响应为 `application/json` 附件，文件名包含构建 ID。

`memory-export-v1` 包含数据版本与许可证、完整构建身份与配置、全部 Memory、多来源原始轮次、关系、Current State 投影及索引身份。导出不受页面分页限制。Pydantic 检查集合身份和来源引用，读取使用同一 SQLite snapshot。活动版本在读取期间切换不会改变已选择集合。

导出仅选择声明字段，不包含 QA 参考答案、导入附加标注、凭据、向量、提供方原始响应或调用日志。Memory 的 `source_ids` 可定位 `sources` 中的 `source_id`、`session_id` 和 `dia_id`。一个来源支持多条 Memory、一个 Memory 引用多个会话来源时均保留原映射。无完整版本或选择部分版本返回 409；不存在的构建返回 404。

OpenAPI 的 `MemoryExport` 描述完整 JSON schema。版本集合或引用校验失败返回 `invalid_export`，不会下载伪完整内容。
