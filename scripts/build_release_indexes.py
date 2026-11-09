#!/usr/bin/env python3
"""Build source-bound experiment and component indexes without private QA reads."""
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT=Path(__file__).resolve().parents[1]
WTS=ROOT.parent
ARC=WTS/'research-process-archive-20261103/docs/research-process/entries'
RN=WTS/'research-next-20261101/docs/research-v2'
M5=ROOT/'docs/m5-development'

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def section(text,heading):
    m=re.search(r'^## '+re.escape(heading)+r'\s*\n(.*?)(?=^## |\Z)',text,re.M|re.S)
    return m[1].strip() if m else 'unavailable'

mapping={
0:['ENG-01','ENG-02','ENG-03','ENG-04','ENG-05','ENG-06','ENG-07','ENG-08'],
1:['R15-01','R15-02','R15-03','R15-04'],2:['R15-04'],3:['R15-05','R15-06'],4:['R15-07','R15-08'],5:['SHOW-01'],
6:['DYN-01','DYN-02','DYN-03','DYN-04'],7:['DIAG-01','TOP7-01','TOP7-02','TOP7-03','TOP7-04'],8:['VERB-01'],
9:['TOP145-01','TOP145-02','TOP145-03','TOP145-04'],10:['INT-01','INT-02'],11:['V2-01'],12:['V2-02','V2-03'],13:['V2-04','V2-05'],14:['V2-06','V2-07','V2-08','V2-09'],
15:['PHASE5_CANARY_RESULTS.md','PHASE6_E7_OFFLINE_RESULTS.md'],16:['PHASE7_FACTUAL_QUALITY_REVIEW.md','PHASE7_FAILURE_ATTRIBUTION_AND_CANDIDATE.md'],
17:['PHASE7_SYSTEM_QUALITY_AUDIT.md'],18:['PHASE8_RESULTS.md','PHASE8_DECISION.md'],19:['PHASE9_RESULTS_AND_DECISION.md','PHASE9_HINDSIGHT_SOURCE_AUDIT.md'],
20:['EXPERIMENT_RESULTS.md','BONUS_FEATURES.md'],21:['DYNAMIC_TRUTH_PROTOCOL.md'],22:['LEVEL_C_RESULTS.md'],23:['LEVEL_C_INPUT_V2_RESULTS.md'],
24:['CONV44_SIXTH_EXPORT_SUCCESSOR_V1_REVIEW.md','CONV44_RELATION_SUCCESSOR_V1_RESULTS.md'],25:['LEVEL_E_RESULTS_V1.md','FINAL_DELIVERY_EVIDENCE_INDEX_V1.md']}
# Exact source names are discovered, never fabricate a missing file.
for i,term in [(15,'PHASE5'),(21,'EFFECTIVE'),(24,'SIX')]:
    directory=RN if i==15 else M5
    candidates=[p.name for p in directory.glob('*.md') if term in p.name and ('RESULT' in p.name or 'REVIEW' in p.name or 'EXPORT' in p.name)]
    for name in candidates:
        if name not in mapping[i]:mapping[i].append(name)
metrics=json.loads((ROOT/'docs/supplement/data/metrics.json').read_text())
rows=[]
for i,refs in mapping.items():
    metadata=next(x for x in metrics['timeline'] if x['id']==f'E{i}')
    docs=[]
    for ref in refs:
        directory=ARC if i<=14 else RN if i<=19 else M5
        path=directory/(ref if ref.endswith('.md') else ref+'.md')
        if not path.exists():
            docs.append({'path':str(path),'status':'unavailable'});continue
        text=path.read_text()
        info={'path':str(path),'sha256':sha(path),'status':'available_local',
              'in_public_package':path.is_relative_to(M5),
              'source_ref':('3e64811:docs/research-process/entries/' if i<=14 else '97bfaaa:docs/research-v2/' if i<=19 else '28ce63d:docs/m5-development/')+path.name}
        repo=path
        while repo!=repo.parent and not (repo/'.git').exists():repo=repo.parent
        if (repo/'.git').exists():
            rel=str(path.relative_to(repo))
            info['tracked_at_recorded_head']=subprocess.run(['git','cat-file','-e',('3e64811' if i<=14 else '97bfaaa' if i<=19 else '28ce63d')+':'+rel],cwd=ROOT,capture_output=True).returncode==0
        for heading,key in [('配置','model_configuration'),('执行代码身份','code_commit'),('Run ID','run_id'),('Build ID','build_id'),('统计分母','input_denominator'),('费用口径','cost_ledger'),('复核类型','scoring_reviewer'),('结论与采用状态','conclusion')]:
            value=section(text,heading)
            if value!='unavailable':info[key]=value
        docs.append(info)
    row={'experiment':f'E{i}','title':metadata['label'],'dates':metadata['start']+'–'+metadata['end'],
         'research_question':'RQ1 / RQ2 / RQ3; precise stage hypothesis in source documents',
         'strategies':'Full Text / Vector / Hybrid / Dynamic according to source; Bonus and ablations only as explicitly recorded',
         'documents':docs,'private_archive':'archive-v1 research-evidence.tar.gz + archive-source-v2; full member SHA inventory kept locally',
         'free_recompute':'Only frozen summaries/hash/structure/offline source replay; no new model generation',
         'controlled_source_required':True,'paid_reexecution_allowed':False,
         'raw_missing_policy':'Historical /tmp or absent raw artifacts are unavailable; a document is not proof raw data still exists',
         'result_identity':'Original source commit/Run/Build; current Release has no new QA score'}
    if i==2:row['limitation']='E2 quality increments share R15 source; no uniquely named standalone raw archive established, partial provenance'
    rows.append(row)
(ROOT/'experiments/personal-release/experiment-archive-index.json').write_text(json.dumps({'version':'personal-experiments-e0-e25-v1','experiments':rows},indent=2,ensure_ascii=False)+'\n')
lines=['# E0–E25 实验档案索引','','原件保留，未重新评分/生成。机器索引 `experiments/personal-release/experiment-archive-index.json` 逐条保存文档SHA、配置、commit、Build/Run、分母、审阅及成本原字段；缺字段不补造。历史源文档未必在公开包，明确in_public_package；它们可从固定Git对象或本机受控归档定位。','','| 实验 | 研究单元 | 来源（按记录时HEAD/本地SHA） | 归档/测量边界 |','|---|---|---|---|']
for row in rows:
    names=', '.join(Path(d['path']).name+(' unavailable' if d['status']=='unavailable' else '') for d in row['documents'])
    lines.append(f"| {row['experiment']} | {row['dates']} {row['title']} | {names} | 免费校验；原文/Gold受控；付费重跑不允许 |")
lines += ['','## 研究者与评审者入口','','- `scripts/personal-release verify-public-evidence --manifest public-evidence-manifest.json --directory .`：包内逐文件SHA/JSON，无key/原文。','- `scripts/personal-release verify-private-archive --manifest <private-archive-manifest.json> --directory <archive-dir>`：合法本机受控成员SHA、安全路径/JSON/SQLite检查，不执行历史runner。','- `scripts/personal-release replay-offline-demo`：只读Synthetic文件，不能冒充真实答案分数。','- `scripts/personal-release run-tests`：当前工程离线全仓；公开包使用`--public`明确排controlled_data。','','E12旧757与E22开发100/E23同100新配置/E25留出400分开。类别5字面拒答、Source Recall代理、AI标签/教师真值、费用预约/已报usage/实际账单分开。完整分母失败记零，不以成功子集替代。','','E0–E14源为3e64811；E15–E19研究工作区97bfaaa及未提交文件，source_ref不存在时tracked_at_recorded_head=false，以本地SHA和归档为准。E2仅共享R15来源，精确独立raw身份partial。Hindsight外部完整后端未完成，不是App正式功能。','','主档35,440成员/2,301,324,861bytes，SHA bfb7f58a42cf5f76e35db580f06e215a3bc15beb691892d781a02fa0251f5ddd；源码补档2,446成员/5,880,956bytes，SHA 546a29a16cf4a7cffd40200a7a82cdb03112eb43833f83320e676f2e77200eef。完整路径及恢复验证见LOCAL_ARCHIVE_AND_CLEANUP_PLAN。受保护日志/凭据/caches未复制，原位保留；既有Level E白名单原档也完整保留。']
(ROOT/'EXPERIMENT_ARCHIVE_INDEX.md').write_text('\n'.join(lines)+'\n')
print('indexed',len(rows),'experiments; missing source documents',[(r['experiment'],Path(d['path']).name) for r in rows for d in r['documents'] if d['status']=='unavailable'])
