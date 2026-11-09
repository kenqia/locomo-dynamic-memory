"""One independently authorized failed-task retry; preserve all prior attempts.

The extra wire-input contract is recorded separately from the unchanged Build
fingerprint. A related recovery can be completed only in another local copy.
"""
import argparse
from collections import Counter
from decimal import Decimal
import json
import re
from pathlib import Path
import sqlite3

import httpx

from locomo_memory.builds import BuildService
from locomo_memory.database import Database, backend_ownership
from locomo_memory.export_schemas import MemoryExport
from locomo_memory.exports import ExportService
from locomo_memory.m5_budget import BudgetTransport
from locomo_memory.model import DeepSeekModel
from locomo_memory.projection import create_projection
from locomo_memory.relation_schemas import MemoryRelation
from locomo_memory.relations import RelationService
from locomo_memory.versions import VersionsService
from tools.m5 import complete_export_copy as artifacts
from tools.m5 import conv44_relations as r
from tools.m5.holdout_relations import NoProvider
from tools.m5.offline import ROOT, sha, write

VERSION='m5-conv44-relation-recovery-v1'
INPUT_VERSION='relation-full-endpoint-source-ids-v1'
SCOPE='conv-44 frozen failed relation tasks only; independent retry; no publish/query/QA'
PARENT_TERMINAL='m5-conv44-relations-terminal-v1'
TERMINAL='m5-conv44-relation-recovery-terminal-v1'
require,readonly,digest=r.require,r.readonly,r.digest
SAFE_PATH=r'judgments\[\d{1,5}\](?:\.(?:source_ids|old_memory_id|new_memory_id|label|reason|support_quote|applicability|update_evidence|from_date|to_date|condition|condition_satisfied|condition_source_ids|time_anchor_source_id|original_time_expression|time_basis|same_process|real_stage_changed|old_stage|new_stage|description|source_id|quote)(?:\[\d{1,5}\])?)*'
SAFE_ERRORS={'known_source_required','same_state_dimension_required','endpoint_evidence_required','both_endpoints_evidence_required',
    'every_candidate_required','invalid_output','verbatim_support_required','model_timeout','model_http_error'}


def producers():
    return {**r.producer_hashes(),str(Path(__file__).relative_to(ROOT)):sha(Path(__file__)),
        str(Path(artifacts.__file__).relative_to(ROOT)):sha(Path(artifacts.__file__))}


def terminal_check(stage,terminal,version,status):
    r.conversation_only(stage/'memory.sqlite3',r.INDEX_TABLES|r.RELATION_TABLES)
    frozen=json.loads(terminal.read_text());plan=json.loads((stage/'plan.json').read_text())
    require(frozen['version']==version and frozen['status']==status and frozen['build_id']==plan['build_id']
        and bool(frozen['checks']) and all(v is True for v in frozen['checks'].values()),'frozen_terminal_required')
    files=dict(plan_sha256='plan.json',settings_sha256='settings.json',inheritance_sha256='inheritance.json',
        authorization_sha256='authorization.json',outcome_sha256='outcome.json')
    require(all(sha(stage/name)==frozen[key] for key,name in files.items())
        and r.snapshot(stage/'memory.sqlite3')==frozen['final_database_logical_snapshot']
        and r.snapshot(stage/'physical-requests.sqlite3')==frozen['final_ledger_logical_snapshot'],'terminal_identity_changed')
    return plan


def accounting(stage,calls,policy):
    with readonly(stage/'physical-requests.sqlite3') as db:
        rows=db.execute('SELECT * FROM physical_requests ORDER BY rowid').fetchall()
        stored=db.execute('SELECT singleton,json FROM policy').fetchall()
    expected=dict(max_requests=policy['max_requests'],max_usd=str(Decimal(policy['max_usd'])),model=policy['model'],
        input_rate=str(Decimal(policy['input_usd_per_million'])),output_rate=str(Decimal(policy['output_usd_per_million'])),
        max_input_bytes=policy['max_input_bytes'],max_output_tokens=policy['max_output_tokens'])
    ceiling=(Decimal(policy['max_input_bytes'])*Decimal(expected['input_rate'])+Decimal(policy['max_output_tokens'])*Decimal(expected['output_rate']))/1000000
    require(len(stored)==1 and stored[0]['singleton']==1 and json.loads(stored[0]['json'])==expected
        and Decimal(expected['input_rate'])>0,'ledger_policy_changed')
    output_booking=Decimal(policy['max_output_tokens'])*Decimal(expected['output_rate'])
    input_bytes=[(Decimal(row['reserved_usd'])*1000000-output_booking)/Decimal(expected['input_rate']) for row in rows]
    require(len(rows)==len(calls)<=policy['max_requests']
        and [json.loads(row['usage_json']) or {} for row in rows]==[c.get('usage',{}) for c in calls]
        and all(row['status'] in {'transport_unknown','response_received','response_usage_unknown'}
            and (row['status']=='transport_unknown')!=bool(c.get('response_received')) for row,c in zip(rows,calls))
        and all(c['thinking']=={'type':'disabled'} and c.get('reasoning_effort') is None
            and c.get('requested_model')==policy['model'] and c.get('max_tokens')==policy['max_output_tokens'] for c in calls)
        and all(0<Decimal(row['reserved_usd'])<=ceiling for row in rows)
        and all(value==value.to_integral_value() and 1<=value<=policy['max_input_bytes'] for value in input_bytes),
        'physical_call_ledger_mismatch')
    reserved=sum((Decimal(row['reserved_usd']) for row in rows),Decimal(0));tokens=Counter()
    unknown=0;unknown_reserved=Decimal(0)
    for row in rows:
        usage=json.loads(row['usage_json'])
        if not isinstance(usage,dict) or not all(type(usage.get(k)) is int for k in ('prompt_tokens','completion_tokens')):
            unknown+=1;unknown_reserved+=Decimal(row['reserved_usd'])
        if isinstance(usage,dict):tokens.update(usage)
    require(reserved<=Decimal(policy['max_usd']),'physical_budget_exceeded')
    return dict(physical_requests=len(rows),reserved_usd=str(reserved),reported_tokens=dict(tokens),
        known_usage_peak_upper_usd=str((Decimal(tokens['prompt_tokens'])*Decimal('.30')+Decimal(tokens['completion_tokens'])*Decimal('1.20'))/1000000),
        unknown_usage_requests=unknown,unknown_reserved_usd=str(unknown_reserved),request_statuses=dict(Counter(row['status'] for row in rows)))


def parent_check(source,terminal):
    p=terminal_check(source,terminal,PARENT_TERMINAL,'relations_failed_not_complete')
    settings=r.settings_at(source);bid=p['build_id']
    require(p['version']==r.VERSION and p['scope']==r.SCOPE and p['implementation_sha256']==r.producer_hashes()
        and p['script_sha256']==sha(Path(r.__file__)) and p['settings_sha256']==sha(source/'settings.json')
        and p['inheritance_sha256']==sha(source/'inheritance.json')
        and p['policy']==r.policy_for(p['relation_tasks'],settings)
        and json.loads((source/'authorization.json').read_text())==r.authorization(source),'parent_producer_or_policy_changed')
    require(r.schema_snapshot(source/'memory.sqlite3')==p['prepared_schema_sha256']
        and r.protected(source/'memory.sqlite3',bid,p['initial_metadata'],r.RELATION_TABLES)==p['protected_snapshot']
        and digest(r.task_rows(source/'memory.sqlite3',bid))==p['tasks_sha256'],'parent_prepared_contract_changed')
    index=Path(p['source_index_stage']);_,summary=r.check_index(index)
    require(sha(index/'index-summary.json')==p['source_index_summary_sha256'] and summary['build_id']==bid
        and summary['source_identity']==p['source_identity'] and summary['source_terminal_sha256']==p['source_terminal_sha256']
        and summary['source_identity']['ledger']==p['source_ledger_snapshot'],'parent_index_changed')
    with readonly(source/'memory.sqlite3') as db:
        build=dict(db.execute('SELECT * FROM build_versions WHERE build_id=?',(bid,)).fetchone())
        phase=dict(db.execute('SELECT * FROM relation_phases WHERE build_id=?',(bid,)).fetchone())
        tasks=[dict(row) for row in db.execute('SELECT * FROM relation_tasks WHERE build_id=? ORDER BY ordinal',(bid,))]
        calls,task_calls=r.terminal_calls(db,bid)
        require(build['sample_id']=='conv-44' and build['status']=='relations_failed' and build['phase']=='relations'
            and json.loads(build['config_json'])==settings.snapshot() and phase['status']=='failed'
            and phase['prompt_version']==p['progress']['prompt_version'] and phase['schema_version']==p['progress']['schema_version']
            and all(t['status'] in {'succeeded','failed'} for t in tasks)
            and not db.execute('SELECT 1 FROM current_state_projections WHERE build_id=?',(bid,)).fetchone(),'parent_not_closed_failure')
        metadata=json.loads(build['model_metadata_json']);inheritance=json.loads((source/'inheritance.json').read_text())
        require(calls==task_calls and metadata['calls']==p['initial_metadata']['calls']+calls
            and metadata['inheritance']['provenance_sha256']==digest(inheritance)
            and inheritance['successor_build_id']==bid and inheritance['mixed_extraction_producers'],'parent_call_or_inheritance_changed')
    failed=[t for t in tasks if t['status']=='failed'];require(bool(failed),'failed_tasks_required')
    outcome=json.loads((source/'outcome.json').read_text())
    require(outcome['status']=='relations_failed' and outcome['build_id']==bid and not outcome['published']
        and outcome['physical_requests']==len(calls),'parent_outcome_changed')
    accounting(source,calls,p['policy'])
    return settings,bid,failed,metadata


def preserved(path,bid,failed,initial,old_relations):
    """Freeze every original row, allowing only the explicitly retried records."""
    failed_ids={t['task_id'] for t in failed};data={}
    with readonly(path) as db:
        for name, in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
            rows=[]
            for raw in db.execute('SELECT * FROM "'+name+'"'):
                row=dict(raw)
                if name=='build_versions' and row['build_id']==bid:
                    for key in ('status','phase','updated_at'):row.pop(key)
                    metadata=json.loads(row['model_metadata_json']);calls=metadata['calls']
                    require(calls[:len(initial['calls'])]==initial['calls']
                        and metadata['returned_models']==list(dict.fromkeys(c['returned_model'] for c in calls if c.get('returned_model'))),'old_calls_changed')
                    metadata['calls']=initial['calls'];metadata['returned_models']=initial['returned_models'];row['model_metadata_json']=metadata
                if name=='relation_tasks' and row['task_id'] in failed_ids:
                    for key in ('status','attempts','error_code','metadata_json'):row.pop(key)
                if name in {'relation_attempts','relation_provider_calls'} and row['task_id'] in failed_ids and row['logical_attempt']==2:continue
                if name=='relation_phases' and row['build_id']==bid:
                    row.pop('status');row.pop('error_code')
                if name=='memory_relations' and row['build_id']==bid and row['relation_id'] not in old_relations:continue
                if name=='current_state_projections' and row['build_id']==bid:continue
                rows.append(json.dumps(row,sort_keys=True,ensure_ascii=False,default=str))
            if rows:data[name]=sorted(rows)
        require(not db.execute('PRAGMA foreign_key_check').fetchall(),'foreign_key_failure')
    return digest(dict(rows=data,schema=r.schema_snapshot(path)))


def prepare(source,terminal,output):
    source,terminal,output=source.resolve(),terminal.resolve(),output.resolve()
    settings,bid,failed,initial=parent_check(source,terminal);identity=r.source_identity(source)
    with readonly(source/'memory.sqlite3') as db:
        old_relations=[row[0] for row in db.execute('SELECT relation_id FROM memory_relations WHERE build_id=? ORDER BY relation_id',(bid,))]
    frozen=preserved(source/'memory.sqlite3',bid,failed,initial,old_relations)
    builds=r.copy_stage(source,output,settings);builds.require_current_contract(builds.get(bid))
    progress=RelationService(builds,NoProvider()).start(bid)
    with readonly(output/'memory.sqlite3') as db:
        pending=[row[0] for row in db.execute("SELECT task_id FROM relation_tasks WHERE status='pending' AND build_id=? ORDER BY ordinal",(bid,))]
        require(pending==[t['task_id'] for t in failed]
            and all(dict(db.execute('SELECT * FROM relation_tasks WHERE task_id=?',(t['task_id'],)).fetchone())==
                {**t,'status':'pending','error_code':None} for t in failed),'retry_queue_changed')
    policy=r.policy_for(len(failed),settings);BudgetTransport(output/'physical-requests.sqlite3',None,**policy).close()
    require(preserved(output/'memory.sqlite3',bid,failed,initial,old_relations)==frozen and r.source_identity(source)==identity,'parent_changed')
    plan=dict(version=VERSION,scope=SCOPE,status='prepared_not_authorized',build_id=bid,policy=policy,failed_tasks=failed,
        initial_metadata=initial,old_relation_ids=old_relations,preserved_snapshot=frozen,progress=progress,
        source_stage=str(source),source_terminal=str(terminal),source_terminal_sha256=sha(terminal),source_identity=identity,
        settings_sha256=sha(output/'settings.json'),inheritance_sha256=sha(output/'inheritance.json'),
        implementation_sha256=producers(),script_sha256=sha(Path(__file__)),input_contract_version=INPUT_VERSION,
        wire_contract_in_build_fingerprint=False,mixed_relation_input_producers=True,
        prepared_database_snapshot=r.snapshot(output/'memory.sqlite3'),prepared_ledger_snapshot=r.snapshot(output/'physical-requests.sqlite3'),
        provider_requests=0,holdout_qa_read=False,old_budget_transferred=False)
    write(output/'plan.json',plan);write(output/'authorization-template.json',{**authorization(output),'approved':False})
    return plan


def authorization(stage):
    p=json.loads((stage/'plan.json').read_text())
    return dict(approved=True,version=VERSION,scope=SCOPE,build_id=p['build_id'],policy=p['policy'],plan_sha256=sha(stage/'plan.json'))


class EndpointModel:
    def __init__(self,model,failed,wrapper_sha):
        self.model,self.wrapper_sha=model,wrapper_sha
        self.errors={t['new_memory_id']:json.loads(t['metadata_json']).get('calls',[]) for t in failed}

    def generate(self,operation,payload,schema,*,context,on_call):
        require(operation=='relate' and payload['new_memory']['memory_id'] in self.errors,'recovery_model_scope_changed')
        endpoints=[context['new_memory'],*context['history']]
        mapping={m['memory_id']:list(m['source_ids']) for m in endpoints}
        require(all(set(ids)<=set(context['sources']) for ids in mapping.values()),'endpoint_source_map_invalid')
        previous=self.errors[payload['new_memory']['memory_id']]
        code=previous[-1].get('error_code') if previous else None
        path=previous[-1].get('field_path') if previous else None
        feedback=dict(error_code=code if code in SAFE_ERRORS else 'prior_task_failed',
            field_path=path if isinstance(path,str) and re.fullmatch(SAFE_PATH,path) else None,
            instruction='Regenerate the full batch. Copy complete source IDs exactly from endpoint_source_ids. Each judgment must cite actual sources from both endpoints. Do not shorten, invent, repair or guess IDs. Keep all original evidence validation. Respect allowed_labels_by_old_memory. RETAIN, SUPERSEDE and CONFLICT require identical state_key. Never change endpoint identities or state dimensions, or force a label to pass. undetermined is valid when evidence is insufficient.')
        augmented={**payload,'endpoint_source_ids':mapping,'recovery_feedback':feedback}
        def observe(call):
            call.update(input_contract_version=INPUT_VERSION,input_wrapper_sha256=self.wrapper_sha)
            on_call(call)
        return self.model.generate(operation,augmented,schema,context=context,on_call=observe)


def new_calls(db,p):
    calls=[];code='recovery_attempt_identity_or_terminal_changed'
    for old in p['failed_tasks']:
        task=dict(db.execute('SELECT * FROM relation_tasks WHERE task_id=?',(old['task_id'],)).fetchone())
        attempts=db.execute('SELECT * FROM relation_attempts WHERE task_id=? ORDER BY logical_attempt',(old['task_id'],)).fetchall()
        require(task['attempts']==2 and [a['logical_attempt'] for a in attempts]==[1,2]
            and task['status'] in {'succeeded','failed'},code)
        attempt=attempts[-1]
        require(attempt['status']==task['status'] and attempt['error_code']==task['error_code']
            and bool(attempt['started_at']) and bool(attempt['completed_at']) and attempt['completed_at']>=attempt['started_at']
            and (task['status']!='succeeded' or task['error_code'] is None),code)
        providers=db.execute('SELECT * FROM relation_provider_calls WHERE task_id=? AND logical_attempt=2 ORDER BY provider_attempt',(old['task_id'],)).fetchall()
        require([x['provider_attempt'] for x in providers]==list(range(1,len(providers)+1)) and len(providers)<=3,code)
        current=[]
        for row in providers:
            call=json.loads(row['metadata_json']);expected=dict(build_id=p['build_id'],task_id=row['task_id'],logical_attempt=2,
                provider_attempt=row['provider_attempt'],attempt=row['provider_attempt'],call_id=f"{row['task_id']}:2:{row['provider_attempt']}",
                input_contract_version=INPUT_VERSION,input_wrapper_sha256=p['script_sha256'])
            require(all(call.get(k)==v for k,v in expected.items()) and call.get('status') in
                {'succeeded','invalid_output','model_timeout','model_http_error','context_length_exceeded'}
                and call.get('outcome')==call['status'] and bool(call.get('completed_at'))
                and bool(call.get('timestamp')) and call['completed_at']>=call['timestamp'],code)
            current.append(call)
        require(json.loads(task['metadata_json']).get('calls',[])==current
            and (task['status']!='succeeded' or bool(current) and current[-1]['status']=='succeeded'),code)
        calls.extend(current)
    return calls


def check_relations(db,p):
    expected=set();actual=set();bid=p['build_id']
    for old in p['failed_tasks']:
        if db.execute('SELECT status FROM relation_tasks WHERE task_id=?',(old['task_id'],)).fetchone()[0]=='succeeded':
            expected.update((identity,old['new_memory_id']) for identity in json.loads(old['history_ids_json']))
    for row in db.execute('SELECT * FROM memory_relations WHERE build_id=?',(bid,)):
        if row['relation_id'] in p['old_relation_ids']:continue
        relation=MemoryRelation.model_validate_json(row['relation_json'])
        old,new=(json.loads(db.execute('SELECT memory_json FROM memories WHERE memory_id=? AND build_id=?',(identity,bid)).fetchone()[0])
            for identity in (relation.old_memory_id,relation.new_memory_id))
        sources={identity:dict(db.execute('SELECT * FROM source_turns WHERE source_id=?',(identity,)).fetchone()) for identity in set(old['source_ids']+new['source_ids'])}
        MemoryRelation.model_validate_json(row['relation_json'],context=dict(new_memory=new,history=[old],sources=sources))
        require(relation.build_id==bid and row['old_memory_id']==relation.old_memory_id and row['new_memory_id']==relation.new_memory_id
            and row['label']==relation.label and row['relation_id']==relation.relation_id,'recovery_relation_columns_changed')
        pair=(relation.old_memory_id,relation.new_memory_id)
        require(pair not in actual,'duplicate_recovery_relation');actual.add(pair)
    require(actual==expected,'recovery_relation_scope_changed')


def prepared_check(stage):
    p=json.loads((stage/'plan.json').read_text());settings=r.settings_at(stage)
    require(p['version']==VERSION and p['scope']==SCOPE and p['status']=='prepared_not_authorized'
        and p['policy']==r.policy_for(len(p['failed_tasks']),settings) and p['input_contract_version']==INPUT_VERSION
        and p['implementation_sha256']==producers() and p['script_sha256']==sha(Path(__file__))
        and p['settings_sha256']==sha(stage/'settings.json') and p['inheritance_sha256']==sha(stage/'inheritance.json')
        and json.loads((stage/'authorization.json').read_text())==authorization(stage),'recovery_plan_or_authorization_changed')
    source=Path(p['source_stage']);terminal=Path(p['source_terminal'])
    parent_check(source,terminal)
    require(sha(terminal)==p['source_terminal_sha256'] and r.source_identity(source)==p['source_identity'],'parent_identity_changed')
    return p,settings


def audit(stage):
    r.conversation_only(stage/'memory.sqlite3',r.INDEX_TABLES|r.RELATION_TABLES)
    p,settings=prepared_check(stage);bid=p['build_id']
    require(json.loads((stage/'execution-started.json').read_text())==dict(scope=SCOPE,plan_sha256=sha(stage/'plan.json')),'execution_marker_changed')
    require(preserved(stage/'memory.sqlite3',bid,p['failed_tasks'],p['initial_metadata'],p['old_relation_ids'])==p['preserved_snapshot'],'preserved_rows_changed')
    with readonly(stage/'memory.sqlite3') as db:
        calls=new_calls(db,p);check_relations(db,p)
        row=dict(db.execute('SELECT * FROM build_versions WHERE build_id=?',(bid,)).fetchone())
        phase=dict(db.execute('SELECT * FROM relation_phases WHERE build_id=?',(bid,)).fetchone())
        statuses=[x[0] for x in db.execute('SELECT status FROM relation_tasks WHERE build_id=?',(bid,))]
        if row['status']=='related':
            projection=db.execute('SELECT * FROM current_state_projections WHERE build_id=?',(bid,)).fetchone()
            expected=create_projection(db,row)
            require(projection is not None and expected==json.loads(projection['projection_json'])
                and expected['fingerprint']==projection['fingerprint'] and expected['cutoff']==projection['cutoff'],'recovery_projection_changed')
    require(row['status'] in {'related','relations_failed'} and row['phase']=='relations'
        and phase['status'] in {'succeeded','failed'} and (row['status']=='related')==(phase['status']=='succeeded')
        and all(s in {'succeeded','failed'} for s in statuses)
        and (row['status']!='related' or all(s=='succeeded' for s in statuses) and phase['error_code'] is None)
        and json.loads(row['model_metadata_json'])['calls']==p['initial_metadata']['calls']+calls,'recovery_global_terminal_changed')
    costs=accounting(stage,calls,p['policy'])
    return dict(version=VERSION,scope=SCOPE,build_id=bid,status=row['status'],phase=row['phase'],
        failed_tasks=len(p['failed_tasks']),**costs,thinking='disabled',mixed_relation_input_producers=True,
        wire_contract_in_build_fingerprint=False,original_calls_prefix_unchanged=True,source_and_success_rows_unchanged=True,
        published=False,holdout_qa_read=False,automatic_retry=False,actual_invoice='not_accessed')


def execute(stage,delegate=None):
    stage=stage.resolve();require(not (stage/'execution-started.json').exists(),'recovery_already_started')
    p,settings=prepared_check(stage);target=stage/'memory.sqlite3'
    with backend_ownership(target):
        r.conversation_only(target,r.INDEX_TABLES|r.RELATION_TABLES)
        require(r.snapshot(target)==p['prepared_database_snapshot']
            and r.snapshot(stage/'physical-requests.sqlite3')==p['prepared_ledger_snapshot']
            and preserved(target,p['build_id'],p['failed_tasks'],p['initial_metadata'],p['old_relation_ids'])==p['preserved_snapshot'],'prepared_state_changed')
        builds=BuildService(Database(target),settings,NoProvider());builds.require_current_contract(builds.get(p['build_id']))
        require(builds.get(p['build_id'])['status']=='queued' and builds.get(p['build_id'])['phase']=='relations','retry_not_queued')
        write(stage/'execution-started.json',dict(scope=SCOPE,plan_sha256=sha(stage/'plan.json')))
        own=delegate is None;delegate=httpx.HTTPTransport(retries=0) if own else delegate
        try:
            guard=BudgetTransport(stage/'physical-requests.sqlite3',delegate,**p['policy'])
            model=EndpointModel(DeepSeekModel(settings,transport=guard),p['failed_tasks'],p['script_sha256'])
            RelationService(builds,model).run(p['build_id'])
        finally:
            if own:delegate.close()
        outcome=audit(stage);write(stage/'outcome.json',outcome)
    if outcome['status']!='related':raise RuntimeError('relation_recovery_incomplete_no_automatic_retry')
    return outcome


def complete_export(source,terminal,output):
    source,terminal,output=source.resolve(),terminal.resolve(),output.resolve()
    p=terminal_check(source,terminal,TERMINAL,'related_not_complete');outcome=audit(source)
    require(outcome==json.loads((source/'outcome.json').read_text()) and outcome['status']=='related','recovery_terminal_outcome_changed')
    settings=r.settings_at(source);bid=p['build_id'];before=r.source_identity(source);terminal_sha=sha(terminal)
    initial=r.metadata_at(source/'memory.sqlite3',bid)
    preserved_copy=r.protected(source/'memory.sqlite3',bid,initial,{'active_versions'})
    builds=r.copy_stage(source,output,settings);builds.require_current_contract(builds.get(bid))
    with backend_ownership(output/'memory.sqlite3'):
        versions=VersionsService(builds);completed=versions.publish(bid)
        require(versions.pin(completed['dataset_id'],'conv-44',bid)==bid,'copy_pin_failed')
        bundle=ExportService(versions).export(bid)
        require(bundle.schema_version=='memory-export-v2' and bundle.build.build_id==bid and bundle.build.sample_id=='conv-44' and bundle.build.status=='complete','strict_export_required')
        require(r.protected(output/'memory.sqlite3',bid,initial,{'active_versions'})==preserved_copy,'completion_copy_changed')
        with readonly(output/'memory.sqlite3') as db:
            require([tuple(x) for x in db.execute('SELECT * FROM active_versions')]==[(completed['dataset_id'],'conv-44',bid)],'copy_pin_scope_changed')
        (output/'exports').mkdir(mode=0o700);path=output/'exports/conv-44.json';write(path,bundle.model_dump(mode='json'))
        require(MemoryExport.model_validate_json(path.read_text())==bundle,'strict_roundtrip_changed')
    inheritance=json.loads((source/'inheritance.json').read_text())
    require(set(inheritance['memory_id_map'].values())<={m.memory_id for m in bundle.memories},'inherited_export_memories_missing')
    sidecar=dict(version=VERSION,export_sha256=sha(path),build_id=bid,mixed_extraction_producers=True,inheritance=inheritance,
        mixed_relation_input_producers=True,wire_contract_in_build_fingerprint=False,
        logical_attempt_1=dict(stage=p['source_stage'],terminal_sha256=p['source_terminal_sha256'],
            ledger_snapshot=p['source_identity']['ledger'],plan_sha256=p['source_identity']['plan'],input_contract='original-core-relation-payload'),
        logical_attempt_2=dict(stage=str(source),terminal_sha256=terminal_sha,ledger_snapshot=before['ledger'],
            plan_sha256=before['plan'],input_contract=INPUT_VERSION,wrapper_sha256=p['script_sha256']),
        all_relation_thinking='disabled',implementation_sha256=producers())
    sidepath=output/'exports/conv-44.provenance.json';write(sidepath,sidecar)
    terminal_check(source,terminal,TERMINAL,'related_not_complete')
    require(audit(source)==outcome and r.source_identity(source)==before and sha(terminal)==terminal_sha,'completion_source_changed')
    result=dict(version=VERSION,status='sixth_strict_export_complete_local_copy_only',build_id=bid,memories=len(bundle.memories),
        relations=len(bundle.relations),export=str(path),export_sha256=sha(path),provenance=str(sidepath),provenance_sha256=sha(sidepath),
        strict_roundtrip=True,source_and_ledgers_unchanged=True,provider_requests=0,holdout_qa_read=False,source_status='related',level_e_executed=False)
    write(output/'summary.json',result)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('mode',choices=('prepare','execute-authorized','complete-export'))
    parser.add_argument('--source',type=Path);parser.add_argument('--source-terminal',type=Path)
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    if args.mode=='execute-authorized':result=execute(args.output)
    else:
        if args.source is None or args.source_terminal is None:parser.error('--source and --source-terminal required')
        result=(prepare if args.mode=='prepare' else complete_export)(args.source,args.source_terminal,args.output)
    public={k:result[k] for k in ('version','status','build_id','policy','failed_tasks','physical_requests','provider_requests','export_sha256') if k in result}
    if isinstance(public.get('failed_tasks'),list):public['failed_tasks']=len(public['failed_tasks'])
    print(json.dumps(public))
