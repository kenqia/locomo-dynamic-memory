"""Frozen full-development baseline, one shot only, explicitly approved at launch.

No production entry point imports this module. `check` is fully offline.
`execute` is chargeable and must only be invoked after separate human approval.
"""
import argparse
from collections import Counter
from contextlib import contextmanager
import fcntl
import importlib.metadata
import json
import os
from pathlib import Path
import resource
import sqlite3
import time
import uuid

import httpx
from fastapi.testclient import TestClient

from locomo_memory.api import create_app
from locomo_memory.builds import BuildError
from locomo_memory.config import Settings
from locomo_memory.experiment import Experiment, ExperimentError, write_json
from locomo_memory.imports import canonical_json
from locomo_memory.model import utc_now
from tools.research_v2.observer import Halt, ObservedDeepSeekModel, durable, sha
from tools.research_v2.full_budget import FullLedger, LIMITS
from tools.research_v2.smoke import code_identity, ObservedMiniLM

ROOT = Path(__file__).resolve().parents[2]
DEVELOPMENT = {'conv-26': (419,199), 'conv-30': (369,105), 'conv-41': (663,193), 'conv-42': (629,260)}
STRATEGIES = ['full_text','vector','hybrid_no_resolution','dynamic']
PREFLIGHT = ROOT/'var/research-v2-full-preflight-20261101'
IDENTITY = ROOT/'experiments/research-v2/FULL_BASELINE_EXECUTION_IDENTITY.json'


def read(path):
    return json.loads(Path(path).read_text())


def digest(path):
    h = __import__('hashlib').sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''): h.update(block)
    return h.hexdigest()


def dependencies():
    return dict(sorted((d.metadata['Name'].lower(), d.version) for d in importlib.metadata.distributions()
                       if d.metadata['Name']))


def validate_plan(plan):
    if plan['strategies'] != STRATEGIES or plan['question_count'] != 757 or plan['combination_count'] != 3028:
        raise Halt('plan_scope_changed')
    if Counter(q['sample_id'] for q in plan['questions']) != Counter({s:n[1] for s,n in DEVELOPMENT.items()}):
        raise Halt('conversation_scope_changed')
    expected = [(s,i) for s,(_,n) in DEVELOPMENT.items() for i in range(n)]
    if [(q['sample_id'],q['qa_index']) for q in plan['questions']] != expected:
        raise Halt('official_question_order_changed')


def check(identity_path=IDENTITY):
    identity = read(identity_path)
    if identity['code_files'] != code_identity() or identity['dependencies'] != dependencies():
        raise Halt('code_or_dependency_changed')
    if identity['budget'] != LIMITS:
        raise Halt('budget_changed')
    for file, expected in identity['files'].items():
        if digest(file) != expected: raise Halt('frozen_artifact_changed')
    validate_plan(read(identity['plan_path']))
    if identity['query_config'] != identity['producer_config']:
        raise Halt('producer_query_configuration_changed')
    settings = Settings.model_validate(identity['query_config'])
    if settings.model_max_tokens != 32768 or settings.resolution_input_budget != 96000:
        raise Halt('research_parameters_changed')
    with sqlite3.connect(Path(identity['prepared_database']).as_uri()+'?mode=ro', uri=True) as db:
        if db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok': raise Halt('database_integrity')
        if any(db.execute('SELECT COUNT(*) FROM '+t).fetchone()[0] for t in ('build_versions','evaluation_runs')):
            raise Halt('fresh_database_required')
    return identity


@contextmanager
def claim(identity, identity_sha, approval, *, control=None, started=None):
    """Claim outside runtime DB; deleting/recreating the DB cannot clear the claim."""
    if approval != identity_sha: raise Halt('explicit_identity_approval_required')
    control = Path(control or identity['control_directory'])
    control.mkdir(parents=True, exist_ok=True, mode=0o700)
    if control.stat().st_mode & 0o077: raise Halt('private_directory_required')
    with (control/'owner.lock').open('a') as lock:
        os.chmod(control/'owner.lock', 0o600)
        try: fcntl.flock(lock, fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError: raise Halt('owner_already_running') from None
        try:
            if (control/'start-claim.json').exists(): raise Halt('already_started_no_automatic_resume')
            # A one-use exclusive fsynced receipt is written before any runtime DB/HTTP.
            durable(control/'start-claim.json', json.dumps(dict(identity_sha256=identity_sha,
                started_at=time.time() if started is None else started, approval='explicit CLI identity confirmation', budget=LIMITS)).encode())
            yield read(control/'start-claim.json')
        finally: fcntl.flock(lock, fcntl.LOCK_UN)


def instrument(app, ledger):
    original = app.state.builds._extract_fragment
    def extract(build_id, fragment):
        ledger.assert_available()
        with ledger.scope(build_id=build_id, fragment_id=fragment['fragment_id']): return original(build_id, fragment)
    app.state.builds._extract_fragment = extract
    judge = app.state.relations._judge
    def relation(build_id, task):
        ledger.assert_available()
        with ledger.scope(build_id=build_id, task_id=task['task_id']): return judge(build_id, task)
    app.state.relations._judge = relation


class FullRun:
    """Existing SQLite item/attempt format and scorer; research coordinator v3.

    v3 deliberately fails the native v2 resume compatibility gate. No resume CLI.
    Persist the complete denominator before the first Build or provider request.
    """
    def __init__(self, app, inputs, plan, execution_sha):
        self.app, self.db, self.service = app, app.state.database, app.state.evaluation
        self.execution = self.service.execution
        self.run = dict(run_id=uuid.uuid4().hex, execution_version=3,
            coordinator='research-full-baseline-v1', creation_token=execution_sha,
            input=inputs, input_id=inputs['input_id'], plan=plan, plan_id=plan['plan_id'],
            strategies=STRATEGIES, pins={s:None for s in DEVELOPMENT}, builds={},
            build_artifacts={}, build_indexes={}, config=app.state.builds.settings.snapshot(),
            status='running', started_at=utc_now(), completed_at=None, elapsed_seconds=0,
            execution_identity_sha256=execution_sha, fingerprint=execution_sha, build_failures={}, course_metrics={'status':'unavailable','reason':'independent_truth_missing'})
        self.items=[]
        for index,q in enumerate(plan['questions']):
            for strategy in STRATEGIES:
                self.items.append(dict(ordinal=len(self.items),sample_index=index,**q,strategy=strategy,
                                       status='pending',attempts=[],result=None))
        with self.db.connect() as db:
            db.execute('INSERT INTO evaluation_runs VALUES (?,?)',(self.run['run_id'],canonical_json(self.run)))
            db.executemany('INSERT INTO evaluation_run_items VALUES (?,?,?,?)',
                [(self.run['run_id'],i['ordinal'],i['status'],canonical_json(i)) for i in self.items])

    def save(self):
        with self.db.connect() as db: self.execution.save_metadata(db,self.run)

    def save_item(self,item):
        with self.db.connect() as db:
            db.execute('UPDATE evaluation_run_items SET status=?,item_json=? WHERE run_id=? AND ordinal=?',
                       (item['status'],canonical_json(item),self.run['run_id'],item['ordinal']))

    def pin(self,sid,bid):
        self.app.state.versions.pin(self.run['input']['dataset_id'],sid,bid)
        self.run['pins'][sid]=bid;self.run['builds'][sid]=self.app.state.builds.get(bid)
        self.run['build_artifacts'][sid]=self.app.state.versions.pin_details(self.run['input']['dataset_id'],sid,bid)
        self.run['build_indexes'][sid]=self.app.state.retrieval.index_info(bid)
        self.save()

    def query(self,ledger):
        for item in self.items:
            if item['status'] != 'pending': continue
            bid=self.run['pins'][item['sample_id']]
            if not bid:
                item.update(status='failed',error={'code':'dependency_build_unavailable'},result=None)
                self.save_item(item); continue
            ledger.assert_available()
            a=dict(attempt_id=uuid.uuid4().hex,number=1,started_at=utc_now(),status='running',result=None)
            item['attempts'].append(a);item['status']='running';self.save_item(item)
            tick=time.perf_counter()
            try:
                with ledger.scope(scope='development-query',run_id=self.run['run_id'],build_id=bid,
                    sample_id=item['sample_id'],qa_index=item['qa_index'],question_id=item['question_id'],strategy=item['strategy']):
                    result=self.service.execute_item(self.run['input'],item['sample_index'],
                        self.run['input']['samples'][item['sample_index']],item['strategy'],bid)
                status='failed' if result.get('error') else 'succeeded'
                # A caught adapter failure may conceal a charged unknown request.
                ledger.assert_available()  # Reject newly unknown physical outcomes.
            except Exception:
                result,status=None,'unknown'
            a.update(result=result,status=status,elapsed_seconds=time.perf_counter()-tick,completed_at=utc_now())
            item.update(result=result,status=status);self.save_item(item)
            if status=='unknown':
                ledger.event('halt',{'code':'query_outcome_unknown'});break

    def finish(self,seconds):
        with self.db.connect() as db:
            self.execution.normalize_orphan_items(db,self.run['run_id'])
        self.items=self.execution.items(self.run['run_id'])
        complete=all(i['status'] in ('succeeded','failed') for i in self.items)
        self.run.update(status=('completed_with_errors' if any(i['status']=='failed' for i in self.items) else 'completed') if complete else 'interrupted',
                        elapsed_seconds=seconds,completed_at=utc_now() if complete else None)
        self.save()
        return self.execution.read(self.run['run_id'])


def build_all(app,experiment,coordinator,ledger):
    for sid in DEVELOPMENT:
        ledger.assert_available()
        ledger.global_tags=dict(scope='development-build',sample_id=sid,run_id=coordinator.run['run_id'])
        try:
            build=app.state.builds.start(coordinator.run['input']['dataset_id'],sid,'full-baseline-20261101:'+sid)
            bid=build['build_id'];experiment.state['builds'][sid]=bid;experiment.save()
            app.state.builds.run(bid)
            if app.state.builds.get(bid)['status']!='extracted': raise BuildError('extraction_failed')
            app.state.retrieval.create_index(bid)
            if app.state.builds.get(bid)['status']!='indexed': raise BuildError('index_failed')
            app.state.relations.start(bid);app.state.relations.run(bid)
            if app.state.builds.get(bid)['status']!='related': raise BuildError('relation_failed')
            app.state.versions.publish(bid)
            coordinator.pin(sid,bid)
        except (BuildError, ExperimentError) as error:
            coordinator.run['build_failures'][sid]={'code':error.code,'build_id':experiment.state['builds'].get(sid)}
            coordinator.save()
            # Semantic Build failure does not spend another conversation's denominator.
            # Budget/unknown failures stop here; ordinary Build failures may continue.
            ledger.assert_available()
        finally:
            bid=experiment.state['builds'].get(sid)
            if bid: experiment.snapshot_build(bid)
    ledger.global_tags={}


def execute(identity_path,approval):
    invoked_at=time.time()
    os.umask(0o077)
    identity=check(identity_path);identity_sha=digest(identity_path)
    if approval!=identity_sha: raise Halt('explicit_identity_approval_required')
    if not os.environ.get('DEEPSEEK_API_KEY'): raise Halt('missing_credentials')
    from tools.research_v2.full_preflight import fetch_contract
    # Public unauthenticated docs only. Recheck on execution day before claiming.
    current=fetch_contract(Path(identity['control_directory'])/'launch-contract')
    if current['contract'] != identity['official_contract']['contract']: raise Halt('official_contract_changed')
    with claim(identity,identity_sha,approval,started=invoked_at) as receipt:
        directory=Path(identity['runtime_directory'])
        directory.mkdir(mode=0o700)  # exclusive: never adopt an old runtime
        with sqlite3.connect(Path(identity['prepared_database']).as_uri()+'?mode=ro',uri=True) as source,sqlite3.connect(directory/'memory.sqlite3') as target:
            source.backup(target)
        state=read(identity['prepared_state']);state.update(builds={},development_run_id=None,initiation_receipts=[])
        state.pop('pending_initiation',None);write_json(directory/'experiment.json',state)
        import shutil
        shutil.copytree(Path(identity['prepared_state']).parent/'sources',directory/'sources')
        ledger=FullLedger(directory/'observer');pool=httpx.HTTPTransport(retries=0,trust_env=False)
        started=receipt['started_at'];coordinator=None;tick=time.perf_counter()
        try:
            ledger.arm(dict(execution_identity_sha256=identity_sha,expected_system_fingerprint=identity['expected_system_fingerprint']),
                       started=started,deadline=started+LIMITS['max_seconds'])
            ledger.watchdog();ledger.sample_resources()
            from tools.research_v2.full_preflight import daily_contract_guard
            ledger.contract_guard=daily_contract_guard(identity)
            settings=Settings.model_validate(identity['query_config'])
            model=ObservedDeepSeekModel(settings,ledger,pool)
            app=create_app(settings,model=model,embedder=ObservedMiniLM(settings,ledger));instrument(app,ledger)
            with TestClient(app) as client:
                experiment=Experiment(client,directory)
                inputs=app.state.evaluation.get('evaluation_inputs',read(identity['plan_path'])['input_id'])
                coordinator=FullRun(app,inputs,read(identity['plan_path']),identity_sha)
                state=experiment.state;state.update(development_run_id=coordinator.run['run_id'],status='research_full_running',
                    full_baseline='running',blockers=[],run_origins={coordinator.run['run_id']:
                        dict(real_provider=True,real_embedding=True,mock_transport=False)})
                experiment.save()
                write_json(directory/'execution-identity.json',identity)
                write_json(directory/'observed-provider-origin.json',dict(real_provider=True,real_embedding=True,
                    mock_transport=False,adapter=type(model).__name__,identity_sha256=identity_sha))
                try:
                    build_all(app,experiment,coordinator,ledger)
                    coordinator.query(ledger)
                finally:
                    run=coordinator.finish(time.perf_counter()-tick)
                    experiment.state.update(full_baseline=run['status'],status=run['status'])
                    experiment.save()
                    target=directory/'runs'/run['run_id'];write_json(target/'run.json',run)
                    from tools.research_v2.full_analysis import analyze
                    analyze(run,target/'run.json',directory)
                    write_json(directory/'resource-usage.json',dict(cpu_user_seconds=resource.getrusage(resource.RUSAGE_SELF).ru_utime,
                        cpu_system_seconds=resource.getrusage(resource.RUSAGE_SELF).ru_stime,
                        peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                        wall_seconds=time.perf_counter()-tick,local_compute_money_cny=None))
            ledger.event('halt',{'code':'full_baseline_finished_no_more_calls'})
            from tools.research_v2.full_analysis import archive_saved
            archive_saved(directory, Path(identity['archive_directory']), identity_sha)
            return {'status':run['status'],'run_id':run['run_id'],'progress':run['progress']}
        finally:
            ledger.event('halt',{'code':'coordinator_exit_no_automatic_resume'})
            pool.close();ledger.close()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('command',choices=['check','execute']);p.add_argument('--identity',type=Path,default=IDENTITY)
    p.add_argument('--approve-identity');a=p.parse_args()
    try:
        result=execute(a.identity,a.approve_identity) if a.command=='execute' else {'status':'offline_checks_passed_not_authorized','identity_sha256':digest(a.identity),'combinations':check(a.identity)['combination_count']}
        print(json.dumps(result,indent=2))
    except (Halt,FileExistsError) as error:
        print(json.dumps({'status':'blocked','code':getattr(error,'code','already_started_or_artifact_exists')}));raise SystemExit(2)

if __name__=='__main__': main()
