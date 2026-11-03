"""Read-only historical audit and exclusive offline full-baseline identity freeze."""
import argparse
from collections import Counter
from datetime import datetime, timezone, timedelta
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import urllib.request

from locomo_memory.config import Settings
from locomo_memory.model import utc_now
from locomo_memory.experiment import write_json
from tools.research_v2.full_baseline import (ROOT, PREFLIGHT, DEVELOPMENT, STRATEGIES, IDENTITY,
    digest, read, dependencies, validate_plan)
from tools.research_v2.full_budget import LIMITS
from tools.research_v2.observer import Halt, sha
from tools.research_v2.prepare import prepare
from tools.research_v2.smoke import code_identity

SMOKE=ROOT/'var/research-v2-resolution-smoke-96000-20261101'
ARCHIVE=ROOT.parent.parent/'locomo-archives/20261101-research-v2-resolution96000'
PUBLIC=ROOT/'experiments/research-v2/full-baseline'
RUNTIME=ROOT/'var/research-v2-full-baseline-20261101'


class Text(HTMLParser):
    def __init__(self): super().__init__(); self.parts=[]
    def handle_data(self,value): self.parts.append(value)


def contract_from_pages(pages):
    text={}
    for k,raw in pages.items():
        parser=Text();parser.feed(raw.decode());text[k]=' '.join(parser.parts)
    pricing=text['pricing']
    patterns=['DeepSeek-V4.1-Flash-1017','deepseek-flash','1M','最大 384K',
              r'高峰时段\s+0\.04元\s+0\.30元',r'高峰时段\s+2元\s+9\.0元',
              r'高峰时段\s+8元\s+27\.0元',r'并发限制.*?2500\s+500']
    if not all(re.search(p,pricing) for p in patterns): raise Halt('official_pricing_requires_review')
    if not all(s in text['chat'] for s in ('max_tokens','393216','reasoning_effort','prompt_cache_hit_tokens','prompt_cache_miss_tokens')):
        raise Halt('official_chat_contract_requires_review')
    return dict(model='deepseek-flash',documented_version='DeepSeek-V4.1-Flash-1017',context_tokens=1048576,
                max_output_tokens=393216,price_nano_cny_per_token={'hit':40,'miss':2000,'output':8000},
                provider_concurrency_limit=2500,application_concurrency_limit=1,
                endpoint='https://api.deepseek.com/chat/completions',format='json_object')


def fetch_contract(directory):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=False,mode=0o700)
    rows=[];pages={}
    for name,route in [('pricing','quick_start/pricing'),('chat','api/create-chat-completion'),('cache','guides/kv_cache')]:
        url='https://api-docs.deepseek.com/zh-cn/'+route
        with urllib.request.urlopen(url,timeout=30) as response: raw=response.read()
        p=directory/(name+'.html');p.write_bytes(raw);os.chmod(p,0o600);pages[name]=raw
        rows.append(dict(name=name,url=url,path=str(p.resolve()),sha256=digest(p),
                         retrieved_at=datetime.now(timezone.utc).isoformat()))
    result=dict(contract=contract_from_pages(pages),sources=rows,paid_provider_calls=0)
    write_json(directory/'sources.json',result)
    return result


def daily_contract_guard(identity, *, today=None, fetch=fetch_contract):
    """Recheck public contract before the first physical model send each Beijing day."""
    today=today or (lambda:datetime.now(timezone(timedelta(hours=8))).date().isoformat())
    checked=today()
    def guard():
        nonlocal checked
        day=today()
        if day!=checked:
            result=fetch(Path(identity['control_directory'])/('daily-contract-'+day))
            if result['contract']!=identity['official_contract']['contract']:
                raise Halt('official_contract_changed')
            checked=day
    return guard


def audit_history():
    manifest=read(ARCHIVE/'artifact-manifest.json')
    rows=manifest if isinstance(manifest,list) else manifest['files']
    bad=[r['path'] for r in rows if digest(ARCHIVE/'controlled'/r['path'])!=r['sha256']]
    index=read(ROOT/'experiments/research-v2/resolution96000-archive-index.json')
    old=index if isinstance(index,list) else index['files']
    changed=[r['path'] for r in old if digest(SMOKE/r['path'])!=r['sha256']]
    ident=read(SMOKE/'execution-identity.json')
    frozen_bad=[name for name,h in ident['code_files'].items() if digest(SMOKE/'frozen-code'/name)!=h]
    with sqlite3.connect((SMOKE/'memory.sqlite3').as_uri()+'?mode=ro',uri=True) as db:
        integrity=db.execute('PRAGMA integrity_check').fetchone()[0]
        build=db.execute('SELECT status,config_json,fingerprint FROM build_versions WHERE build_id=?',(ident['build_id'],)).fetchone()
        counts={t:db.execute('SELECT COUNT(*) FROM '+t+' WHERE build_id=?',(ident['build_id'],)).fetchone()[0]
                for t in ('memories','relation_tasks')}
    with sqlite3.connect((SMOKE/'observer/budget.sqlite3').as_uri()+'?mode=ro',uri=True) as db:
        ledger_integrity=db.execute('PRAGMA integrity_check').fetchone()[0]
        physical,unknown,cost=db.execute("SELECT COUNT(*),SUM(status!='settled'),SUM(cost) FROM requests").fetchone()
        policy=json.loads(db.execute('SELECT document FROM policy').fetchone()[0])
        halted=db.execute("SELECT COUNT(*) FROM events WHERE kind='halt'").fetchone()[0]
    run=read(SMOKE/'runs/1f5ad0252c1a4832ba5065f6d7998a41/run.json')
    bundle=ARCHIVE/'research-resolution-delivery.bundle'
    verify=subprocess.run(['git','bundle','verify',str(bundle)],cwd=ROOT,capture_output=True)
    result=dict(passed=not bad and not changed and not frozen_bad and integrity==ledger_integrity=='ok' and verify.returncode==0
                and build[0]=='complete' and run['progress']['succeeded']==20 and unknown==0 and bool(halted),
        archive_files_checked=len(rows),archive_mismatches=bad,smoke_files_checked=len(old),smoke_mismatches=changed,
        frozen_code_files_checked=len(ident['code_files']),frozen_code_mismatches=frozen_bad,
        sqlite_integrity=integrity,ledger_integrity=ledger_integrity,bundle_verified=verify.returncode==0,bundle_sha256=digest(bundle),
        smoke_identity_sha256=digest(SMOKE/'execution-identity.json'),build_id=ident['build_id'],build_status=build[0],build_counts=counts,
        producer_config=json.loads(build[1]),producer_fingerprint=build[2],run_id=run['run_id'],progress=run['progress'],
        final_smoke_physical=physical,cumulative_physical=physical+policy['prior_requests'],
        cumulative_peak_nano_cny=cost+policy['prior_cost_nano_cny'],unknown_billing=unknown,ledger_halted=bool(halted))
    if result['smoke_identity_sha256']!='f7d53c5ee721c182c291ba0019f26b89839ea7c6081f2dc05a3a4a56cd9d6b2e':
        result['passed']=False
    write_json(PREFLIGHT/'history-audit.json',result)
    if not result['passed']: raise Halt('historical_evidence_changed')
    return result


def freeze(tests):
    os.umask(0o077)
    if IDENTITY.exists(): raise Halt('identity_already_frozen')
    import xml.etree.ElementTree as ET
    tree=ET.parse(tests).getroot();suites=list(tree.iter('testsuite'))
    if not suites or any(int(s.get(k,'0')) for s in suites for k in ('errors','failures','skipped')):
        raise Halt('fresh_tests_required')
    required={'test_full_request_ceiling_exact','test_full_money_reservation_boundary',
        'test_crash_receipt_cannot_be_reset_by_new_ledger','test_full_coordinator_fixed_denominator_and_failed_build',
        'test_full_watchdog_preserves_unknown_reservation','test_blind_material_hides_strategy_and_order','test_official_entrypoint_end_to_end_mock_only','test_freeze_artifacts_end_to_end_offline'}
    names={c.get('name') for c in tree.iter('testcase')}
    if not required <= names: raise Halt('required_test_cases_missing')
    audit=audit_history()
    prepared=PREFLIGHT/'prepared'
    record=prepare(prepared,verify_embedding=True)
    plan=read(prepared/'plan-development.json');validate_plan(plan)
    inputs=read(prepared/'evaluation-input-development.json')
    if [(x['sample_id'],x['qa_index'],x['question_id']) for x in inputs['question_identities']] != [(x['sample_id'],x['qa_index'],x['question_id']) for x in plan['questions']]:
        raise Halt('evaluation_input_order_changed')
    pages={k:(PREFLIGHT/'official'/f'{k}.html').read_bytes() for k in ('pricing','chat','cache')}
    official=dict(contract=contract_from_pages(pages),sources=read(PREFLIGHT/'official/sources.json'))
    config=Settings(db_path=RUNTIME/'memory.sqlite3',model_max_tokens=32768,resolution_input_budget=96000).snapshot()
    diff={k:{'old':audit['producer_config'].get(k),'new':v} for k,v in config.items() if audit['producer_config'].get(k)!=v}
    counts={s:{'source_turns':len(read(prepared/'sources'/f'{s}.json')),
               'qa':sum(q['sample_id']==s for q in plan['questions']),
               'sha256':digest(prepared/'sources'/f'{s}.json')} for s in DEVELOPMENT}
    if any((c['source_turns'],c['qa'])!=DEVELOPMENT[s] for s,c in counts.items()): raise Halt('source_counts_changed')
    PUBLIC.mkdir(parents=True,exist_ok=True)
    files={str(p.resolve()):digest(p) for p in [tests,prepared/'memory.sqlite3',prepared/'experiment.json',
        prepared/'plan-development.json',prepared/'evaluation-input-development.json',prepared/'logical-combinations.jsonl',
        PREFLIGHT/'history-audit.json',PREFLIGHT/'preservation-before.json',*[prepared/'sources'/f'{s}.json' for s in DEVELOPMENT],
        *[PREFLIGHT/'official'/f'{s}.html' for s in pages]]}
    for p in sorted((ROOT/'tests').glob('test_research*.py')): files[str(p)]=digest(p)
    manifest=[]
    for i,line in enumerate((prepared/'logical-combinations.jsonl').read_text().splitlines()):
        row=json.loads(line);row.update(ordinal=i,build_creation_token='full-baseline-20261101:'+row['sample_id'],
            build_id=None,run_id=None,status='not_authorized');manifest.append(row)
    manifest_path=PUBLIC/'manifest.jsonl'
    manifest_path.write_text(''.join(json.dumps(x,sort_keys=True)+'\n' for x in manifest))
    files[str(manifest_path)]=digest(manifest_path)
    from locomo_memory import model as prompts
    from locomo_memory.memory_schemas import ExtractionBatch
    from locomo_memory.relation_schemas import RelationBatch
    from locomo_memory.query_schemas import EffectiveResolution, EvidenceAnswer
    from locomo_memory.retrieval_schemas import QueryAnalysis
    contracts={}
    for stage,prompt,schema in [('Extraction',prompts.EXTRACTION_PROMPT,ExtractionBatch),
        ('Relation',prompts.RELATION_PROMPT,RelationBatch),('Query Analysis',prompts.QUERY_ANALYSIS_PROMPT,QueryAnalysis),
        ('Resolution',prompts.RESOLUTION_PROMPT,EffectiveResolution),('Answer',prompts.ANSWER_PROMPT,EvidenceAnswer)]:
        contracts[stage]=dict(prompt_sha256=sha(prompt.encode()),schema_sha256=sha(json.dumps(schema.model_json_schema(),sort_keys=True).encode()))
    identity=dict(stage_contracts=contracts,dependencies_sha256=sha(json.dumps(dependencies(),sort_keys=True).encode()),status='frozen_offline_awaiting_separate_paid_approval',phase='Research v2 Phase 2',
        base_head='33d89330e69f5678735931888d167ab79034a4d3',frozen_at=utc_now(),
        code_files=code_identity(),dependencies=dependencies(),files=files,
        prepared_database=str(prepared/'memory.sqlite3'),prepared_state=str(prepared/'experiment.json'),
        runtime_directory=str(RUNTIME),control_directory=str(PREFLIGHT/'control'),archive_directory=str(ROOT.parent.parent/'locomo-archives/20261101-research-v2-full-baseline'),
        plan_path=str(prepared/'plan-development.json'),manifest_path=str(manifest_path),
        producer_config=config,query_config=config,configuration_type='research; production defaults remain 8192/24000',
        source_identity=record['source_identity'],datasets=counts,question_count=757,combination_count=3028,strategies=STRATEGIES,
        builds={s:{'build_id':None,'creation_token':'full-baseline-20261101:'+s,'policy':'new_independent_complete_build'} for s in DEVELOPMENT},
        run={'run_id':None,'policy':'new persisted research coordinator v3; 3028 items before first paid request; no native v2 resume'},
        conv26_reuse={'permitted':False,'historical_build_id':audit['build_id'],'differences':diff,
                     'reason':'Strict full Settings/fingerprint identity differs; no normalization or silent equivalence.'},
        official_contract=official,expected_system_fingerprint='bc19ba97cbe016479903222bb1578db6',
        provider_identity_policy='mutable alias; compare actual model and fingerprint each response; stop after first mismatch, preserve known usage',
        budget=LIMITS,paid_authorization=None,budget_ledger_path=str(RUNTIME/'observer/budget.sqlite3'),
        budget_claim_path=str(PREFLIGHT/'control/start-claim.json'),
        retry={'physical_max_attempts_per_operation':3,'settings_model_retries':2,
               'unknown':'retain maximum reservation; stop all sends','logical_retries':0,'build_phase_retries':0,'automatic_resume':False},
        denominator_policy='Never remove a logical item. Missing Build -> failed dependency with no attempt. Stop -> pending/unknown retained.',
        scoring=record['scorer_sha256'],tests={'path':str(tests.resolve()),'sha256':digest(tests),'cases':len(list(tree.iter('testcase')))},
        semantic_metrics='independent blind review required; unreviewed is not evaluated',
        smoke_scores_reused=False)
    write_json(IDENTITY,identity)
    write_json(PUBLIC/'sha256-index.json',dict(execution_identity_sha256=digest(IDENTITY),files=files,code_files=identity['code_files']))
    write_json(ROOT/'experiments/research-v2/FULL_BASELINE_BUDGET.json',dict(status='NOT_AUTHORIZED',**LIMITS,
        execution_identity_sha256=digest(IDENTITY),reservation_nano_cny=1048576*2000+32768*8000,
        independent_of_smoke=True,unknown_keeps_reservation=True,reset_or_resume_allowed=False,
        ledger=identity['budget_ledger_path'],claim=identity['budget_claim_path']))
    return dict(status=identity['status'],identity_sha256=digest(IDENTITY),combination_count=3028,
                conv26_reuse=False,paid_calls=0,new_builds=0,new_runs=0)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--tests',type=Path,required=True)
    print(json.dumps(freeze(p.parse_args().tests),indent=2))
