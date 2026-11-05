"""Retry the single closed logical-2 failure in an independent logical-3 copy.

prepare never authorizes calls. execute-authorized stops at related; complete-export
requires a separately audited terminal and writes another local copy. No prior
stage, producer, evidence validator, endpoint or response is modified.
"""
import argparse
import json
from pathlib import Path

import httpx

from locomo_memory.builds import BuildService
from locomo_memory.database import Database, backend_ownership
from locomo_memory.export_schemas import MemoryExport
from locomo_memory.exports import ExportService
from locomo_memory.m5_budget import BudgetTransport
from locomo_memory.model import DeepSeekModel
from locomo_memory.projection import create_projection
from locomo_memory.relation_schemas import relation_label_error
from locomo_memory.relations import RelationService
from locomo_memory.versions import VersionsService
from tools.m5 import conv44_relation_recovery as q
from tools.m5.holdout_relations import NoProvider
from tools.m5.offline import ROOT, sha, write

r=q.r
require,readonly,digest=q.require,q.readonly,q.digest
VERSION='m5-conv44-relation-successor-v1'
TERMINAL='m5-conv44-relation-successor-terminal-v1'
SCOPE='conv-44 single closed logical-2 relation failure only; independent logical-3 retry; no publish/query/QA'
INPUT_VERSION='relation-endpoint-label-prerequisites-v1'
LABELS=('RETAIN','UPDATE','SUPERSEDE','CONFLICT','undetermined')
POLICY=dict(model='deepseek-flash',input_usd_per_million='0.30',output_usd_per_million='1.20',
    max_input_bytes=160000,max_output_tokens=32768,max_requests=3,max_usd='0.2619648')


def producers():
    return {**q.producers(),str(Path(__file__).relative_to(ROOT)):sha(Path(__file__))}


def parent_check(source,terminal):
    p=q.terminal_check(source,terminal,q.TERMINAL,'relations_failed_not_complete')
    outcome=q.audit(source)
    require(outcome==json.loads((source/'outcome.json').read_text()) and outcome['status']=='relations_failed',
        'closed_parent_outcome_required')
    settings=r.settings_at(source);bid=p['build_id']
    require(r.policy_for(1,settings)==POLICY,'successor_exact_policy_required')
    with readonly(source/'memory.sqlite3') as db:
        failed=[dict(row) for row in db.execute("SELECT * FROM relation_tasks WHERE build_id=? AND status='failed' ORDER BY ordinal",(bid,))]
    require(len(failed)==1 and failed[0]['attempts']==2,'single_logical_two_failure_required')
    calls=json.loads(failed[0]['metadata_json']).get('calls',[])
    require(len(calls)==3 and all(c['error_code']=='same_state_dimension_required'
        and c['field_path']=='judgments[1]' for c in calls),'safe_failure_profile_changed')
    return settings,bid,failed,r.metadata_at(source/'memory.sqlite3',bid)


def preserved(path,bid,failed,initial,old_relations):
    """Freeze all earlier attempts, successful tasks, relations and call prefixes."""
    failed_ids={t['task_id'] for t in failed};data={}
    r.conversation_only(path,r.INDEX_TABLES|r.RELATION_TABLES)
    with readonly(path) as db:
        for name, in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
            rows=[]
            for raw in db.execute('SELECT * FROM "'+name+'"'):
                row=dict(raw)
                if name=='build_versions' and row['build_id']==bid:
                    for key in ('status','phase','updated_at'):row.pop(key)
                    metadata=json.loads(row['model_metadata_json']);calls=metadata['calls']
                    require(calls[:len(initial['calls'])]==initial['calls'] and metadata['returned_models']==
                        list(dict.fromkeys(c['returned_model'] for c in calls if c.get('returned_model'))),'old_calls_changed')
                    metadata['calls']=initial['calls'];metadata['returned_models']=initial['returned_models'];row['model_metadata_json']=metadata
                if name=='relation_tasks' and row['task_id'] in failed_ids:
                    for key in ('status','attempts','error_code','metadata_json'):row.pop(key)
                if name in {'relation_attempts','relation_provider_calls'} and row['task_id'] in failed_ids and row['logical_attempt']==3:continue
                if name=='relation_phases' and row['build_id']==bid:row.pop('status');row.pop('error_code')
                if name=='memory_relations' and row['build_id']==bid and row['relation_id'] not in old_relations:continue
                if name=='current_state_projections' and row['build_id']==bid:continue
                rows.append(json.dumps(row,sort_keys=True,ensure_ascii=False,default=str))
            if rows:data[name]=sorted(rows)
        require(not db.execute('PRAGMA foreign_key_check').fetchall(),'foreign_key_failure')
    return digest(dict(rows=data,schema=r.schema_snapshot(path)))


def prepare(source,terminal,output):
    source,terminal,output=source.resolve(),terminal.resolve(),output.resolve()
    settings,bid,failed,initial=parent_check(source,terminal);before=r.source_identity(source)
    with readonly(source/'memory.sqlite3') as db:
        old_relations=[row[0] for row in db.execute('SELECT relation_id FROM memory_relations WHERE build_id=? ORDER BY relation_id',(bid,))]
    frozen=preserved(source/'memory.sqlite3',bid,failed,initial,old_relations)
    builds=r.copy_stage(source,output,settings);progress=RelationService(builds,NoProvider()).start(bid)
    with readonly(output/'memory.sqlite3') as db:
        pending=[dict(row) for row in db.execute("SELECT * FROM relation_tasks WHERE build_id=? AND status='pending' ORDER BY ordinal",(bid,))]
    require(pending==[{**failed[0],'status':'pending','error_code':None}],'retry_queue_changed')
    BudgetTransport(output/'physical-requests.sqlite3',None,**POLICY).close()
    p=dict(version=VERSION,scope=SCOPE,status='prepared_not_authorized',build_id=bid,policy=POLICY,failed_tasks=failed,
        initial_metadata=initial,old_relation_ids=old_relations,preserved_snapshot=frozen,progress=progress,
        source_stage=str(source),source_terminal=str(terminal),source_terminal_sha256=sha(terminal),source_identity=before,
        settings_sha256=sha(output/'settings.json'),inheritance_sha256=sha(output/'inheritance.json'),
        implementation_sha256=producers(),script_sha256=sha(Path(__file__)),input_contract_version=INPUT_VERSION,
        wire_contract_in_build_fingerprint=False,mixed_relation_input_producers=True,
        prepared_database_snapshot=r.snapshot(output/'memory.sqlite3'),prepared_ledger_snapshot=r.snapshot(output/'physical-requests.sqlite3'),
        provider_requests=0,holdout_qa_read=False,old_budget_transferred=False)
    require(preserved(output/'memory.sqlite3',bid,failed,initial,old_relations)==frozen and r.source_identity(source)==before,'parent_changed')
    write(output/'plan.json',p);write(output/'authorization-template.json',{**authorization(output),'approved':False})
    return p


def authorization(stage):
    p=json.loads((stage/'plan.json').read_text())
    return dict(approved=True,version=VERSION,scope=SCOPE,build_id=p['build_id'],policy=POLICY,plan_sha256=sha(stage/'plan.json'))


class EndpointModel:
    def __init__(self,model,failed,wrapper_sha):
        self.previous=q.EndpointModel(model,failed,wrapper_sha)
        self.wrapper_sha=wrapper_sha

    def generate(self,operation,payload,schema,*,context,on_call):
        new=context['new_memory'];matrix={}
        for old in context['history']:
            errors={label:relation_label_error(label,old,new) for label in LABELS}
            matrix[old['memory_id']]=dict(new_memory_id=new['memory_id'],same_state_key=old['state_key']==new['state_key'],
                old_memory_type=old['memory_type'],new_memory_type=new['memory_type'],
                old_statement_type=old['statement_type'],new_statement_type=new['statement_type'],
                allowed_labels=[label for label in LABELS if errors[label] is None],
                forbidden_labels={label:code for label,code in errors.items() if code is not None})
        augmented={**payload,'label_prerequisites_by_old_memory':matrix,
            'label_prerequisite_instruction':'For each old_memory_id independently, choose only an allowed label in its prerequisite row. A label being allowed does not establish its semantic evidence. UPDATE still requires actual same-process stage change and verbatim endpoint stage evidence. Do not change memory identities, state_key, statement types or sources. Do not copy labels between candidates or infer endpoints from a prior judgment index. Regenerate and validate the full batch from the original evidence; never repair a prior response or select a label merely to pass validation.'}
        def observe(call):
            call.update(input_contract_version=INPUT_VERSION,input_wrapper_sha256=self.wrapper_sha)
            on_call(call)
        return self.previous.generate(operation,augmented,schema,context=context,on_call=observe)


def prepared_check(stage):
    p=json.loads((stage/'plan.json').read_text());settings=r.settings_at(stage)
    require(p['version']==VERSION and p['scope']==SCOPE and p['status']=='prepared_not_authorized'
        and p['policy']==POLICY==r.policy_for(1,settings) and p['input_contract_version']==INPUT_VERSION
        and p['implementation_sha256']==producers() and p['script_sha256']==sha(Path(__file__))
        and p['settings_sha256']==sha(stage/'settings.json') and p['inheritance_sha256']==sha(stage/'inheritance.json')
        and json.loads((stage/'authorization.json').read_text())==authorization(stage),'successor_plan_or_authorization_changed')
    source,terminal=Path(p['source_stage']),Path(p['source_terminal'])
    _,bid,failed,initial=parent_check(source,terminal)
    require(bid==p['build_id'] and failed==p['failed_tasks'] and initial==p['initial_metadata']
        and sha(terminal)==p['source_terminal_sha256'] and r.source_identity(source)==p['source_identity'],'parent_identity_changed')
    return p,settings


def new_calls(db,p):
    old=p['failed_tasks'][0];task=dict(db.execute('SELECT * FROM relation_tasks WHERE task_id=?',(old['task_id'],)).fetchone())
    attempts=db.execute('SELECT * FROM relation_attempts WHERE task_id=? ORDER BY logical_attempt',(old['task_id'],)).fetchall()
    code='successor_attempt_identity_or_terminal_changed'
    require(task['attempts']==3 and [a['logical_attempt'] for a in attempts]==[1,2,3] and task['status'] in {'succeeded','failed'},code)
    last=attempts[-1]
    require(last['status']==task['status'] and last['error_code']==task['error_code'] and bool(last['started_at'])
        and bool(last['completed_at']) and last['completed_at']>=last['started_at']
        and (task['status']!='succeeded' or task['error_code'] is None),code)
    providers=db.execute('SELECT * FROM relation_provider_calls WHERE task_id=? AND logical_attempt=3 ORDER BY provider_attempt',(old['task_id'],)).fetchall()
    require([row['provider_attempt'] for row in providers]==list(range(1,len(providers)+1)) and len(providers)<=3,code)
    calls=[]
    for row in providers:
        call=json.loads(row['metadata_json']);expected=dict(build_id=p['build_id'],task_id=old['task_id'],logical_attempt=3,
            provider_attempt=row['provider_attempt'],attempt=row['provider_attempt'],call_id=f"{old['task_id']}:3:{row['provider_attempt']}",
            input_contract_version=INPUT_VERSION,input_wrapper_sha256=p['script_sha256'])
        require(all(call.get(k)==v for k,v in expected.items()) and call.get('status') in
            {'succeeded','invalid_output','model_timeout','model_http_error','context_length_exceeded'}
            and call.get('outcome')==call['status'] and bool(call.get('completed_at')) and bool(call.get('timestamp'))
            and call['completed_at']>=call['timestamp'],code)
        calls.append(call)
    require(json.loads(task['metadata_json']).get('calls',[])==calls
        and (task['status']!='succeeded' or bool(calls) and calls[-1]['status']=='succeeded'),code)
    return calls


def audit(stage):
    r.conversation_only(stage/'memory.sqlite3',r.INDEX_TABLES|r.RELATION_TABLES)
    p,_=prepared_check(stage);bid=p['build_id']
    require(json.loads((stage/'execution-started.json').read_text())==dict(scope=SCOPE,plan_sha256=sha(stage/'plan.json')),'execution_marker_changed')
    require(preserved(stage/'memory.sqlite3',bid,p['failed_tasks'],p['initial_metadata'],p['old_relation_ids'])==p['preserved_snapshot'],'preserved_rows_changed')
    with readonly(stage/'memory.sqlite3') as db:
        calls=new_calls(db,p);q.check_relations(db,p)
        row=dict(db.execute('SELECT * FROM build_versions WHERE build_id=?',(bid,)).fetchone())
        phase=dict(db.execute('SELECT * FROM relation_phases WHERE build_id=?',(bid,)).fetchone())
        statuses=[x[0] for x in db.execute('SELECT status FROM relation_tasks WHERE build_id=?',(bid,))]
        if row['status']=='related':
            projection=db.execute('SELECT * FROM current_state_projections WHERE build_id=?',(bid,)).fetchone();expected=create_projection(db,row)
            require(projection is not None and expected==json.loads(projection['projection_json'])
                and expected['fingerprint']==projection['fingerprint'] and expected['cutoff']==projection['cutoff'],'successor_projection_changed')
    require(row['status'] in {'related','relations_failed'} and row['phase']=='relations'
        and phase['status'] in {'succeeded','failed'} and (row['status']=='related')==(phase['status']=='succeeded')
        and all(s in {'succeeded','failed'} for s in statuses)
        and (row['status']!='related' or all(s=='succeeded' for s in statuses) and phase['error_code'] is None)
        and json.loads(row['model_metadata_json'])['calls']==p['initial_metadata']['calls']+calls,'successor_global_terminal_changed')
    return dict(version=VERSION,scope=SCOPE,build_id=bid,status=row['status'],phase=row['phase'],failed_tasks=1,
        **q.accounting(stage,calls,POLICY),thinking='disabled',mixed_relation_input_producers=True,
        wire_contract_in_build_fingerprint=False,original_calls_prefix_unchanged=True,source_and_success_rows_unchanged=True,
        published=False,holdout_qa_read=False,automatic_retry=False,actual_invoice='not_accessed')


def execute(stage,delegate=None):
    stage=stage.resolve();require(not (stage/'execution-started.json').exists(),'successor_already_started')
    p,settings=prepared_check(stage);target=stage/'memory.sqlite3'
    with backend_ownership(target):
        r.conversation_only(target,r.INDEX_TABLES|r.RELATION_TABLES)
        require(r.snapshot(target)==p['prepared_database_snapshot'] and r.snapshot(stage/'physical-requests.sqlite3')==p['prepared_ledger_snapshot']
            and preserved(target,p['build_id'],p['failed_tasks'],p['initial_metadata'],p['old_relation_ids'])==p['preserved_snapshot'],'prepared_state_changed')
        builds=BuildService(Database(target),settings,NoProvider());builds.require_current_contract(builds.get(p['build_id']))
        require(builds.get(p['build_id'])['status']=='queued' and builds.get(p['build_id'])['phase']=='relations','retry_not_queued')
        write(stage/'execution-started.json',dict(scope=SCOPE,plan_sha256=sha(stage/'plan.json')))
        own=delegate is None;delegate=httpx.HTTPTransport(retries=0) if own else delegate
        try:
            guard=BudgetTransport(stage/'physical-requests.sqlite3',delegate,**POLICY)
            RelationService(builds,EndpointModel(DeepSeekModel(settings,transport=guard),p['failed_tasks'],p['script_sha256'])).run(p['build_id'])
        finally:
            if own:delegate.close()
        outcome=audit(stage);write(stage/'outcome.json',outcome)
    if outcome['status']!='related':raise RuntimeError('relation_successor_incomplete_no_automatic_retry')
    return outcome


def complete_export(source,terminal,output):
    source,terminal,output=source.resolve(),terminal.resolve(),output.resolve()
    p=q.terminal_check(source,terminal,TERMINAL,'related_not_complete');outcome=audit(source)
    require(outcome==json.loads((source/'outcome.json').read_text()) and outcome['status']=='related','successor_terminal_outcome_changed')
    settings=r.settings_at(source);bid=p['build_id'];before=r.source_identity(source);terminal_sha=sha(terminal)
    initial=r.metadata_at(source/'memory.sqlite3',bid);frozen=r.protected(source/'memory.sqlite3',bid,initial,{'active_versions'})
    builds=r.copy_stage(source,output,settings);builds.require_current_contract(builds.get(bid))
    with backend_ownership(output/'memory.sqlite3'):
        versions=VersionsService(builds);completed=versions.publish(bid)
        require(versions.pin(completed['dataset_id'],'conv-44',bid)==bid,'copy_pin_failed')
        bundle=ExportService(versions).export(bid)
        require(bundle.schema_version=='memory-export-v2' and bundle.build.build_id==bid and bundle.build.sample_id=='conv-44'
            and bundle.build.status=='complete','strict_export_required')
        require(r.protected(output/'memory.sqlite3',bid,initial,{'active_versions'})==frozen,'completion_copy_changed')
        with readonly(output/'memory.sqlite3') as db:
            require([tuple(x) for x in db.execute('SELECT * FROM active_versions')]==[(completed['dataset_id'],'conv-44',bid)],'copy_pin_scope_changed')
        (output/'exports').mkdir(mode=0o700);path=output/'exports/conv-44.json';write(path,bundle.model_dump(mode='json'))
        require(MemoryExport.model_validate_json(path.read_text())==bundle,'strict_roundtrip_changed')
    prior=json.loads((Path(p['source_stage'])/'plan.json').read_text());inheritance=json.loads((source/'inheritance.json').read_text())
    require(set(inheritance['memory_id_map'].values())<={m.memory_id for m in bundle.memories},'inherited_export_memories_missing')
    stages=[dict(logical_attempt=1,stage=prior['source_stage'],terminal_sha256=prior['source_terminal_sha256'],
            ledger_snapshot=prior['source_identity']['ledger'],plan_sha256=prior['source_identity']['plan'],input_contract='original-core-relation-payload'),
        dict(logical_attempt=2,stage=p['source_stage'],terminal_sha256=p['source_terminal_sha256'],
            ledger_snapshot=p['source_identity']['ledger'],plan_sha256=p['source_identity']['plan'],input_contract=q.INPUT_VERSION,wrapper_sha256=prior['script_sha256']),
        dict(logical_attempt=3,stage=str(source),terminal_sha256=terminal_sha,ledger_snapshot=before['ledger'],
            plan_sha256=before['plan'],input_contract=INPUT_VERSION,wrapper_sha256=p['script_sha256'])]
    side=output/'exports/conv-44.provenance.json'
    write(side,dict(version=VERSION,export_sha256=sha(path),build_id=bid,mixed_extraction_producers=True,inheritance=inheritance,
        mixed_relation_input_producers=True,wire_contract_in_build_fingerprint=False,relation_stages=stages,
        all_relation_thinking='disabled',implementation_sha256=producers()))
    q.terminal_check(source,terminal,TERMINAL,'related_not_complete')
    require(audit(source)==outcome and r.source_identity(source)==before and sha(terminal)==terminal_sha,'completion_source_changed')
    result=dict(version=VERSION,status='sixth_strict_export_complete_local_copy_only',build_id=bid,memories=len(bundle.memories),relations=len(bundle.relations),
        export=str(path),export_sha256=sha(path),provenance=str(side),provenance_sha256=sha(side),strict_roundtrip=True,
        source_and_ledgers_unchanged=True,provider_requests=0,holdout_qa_read=False,source_status='related',level_e_executed=False)
    write(output/'summary.json',result);return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('mode',choices=('prepare','execute-authorized','complete-export'))
    parser.add_argument('--source',type=Path);parser.add_argument('--source-terminal',type=Path);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.mode=='execute-authorized':result=execute(args.output)
    else:
        if args.source is None or args.source_terminal is None:parser.error('--source and --source-terminal required')
        result=(prepare if args.mode=='prepare' else complete_export)(args.source,args.source_terminal,args.output)
    public={k:result[k] for k in ('version','status','build_id','policy','failed_tasks','physical_requests','provider_requests','export_sha256') if k in result}
    if isinstance(public.get('failed_tasks'),list):public['failed_tasks']=len(public['failed_tasks'])
    print(json.dumps(public))
