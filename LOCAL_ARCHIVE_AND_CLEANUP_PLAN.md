# 本地归档与仅拟清理计划

本轮删除数为0。不reset/clean/stash主仓，不删var/Gold/Trace/账本/工作树，不prune不明注册项。

## 已完成归档与恢复验证

本地受保护目录：`/home/kenqia/my_folder/locomo-private-delivery/m5-personal-candidate-20261105/`，目录0700、受控数据/归档0600。

- `archive-v1/research-evidence.tar.gz`：2,301,324,861bytes、35,440成员、原成员合计12,252,036,254bytes；SHA `bfb7f58a42cf5f76e35db580f06e215a3bc15beb691892d781a02fa0251f5ddd`。完整文件清单/每成员SHA/原路径/SQLite备份依据在同目录`private-archive-manifest.json`。所有成员实际回读流式SHA、大小、顺序与源快照一致。
- `archive-source-v2/research-evidence.tar.gz`：5,880,956bytes、2,446成员、源码原成员18,719,075bytes；SHA `546a29a16cf4a7cffd40200a7a82cdb03112eb43833f83320e676f2e77200eef`。补足历史未提交src/tools/tests/scripts，包括Phase7/8/9隔离研究；不把未提交文件冒称97bfaaa Git对象。
- 六份真实JSON另在`memory-exports/`，39,771,212bytes，逐份SHA与原件一致；本轮未把它们提交Git。
- `appendix-rebuilt/`保留实际重建版本，原3392faf图文/PDF仍按原字节入Release；不是覆盖旧研究档案。
- 既有Level E原白名单归档仍在原路径：55,172,721bytes、863成员，SHA `72d6bd2dd5261ff863ec861eab780a5b580e4dec6889f5948ac73f45f44a31f5`，非作者再次核验路径/权限/SHA。

归档脚本只读源文件；SQLite用mode=ro一致性backup并quick_check，不以原main字节代替含WAL逻辑快照。没有恢复一次性实验执行权限。日志、凭据、WAL/SHM、symlink、venv/model缓存/外部checkout按清单排除并原位保留；排除项不声称已完整备份，不能据此批准原目录删除。

## 全部目录分类

每个实际目录的HEAD/dirty_entries/原状态哈希见`experiments/personal-release/local-archive-summary.json`及`initial-state.json`。归档脚本的B是保守保留标签；下表是最终分类依据，未知归属不推断。

| 类别 | 路径/范围 | 处理 |
|---|---|---|
| A Release必需 | m5-release-integration-20261105、six JSON受控副本、staging | 保留；Git版本化与清单 |
| B 原始研究证据 | research-next/research-process-archive、m5-final-development/input-v2/build-repair/completion/conv44-recovery/conv44-relations各docs/experiments/process/研究var | 主档+源码补档；原件全留 |
| B 生产身份 | production-integration-20261101、v2-6d-production-safe/research-safe及已确认历史locomo工作树 | 保留HEAD与原件；归档证据，不合流代码 |
| C 用户其它工作 | 主仓36项dirty；m1/m2/m4交付、.scratch、用户课程文档/脚本 | 保留原位；不整体搬入Release、不stash |
| D 已证明重复缓存 | 当前没有完成逐字归档+可恢复性证明的历史缓存 | 拟删除名单为空，释放0bytes |
| E 可重建输出 | 各.venv、__pycache__、研究外部backend checkout、模型缓存、测试临时输出 | 仅候选清单；并未确认可安全删除 |
| F 不明身份 | v2-6d-clean-clone等未注册目录、非Gitbrowser-env/context目录、4个prunable /tmp review注册项 | 保留待确认；不prune |

根仓主状态校验严格使用`git status --porcelain=v1 -z`原始bytes（含尾NUL），不是strip/newline文本。初始36项哈希记录，非作者已核同一命令一致；最终再次核验。源码/数据库完整性报告与Git状态均不能替代排除日志的备份。

## 拟删除清单（仅建议）

没有历史D类得到充分证明，因此本轮不批准任何历史删除。E/F范围只供负责人后续核查：各历史`.venv`/`var/.../venv`、`__pycache__`、外部backend clone、ollama权重、4个失效/tmp worktree注册项。容量估计单列`cleanup-candidates.json`，删除原因=可重建候选，恢复性=尚未验证，许可删除=false；不将预计空间算作已释放。

恢复示例：在新的0700目录验证manifest，再按明确成员恢复tar（先核safe path，不能覆盖原目录）。如原研究SQLite需要使用，先恢复为新文件；不要原地替换现有DB。所有历史删除/工作树移除必须另获用户确认。

本轮验收原记录另归档至受控`release-verification-v1.tar.gz`：117,348bytes、27成员，SHA `f180dc739b8535f5fdebe3f4a9debdd95a0fcdae75597d8f33444c3f1c10d8da`。包含自有失败/中断/最终pytest stdout及JUnit，逐成员SHA/size验证；不含服务敏感日志。清单见`experiments/personal-release/verification-archive.json`。历史删除0，实际释放0。
