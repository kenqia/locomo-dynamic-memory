"""Complete and strictly export only a frozen related conv-44 successor copy.

The paid stage remains related and unpublished. No models, embeddings, queries,
evaluation inputs, credentials, or remote services are used.
"""
import argparse
import json
from pathlib import Path
import sqlite3

from locomo_memory.builds import BuildService
from locomo_memory.database import Database, backend_ownership
from locomo_memory.export_schemas import MemoryExport
from locomo_memory.exports import ExportService
from locomo_memory.versions import VersionsService
from tools.m5 import complete_export_copy as prior
from tools.m5 import conv44_relations as relations
from tools.m5.holdout_relations import NoProvider
from tools.m5.offline import ROOT, sha

VERSION='m5-conv44-complete-export-v1'
TERMINAL_VERSION='m5-conv44-relations-terminal-v1'
require, readonly, write_new = relations.require, relations.readonly, prior.write_new


def producers():
    paths=(Path(__file__),Path(prior.__file__))
    return {**relations.producer_hashes(),**{str(p.relative_to(ROOT)):sha(p) for p in paths}}


def check_source(stage,terminal):
    """Check SQL absence of QA before hashing any relation database payload."""
    relations.conversation_only(stage/'memory.sqlite3',relations.INDEX_TABLES|relations.RELATION_TABLES)
    frozen=json.loads(terminal.read_text());plan=json.loads((stage/'plan.json').read_text())
    require(frozen['version']==TERMINAL_VERSION and frozen['status']=='related_not_complete'
        and bool(frozen['checks']) and all(v is True for v in frozen['checks'].values())
        and frozen['build_id']==plan['build_id'],'related_terminal_required')
    paths=dict(plan_sha256='plan.json',settings_sha256='settings.json',inheritance_sha256='inheritance.json',
        authorization_sha256='authorization.json',outcome_sha256='outcome.json')
    require(all(sha(stage/name)==frozen[field] for field,name in paths.items())
        and relations.snapshot(stage/'memory.sqlite3')==frozen['final_database_logical_snapshot']
        and relations.snapshot(stage/'physical-requests.sqlite3')==frozen['final_ledger_logical_snapshot'],
        'source_not_terminal_snapshot')
    require(plan['version']==relations.VERSION and plan['scope']==relations.SCOPE
        and plan['implementation_sha256']==relations.producer_hashes()
        and plan['script_sha256']==sha(Path(relations.__file__))
        and plan['settings_sha256']==frozen['settings_sha256']
        and plan['inheritance_sha256']==frozen['inheritance_sha256']
        and json.loads((stage/'authorization.json').read_text())==relations.authorization(stage),
        'source_producer_or_authorization_changed')
    settings=relations.settings_at(stage);bid=plan['build_id']
    require(plan['policy']==relations.policy_for(plan['relation_tasks'],settings)
        and relations.schema_snapshot(stage/'memory.sqlite3')==plan['prepared_schema_sha256']
        and relations.protected(stage/'memory.sqlite3',bid,plan['initial_metadata'],relations.RELATION_TABLES)==plan['protected_snapshot']
        and relations.digest(relations.task_rows(stage/'memory.sqlite3',bid))==plan['tasks_sha256'],
        'source_prepared_contract_changed')
    index=Path(plan['source_index_stage']);_,summary=relations.check_index(index)
    require(sha(index/'index-summary.json')==plan['source_index_summary_sha256']
        and summary['source_identity']==plan['source_identity'] and summary['build_id']==bid
        and summary['source_terminal_sha256']==plan['source_terminal_sha256']
        and summary['source_identity']['ledger']==plan['source_ledger_snapshot'],'source_index_changed')
    provenance=json.loads((stage/'inheritance.json').read_text())
    with readonly(stage/'memory.sqlite3') as db:
        build=dict(db.execute('SELECT * FROM build_versions WHERE build_id=?',(bid,)).fetchone())
        require(build['sample_id']=='conv-44' and build['status']=='related' and build['phase']=='relations'
            and json.loads(build['config_json'])==settings.snapshot(),'source_build_scope_changed')
        metadata=json.loads(build['model_metadata_json']);calls,task_calls=relations.terminal_calls(db,bid)
        phase=db.execute('SELECT * FROM relation_phases WHERE build_id=?',(bid,)).fetchone()
        require(phase['status']=='succeeded' and phase['error_code'] is None
            and phase['prompt_version']==plan['progress']['prompt_version']
            and phase['schema_version']==plan['progress']['schema_version']
            and not db.execute("SELECT 1 FROM relation_tasks WHERE build_id=? AND status!='succeeded'",(bid,)).fetchone()
            and not db.execute("SELECT 1 FROM build_fragments WHERE build_id=? AND status!='succeeded'",(bid,)).fetchone(),
            'source_build_incomplete')
        require(calls==task_calls and metadata['calls']==plan['initial_metadata']['calls']+calls
            and all(c['thinking']=={'type':'disabled'} and c.get('reasoning_effort') is None for c in calls),
            'source_relation_calls_changed')
        require(provenance['successor_build_id']==bid and provenance['mixed_extraction_producers']
            and metadata['inheritance']['provenance_sha256']==relations.digest(provenance),'source_inheritance_changed')
    outcome=json.loads((stage/'outcome.json').read_text())
    require(outcome['status']=='related' and outcome['build_id']==bid and not outcome['published']
        and outcome['physical_requests']==len(calls),'source_outcome_changed')
    return settings,bid,plan,provenance,calls


def export_copy(source,terminal,output):
    source,terminal,output=source.resolve(),terminal.resolve(),output.resolve()
    require(not output.exists(),'preserve_existing_output')
    settings,bid,plan,inheritance,calls=check_source(source,terminal)
    before=prior.logical(source/'memory.sqlite3');ledger_before=prior.logical(source/'physical-requests.sqlite3')
    frozen_producers=producers();terminal_sha=sha(terminal)
    with readonly(source/'memory.sqlite3') as db:
        before_builds={r['build_id']:dict(r) for r in db.execute('SELECT * FROM build_versions')}
    output.mkdir(parents=True,exist_ok=False,mode=0o700)
    (output/'exports').mkdir(mode=0o700)
    write_new(output/'settings.json',settings.snapshot())
    write_new(output/'inheritance.json',inheritance)
    require(sha(output/'settings.json')==sha(source/'settings.json')
        and sha(output/'inheritance.json')==sha(source/'inheritance.json'),'copy_configuration_changed')
    target=output/'memory.sqlite3'
    with readonly(source/'memory.sqlite3') as src,sqlite3.connect(target) as dst:src.backup(dst)
    target.chmod(0o600)
    require(prior.logical(target)==before,'backup_not_identical')
    with backend_ownership(target):
        builds=BuildService(Database(target),settings,NoProvider())
        builds.require_current_contract(builds.get(bid))
        versions=VersionsService(builds);completed=versions.publish(bid)
        require(versions.pin(completed['dataset_id'],'conv-44',bid)==bid,'copy_pin_failed')
        bundle=ExportService(versions).export(bid)
        require(bundle.schema_version=='memory-export-v2' and bundle.build.sample_id=='conv-44'
            and bundle.build.build_id==bid and bundle.build.status=='complete','strict_conv44_export_required')
        path=output/'exports/conv-44.json';write_new(path,bundle.model_dump(mode='json'))
        require(MemoryExport.model_validate_json(path.read_text())==bundle,'strict_export_roundtrip_changed')
        with readonly(target) as db:
            prior.zero_queries(db)
            after_builds={r['build_id']:dict(r) for r in db.execute('SELECT * FROM build_versions')}
            require(set(before_builds)==set(after_builds),'copy_builds_changed')
            for identity,old in before_builds.items():
                new=after_builds[identity]
                if identity==bid:
                    allowed={'status','phase','updated_at'}
                    require(new['status']==new['phase']=='complete'
                        and {k:v for k,v in old.items() if k not in allowed}=={k:v for k,v in new.items() if k not in allowed},
                        'copy_build_contract_changed')
                else:require(new==old,'other_build_changed')
            require([tuple(r) for r in db.execute('SELECT * FROM active_versions')]==
                [(completed['dataset_id'],'conv-44',bid)],'copy_active_scope_changed')
        after=prior.logical(target)
        require(set(after['tables'])==set(before['tables'])|{'active_versions'}
            and all(after['tables'][name]==value for name,value in before['tables'].items() if name!='build_versions')
            and relations.schema_snapshot(target,{'active_versions'})==relations.schema_snapshot(source/'memory.sqlite3'),
            'copy_unexpected_table_or_schema_change')
    require(set(inheritance['memory_id_map'].values()) <= {m.memory_id for m in bundle.memories},
        'inherited_memories_missing_from_export')
    sidecar=dict(version=VERSION,export_file='conv-44.json',export_sha256=sha(path),
        schema_version=bundle.schema_version,build_id=bid,build_fingerprint=bundle.build.fingerprint,
        mixed_extraction_producers=True,inheritance=inheritance,inheritance_file_sha256=sha(output/'inheritance.json'),
        historical_producer_claim='inherited facts retain the original extraction producer recorded in inheritance',
        relation_thinking='disabled',relation_reasoning_effort_sent=False,relation_attempts=prior.call_profile(calls),
        relation_implementation_sha256=plan['implementation_sha256'],relation_plan_sha256=sha(source/'plan.json'),
        relation_terminal_sha256=terminal_sha,relation_ledger_snapshot=ledger_before,
        completion='only a new local scratch copy was completed and pinned; source remains related')
    sidecar_path=output/'exports/conv-44.provenance.json';write_new(sidecar_path,sidecar)
    check_source(source,terminal)
    require(prior.logical(source/'memory.sqlite3')==before and prior.logical(source/'physical-requests.sqlite3')==ledger_before
        and sha(terminal)==terminal_sha and producers()==frozen_producers,'original_source_or_producer_changed')
    result=dict(version=VERSION,status='sixth_strict_export_complete_local_copy_only',build_id=bid,sample_id='conv-44',
        export=str(path),export_sha256=sha(path),export_bytes=path.stat().st_size,
        provenance=str(sidecar_path),provenance_sha256=sha(sidecar_path),strict_roundtrip=True,
        memories=len(bundle.memories),relations=len(bundle.relations),sources=len(bundle.sources),
        inherited_fragments=len(inheritance['fragments']),inherited_memories=len(inheritance['memory_id_map']),
        mixed_extraction_producers=True,relation_thinking='disabled',source_stage=str(source),source_status='related',
        source_terminal_sha256=terminal_sha,source_and_ledger_unchanged=True,all_other_builds_and_tables_unchanged=True,
        copied_database_snapshot=after,source_database_snapshot=before,source_ledger_snapshot=ledger_before,
        implementation_sha256=frozen_producers,script_sha256=sha(Path(__file__)),
        provider_requests=0,credentials_accessed=False,holdout_qa_evidence_answers_read=False,
        query_or_evaluation_run=False,remote_write=False,level_e_executed=False)
    write_new(output/'summary.json',result)
    require(all((p.stat().st_mode&0o777)==0o600 for p in (target,output/'settings.json',output/'inheritance.json',
        path,sidecar_path,output/'summary.json')),'private_file_permissions_incorrect')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--source-terminal',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    result=export_copy(args.source,args.source_terminal,args.output)
    print(json.dumps({k:result[k] for k in ('version','status','build_id','memories','relations','provider_requests','export_sha256','provenance_sha256')}))
