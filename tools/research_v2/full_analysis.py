"""Offline-only full-run report, wire lineage, atlas and blinded review packets."""
import argparse
from collections import Counter
from copy import deepcopy
import shutil
import json
import os
from pathlib import Path
import random
import sqlite3
import uuid

from locomo_memory.experiment import write_json
from locomo_memory.evaluation_reports import summarize_run, group_report
from tools.research_v2.atlas import make_atlas, artifact
from tools.research_v2.cache_analysis import rows, aggregate
from tools.research_v2.observer import sha


def blind_material(run, directory):
    """Neutral answers and source citations; sealed mapping never enters packets."""
    packets=[];key=[];rng=random.SystemRandom()
    for index,sample in enumerate(run['input']['samples']):
        candidates=[i for i in run['items'] if i['sample_index']==index and i['result'] is not None]
        rng.shuffle(candidates)
        for item in candidates:
            trace=item['result'].get('trace',{});answer=trace.get('answer') or {}
            ticket=uuid.uuid4().hex
            # Citation memory IDs and candidate list shape would reveal method.
            cited=[]
            for c in answer.get('citations',[]):
                if isinstance(c,dict): cited.extend(c.get('source_ids',[]))
            packets.append(dict(ticket=ticket,question=sample['question'],answer=answer.get('answer'),
                cited_source_ids=sorted(set(cited)),source_document=sample['sample_id']+'.json',
                review=dict(fact_support=None,citation_correctness=None,temporal_identity=None,
                    person_identity=None,event_identity=None,severe_error=None,incorrect_refusal=None,
                    partial_answer=None,omissions=None,status='not_evaluated')))
            key.append(dict(ticket=ticket,run_id=run['run_id'],ordinal=item['ordinal'],strategy=item['strategy']))
    rng.shuffle(packets);rng.shuffle(key)
    return packets,key


def analyze(run,run_path,directory):
    directory=Path(directory);records=rows(directory)
    target=directory/'analysis'/uuid.uuid4().hex;target.mkdir(parents=True,mode=0o700)
    cases,summary=make_atlas(run,Path(run_path),directory)
    available=0
    for case in cases:
        if not case['build_id']:
            failed=run.get('build_failures',{}).get(case['conversation'],{})
            bid=failed.get('build_id');case['build_id']=bid
            case['lineage']['build_version']=dict(build_id=bid,published=False,
                artifact=artifact(directory/'builds'/str(bid)/'build.json'))
            case['lineage']['extracted_memory']=dict(status='partial_database_only' if bid else 'not_created',
                database=artifact(directory/'memory.sqlite3'),table='memories',build_id=bid)
            case['lineage']['memory_source_mapping']=dict(status='partial_database_only' if bid else 'not_created',
                database=artifact(directory/'memory.sqlite3'),table='memory_sources JOIN memories USING(memory_id)',build_id=bid)
        group=[r for r in records if r.get('run_id')==run['run_id'] and r.get('question_id')==case['question_id'] and r.get('strategy')==case['strategy']]
        wire=[]
        for r in group:
            entry=dict(physical_id=r['request_id'],stage=r['stage'],status=r['status'],
                       request_sha256=r['request_sha256'],response_sha256=r.get('response_sha256'))
            for side,field in [('request','wire_path'),('response','response_path')]:
                name=r.get(field)
                if name:
                    p=directory/'observer'/name
                    if not p.is_file() or sha(p.read_bytes()) != entry[side+'_sha256']:
                        raise ValueError('Wire artifact missing or changed')
                    entry[side+'_path']=str(p)
            wire.append(entry)
        case['lineage']['actual_model_context']=dict(status='exact_wire_recorded' if wire else 'not_observed',
            artifacts=wire,credentials_included=False)
        case['metrics']['cost']['physical_ledger_measurement']=aggregate(group)
        available+=bool(wire)
    summary.update(exact_wire_available=available==len(cases) if cases else None,
                   cases_with_wire=available,semantic_review_status='not_evaluated',
                   semantic_metrics={k:None for k in ('fact_support','citation_correctness','temporal_identity','person_identity',
                       'event_identity','severe_error_ratio','incorrect_refusal','partial_answer','omission')})
    # Full Text source count is an input-completeness metric, not retrieval quality.
    full_text={k:v['source_coverage'] for k,v in run['summary'].items() if k=='full_text'}
    for report in [run['overall_summary'],*run['summary'].values()]:
        report['coverage_notice']='Source-ID overlap only; semantic correctness not evaluated. Full Text is input coverage.'
    write_json(target/'failure-atlas-summary.json',summary)
    (target/'failure-atlas.jsonl').write_text(''.join(json.dumps(c)+'\n' for c in cases))
    packets,key=blind_material(run,directory)
    (target/'blind-review.jsonl').write_text(''.join(json.dumps(p)+'\n' for p in packets))
    write_json(target/'sealed-review-key.json',key)
    strategy_reports=deepcopy(run['summary'])
    strategy_reports['full_text']['full_text_input_coverage']=strategy_reports['full_text'].pop('source_coverage')
    overall=deepcopy(run['overall_summary'])
    overall['mixed_input_source_overlap_not_retrieval_quality']=overall.pop('source_coverage')
    retrieval=group_report([i for i in run['items'] if i['strategy']!='full_text'],run['input'])['source_coverage']
    write_json(target/'metrics.json',dict(run_id=run['run_id'],progress=run['progress'],summary=strategy_reports,
        overall=overall,groups=run['grouped_summary'],retrieval_source_overlap=
        dict(value=retrieval,semantic_correctness='not_evaluated'),full_text_input_coverage=full_text,
        semantic_metrics=summary['semantic_metrics'],cost=aggregate(records),
        cost_by_stage={stage:aggregate([r for r in records if r['stage']==stage]) for stage in sorted({r['stage'] for r in records})},
        cost_by_scope={scope:aggregate([r for r in records if r.get('scope')==scope]) for scope in sorted({r.get('scope','') for r in records})},
        billing_notice='Provider tokens at frozen peak tariff, not account debits. Unknown reservations remain.'))
    with sqlite3.connect((directory/'observer/budget.sqlite3').as_uri()+'?mode=ro',uri=True) as db:
        events=[dict(kind=r[0],document=json.loads(r[1])) for r in db.execute('SELECT kind,document FROM events ORDER BY id')]
    write_json(target/'events.json',events)
    (target/'review-rubric.md').write_text('Independent reviewer: inspect the common complete source document and every cited fact. '
        'Review answer support, time/person/event identity, refusal, omissions, partial answer and severity separately. '
        'Mark insufficient evidence Unknown. Do not use QA score, Source ID presence, schema success or model self-review as semantic truth. '
        'Keep sealed-review-key.json away from reviewers. No independence or blindness claim until a separate reviewer completes the review.\n')
    return target



def archive_saved(directory, archive, identity_sha):
    """Exclusive external snapshot; active SQLite files use SQLite backup."""
    directory,archive=Path(directory),Path(archive)/identity_sha/uuid.uuid4().hex
    archive.mkdir(parents=True,mode=0o700)
    rows=[]
    for p in sorted(directory.rglob('*')):
        if not p.is_file() or p.name.endswith(('-wal','-shm','.runtime.lock')) or p.name=='owner.lock': continue
        relative=p.relative_to(directory);target=archive/relative
        target.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
        if p.suffix=='.sqlite3':
            with sqlite3.connect(p.resolve().as_uri()+'?mode=ro',uri=True) as source,sqlite3.connect(target) as backup:
                source.backup(backup)
                if backup.execute('PRAGMA integrity_check').fetchone()[0]!='ok': raise ValueError('Archive integrity check failed')
        else: shutil.copyfile(p,target)
        os.chmod(target,0o600)
        h=__import__('hashlib').sha256()
        with target.open('rb') as stream:
            for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
        rows.append(dict(path=str(relative),sha256=h.hexdigest(),bytes=target.stat().st_size))
    write_json(archive/'manifest.json',dict(execution_identity_sha256=identity_sha,files=rows,
        credential_files_copied=False,sqlite_method='sqlite3.backup, integrity_check=ok'))
    return archive

def export_saved(directory):
    """Read SQLite without app startup, provider, recovery, or new Run creation."""
    directory=Path(directory).resolve()
    with sqlite3.connect((directory/'memory.sqlite3').as_uri()+'?mode=ro',uri=True) as db:
        meta=[json.loads(r[0]) for r in db.execute('SELECT result_json FROM evaluation_runs')]
        selected=[r for r in meta if r.get('coordinator')=='research-full-baseline-v1']
        if len(selected)!=1: raise ValueError('Exactly one full baseline Run required')
        run=selected[0]
        run['items']=[json.loads(r[0]) for r in db.execute('SELECT item_json FROM evaluation_run_items WHERE run_id=? ORDER BY ordinal',(run['run_id'],))]
    for item in run['items']:
        if item['status']=='running':
            item['saved_status']='running';item['status']='unknown'
            item['attempts'][-1]['status']='unknown'
            item['attempts'][-1]['report_notice']='Derived unknown from unfinished saved attempt; original SQLite unchanged.'
    if run['status']=='running':
        run.update(saved_status='running',status='interrupted',completed_at=None)
    run['results']=[i['result'] for i in run['items'] if i.get('result') is not None]
    run['progress']=dict(total=len(run['items']),**Counter(i['status'] for i in run['items']))
    summarize_run(run)
    out=directory/'offline-exports'/uuid.uuid4().hex/'run.json';write_json(out,run)
    return analyze(run,out,directory)

if __name__=='__main__':
    os.umask(0o077)
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--directory',type=Path,required=True)
    print(export_saved(p.parse_args().directory))
