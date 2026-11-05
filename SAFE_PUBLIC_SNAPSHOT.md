# Personal Core Release — pending team integration

本分支 `m5/personal-public-core` 从 `origin/main@f5a5dfdec5235d1c411cb5d4b525467e40fef415` 创建。只按已验收公开 tar 导入文件，不合并、cherry-pick 或推送个人研究分支历史。它是待团队集成的个人核心快照，不是课程最终提交。

## 来源与文件范围

- 原个人 Release 记录：`af54f0eed24c4a52116bcccf85682f1334d5d116`，仅作血缘引用，不是本分支祖先。
- tar 来源：`c63c9ce4fd26b3e1c1f6509e8d4419d55554aae4`，12,620,367 bytes。
- tar SHA256：`8c2cfdb818316887df98c847f67fb10d67fbcfa96e595e38d731f86fe1a3dd77`。
- tar 原导入清单：[imported-tar-evidence-manifest.json](docs/public-release/imported-tar-evidence-manifest.json)。801个文件初始逐SHA核验：119与main相同、40修改、642新增；第802成员是清单本身。
- 每个导入路径的base/tar SHA与状态：[import-audit.json](docs/public-release/import-audit.json)。main未在tar内的路径见[retained-main-paths.json](docs/public-release/retained-main-paths.json)。没有删除团队材料。
- `RELEASE_MANIFEST.md`、`RELEASE_COMMIT_MAP.json`、`docs/release/`及个人实验审查报告描述原本地Release；其991/937结果是历史验收，不替代新组合快照验收。原始commit在安全快照clone中未必存在，不运行旧分支的git checkout来复现。直接运行本分支README中的命令。

本轮导入之后的集成差异仅限：README增加本页入口；`extraction_patch.py`移除一个多余EOF空行（无行为变化）；CI改用完整公开离线测试集和45分钟限时；新增来源/审计/当前验收文档。三份原始pytest失败报告含尾空格，`.gitattributes`仅对这三个精确路径取消尾空格检查，保留原字节和冻结SHA；所有源文件继续接受正常`git diff --check`。

## 数据与隐私边界

本次新增快照不包含六份完整Memory JSON、受控原文、私有Gold、raw wire、研究数据库、凭据或本地归档。原创合成Replay采用CC0，真实实验只展示冻结公共汇总；它不把合成答案当作LoCoMo模型成绩。

main已经跟踪公开上游LoCoMo原始数据及官方QA（`data/raw/locomo/`，CC-BY-NC-4.0、上游commit及哈希见provenance），并有历史逐题实验/AI审阅材料。本轮不修改这些继承文件、不将其描述为新上传的受控六JSON，也不将官方公开QA称为私有Gold。原tar的隐私通过范围不能扩大到这些继承材料；本轮单独记录其来源与扫描边界。发现无法解释的私有来源或凭据时停止合并。

六份完整Memory导出仍仅受控本地保存。交付需确认课程渠道、接收者和数据授权，不通过GitHub公开PR传输。实验档案和实际账单不上传、不读取凭据，不运行任何付费或历史一次性实验。

## 本轮验证与运行

新快照测试结果及审查状态见[PUBLIC_SNAPSHOT_VALIDATION.json](docs/public-release/PUBLIC_SNAPSHOT_VALIDATION.json)。只有本轮完整测试、Web/Replay、隐私审查及GitHub Checks通过后才允许合main。公开测试明确排除24个controlled_data和4个live_model/local_embedding opt-in；其余main与tar测试全部执行，不以旧报告替代。

```sh
uv sync --locked --python 3.12
scripts/personal-release doctor
scripts/personal-release run-tests --public
scripts/personal-release start
# 单独终端、无凭据只读演示
scripts/personal-release replay-offline-demo
```

API/UI：127.0.0.1:8000/8501；独立Replay：127.0.0.1:18010/18510；API健康路径`/health`。真实Dense Build需另安装embedding extra并已有固定模型缓存。没有凭据可完成全部只读Replay，不创建Build/Resolve/Answer或研究SQLite。

当前`public-evidence-manifest.json`用于核对本安全快照的导入/集成文件；原tar清单冻结在docs/public-release中，两者不可混用。完整仓库包含既有团队文件，不能把此清单误称为全部main历史安全证明。

## 团队接入与回滚

核心包括Build/Version/Source、Hybrid/Dynamic问答、关系历史、Trace、评测、MemoryExport v2、FastAPI/Streamlit与只读Replay。Graph浏览可选；Graph多跳、compression wire、Adaptive与新增Temporal soft priority默认关闭，工程通过不代表QA增益。

Product #26–29仍需完整页面与浏览器证据；PR #39不在本次合并范围。Architecture PR #38语义审查未通过，不进入默认链，未来仅opt-in Sidecar接入并重验。Delivery #34–37仍需PPTX、MP4、团队总报告和单包要求核对。没有修改队友Issue或课程提交状态。未找到本轮关联Notion任务，不宣称已同步，由负责人补录。

合并使用GitHub squash，使main仅增加安全快照提交。回滚点是合并前main的完整SHA（记录在合并后本地回执），回滚用独立revert PR，不reset、不force push、不覆盖历史数据库。检查期间main若变化，先重审差异及相容性，再合并。
