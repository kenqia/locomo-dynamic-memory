# 实验附录核验与勘误

原件来自 docs/experiment-supplement@3392faf，37页，PDF SHA256 `2398340833f500690b6d511756ce04d117cae755cfca4a4e5a1489a36a007da3`。本Release按原件保存，未覆盖冻结实验。独立研究过程记录，不是团队最终报告。

`UV_PROJECT_ENVIRONMENT=$PWD/var/supplement-build-venv bash docs/supplement/build.sh` 实际成功；20张图重建，37页，`pdftotext -layout`输出与原件逐字一致。重建PDF SHA `edf15fed6daa1b328e03eb235cfe32aaf02364b84ae281ab01c2669c85fb97d4`，字节3488506，对原件3488513；创建时间/PDF元数据不同。原件及图表恢复为3392faf的精确字节；重建副本保留在受控交付区appendix-rebuilt，不用新元数据冒充旧SHA。

## 内容勘误（优先于附录原措辞）

- supplement.md第37/696行的conv44 6973关系、6769 undetermined是恢复前历史快照。最终第六份JSON为392 Memory、7134关系、384/384任务，六份合计2031/37445；完整性不是语义准确率。
- 第650行“只放宽输入上限”不可作单变量因果结论。E22→E23同时改变messages字节上限160000→640000、resolve代理tokens96000→192000及resolution thinking low→disabled。样本相同，配置不同；不能把差异仅归因于预算。
- metrics.json中RN PHASE7_FAILURE_ATTRIBUTION_AND_CANDIDATE.md确实在research-next工作区，但不是97bfaaa已提交Git对象。原文件8200bytes，SHA `618042ab3a20dfb843fcb0420e4711b2f4fe38b10ad6c38bb7f0677299f740e1`，列入受控归档；不称全部来源已冻结Git。其35题次分布及5/8抽取缺口与文档相符，其它5种src引用均可定位Git对象。数值被保留，provenance解释被修正。
- f1_by_stage E5为16道可回答题成功项口径；E12、E22/E23、E25不可跨样本/模型/thinking/分母作严格因果比较。类别5为字面拒答，Source Recall是来源代理，单AI标签不是人工/教师真值。

- cost_ratio._note把全部行统称cache-miss峰价不准确：E12人民币9.597679/98.930522来自reported hit/miss价格，含cache-hit和miss；后三轮M5美元才是all-input-cache-miss峰价上界。金额数值不改，引用时保留各自原价格口径。

282个数值叶字段已由非作者实际核对，0差异：201字段来自结构化JSON、81来自冻结公开报告表；28来源SHA已绑定。日期/标签/因果表述及历史raw未完整重新评分，因此总体数值审计保守标PARTIAL。脚本和报告见scripts/verify_supplement_metrics.py及experiments/personal-release/independent-metrics-audit.json。

## 版面与构建边界

全部37页已实际渲染并检查总览：目录、中文、20图、表格均在页面内；第31–32页实验大表有跨页，内容按列换行，未观察页面外裁切。字体表见experiments/personal-release/supplement-rebuild.json，CJK字体已嵌入。图注和金额/秒/token单位保留。未做印刷色彩校样。

原build.sh对matplotlib只声明`--with`，不是完全锁定的排版环境；本次隔离环境版本另存记录，不能保证未来任意matplotlib版本字节一致。无需模型/API key，禁止用此命令重跑实验。附录源日期2026-11-05正确。
