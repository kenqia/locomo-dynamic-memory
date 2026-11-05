# conv-44 successor第六份实际导出与六份JSON独立复核

2026-11-05。**结论：6组独立实际导出检查全部通过，六份memory-export-v2 JSON均按原SHA重新严格验证，可开始最终配置锁定工作。** 当前复核不构成最终配置锁、Release、QA读取或Level E执行授权。根代理通知本次complete-export以exit 0结束后才运行本审计；新增provider请求为0。

复核者为非作者代理 `/root/final_actual_review`。[独立导出JSON](../../experiments/m5-development/conv44-sixth-export-successor-independent-v1.json) SHA为 `d5e7a3a723bba6816b5b8b967e8e826403fc2f35b84d03601bf1e6f58c18eefc`；[独立related终态](CONV44_RELATION_SUCCESSOR_V1_TERMINAL_REVIEW.md)保留源执行终态。一次性导出审计脚本 `/tmp/conv44_sixth_export_successor_independent_audit.py` SHA为 `13d17b5675a8220c479f0cfb4dc6b786e4a922ee774e30264dbb57b3980f0139`。

实际执行使用项目venv、撤销模型凭据变量、HF/Transformers离线及offline_guard，运行该脚本并传入 `--root-confirmed-export-finished --export-stage var/m5-development/conv44-sixth-export-successor-v1 --output experiments/m5-development/conv44-sixth-export-successor-independent-v1.json`。所有SQLite连接为mode=ro、query_only和读事务；源及copy先做精确表白名单、无评测annotations与空queries检查，再读记录或快照。没有实例化写服务、修改代码/数据库/旧工件或读取raw、私有stdout、凭据及留出QA/evidence/answers。

| 独立检查组 | 结果 |
| --- | --- |
| 1. 源终态与SQL gate | logical3源、logical2恢复源、logical1原关系阶段及相关公共终态身份相符。源仍related/relations，两个旧阶段保持各自失败历史；无QA/查询表或非空评测annotations。 |
| 2. copy逐行保护 | 新copy只将目标Build的status/phase/updated_at改为complete，并增加active_versions及唯一正确pin；所有其余旧行含rowid、schema、Memory/Source/片段/索引/relations/projection/attempt/provider/calls完全保留。copy395 attempts、430 provider、431 Build calls；原阶段DB/ledger未修改。 |
| 3. 实际严格JSON | 第六JSON严格roundtrip相等，逐字段等于copy的独立白名单SQL重建：392 Memory、281 SourceTurn、7134关系。projection精确重算，392×384向量finite/归一化、index文本和fingerprint重新核对。未重编码。 |
| 4. 三代sidecar | 导出SHA、Build、抽取继承和全部映射Memory、88 producer及混合输入标识相符。logical1/2/3逐一绑定正确stage、plan、终态、独立ledger快照、各自wire契约和wrapper SHA；全部关系调用thinking disabled。未重拼wire，也不宣称额外契约进入既有Build fingerprint。 |
| 5. 六份实际JSON | 五份旧JSON从冻结的m5-final-build-repair-20261104路径读取，SHA与原公共五份清单相等；新第六份按实际copy读取。六份均通过memory-export-v2、relation-v2-stage-evidence、身份/来源/关系及projection引用严格验证和原JSON roundtrip；完整六个sample身份无缺失。 |
| 6. 末尾不变性 | 审计前后三个关系源DB/ledger、全部冻结计划/配置/授权/marker/outcome和相关公共终态身份相同。新copy及exports目录0700，全部私有载荷0600；现有Linux advisory runtime.lock为0644但大小0字节，位于0700目录内。该空锁不含数据。 |

六份严格结果如下；仅列计数和SHA，不输出正文。

| sample | Memory | SourceTurn | 关系 | SHA-256 |
| --- | --- | --- | --- | --- |
| conv-26 | 259 | 190 | 4740 | `08f4624a39c98793e0ad288e6de6c4ba058e0f30fa27f49569de0bdec0f1be78` |
| conv-30 | 244 | 154 | 4460 | `efb5c9cdfea490358982f1c2b82818759aa46aad83d6f0d3f459415c268ec1ae` |
| conv-41 | 321 | 243 | 5767 | `e15b30e89de463cca4ff9fcd347b332a72525f0fbfb8506a5476df120fd4b488` |
| conv-42 | 413 | 297 | 7724 | `89d6bdf02e7eca10014688e0a7946fd536b846c4ff6c8b09a84bb8671680e3fd` |
| conv-43 | 402 | 300 | 7620 | `2ae95deb13dcf22e1bb91cff44db88feba7c3bcf1b753e907ba121f4ac972f17` |
| conv-44 | 392 | 281 | 7134 | `1006ce3d855ffb496cb8a2c029276511707427bb7129474013f4b1768639611f` |

第六导出为 `var/m5-development/conv44-sixth-export-successor-v1/exports/conv-44.json`，其sidecar SHA为 `19d1272ceb3482db11b3698d9e9c1ea4e260dd280b80e226dae14e2e29d18580`，summary SHA为 `54a7d6fb31a8bb0d2ab7b832f13eea784f3c6610c5ae57443d5fe73b5fceaade`，copy database逻辑快照为 `192eb8cb866c2e9fbf0c52b496454cbd661235d6705693140804bdd4b60d4324`。

根代理[六份聚合](../../experiments/m5-development/six-build-exports-v1.json) SHA为 `d4a9cda9fbf6460382424dd8f37326182212cef78575f8be2fba1992e3624f08`；独立核对其六个Build的身份、计数、SHA、实际路径和strict状态均相等。该聚合与本独立检查是不同验证范围，不混计测试或检查数量。

本结论证明六份实际导出满足冻结工程契约及来源完整性，不证明Memory或关系语义准确率、QA质量或教师评分。未读取实际账单、重跑测试、重编码或改动历史思考配置。现阶段可锁定最终少数策略、六Build、全部Settings、代码/producer、模型/Prompt、评分与预算政策；必须完成该锁和后续独立准入后，才进行明确获准的问题投影或Level E准备。任何生成仍须精确范围与费用授权，全部生成冻结后才可打开Gold。
