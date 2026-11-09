# Level C 首次 resolve 输入诊断独立复核 v1

初审结论：公共报告的纯数字重算通过，发现1项P2冻结归属缺口：诊断未验证冻结plan及原始受保护来源状态，等token的来源变化仍可被报告为完整重建。作者已收到独立synthetic复现，修复前不能把当前工具的重建声明当成独立完整性证明。该发现不证明真实来源发生变化，也不推翻当前公共报告内部一致的阈值计数。

2026-11-04。非作者审查者 `final_code_review_v6`。工作树 `/home/kenqia/my_folder/locomo-worktrees/m5-final-development-20261104`，初审HEAD `3335862dba1e9658f4d5c515b602c98049826d7c`。报告沿用已读取的 `google-developer-docs` 技能。审阅指定工具、tests和公共JSON，并只读核对必要的 `QueryService`、完整输入预算及冻结准备代码。没有修改实现或提交commit。

| 文件 | 初审 SHA256 |
| --- | --- |
| `tools/m5/level_c_input_diagnostics.py` | `b860d694a9db7486c7940876faa16533943c4a6b197ce7b7a27d0bae16c9ff1f` |
| `tests/test_m5_level_c_input_diagnostics.py` | `282c5c7a5f6cd96c262cbd7af7ebc53157dcda2eeaf1ae702ca6a7dd97832081` |
| `experiments/m5-development/level-c-input-diagnostics-v1.json` | `24efafb219916ca320fb9e2ba451bd9f62564b93ae137fa88dfafa2472dfa2d9` |

## [P2] 将重建依赖绑定冻结plan和受保护数据库状态

初版run核对Dynamic item文件与freeze的100个Dynamic哈希、外层身份、问题和Trace config，并比较重建token估计与保存审计。但它没有读取plan.json、校验freeze的plan绑定或完整200项freeze，也没有将settings、inputs、producer实现及当前来源数据库状态绑定冻结plan。来源正文只按Source ID重读；保存的token计数和来源ID顺序不能证明正文或序列化字节未变。

独立实际复现只使用现有synthetic测试helper，在新的TemporaryDirectory创建100个Dynamic item与synthetic来源表。fixture没有plan.json，freeze只包含100个Dynamic哈希但声称planned_items=200，初版run接受为complete。首次诊断后，仅执行：

```sql
UPDATE source_turns SET text = text || '     ';
```

没有改freeze、items、settings或inputs。第二次run仍返回status=complete、observed_causes_reproduced=100；100项token估计全部不变，但100项messages_sha256全部改变、每项messages字节增加10。该复现证明，token一致不足以绑定原始payload字节。已在修改前通知主任务及作者 `level_c_source_a`；作者确认将复用完整freeze/plan与终态保护snapshot校验。

建议在读取重建来源前验证完整200项freeze、plan及settings/inputs/producer身份，并验证当前受保护数据库逻辑快照仍与原终态审计及准备plan一致；完成后再次检查文件及数据库绑定，避免诊断期间变化。修复应保留旧公共工件SHA，以新工件记录复核结果。

## 公共阈值计数独立重算

从获准公共JSON的100项数值直接重算15个总体/分层/对话汇总和两种场景共30个分组，所有计数、分布min/median/max/total、overrun及inclusive边界一致。100个question_id和item_id均唯一，80/20分层、每对话25项完整。

| 原始双门槛分区 | 项数 |
| --- | --- |
| 同时满足160,000 bytes与96,000 regex tokens | 51 |
| 仅bytes超限 | 35 |
| 同时超限 | 14 |
| 仅token超限 | 0 |

49项失败均在resolve，公开记录resolve物理调用数为0；35项字节拒绝与14项完整token拒绝的顺序分类吻合。后14项也超过字节门槛，但先被完整输入token门槛拒绝，不能重复算成额外失败。

| 离线门槛场景 | 可通过两个输入门槛 | bytes超限 | token超限 | 其中同时超限 |
| --- | --- | --- | --- | --- |
| 320,000 bytes＋96,000 regex tokens | 86/100 | 13 | 14 | 13 |
| 320,000 bytes＋192,000 regex tokens | 87/100 | 13 | 0 | 0 |

这些是原完整首次输入的离线阈值算术，不是新模型调用成功率。后一个场景仍有13项超过320,000 bytes；不能推断所有100题可运行，也不能据此授权费用、配置变更或补跑。最大重建输入为480,456 bytes、145,670 regex tokens；本报告未将regex估计解释为provider tokenizer或实际usage。

## 重建与无损探针边界

重建逻辑按expanded候选顺序收集Memory，按Memory的source_ids顺序执行与QueryService相同的来源SQL，使用相同纯时间正规化函数，并按relation_id查询关系。代码核对完整Memory/Source顺序、时间诊断、关系内容、未截断及保存token审计；第一次payload只使用initial analysis、cutoff时间及完整输入，不使用最终resolution或answer。失败Trace的嵌套key顺序按原调用方恢复，synthetic测试核对字节相等；成功项另有保存的live嵌套顺序交叉核对。未保存原始wire capture，因此输出正确标记 `caller_reconstructed_not_captured_on_wire`，不能把重建SHA称为实测原wire SHA。初审P2限制了其冻结归属证明。

compact-user-JSON探针仅移除内层JSON格式空白，解析后的数据与原payload相等、system prompt/schema不变，regex计数不变；公共数据中新跨越字节门槛1项，双门槛可通过从51到52。外层HTTP空白会被transport重新序列化，不节省policy字节，全部报告为0。

现有wire grouping在43项应用，计入decoder guidance并逐项验证解码后payload及Memory相等。它使原字节失败项重新合格的数量为0，双门槛可通过仍为51。完整token门槛先于下游wire grouping，不能让压缩后的较小输入绕过前置token拒绝。数据可逆不证明模型解码正确、语义非劣或未来质量收益，报告保留这些未评估状态。

报告记录的是历史 `deepseek-flash`、analysis/answer disabled、resolution low。两组阈值统计不验证未来 `V4.1-Flash-1017` 加全部thinking disabled后的模型行为，亦不把可变alias证明为不可变服务版本。未来阈值/模型/effort配置与新运行结果应单独授权、记录和验证。

## 新鲜验证与边界

实际独立运行：

```sh
./tools/integration/check.sh tests/test_m5_level_c_input_diagnostics.py -q
```

结果：`9 passed, 1 warning in 1.40s`。warning为既有Starlette/TestClient的httpx弃用提示。测试涵盖canonical失败Trace重建、缺失来源/候选顺序/关系变化拒绝、双门槛边界、数据相等、分组guidance成本、先行token门槛及完整synthetic诊断。另实际运行上述等token来源空格变化复现和独立公共数值重算，没有重跑旧全仓测试。

代码路径只读目标开发数据库的source_turns与memory_relations，没有Gold查询、provider调用或生成服务构造；synthetic测试将HTTP Client与model.generate设为失败陷阱，并比较stage文件前后哈希不变。审查者未在真实stage上执行工具，没有访问真实items、原文、private数据库、Gold、holdout或凭据，真实provider调用为0；没有干预关系session85918。公共报告的provider_calls/gold_read等为工具路径声明，本次没有用私有访问去证明真实执行历史。

## 修复后独立复核：P2 已关闭

2026-11-04，非作者审查者复核最终实现并独立运行诊断测试。入口与出口现在分别调用既有完整 `level_c_audit.audit`，核对完整200项freeze、plan、producer、settings/inputs、准备时保护逻辑快照、查询checkpoint及空evaluation表；两次完整审计结果必须相等。重建来源保持同一只读SQLite事务，结束时另比较freeze/settings/inputs文件哈希。原先等token来源字节变更、缺plan和部分freeze等缺口已覆盖，原P2关闭，未发现新的P0/P1/P2。

新增synthetic回归先证明来源空格变更确实不改token计数但改变messages字节/哈希，再要求实际完整audit拒绝；另覆盖settings、inputs、producer身份变化和重建期间WAL并发写入。正例使用完整200项MockTransport流水线；禁止provider/client调用并验证没有打开原始reference数据库。未以monkeypatch跳过完整审计来证明守卫有效。

| 文件 | 最终 SHA256 |
| --- | --- |
| `tools/m5/level_c_input_diagnostics.py` | `2d8fff7bd6a97a120ec8c0a777f1fdbde13e26a0f0e17eb4502d51f0b5c85b02` |
| `tests/test_m5_level_c_input_diagnostics.py` | `81b44247cc6bcc5612d51b5815d72d32b7cc7aacd0a61af18e814b32fd5beca1` |
| `experiments/m5-development/level-c-input-diagnostics-final-v2.json` | `e129ae0caec789b640533c3a863aa20646213b45859278770c34f6f0721f14af` |

独立新鲜执行相同诊断test命令，结果为 `17 passed, 1 warning in 89.61s`；warning仍为既有Starlette/TestClient的httpx弃用提示。未重复旧全仓或其他预算/压缩测试。

另从获准的public final-v2独立重算和比较：旧v1 SHA仍为 `24efafb219916ca320fb9e2ba451bd9f62564b93ae137fa88dfafa2472dfa2d9`，final-v2的supersedes绑定正确；100项全部数值、原分组统计及A/B场景与旧v1完全相等。新C场景640,000 bytes＋192,000 regex tokens的总体、分层、对话及交叉分组均为全部100项满足原首次输入双门槛。完整性元数据明确200项完整freeze、前后audit相等；本次未打开private stage重新执行真实audit。

C场景100/100只描述历史原完整首次resolve输入在新阈值下的算术可容纳性，没有计入后续校验重试feedback，也没有评估未来全部thinking disabled后的模型质量、provider tokenizer或context是否接受。它不代表100题运行成功、不能保证语义非劣、不能授权补跑或支出。原caller重建而非wire捕获的限制继续适用。此次仍无真实provider调用或private/Gold访问，没有修改作者代码或干预85918。
