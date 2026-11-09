"""Index a frozen conv-44 successor locally, then prepare one paid relation phase.

Preparation never authorizes generation. Only the explicit successor is mutable;
its inherited facts and extraction provenance remain frozen throughout.
"""
import argparse
from collections import Counter
from decimal import Decimal
import json
from pathlib import Path
import sqlite3

import httpx

from locomo_memory.builds import BuildService
from locomo_memory.config import Settings
from locomo_memory.database import Database, backend_ownership
from locomo_memory.embeddings import MiniLMEmbedder
from locomo_memory.m5_budget import BudgetTransport
from locomo_memory.model import DeepSeekModel
from locomo_memory.relations import RelationService
from locomo_memory.retrieval import RetrievalService
from tools.m5 import conv44_successor as successor
from tools.m5.holdout_relations import BASE_POLICY, NoProvider
from tools.m5.offline import ROOT, sha, write

VERSION = 'm5-conv44-relations-v1'
SCOPE = 'conv-44 explicit successor relation phase only; no publish/query/QA'
BASE_TABLES = {'datasets','import_artifacts','conversations','source_turns',
               'build_versions','build_fragments','memories','memory_sources'}
INDEX_TABLES = {'build_indexes','index_entries','candidate_queries'}
INDEX_MUTABLE = INDEX_TABLES-{'candidate_queries'}
RELATION_TABLES = {'relation_phases','relation_tasks','memory_relations',
                   'current_state_projections','relation_attempts','relation_provider_calls'}
require, digest, readonly = successor.require, successor.digest, successor.prior.readonly
snapshot = successor.prior.legacy.snapshot


def producer_hashes():
    helpers = (Path(__file__), Path(successor.__file__), Path(successor.prior.__file__),
               ROOT/'tools/m5/holdout_relations.py')
    return {**successor.producer_hashes(), **{str(p.relative_to(ROOT)):sha(p) for p in helpers}}


def conversation_only(path, extra=()):
    """Reject evaluation tables/annotations in SQL before reading or hashing rows."""
    with readonly(path) as db:
        tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        require(tables == BASE_TABLES | set(extra), 'conversation_only_tables_required')
        require(not db.execute("SELECT COUNT(*) FROM import_artifacts a,json_each(a.annotations_json) s,"
            "json_each(s.value) f WHERE f.key!='sample_id' AND f.type!='null'").fetchone()[0],
            'nonempty_annotations_forbidden')
        if 'candidate_queries' in tables:
            require(not db.execute('SELECT COUNT(*) FROM candidate_queries').fetchone()[0], 'queries_forbidden')


def settings_at(stage):
    settings = Settings.model_validate_json((stage/'settings.json').read_text())
    require(settings.model_name == BASE_POLICY['model'] and settings.model_retries == 2
        and (settings.relation_max_tokens or settings.model_max_tokens) == BASE_POLICY['max_output_tokens']
        and settings.embedding_local_files_only and not settings.thinking_enabled
        and all(v=='disabled' for k,v in settings.snapshot().items() if k.endswith('_thinking_effort')),
        'disabled_relation_settings_required')
    return settings


def source_identity(stage):
    return dict(database=snapshot(stage/'memory.sqlite3'),ledger=snapshot(stage/'physical-requests.sqlite3'),
        plan=sha(stage/'plan.json'),settings=sha(stage/'settings.json'),inheritance=sha(stage/'inheritance.json'))


def source_check(source, terminal):
    conversation_only(source/'memory.sqlite3')
    frozen = json.loads(terminal.read_text()); plan = json.loads((source/'plan.json').read_text())
    identity = source_identity(source)
    require(frozen['version']==successor.VERSION+'-terminal-v1'
        and frozen['status']=='extracted_not_complete' and all(frozen['checks'].values())
        and identity['database']==frozen['final_database_logical_snapshot']
        and identity['ledger']==frozen['final_ledger_logical_snapshot']
        and identity['plan']==frozen['plan_sha256'], 'source_not_frozen_terminal')
    require(plan['version']==successor.VERSION and plan['scope']==successor.SCOPE
        and plan['implementation_sha256']==successor.producer_hashes()
        and plan['script_sha256']==sha(Path(successor.__file__)), 'source_producer_changed')
    require(successor.parent_snapshot(source/'memory.sqlite3',plan['source_parent_row_bounds'])==plan['parent_rows_snapshot'],
        'source_parent_schema_or_rows_changed')
    require(identity['settings']==plan['settings_sha256'] and identity['inheritance']==plan['inheritance_sha256'],
        'source_config_or_inheritance_changed')
    require(sha(source/'authorization.json')==frozen['authorization_sha256']
        and sha(source/'outcome.json')==frozen['outcome_sha256']
        and json.loads((source/'authorization.json').read_text())==successor.authorization(source), 'source_authorization_changed')
    settings=settings_at(source); bid=frozen['build_id']
    require(bid==plan['build_id'], 'source_build_id_changed')
    # Never instantiate a service against the immutable source database.
    with readonly(source/'memory.sqlite3') as db:
        row=dict(db.execute('SELECT * FROM build_versions WHERE build_id=?',(bid,)).fetchone())
        require(row['sample_id']=='conv-44' and row['status']=='extracted' and row['phase']=='extraction'
            and json.loads(row['config_json'])==settings.snapshot(), 'source_build_scope_changed')
        metadata=json.loads(row['model_metadata_json'])
        provenance=json.loads((source/'inheritance.json').read_text())
        require(provenance['successor_build_id']==bid and provenance['mixed_extraction_producers']
            and metadata['inheritance']['provenance_sha256']==digest(provenance), 'source_provenance_changed')
    return settings,bid,identity


def copy_stage(source, output, settings):
    output.mkdir(parents=True,exist_ok=False,mode=0o700)
    with readonly(source/'memory.sqlite3') as src,sqlite3.connect(output/'memory.sqlite3') as dst:src.backup(dst)
    (output/'memory.sqlite3').chmod(0o600)
    write(output/'settings.json',settings.snapshot())  # db_path is part of the producer fingerprint.
    write(output/'inheritance.json',json.loads((source/'inheritance.json').read_text()))
    return BuildService(Database(output/'memory.sqlite3'),settings,NoProvider())


def metadata_at(path,bid):
    with readonly(path) as db:
        return json.loads(db.execute('SELECT model_metadata_json FROM build_versions WHERE build_id=?',(bid,)).fetchone()[0])


def schema_snapshot(path, excluded=()):
    with readonly(path) as db:
        return digest([tuple(r) for r in db.execute('SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY type,name')
            if r['tbl_name'] not in excluded])


def protected(path,bid,initial,mutable):
    """Preserve all existing facts, other Builds, and the extraction call prefix."""
    data={}
    with readonly(path) as db:
        tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        for name in sorted(tables):
            rows=[]
            for raw in db.execute('SELECT * FROM "'+name+'"'):
                row=dict(raw)
                if name in mutable and row.get('build_id')==bid:continue
                if name in {'relation_attempts','relation_provider_calls'} and name in mutable:
                    if db.execute('SELECT 1 FROM relation_tasks WHERE task_id=? AND build_id=?',(row['task_id'],bid)).fetchone():continue
                if name=='build_versions' and row['build_id']==bid:
                    for key in ('status','phase','updated_at'):row.pop(key)
                    metadata=json.loads(row['model_metadata_json']); calls=metadata.get('calls',[])
                    require(metadata.get('returned_models',[])==list(dict.fromkeys(c['returned_model'] for c in calls if c.get('returned_model'))), 'returned_models_changed')
                    require(calls[:len(initial['calls'])]==initial['calls'], 'extraction_calls_changed')
                    metadata['calls']=calls[:len(initial['calls'])]
                    metadata['returned_models']=initial.get('returned_models',[])
                    row['model_metadata_json']=metadata
                rows.append(json.dumps(row,sort_keys=True,ensure_ascii=False,default=str))
            # Empty newly-created phase tables carry no preexisting rows.
            if rows:data[name]=sorted(rows)
        require(not db.execute('PRAGMA foreign_key_check').fetchall(),'foreign_key_failure')
    schema_additions=INDEX_TABLES if mutable==INDEX_MUTABLE else mutable
    return digest(dict(rows=data,schema=schema_snapshot(path,schema_additions)))


def index(source, terminal, output, embedder=None):
    source,terminal,output=source.resolve(),terminal.resolve(),output.resolve()
    settings,bid,before=source_check(source,terminal)
    initial=metadata_at(source/'memory.sqlite3',bid)
    preserved=protected(source/'memory.sqlite3',bid,initial,INDEX_MUTABLE)
    builds=copy_stage(source,output,settings)
    builds.require_current_contract(builds.get(bid))
    retrieval=RetrievalService(builds,settings,embedder or MiniLMEmbedder(settings),NoProvider())
    info=retrieval.create_index(bid)
    conversation_only(output/'memory.sqlite3',INDEX_TABLES)
    require(metadata_at(output/'memory.sqlite3',bid)==initial
        and protected(output/'memory.sqlite3',bid,initial,INDEX_MUTABLE)==preserved
        and source_identity(source)==before,'index_protected_state_changed')
    summary=dict(version=VERSION,status='indexed_not_complete',scope=SCOPE,build_id=bid,
        source_stage=str(source),source_terminal=str(terminal),source_terminal_sha256=sha(terminal),source_identity=before,
        database_snapshot=snapshot(output/'memory.sqlite3'),schema_sha256=schema_snapshot(output/'memory.sqlite3'),settings_sha256=sha(output/'settings.json'),
        inheritance_sha256=sha(output/'inheritance.json'),implementation_sha256=producer_hashes(),
        script_sha256=sha(Path(__file__)),index=info,initial_metadata=initial,protected_snapshot=preserved,
        provider_requests=0,holdout_qa_read=False,published=False)
    write(output/'index-summary.json',summary)
    return summary


def check_index(stage):
    conversation_only(stage/'memory.sqlite3',INDEX_TABLES)
    summary=json.loads((stage/'index-summary.json').read_text());settings=settings_at(stage)
    require(summary['version']==VERSION and summary['status']=='indexed_not_complete'
        and summary['scope']==SCOPE and summary['implementation_sha256']==producer_hashes()
        and summary['script_sha256']==sha(Path(__file__)),'index_producer_changed')
    require(summary['database_snapshot']==snapshot(stage/'memory.sqlite3')
        and summary['schema_sha256']==schema_snapshot(stage/'memory.sqlite3')
        and summary['settings_sha256']==sha(stage/'settings.json')
        and summary['inheritance_sha256']==sha(stage/'inheritance.json'),'index_identity_changed')
    source=Path(summary['source_stage']);terminal=Path(summary['source_terminal'])
    require(sha(terminal)==summary['source_terminal_sha256'],'source_terminal_changed')
    _,bid,identity=source_check(source,terminal)
    require(bid==summary['build_id'] and identity==summary['source_identity'],'index_source_changed')
    return settings,summary


def task_rows(path,bid):
    with readonly(path) as db:
        return [{k:v for k,v in dict(row).items() if k not in {'status','attempts','error_code','metadata_json'}}
            for row in db.execute('SELECT * FROM relation_tasks WHERE build_id=? ORDER BY ordinal',(bid,))]


def terminal_calls(db,bid):
    """Bind durable logical/provider identities to closed task outcomes."""
    calls=[];task_calls=[];code='relation_attempt_identity_or_terminal_changed'
    tasks=db.execute('SELECT * FROM relation_tasks WHERE build_id=? ORDER BY ordinal',(bid,)).fetchall()
    for task in tasks:
        attempts=db.execute('SELECT * FROM relation_attempts WHERE task_id=? ORDER BY logical_attempt',(task['task_id'],)).fetchall()
        require(task['status'] in {'succeeded','failed'} and task['attempts']==1
            and [a['logical_attempt'] for a in attempts]==list(range(1,task['attempts']+1)),code)
        for attempt in attempts:
            require(attempt['status']==task['status'] and attempt['error_code']==task['error_code']
                and (task['status']!='succeeded' or task['error_code'] is None)
                and bool(attempt['started_at']) and bool(attempt['completed_at'])
                and attempt['completed_at']>=attempt['started_at'],code)
            providers=db.execute('SELECT * FROM relation_provider_calls WHERE task_id=? AND logical_attempt=? ORDER BY provider_attempt',
                (task['task_id'],attempt['logical_attempt'])).fetchall()
            require([r['provider_attempt'] for r in providers]==list(range(1,len(providers)+1)) and len(providers)<=3,code)
            for row in providers:
                call=json.loads(row['metadata_json'])
                expected=dict(build_id=bid,task_id=row['task_id'],logical_attempt=row['logical_attempt'],
                    provider_attempt=row['provider_attempt'],attempt=row['provider_attempt'],
                    call_id=f"{row['task_id']}:{row['logical_attempt']}:{row['provider_attempt']}")
                require(all(call.get(k)==v for k,v in expected.items())
                    and call.get('status') in {'succeeded','model_timeout','model_http_error','invalid_output','context_length_exceeded'}
                    and call.get('outcome')==call['status'] and bool(call.get('completed_at'))
                    and bool(call.get('timestamp')) and call['completed_at']>=call['timestamp'],code)
                calls.append(call)
            # A failed local transport rejection may have no physical checkpoint.
            require(task['status']!='succeeded' or bool(providers) and calls[-1]['status']=='succeeded',code)
        task_calls.extend(json.loads(task['metadata_json']).get('calls',[]))
    return calls,task_calls


def policy_for(count,settings):
    settings_at_values = settings.relation_thinking_effort=='disabled' and settings.model_retries==2
    require(settings_at_values,'disabled_relation_settings_required')
    maximum=(Decimal(BASE_POLICY['max_input_bytes'])*Decimal('.30')+
             Decimal(BASE_POLICY['max_output_tokens'])*Decimal('1.20'))/1000000*3*count
    return dict(BASE_POLICY,max_requests=3*count,max_usd=str(maximum))


def prepare(index_stage,output):
    index_stage,output=index_stage.resolve(),output.resolve()
    settings,summary=check_index(index_stage);bid=summary['build_id']
    initial=metadata_at(index_stage/'memory.sqlite3',bid)
    preserved=protected(index_stage/'memory.sqlite3',bid,initial,RELATION_TABLES)
    builds=copy_stage(index_stage,output,settings)
    service=RelationService(builds,NoProvider());progress=service.start(bid)
    conversation_only(output/'memory.sqlite3',INDEX_TABLES|RELATION_TABLES)
    tasks=task_rows(output/'memory.sqlite3',bid);policy=policy_for(len(tasks),settings)
    BudgetTransport(output/'physical-requests.sqlite3',None,**policy).close()
    require(metadata_at(output/'memory.sqlite3',bid)==initial
        and protected(output/'memory.sqlite3',bid,initial,RELATION_TABLES)==preserved
        and snapshot(index_stage/'memory.sqlite3')==summary['database_snapshot'],'prepare_protected_state_changed')
    plan=dict(version=VERSION,status='prepared_not_authorized',scope=SCOPE,build_id=bid,policy=policy,
        relation_tasks=len(tasks),comparisons=sum(len(json.loads(t['history_ids_json'])) for t in tasks),
        tasks_sha256=digest(tasks),initial_metadata=initial,protected_snapshot=preserved,
        source_index_stage=str(index_stage),source_index_summary_sha256=sha(index_stage/'index-summary.json'),
        source_identity=summary['source_identity'],source_terminal_sha256=summary['source_terminal_sha256'],
        source_ledger_snapshot=summary['source_identity']['ledger'],
        settings_sha256=sha(output/'settings.json'),inheritance_sha256=sha(output/'inheritance.json'),
        implementation_sha256=producer_hashes(),script_sha256=sha(Path(__file__)),
        prepared_database_snapshot=snapshot(output/'memory.sqlite3'),prepared_schema_sha256=schema_snapshot(output/'memory.sqlite3'),prepared_ledger_snapshot=snapshot(output/'physical-requests.sqlite3'),
        provider_requests=0,thinking='disabled',holdout_qa_read=False,published=False,progress=progress,
        price_basis='2026-11-04 peak cache-miss .30 input / 1.20 output USD per million; recheck before execution')
    write(output/'plan.json',plan)
    write(output/'authorization-template.json',{**authorization(output),'approved':False})
    return plan


def authorization(stage):
    plan=json.loads((stage/'plan.json').read_text())
    return dict(approved=True,version=VERSION,scope=SCOPE,build_id=plan['build_id'],
                policy=plan['policy'],plan_sha256=sha(stage/'plan.json'))


def execute(stage,delegate=None):
    stage=stage.resolve()
    require(not (stage/'execution-started.json').exists(),'relation_stage_already_started')
    require(json.loads((stage/'authorization.json').read_text())==authorization(stage),'relation_authorization_mismatch')
    p=json.loads((stage/'plan.json').read_text());settings=settings_at(stage)
    require(p['version']==VERSION and p['status']=='prepared_not_authorized' and p['scope']==SCOPE
        and p['policy']==policy_for(p['relation_tasks'],settings)
        and p['implementation_sha256']==producer_hashes() and p['script_sha256']==sha(Path(__file__)), 'relation_producer_or_plan_changed')
    require(p['settings_sha256']==sha(stage/'settings.json') and p['inheritance_sha256']==sha(stage/'inheritance.json'),
        'relation_config_or_inheritance_changed')
    source=Path(p['source_index_stage']);_,summary=check_index(source)
    require(sha(source/'index-summary.json')==p['source_index_summary_sha256']
        and summary['source_identity']==p['source_identity'] and summary['build_id']==p['build_id']
        and summary['source_terminal_sha256']==p['source_terminal_sha256']
        and summary['source_identity']['ledger']==p['source_ledger_snapshot'],'relation_source_changed')
    target=stage/'memory.sqlite3';bid=p['build_id']
    with backend_ownership(target):
        conversation_only(target,INDEX_TABLES|RELATION_TABLES)
        require(snapshot(target)==p['prepared_database_snapshot'] and schema_snapshot(target)==p['prepared_schema_sha256']
            and snapshot(stage/'physical-requests.sqlite3')==p['prepared_ledger_snapshot'],'relation_prepared_state_changed')
        builds=BuildService(Database(target),settings,NoProvider());build=builds.get(bid)
        builds.require_current_contract(build)
        require(build['sample_id']=='conv-44' and build['status']=='queued' and build['phase']=='relations'
            and digest(task_rows(target,bid))==p['tasks_sha256'],'relation_task_scope_changed')
        write(stage/'execution-started.json',dict(scope=SCOPE,plan_sha256=sha(stage/'plan.json')))
        own=delegate is None;delegate=httpx.HTTPTransport(retries=0) if own else delegate
        try:
            guard=BudgetTransport(stage/'physical-requests.sqlite3',delegate,**p['policy'])
            service=RelationService(builds,DeepSeekModel(settings,transport=guard));service.run(bid)
        finally:
            if own:delegate.close()
        require(schema_snapshot(target)==p['prepared_schema_sha256']
            and protected(target,bid,p['initial_metadata'],RELATION_TABLES)==p['protected_snapshot']
            and digest(task_rows(target,bid))==p['tasks_sha256'],'relation_protected_state_changed')
        check_index(source)
        require(sha(source/'index-summary.json')==p['source_index_summary_sha256']
            and sha(stage/'settings.json')==p['settings_sha256']
            and producer_hashes()==p['implementation_sha256']
            and sha(Path(__file__))==p['script_sha256'],'relation_producer_or_source_changed')
        require(sha(stage/'inheritance.json')==p['inheritance_sha256'],'relation_inheritance_changed')
        with readonly(target) as db:
            calls,task_calls=terminal_calls(db,bid)
            relations=db.execute('SELECT COUNT(*) FROM memory_relations WHERE build_id=?',(bid,)).fetchone()[0]
        result=builds.get(bid);builds.require_current_contract(result)
        progress=service.progress(bid)
        require(result['status'] in {'related','relations_failed'} and result['phase']=='relations'
            and progress['status'] in {'succeeded','failed'}
            and progress['prompt_version']==p['progress']['prompt_version']
            and progress['schema_version']==p['progress']['schema_version']
            and (progress['status']!='succeeded' or progress['error_code'] is None)
            and (result['status']=='related')==(progress['status']=='succeeded')
            and (result['status']!='related' or progress['progress']['failed']==0)
            and not progress['progress']['pending'],'relation_attempt_identity_or_terminal_changed')
        require(calls==task_calls and result['model_metadata']['calls']==p['initial_metadata']['calls']+calls,
            'relation_call_history_changed')
        with readonly(stage/'physical-requests.sqlite3') as db:rows=db.execute('SELECT * FROM physical_requests ORDER BY rowid').fetchall()
        require(len(rows)==len(calls)<=p['policy']['max_requests']
            and [json.loads(r['usage_json']) or {} for r in rows]==[c.get('usage',{}) for c in calls]
            and all((r['status']=='transport_unknown') != bool(c.get('response_received')) for r,c in zip(rows,calls))
            and all(c['thinking']=={'type':'disabled'} and c.get('reasoning_effort') is None for c in calls), 'relation_ledger_calls_changed')
        tokens=Counter();unknown=0;unknown_reserved=Decimal(0)
        for row in rows:
            usage=json.loads(row['usage_json'])
            if not isinstance(usage,dict) or not all(type(usage.get(k)) is int for k in ('prompt_tokens','completion_tokens')):
                unknown+=1;unknown_reserved+=Decimal(row['reserved_usd'])
            if isinstance(usage,dict):tokens.update(usage)
        reserved=sum((Decimal(r['reserved_usd']) for r in rows),Decimal(0))
        require(reserved<=Decimal(p['policy']['max_usd']),'relation_budget_exceeded')
        outcome=dict(version=VERSION,scope=SCOPE,build_id=bid,status=result['status'],phase=result['phase'],
            progress=progress,relations=relations,physical_requests=len(rows),reserved_usd=str(reserved),
            reported_tokens=dict(tokens),known_usage_peak_upper_usd=str((Decimal(tokens['prompt_tokens'])*Decimal('.30')+Decimal(tokens['completion_tokens'])*Decimal('1.20'))/1000000),
            unknown_usage_requests=unknown,unknown_reserved_usd=str(unknown_reserved),request_statuses=dict(Counter(r['status'] for r in rows)),
            inherited_extraction_calls=len(p['initial_metadata']['calls']),protected_state_unchanged=True,
            thinking='disabled',holdout_qa_read=False,published=False,automatic_retry=False,actual_invoice='not_accessed')
        write(stage/'outcome.json',outcome)
    if result['status']!='related':raise RuntimeError('relation_stage_incomplete_no_automatic_retry')
    return outcome


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode',choices=('index','prepare','execute-authorized'))
    parser.add_argument('--source',type=Path);parser.add_argument('--source-terminal',type=Path)
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    if args.mode=='index':
        if args.source is None or args.source_terminal is None:parser.error('index requires --source and --source-terminal')
        result=index(args.source,args.source_terminal,args.output)
    elif args.mode=='prepare':
        if args.source is None:parser.error('prepare requires --source index stage')
        result=prepare(args.source,args.output)
    else:result=execute(args.output)
    print(json.dumps({k:result[k] for k in ('version','status','build_id','provider_requests','relation_tasks','policy','physical_requests') if k in result}))
