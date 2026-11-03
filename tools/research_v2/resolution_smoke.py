"""One explicitly authorized query-only smoke with a 96,000 Resolution input budget."""
import argparse
import json
import os
from pathlib import Path
import shutil
import sqlite3
import time
import xml.etree.ElementTree as ET

import httpx
from fastapi.testclient import TestClient

from locomo_memory.api import create_app
from locomo_memory.config import Settings
from locomo_memory.experiment import Experiment, ExperimentError, write_json
from locomo_memory.model import ModelFailure
from tools.research_v2.observer import Ledger, ObservedDeepSeekModel, Halt, durable, sha
from tools.research_v2.smoke import code_identity, instrument, ObservedMiniLM


def read(path):
    return json.loads(path.read_text())


def digest(path):
    return sha(path.read_bytes())


def validated_window(directory):
    window=read(directory/'window-authorization.json')
    start,end=window['approved_at'],window['deadline']
    if (not window.get('source') or not 0 < end-start <= 3600 or start > time.time()
            or window['max_cny'] != 40 or window['max_physical_http'] != 500
            or window['max_concurrency'] != 1 or window['resolution_input_budget'] != 96000
            or window['model_max_tokens'] != 32768):
        raise Halt('window_authorization_invalid')
    if time.time() >= end:
        raise Halt('deadline')
    return window


def claim_parent(directory, identity):
    window=validated_window(directory)
    if digest(directory/'window-authorization.json') != identity['authorization_sha256']:
        raise Halt('window_authorization_changed')
    parent_path=Path(identity['retry_parent'])
    parent=Ledger(parent_path/'observer')
    try:
        if digest(parent_path/'execution-outcome.json') != identity['retry_parent_outcome_sha256']:
            raise Halt('retry_parent_changed')
        old=parent.policy();records=parent.rows()
        if any(r['status']!='settled' or r['cost_nano_cny'] is None for r in records):
            raise Halt('unknown_billing_requires_external_reconciliation')
        prior_requests=len(records)+old.get('prior_requests',0)
        prior_cost=sum(r['cost_nano_cny'] for r in records)+old.get('prior_cost_nano_cny',0)
        if old['limit_requests']!=500 or old['limit_nano_cny']!=40_000_000_000:
            raise Halt('parent_limit_changed')
        with parent.db() as db:
            db.execute('BEGIN IMMEDIATE')
            if db.execute("SELECT COUNT(*) FROM events WHERE kind='retry_claim'").fetchone()[0]:
                raise Halt('retry_already_claimed')
            codes=[json.loads(row[0]).get('code') for row in db.execute("SELECT document FROM events WHERE kind='halt'")]
            if codes != ['smoke_completed_with_errors_no_more_paid_calls']:
                raise Halt('retry_parent_stop_changed')
            claim={'child_directory':str(directory),'identity_sha256':digest(directory/'execution-identity.json'),
                   'authorization_sha256':identity['authorization_sha256'], 'prior_requests':prior_requests,
                   'prior_cost_nano_cny':prior_cost,'old_deadline':old['deadline'],'new_deadline':window['deadline'],
                   'claimed_at':time.time()}
            db.execute("INSERT INTO events(kind,document) VALUES ('retry_claim',?)",(json.dumps(claim,sort_keys=True),))
        return parent,dict(money=old['limit_nano_cny'],requests=old['limit_requests'],
            seconds=3600,started=window['approved_at'],deadline=window['deadline'],
            prior_requests=prior_requests,prior_cost_nano_cny=prior_cost,max_tokens=32768)
    except BaseException:
        parent.close()
        raise


def freeze(directory, parent, tests):
    os.umask(0o077)
    directory=directory.resolve();parent=parent.resolve()
    if directory==parent or (directory/'execution-identity.json').exists() or (directory/'memory.sqlite3').exists():
        raise Halt('already_frozen')
    if directory.stat().st_mode & 0o077:
        raise Halt('private_directory_required')
    window=validated_window(directory)
    tree=ET.parse(tests).getroot();suites=list(tree.iter('testsuite'))
    if not suites or any(int(s.get(k,'0')) for s in suites for k in ('failures','errors','skipped')):
        raise Halt('offline_tests_required')
    names={case.get('name') for case in tree.iter('testcase')}
    if not {'test_resolution_window_inherits_all_costs_after_original_deadline',
            'test_resolution_window_unknown_parent_cannot_resume',
            'test_resolution_budget_quadruples_without_omission'}.issubset(names):
        raise Halt('required_test_cases_missing')
    previous=read(parent/'execution-outcome.json');state=read(parent/'experiment.json')
    build_id=previous['build_id']
    if previous['progress']!={'total':20,'pending':0,'running':0,'succeeded':15,'failed':5,'interrupted':0,'unknown':0}:
        raise Halt('unexpected_parent_result')
    with sqlite3.connect((parent/'memory.sqlite3').as_uri()+'?mode=ro',uri=True) as source,sqlite3.connect(directory/'memory.sqlite3') as target:
        source.backup(target)
        assert target.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        build=target.execute('SELECT status,config_json,fingerprint FROM build_versions WHERE build_id=?',(build_id,)).fetchone()
        if not build or build[0]!='complete': raise Halt('complete_build_required')
        existing=[row[0] for row in target.execute('SELECT run_id FROM evaluation_runs ORDER BY run_id')]
    copied=[]
    for name in ['plan-smoke.json','plan-development.json','smoke-pricing.md','smoke-chat.md','smoke-cache.md']:
        shutil.copyfile(parent/name,directory/name);copied.append(name)
    shutil.copytree(parent/'sources',directory/'sources')
    producer=read(parent/'execution-identity.json')['config']
    config={**producer,'db_path':str(directory/'memory.sqlite3'),'resolution_input_budget':96000}
    settings=Settings.model_validate(config)
    new_state={'status':'frozen_query_retry','plans':state['plans'],'imported':state['imported'],
        'builds':{'conv-26':build_id},'prior_run_id':previous['run_id'],'smoke_run_id':None,
        'run_origins':{},'full_baseline':'not_run','live_smoke':'not_run'}
    write_json(directory/'experiment.json',new_state)
    identity={'status':'frozen_before_paid_calls','retry_parent':str(parent),
        'retry_parent_outcome_sha256':digest(parent/'execution-outcome.json'),
        'authorization_sha256':digest(directory/'window-authorization.json'),
        'config':settings.snapshot(),'producer_config':json.loads(build[1]),'producer_build_fingerprint':build[2],
        'build_id':build_id,'existing_run_ids':existing,'copied_database_sha256':digest(directory/'memory.sqlite3'),
        'code_files':code_identity(),'tests':{'path':str(tests.resolve()),'sha256':digest(tests)},
        'copied_files':{name:digest(directory/name) for name in copied},
        'source_files':{p.name:digest(p) for p in (directory/'sources').glob('*.json')},
        'build_cost_source':str(parent),'frozen_at':time.time(),
        'scope':'New fixed 20-item Run only; reuse unchanged complete Build. No extraction/probe/relation HTTP.',
        'authorization':window}
    write_json(directory/'execution-identity.json',identity)
    # Preserve exact implementation even if later offline reporting tools evolve.
    for name,h in identity['code_files'].items():
        path=directory/'frozen-code'/name;path.parent.mkdir(parents=True,exist_ok=True)
        durable(path,Path(name).read_bytes());assert digest(path)==h
    return {'status':identity['status'],'build_id':build_id,'resolution_input_budget':96000}


class QueryOnlyModel(ObservedDeepSeekModel):
    def generate(self, operation, *args, **kwargs):
        if operation not in {'query_analysis','resolve','answer'}:
            raise Halt('query_only_scope')
        return super().generate(operation,*args,**kwargs)


def execute(directory):
    os.umask(0o077);directory=directory.resolve();identity=read(directory/'execution-identity.json')
    if (directory/'execution-started.json').exists(): raise Halt('already_started_no_automatic_resume')
    if identity['code_files']!=code_identity() or digest(directory/'memory.sqlite3')!=identity['copied_database_sha256']:
        raise Halt('execution_identity_changed')
    if digest(Path(identity['tests']['path']))!=identity['tests']['sha256']:
        raise Halt('gate_evidence_changed')
    for name,h in identity['copied_files'].items():
        if digest(directory/name)!=h: raise Halt('frozen_file_changed')
    for name,h in identity['source_files'].items():
        if digest(directory/'sources'/name)!=h: raise Halt('source_changed')
    if not os.environ.get('DEEPSEEK_API_KEY'): raise Halt('missing_credentials')
    validated_window(directory)
    durable(directory/'execution-started.json',json.dumps({'started_at':time.time(),'identity_sha256':digest(directory/'execution-identity.json')}).encode())
    parent,inherited=claim_parent(directory,identity)
    ledger=Ledger(directory/'observer');pool=httpx.HTTPTransport(retries=0,trust_env=False)
    outcome={'status':'starting','build_id':identity['build_id'],'run_id':None,'planned':20,'full_experiment_started':False}
    try:
        policy=ledger.arm({'execution_identity_sha256':digest(directory/'execution-identity.json')},**inherited)
        ledger.watchdog();ledger.global_tags={'scope':'smoke'}
        settings=Settings.model_validate(identity['config']);model=QueryOnlyModel(settings,ledger,pool)
        app=create_app(settings,model=model,embedder=ObservedMiniLM(settings,ledger));instrument(app,ledger)
        # Copied historical Runs are immutable, and do not count as the one currently running Run.
        with TestClient(app) as client:
            experiment=Experiment(client,directory);current=experiment.preflight()
            write_json(directory/'observed-provider-origin.json',{'real_provider':True,'mock_transport':False,
                'adapter':type(model).__name__,'producer_build_reused':identity['build_id'],'query_input_budget':96000})
            try:
                run=experiment.request('POST','/evaluation-runs',json={'plan_id':experiment.state['plans']['smoke'],
                    'build_ids':{'conv-26':identity['build_id']},'wait':True})
                outcome.update(status=run['status'],run_id=run['run_id'],progress=run['progress'],metrics=run['summary'])
                experiment.state.update(smoke_run_id=run['run_id'],live_smoke=run['status'],
                    run_origins={run['run_id']:{'real_provider':True,'real_embedding':True}})
                experiment.save();experiment.export('smoke')
                if run['status']=='completed':
                    experiment.inspect_smoke(run,current)
                    outcome['structural_acceptance']='passed; observed real query-only transport recorded separately'
                else: outcome['structural_acceptance']='not_passed'
            except (ModelFailure,ExperimentError) as error:
                outcome.update(status='stopped',error_code=error.code)
            finally:
                experiment.snapshot_build(identity['build_id'])
                experiment.state['research_smoke_outcome']=outcome;experiment.save()
        rows=ledger.rows()
        outcome.update(physical_requests=len(rows),known_peak_upper_cny=sum(r['cost_nano_cny'] or 0 for r in rows)/1e9,
            unknown_requests=sum(r['status']!='settled' for r in rows),elapsed_seconds=time.time()-policy['started'],
            prior_physical_requests=policy['prior_requests'],prior_peak_upper_cny=policy['prior_cost_nano_cny']/1e9)
        outcome.update(cumulative_physical_requests=outcome['physical_requests']+outcome['prior_physical_requests'],
            cumulative_peak_upper_cny=outcome['known_peak_upper_cny']+outcome['prior_peak_upper_cny'])
        write_json(directory/'execution-outcome.json',outcome)
        ledger.event('halt',{'code':'query_smoke_finished_no_more_calls','status':outcome['status']})
        return {k:v for k,v in outcome.items() if k not in ('metrics',)}
    finally:
        pool.close();ledger.close();parent.close()


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['freeze','execute'])
    p.add_argument('--directory',type=Path,required=True);p.add_argument('--parent',type=Path)
    p.add_argument('--tests',type=Path);a=p.parse_args()
    try:
        result=freeze(a.directory,a.parent,a.tests) if a.command=='freeze' else execute(a.directory)
        print(json.dumps(result,indent=2))
    except (Halt,ExperimentError) as error:
        print(json.dumps({'status':'blocked','code':error.code}));raise SystemExit(2)
