"""Prepare an explicit successor Build; inherit verified facts, regenerate only failure.

No original row is edited. Live extraction requires a new exact-plan approval.
Historical fragment producers stay in a private provenance sidecar, separately
from the successor's current execution contract and newly billed calls.
"""
import argparse
from collections import Counter
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import sqlite3

import httpx

from locomo_memory.builds import BuildService
from locomo_memory.config import Settings
from locomo_memory.database import Database, backend_ownership
from locomo_memory.imports import canonical_json
from locomo_memory.memory_schemas import Memory, MemoryDraft
from locomo_memory.model import DeepSeekModel, EXTRACTION_PROMPT_VERSION
from locomo_memory.m5_budget import BudgetTransport
from tools.m5 import isolated_extraction_recovery as prior
from tools.m5.holdout_relations import NoProvider
from tools.m5.offline import sha, write
from tools.m5.level_c import producer_hashes as base_producer_hashes

ROOT = Path(__file__).resolve().parents[2]
SOURCE_CODE_ROOT = ROOT.parent/'m5-final-build-repair-20261104'
VERSION = 'm5-conv44-successor-v3'
SCOPE = 'inherit verified conv44 successful fragments into new Build; extract full failed fragment only; no index/relation/publish/QA'
POLICY = {**prior.POLICY}


def producer_hashes():
    """Freeze the local recovery helper as well as the shared producer set."""
    helper = Path(prior.__file__).resolve()
    return {**base_producer_hashes(), str(helper.relative_to(ROOT)): sha(helper)}


def require(value, code):
    if not value:
        raise ValueError(code)


def digest(value):
    return hashlib.sha256(canonical_json(value).encode()).hexdigest()


def identity(stage):
    prior.require_conversation_only(stage/'memory.sqlite3')
    return dict(database=prior.legacy.snapshot(stage/'memory.sqlite3'),
                ledger=prior.legacy.snapshot(stage/'physical-requests.sqlite3'),
                plan=sha(stage/'plan.json'), settings=sha(stage/'settings.json'))


def parent_snapshot(path, bounds):
    """Include original rowids and rows, allowing append-only successor records."""
    with prior.readonly(path) as db:
        schema = [tuple(r) for r in db.execute('SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY type,name')]
        data = {}
        for name, maximum in bounds.items():
            quoted = '"'+name.replace('"','""')+'"'
            data[name] = [tuple(r) for r in db.execute('SELECT rowid,* FROM '+quoted+' WHERE rowid<=? ORDER BY rowid', (maximum,))]
    return digest(dict(schema=schema, tables=data))


def inherited_snapshot(path, build_id, ordinal):
    with prior.readonly(path) as db:
        fragments = [dict(r) for r in db.execute('SELECT * FROM build_fragments WHERE build_id=? AND ordinal!=? ORDER BY ordinal', (build_id,ordinal))]
        memories = [dict(r) for r in db.execute('SELECT m.* FROM memories m JOIN build_fragments f USING(fragment_id) WHERE m.build_id=? AND f.ordinal!=? ORDER BY memory_id', (build_id,ordinal))]
        links = [tuple(r) for r in db.execute('SELECT s.* FROM memory_sources s JOIN memories m USING(memory_id) JOIN build_fragments f USING(fragment_id) WHERE m.build_id=? AND f.ordinal!=? ORDER BY s.memory_id,s.source_id', (build_id,ordinal))]
    return digest(dict(fragments=fragments,memories=memories,links=links))


def check_source(source, terminal):
    prior.require_conversation_only(source/'memory.sqlite3')
    frozen = json.loads(terminal.read_text())
    require(prior.legacy.snapshot(source/'memory.sqlite3') == frozen['final_database_logical_snapshot'], 'parent_database_not_terminal')
    require(prior.legacy.snapshot(source/'physical-requests.sqlite3') == frozen['final_ledger_logical_snapshot'], 'parent_ledger_not_terminal')
    require(sha(source/'plan.json') == frozen['plan_sha256'], 'parent_plan_changed')
    plan = json.loads((source/'plan.json').read_text())
    require(all(sha(SOURCE_CODE_ROOT/name)==expected for name,expected in plan['implementation_sha256'].items()), 'parent_producer_changed')
    if 'script_sha256' in plan:
        require(sha(SOURCE_CODE_ROOT/'tools/m5/isolated_extraction_recovery.py')==plan['script_sha256'], 'parent_tool_changed')
    settings = Settings.model_validate_json((source/'settings.json').read_text())
    with prior.readonly(source/'memory.sqlite3') as db:
        build = dict(db.execute('SELECT * FROM build_versions WHERE build_id=?',(prior.legacy.BUILD,)).fetchone())
        fragments = [dict(r) for r in db.execute('SELECT * FROM build_fragments WHERE build_id=? ORDER BY ordinal',(prior.legacy.BUILD,))]
    require(build['sample_id']=='conv-44' and build['status']=='failed' and build['phase']=='extraction', 'parent_build_scope_changed')
    require(json.loads(build['config_json'])==settings.snapshot(), 'parent_settings_changed')
    require([f['ordinal'] for f in fragments if f['status']!='succeeded']==[prior.legacy.ORDINAL], 'parent_failed_scope_changed')
    require(settings.extraction_thinking_effort=='disabled', 'inherited_extraction_must_be_disabled')
    return settings,build,fragments


def prepare(source, terminal, output):
    source,terminal,output=source.resolve(),terminal.resolve(),output.resolve()
    old_settings,parent,old_fragments=check_source(source,terminal)
    before=identity(source)
    output.mkdir(parents=True,exist_ok=False,mode=0o700)
    target=output/'memory.sqlite3'
    with prior.readonly(source/'memory.sqlite3') as src,sqlite3.connect(target) as dst:
        src.backup(dst)
    target.chmod(0o600)
    settings=Settings.model_validate({**old_settings.snapshot(),'db_path':str(target),
        **{name:'disabled' for name in Settings.model_fields if name.endswith('_thinking_effort')},
        'resolution_input_budget':192000})
    require(settings.model_max_tokens==POLICY['max_output_tokens'], 'successor_output_policy_changed')
    service=BuildService(Database(target),settings,NoProvider())
    with prior.readonly(target) as db:
        bounds={r[0]:db.execute('SELECT COALESCE(MAX(rowid),0) FROM "'+r[0]+'"').fetchone()[0]
                for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    preserved=parent_snapshot(target,bounds)
    new=service.start(parent['dataset_id'],'conv-44')
    provenance=dict(version=VERSION,parent_stage=str(source),parent_build_id=parent['build_id'],
        parent_fingerprint=parent['fingerprint'],parent_prompt_version=parent['prompt_version'],
        parent_config_sha256=digest(json.loads(parent['config_json'])),parent_source_identity=before,
        parent_terminal_sha256=sha(terminal),parent_implementation_sha256=json.loads((source/'plan.json').read_text())['implementation_sha256'],
        successor_build_id=new['build_id'],successor_fingerprint=new['fingerprint'],
        successor_execution_prompt_version=EXTRACTION_PROMPT_VERSION,
        mixed_extraction_producers=True,source_ids_unchanged=True,fragments=[],memory_id_map={})
    with service.database.connect() as db:
        for old in old_fragments:
            if old['status']!='succeeded':continue
            new_fragment=f"{new['build_id']}:{old['ordinal']}"
            new_row=db.execute('SELECT source_ids_json FROM build_fragments WHERE fragment_id=?',(new_fragment,)).fetchone()
            require(new_row and json.loads(new_row[0])==json.loads(old['source_ids_json']), 'inherited_fragment_membership_changed')
            sources={sid:dict(db.execute('SELECT * FROM source_turns WHERE source_id=?',(sid,)).fetchone()) for sid in json.loads(old['source_ids_json'])}
            rows=[dict(r) for r in db.execute('SELECT * FROM memories WHERE fragment_id=?',(old['fragment_id'],))]
            ordered={r['memory_id']:r for r in rows}
            require(bool(rows) or (isinstance(old['no_facts_reason'],str) and bool(old['no_facts_reason'].strip())),'inherited_empty_fragment_reason_required')
            payload_hashes=[]
            for index in range(len(rows)):
                original_id=hashlib.sha256(f"{old['fragment_id']}:{index}".encode()).hexdigest()[:24]
                require(original_id in ordered,'parent_memory_id_recipe_changed')
                row=ordered[original_id]
                memory=Memory.model_validate_json(row['memory_json'],context={'sources':sources})
                require(memory.build_id==parent['build_id'] and memory.dataset_id==parent['dataset_id'] and memory.sample_id=='conv-44','parent_memory_scope_changed')
                require(row['build_id']==memory.build_id and row['dataset_id']==memory.dataset_id and row['sample_id']==memory.sample_id and row['content']==memory.content and row['entity_id']==memory.entity_id and row['state_dimension']==memory.state_dimension and row['state_key']==memory.state_key,'parent_memory_columns_changed')
                links={r[0] for r in db.execute('SELECT source_id FROM memory_sources WHERE memory_id=?',(original_id,))}
                require(links==set(memory.source_ids),'parent_memory_links_changed')
                require(memory.session_times==list(dict.fromkeys(sources[sid]['session_time'] for sid in memory.source_ids)),'parent_session_times_changed')
                original=memory.model_dump(mode='json')
                MemoryDraft.model_validate({k:v for k,v in original.items() if k in MemoryDraft.model_fields},context={'sources':sources})
                new_id=hashlib.sha256(f'{new_fragment}:{index}'.encode()).hexdigest()[:24]
                converted=Memory.model_validate({**original,'memory_id':new_id,'build_id':new['build_id']},context={'sources':sources})
                require({k:v for k,v in converted.model_dump(mode='json').items() if k not in {'memory_id','build_id'}}=={k:v for k,v in original.items() if k not in {'memory_id','build_id'}},'inherited_semantics_changed')
                db.execute('INSERT INTO memories VALUES (?,?,?,?,?,?,?,?,?,?)',(new_id,new['build_id'],new_fragment,memory.dataset_id,memory.sample_id,memory.content,memory.entity_id,memory.state_dimension,memory.state_key,converted.model_dump_json()))
                db.executemany('INSERT INTO memory_sources VALUES (?,?)',[(new_id,sid) for sid in memory.source_ids])
                provenance['memory_id_map'][original_id]=new_id
                payload_hashes.append(digest(original))
            inherited_metadata=dict(calls=[],inherited_from=dict(build_id=parent['build_id'],fragment_id=old['fragment_id'],prompt_version=parent['prompt_version'],model_metadata=json.loads(old['model_metadata_json'])))
            db.execute("UPDATE build_fragments SET status='succeeded',no_facts_reason=?,model_metadata_json=? WHERE fragment_id=?",(old['no_facts_reason'],canonical_json(inherited_metadata),new_fragment))
            provenance['fragments'].append(dict(ordinal=old['ordinal'],old_fragment_id=old['fragment_id'],new_fragment_id=new_fragment,source_ids=json.loads(old['source_ids_json']),memory_count=len(rows),original_memory_payload_sha256s=payload_hashes,original_metadata_sha256=digest(json.loads(old['model_metadata_json']))))
        metadata=json.loads(db.execute('SELECT model_metadata_json FROM build_versions WHERE build_id=?',(new['build_id'],)).fetchone()[0])
        metadata['inheritance']=dict(provenance_file='inheritance.json',provenance_sha256=digest(provenance),mixed_extraction_producers=True,inherited_calls_not_billed_here=True)
        db.execute('UPDATE build_versions SET model_metadata_json=? WHERE build_id=?',(canonical_json(metadata),new['build_id']))
        require(not db.execute('PRAGMA foreign_key_check').fetchall(),'successor_foreign_key_failure')
    require(parent_snapshot(target,bounds)==preserved and identity(source)==before,'parent_changed_during_prepare')
    with prior.readonly(target) as db:
        new_identity={k:v for k,v in dict(db.execute('SELECT * FROM build_versions WHERE build_id=?',(new['build_id'],)).fetchone()).items() if k not in {'status','updated_at','model_metadata_json'}}
    write(output/'settings.json',settings.snapshot())
    write(output/'inheritance.json',provenance)
    BudgetTransport(output/'physical-requests.sqlite3',None,**POLICY).close()
    plan=dict(version=VERSION,scope=SCOPE,status='prepared_not_authorized',source_stage=str(source),source_terminal=str(terminal),source_terminal_sha256=sha(terminal),source_identity=before,parent_build_id=parent['build_id'],build_id=new['build_id'],new_build_identity=new_identity,fragment_ordinal=prior.legacy.ORDINAL,policy=POLICY,source_parent_row_bounds=bounds,parent_rows_snapshot=preserved,inherited_snapshot=inherited_snapshot(target,new['build_id'],prior.legacy.ORDINAL),inherited_fragments=len(provenance['fragments']),inherited_memories=len(provenance['memory_id_map']),inheritance_sha256=sha(output/'inheritance.json'),settings_sha256=sha(output/'settings.json'),implementation_sha256=producer_hashes(),script_sha256=sha(Path(__file__)),prepared_database_snapshot=prior.legacy.snapshot(target),prepared_ledger_snapshot=prior.legacy.snapshot(output/'physical-requests.sqlite3'),thinking='disabled',holdout_qa_read=False,provider_requests=0,old_budget_transferred=False,limitation='new literal-time guidance and safe diagnostics are offline-validated; live recovery success is unproven')
    write(output/'plan.json',plan)
    write(output/'authorization-template.json',{**authorization(output),'approved':False})
    return plan


def authorization(stage):
    return dict(approved=True,version=VERSION,scope=SCOPE,policy=POLICY,plan_sha256=sha(stage/'plan.json'))


def execute(stage,delegate=None):
    stage=stage.resolve()
    require(not (stage/'execution-started.json').exists(),'successor_already_started')
    require(json.loads((stage/'authorization.json').read_text())==authorization(stage),'successor_authorization_mismatch')
    p=json.loads((stage/'plan.json').read_text())
    require(p['version']==VERSION and p['scope']==SCOPE and p['policy']==POLICY and p['status']=='prepared_not_authorized','successor_plan_changed')
    require(p['implementation_sha256']==producer_hashes() and p['script_sha256']==sha(Path(__file__)),'successor_producer_changed')
    require(p['settings_sha256']==sha(stage/'settings.json') and p['inheritance_sha256']==sha(stage/'inheritance.json'),'successor_config_or_inheritance_changed')
    source=Path(p['source_stage'])
    require(p['source_terminal_sha256']==sha(Path(p['source_terminal'])),'parent_terminal_changed')
    check_source(source,Path(p['source_terminal']))
    require(identity(source)==p['source_identity'],'parent_source_changed')
    settings=Settings.model_validate_json((stage/'settings.json').read_text())
    require(settings.db_path.resolve()==stage/'memory.sqlite3' and all(v=='disabled' for k,v in settings.snapshot().items() if k.endswith('_thinking_effort')),'successor_settings_changed')
    with backend_ownership(settings.db_path):
        require(prior.legacy.snapshot(settings.db_path)==p['prepared_database_snapshot'] and prior.legacy.snapshot(stage/'physical-requests.sqlite3')==p['prepared_ledger_snapshot'],'successor_prepared_state_changed')
        builds=BuildService(Database(settings.db_path),settings,NoProvider())
        builds.require_current_contract(builds.get(p['build_id']))
        write(stage/'execution-started.json',dict(plan_sha256=sha(stage/'plan.json'),scope=SCOPE))
        own=delegate is None
        delegate=httpx.HTTPTransport(retries=0) if own else delegate
        try:
            guard=BudgetTransport(stage/'physical-requests.sqlite3',delegate,**POLICY)
            builds.model=DeepSeekModel(settings,transport=guard)
            builds.run(p['build_id'])
        finally:
            if own:delegate.close()
        require(identity(source)==p['source_identity'] and parent_snapshot(settings.db_path,p['source_parent_row_bounds'])==p['parent_rows_snapshot'],'parent_rows_changed')
        require(inherited_snapshot(settings.db_path,p['build_id'],p['fragment_ordinal'])==p['inherited_snapshot'],'inherited_rows_changed')
        with prior.readonly(settings.db_path) as db:
            row=db.execute('SELECT source_ids_json,model_metadata_json FROM build_fragments WHERE build_id=? AND ordinal=?',(p['build_id'],p['fragment_ordinal'])).fetchone()
            sources={sid:dict(db.execute('SELECT * FROM source_turns WHERE source_id=?',(sid,)).fetchone()) for sid in json.loads(row[0])}
            calls=json.loads(row[1]).get('calls',[])
            new_memories=db.execute('SELECT memory_json FROM memories WHERE fragment_id=?',(f"{p['build_id']}:{p['fragment_ordinal']}",)).fetchall()
            for memory in new_memories:Memory.model_validate_json(memory[0],context={'sources':sources})
            require(not db.execute('PRAGMA foreign_key_check').fetchall(),'successor_foreign_key_failure')
        with prior.readonly(stage/'physical-requests.sqlite3') as db:
            rows=db.execute('SELECT status,reserved_usd,usage_json FROM physical_requests ORDER BY rowid').fetchall()
        require(len(rows)==len(calls)<=POLICY['max_requests'] and all(c['thinking']=={'type':'disabled'} and c.get('reasoning_effort') is None for c in calls),'successor_calls_changed')
        reserved=sum((Decimal(r[1]) for r in rows),Decimal(0))
        require(reserved<=Decimal(POLICY['max_usd']),'successor_budget_exceeded')
        tokens=Counter();unknown=0;unknown_reserved=Decimal(0)
        for row in rows:
            usage=json.loads(row[2]);complete=isinstance(usage,dict) and all(type(usage.get(k)) is int for k in ('prompt_tokens','completion_tokens'))
            if not complete:unknown+=1;unknown_reserved+=Decimal(row[1])
            if isinstance(usage,dict):tokens.update(usage)
        result=builds.get(p['build_id'])
        builds.require_current_contract(result)
        with prior.readonly(settings.db_path) as db:
            actual_identity={k:v for k,v in dict(db.execute('SELECT * FROM build_versions WHERE build_id=?',(p['build_id'],)).fetchone()).items() if k not in {'status','updated_at','model_metadata_json'}}
        require(actual_identity==p['new_build_identity'],'successor_identity_changed')
        require(result['model_metadata']['calls']==calls,'successor_metadata_calls_changed')
        require(result['model_metadata']['inheritance']['provenance_sha256']==digest(json.loads((stage/'inheritance.json').read_text())),'successor_provenance_changed')
        require([json.loads(row[2]) if json.loads(row[2]) is not None else {} for row in rows]==[c.get('usage',{}) for c in calls],'successor_ledger_usage_changed')
        outcome=dict(version=VERSION,scope=SCOPE,build_id=p['build_id'],status=result['status'],phase=result['phase'],progress=result['progress'],new_memories=len(new_memories),inherited_memories=p['inherited_memories'],physical_requests=len(rows),reserved_usd=str(reserved),reported_tokens=dict(tokens),known_usage_peak_upper_usd=str((Decimal(tokens['prompt_tokens'])*Decimal('.30')+Decimal(tokens['completion_tokens'])*Decimal('1.20'))/1000000),unknown_usage_requests=unknown,unknown_reserved_usd=str(unknown_reserved),request_statuses=dict(Counter(r[0] for r in rows)),parent_and_inherited_rows_unchanged=True,thinking='disabled',holdout_qa_read=False,complete_build=False,automatic_retry=False,mixed_extraction_producers=True,actual_invoice='not_accessed',safe_diagnostics=[{k:c[k] for k in ('error_code','field_path','failure_stage','extraction_time_diagnostics') if k in c} for c in calls])
        write(stage/'outcome.json',outcome)
    if result['status']!='extracted':raise RuntimeError('successor_incomplete_no_automatic_retry')
    return outcome


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path)
    parser.add_argument('--source-terminal',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--execute-authorized',action='store_true')
    args=parser.parse_args()
    if args.execute_authorized:
        result=execute(args.output)
    else:
        if args.source is None or args.source_terminal is None:parser.error('--source and --source-terminal required')
        plan=prepare(args.source,args.source_terminal,args.output)
        result={k:plan[k] for k in ('version','status','policy','build_id','inherited_fragments','inherited_memories','provider_requests')}
    print(json.dumps(result))
