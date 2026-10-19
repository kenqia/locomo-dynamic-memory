# Issue #4 independent agent review

Reviewed base `53f116ec20e70edf503933d7782f1b796051866e` through
head `409f0b9ecfa59b0aed737440a69e0d4c097f9e2b`.
The two agents reviewed separately. This review does not establish non-author
human acceptance or authorize remote writes.

## Standards

Scope: fixed diff `53f116ec20e70edf503933d7782f1b796051866e...409f0b9ecfa59b0aed737440a69e0d4c097f9e2b`; read-only review, no broad test rerun or live model calls.

## Hard documented violations

- **[P2] Reject credential-bearing API URLs before recording configuration** — `src/locomo_memory/config.py:15` (serialization at lines 40–42). The session working agreement explicitly requires credentials to be excluded from configuration snapshots, traces and exports. `api_url` accepts URL userinfo unchanged. A synthetic `Settings(api_url='http://synthetic-user:synthetic-password@127.0.0.1:8000')` succeeds and its `snapshot()` retains the password. `BuildService.start`, query traces and `ExportBuild.config: Settings` then preserve this same field, so configuring HTTP Basic credentials exposes them in persisted/displayed/downloaded artifacts. Validate this URL to reject userinfo (and credential query parameters if supported), or separate the UI connection setting from the public settings snapshot. The proof used only literal synthetic inputs and printed a boolean, without reading credentials.

## Heuristic findings

None actionable. Considered MysteriousName, DuplicatedCode, FeatureEnvy, DataClumps, PrimitiveObsession, RepeatedSwitches, ShotgunSurgery, DivergentChange, SpeculativeGenerality, MessageChains, MiddleMan and RefusedBequest. Repeated endpoint pagination and lifecycle patterns do not independently justify abstraction at this project scale. No tool-enforced formatting issue reported.

Other documented rules checked: domain vocabulary and ADR boundary; single local backend/SQLite ownership; Streamlit uses HTTP; finite model retries and sanitized provider errors; local specs/tickets and experiment records; transparent uncompleted live/model/course verification. The existing validation results were supplied by the parent and were not rerun or independently asserted here.

## Spec

发现 2 项 P2，属于已实现但行为不符；未发现明确的额外范围。其余外部前提（DeepSeek 凭据、课程划分和动态标签）不作为实现缺陷。

- **[P2] 历史扩展没有使用查询已经确定的日期。** `src/locomo_memory/expansion.py:81–86` 仅从问题原文重新匹配 ISO 日期；`queries.py:147` 调用扩展时不传 `requested_date` 或已经解析的英文日期。Spec `docs/specs/issue-4-m3-m4-dynamic-memory.md:111` 明确要求“补充同一 state_key 下与问题时间有关的历史”，:105 要求“明确历史日期控制有效证据选择”。受控 API 复现：同维度 London(5/1)、Rome(5/2)、Paris(5/3)，初始召回 Paris，候选总上限 2、关系未确定；UI/API 指定 5/2 或问题写 `2 May 2023`，扩展得到 Paris+London，回答证据不足；同义 ISO 日期问题则得到 Paris+Rome 并正确回答。应把统一解析的查询时间传入扩展，使有上限时优先保留相应历史。

- **[P2] 失败构建可在 Prompt/schema 更新后沿用旧版本恢复。** `src/locomo_memory/builds.py:104–109` 恢复只比较 Settings，后续抽取使用当前模型模块中的 Prompt/schema；`relations.py:50–54` 同样未核对旧关系阶段身份。Spec :115 要求“Prompt/schema 或会影响产物的配置变化必须体现到版本或缓存指纹……不能原地改写既有版本”。受控 API 复现：两片段中首片成功、次片失败；模拟升级抽取 Prompt 及版本 `extract-v2` 后重试，返回 202，首片保留旧产物、次片使用新 Prompt，最终 `extracted`，但 fingerprint 不变、记录仍为 `extract-v1`。应检查完整产物契约指纹，变化时拒绝恢复并要求新建版本，或保存并执行原契约。

复现均使用临时 SQLite、真实 FastAPI/检索和受控 LLM/Embedding，无真实凭据或外部调用：

` .venv/bin/python /tmp/locomo-issue4-context/spec-repro.py`

` .venv/bin/python /tmp/locomo-issue4-context/spec-recovery-repro.py`

Initial review: Standards 1 finding, worst P2; Spec 2 findings, worst P2.

## Standards recheck

The original P2 is resolved in `b30612e`, integrated by `f51c3ba`.
Settings rejects API URL userinfo and all query parameters before snapshotting.
Rejected inputs are redacted in textual and structured validation errors.
The Standards reviewer independently ran `tests/test_config.py`: **3 passed**.
Additional synthetic probes confirmed safe error serialization for userinfo,
query parameters and malformed credential URLs; ordinary base paths remain valid.
No real credentials were read.

## Spec recheck

Both original P2 findings are resolved in the same commit.
The query passes its unified explicit date into bounded expansion; direct
candidate expansion shares English/ISO parsing. Date priority changes ordering
without excluding unknown or other historical dates.

New builds and recovery compare the same artifact fingerprint, including actual
Prompt/schema content and versions, projection version, source and settings.
Extraction retry, index and relation advancement/recovery, and projection rebuild
reject changed contracts before writing. Complete-version reads remain available.
The Spec reviewer independently ran the 15 contract tests and the capped-history
test: **16 passed**, 48.12 seconds. Three additional public API probes confirmed
index, relation and projection advancement return `409 build_contract_changed`
without changing the build after a Prompt change.

The implementer separately ran the complete default suite: **109 passed,
4 skipped**, 187.63 seconds. See `issue-4-review-fixes.md` for RED/GREEN details.
The merge tree exactly matches that tested commit; compile and diff checks passed.

Recheck: Standards 0 unresolved findings; Spec 0 unresolved findings.
