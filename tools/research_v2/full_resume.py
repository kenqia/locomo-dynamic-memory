"""Explicit continuation; historical unknowns retain their full reservations."""
import argparse
from contextlib import contextmanager
import fcntl
import json
import os
from pathlib import Path
import sqlite3
import time

import httpx
from fastapi.testclient import TestClient
from locomo_memory.api import create_app
from locomo_memory.config import Settings
from locomo_memory.experiment import Experiment, write_json
from locomo_memory.model import utc_now
from tools.research_v2.full_baseline import (ROOT, IDENTITY, FullRun, DEVELOPMENT,
    digest, read, dependencies, validate_plan, instrument, build_all)
from tools.research_v2.full_budget import FullLedger, LIMITS
from tools.research_v2.observer import Halt, ObservedDeepSeekModel, durable, sha
from tools.research_v2.smoke import code_identity, ObservedMiniLM
from tools.research_v2.full_preflight import fetch_contract, daily_contract_guard
from tools.research_v2.full_analysis import analyze, archive_saved

MANIFEST = ROOT/'experiments/research-v2/full-baseline-resume-1.json'
PARENT_SHA = 'e55a30615d40a05812660653b8a2abe9103591c8bbbe52a572a987e7c264fa06'


def stopped_state(directory):
    with sqlite3.connect((Path(directory)/'observer/budget.sqlite3').resolve().as_uri()+'?mode=ro', uri=True) as db:
        unknown = {r[0]: sha(json.dumps(list(r[1:]), sort_keys=True).encode()) for r in
                   db.execute("SELECT id,status,reservation,cost,record FROM requests WHERE status!='settled'")}
        return dict(policy=json.loads(db.execute('SELECT document FROM policy').fetchone()[0]), unknown=unknown,
            halt_through=db.execute("SELECT COALESCE(MAX(id),0) FROM events WHERE kind='halt'").fetchone()[0],
            requests=db.execute('SELECT COUNT(*) FROM requests').fetchone()[0],
            budget_occupied_nano_cny=db.execute('SELECT COALESCE(SUM(COALESCE(cost,reservation)),0) FROM requests').fetchone()[0])


class ContinuedLedger(FullLedger):
    def activate(self, stopped):
        if stopped_state(self.directory.parent) != stopped: raise Halt('resume_ledger_changed')
        p = stopped['policy']
        if (p['limit_nano_cny'],p['limit_requests'],p['concurrency']) != (620*10**9,11300,1):
            raise Halt('resume_limits_changed')
        if p['deadline'] > p['started']+111600 or self.clock() >= p['deadline']: raise Halt('deadline')
        self.accepted_unknown = stopped['unknown'];self.halt_through = stopped['halt_through']
        self.bind(p);self.assert_available()

    def assert_available(self):
        if not hasattr(self,'accepted_unknown'): raise Halt('explicit_resume_activation_required')
        if self.closed or getattr(self,'measurement_failed',False): raise Halt('closed_or_measurement_failed')
        p = self.policy()
        if sha(json.dumps(p,sort_keys=True).encode()) != self.policy_digest: raise Halt('budget_policy_changed')
        now = self.clock()
        if now < self.last_wall or now >= p['deadline'] or time.monotonic() >= self.monotonic_deadline:
            raise Halt('deadline_or_clock_regression')
        self.last_wall = now
        state = stopped_state(self.directory.parent)
        if state['unknown'] != self.accepted_unknown: raise Halt('new_unknown_billing_requires_reconciliation')
        if state['halt_through'] != self.halt_through: raise Halt('new_halt_requires_new_approval')


@contextmanager
def resume_claim(control, approval, expected):
    if approval != expected: raise Halt('explicit_resume_approval_required')
    control = Path(control)
    with (control/'owner.lock').open('a') as lock:
        try: fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError: raise Halt('owner_already_running') from None
        try:
            durable(control/'resume-1-claim.json',json.dumps(dict(resume_sha256=expected,
                authorized_at=utc_now(),authority='User: 继续付费执行; 继续',
                ceiling='Original cumulative limits and absolute deadline unchanged')).encode())
            yield
        finally: fcntl.flock(lock,fcntl.LOCK_UN)


def load_run(app, run_id):
    obj = FullRun.__new__(FullRun)
    obj.app, obj.db, obj.service = app, app.state.database, app.state.evaluation
    obj.execution = obj.service.execution
    with obj.db.connect() as db:
        obj.run = json.loads(db.execute('SELECT result_json FROM evaluation_runs WHERE run_id=?',(run_id,)).fetchone()[0])
    obj.items = obj.execution.items(run_id)
    # Startup can mark unattempted pending work interrupted. Only items with
    # zero attempts may return to pending; failed/unknown/successful stay put.
    for item in obj.items:
        if item['status']=='interrupted' and not item['attempts']:
            item['status']='pending';obj.save_item(item)
    return obj


def continue_builds(app, experiment, coordinator, ledger):
    # Reuse the frozen lifecycle for missing conversations; handle existing ones
    # through the same service APIs, never repeat successful physical work.
    original = app.state.builds.start
    for sid in DEVELOPMENT:
        bid = experiment.state['builds'].get(sid)
        if not bid: continue
        ledger.assert_available()
        build = app.state.builds.get(bid)
        app.state.builds.require_current_contract(build)
        if build['status']=='complete':
            if coordinator.run['pins'][sid]!=bid: raise Halt('complete_build_pin_mismatch')
            continue
        if build['phase']!='relations' or build['status']!='interrupted': raise Halt('unsupported_resume_state')
        ledger.global_tags=dict(scope='development-build',sample_id=sid,run_id=coordinator.run['run_id'])
        app.state.relations.start(bid);app.state.relations.run(bid);ledger.assert_available()
        experiment.snapshot_build(bid)
        if app.state.builds.get(bid)['status']=='related':
            app.state.versions.publish(bid);coordinator.pin(sid,bid)
        else:
            coordinator.run['build_failures'][sid]=dict(code='relation_failed',build_id=bid);coordinator.save()
    missing=[sid for sid in DEVELOPMENT if sid not in experiment.state['builds']]
    for sid in missing:
        ledger.assert_available()
        ledger.global_tags=dict(scope='development-build',sample_id=sid,run_id=coordinator.run['run_id'])
        from locomo_memory.builds import BuildError
        from locomo_memory.experiment import ExperimentError
        bid=None
        try:
            b=original(coordinator.run['input']['dataset_id'],sid,'full-baseline-20261101:'+sid)
            bid=b['build_id'];experiment.state['builds'][sid]=bid;experiment.save()
            app.state.builds.run(bid)
            if app.state.builds.get(bid)['status']!='extracted': raise BuildError('extraction_failed')
            app.state.retrieval.create_index(bid)
            if app.state.builds.get(bid)['status']!='indexed': raise BuildError('index_failed')
            app.state.relations.start(bid);app.state.relations.run(bid);ledger.assert_available()
            if app.state.builds.get(bid)['status']!='related': raise BuildError('relation_failed')
            app.state.versions.publish(bid);coordinator.pin(sid,bid)
        except (BuildError,ExperimentError) as error:
            coordinator.run['build_failures'][sid]=dict(code=error.code,build_id=bid);coordinator.save();ledger.assert_available()
        finally:
            if bid: experiment.snapshot_build(bid)
    ledger.global_tags={}


def verify(manifest):
    if digest(IDENTITY)!=PARENT_SHA or manifest['parent_sha256']!=PARENT_SHA: raise Halt('parent_identity_changed')
    parent=read(IDENTITY)
    if code_identity()!=manifest['code_files'] or dependencies()!=parent['dependencies']:
        raise Halt('resume_code_or_dependencies_changed')
    for path,h in {**parent['files'],**manifest['files']}.items():
        if digest(path)!=h: raise Halt('resume_artifact_changed')
    if stopped_state(parent['runtime_directory'])!=manifest['stopped']: raise Halt('resume_ledger_changed')
    validate_plan(read(parent['plan_path']))
    if manifest['stopped']['policy']['deadline'] <= time.time(): raise Halt('deadline')
    return parent


def freeze(tests):
    os.umask(0o077)
    if MANIFEST.exists(): raise Halt('resume_manifest_already_exists')
    parent=read(IDENTITY);current=code_identity();old=parent['code_files']
    allowed={'tools/research_v2/full_baseline.py','tools/research_v2/full_resume.py'}
    if any(current.get(k)!=v for k,v in old.items() if k not in allowed) or set(current)-set(old)!= {'tools/research_v2/full_resume.py'}:
        raise Halt('unapproved_code_difference')
    import subprocess
    original=subprocess.check_output(['git','show','b08ee2251389b1f1803dd30f53fdc3cd942983ab:tools/research_v2/full_baseline.py'],cwd=ROOT).decode()
    before='                with ledger.db() as billing:'+chr(10)+'''                    if billing.execute("SELECT COUNT(*) FROM requests WHERE status!='settled'").fetchone()[0]: status='unknown' '''.rstrip()
    after='                ledger.assert_available()  # Reject newly unknown physical outcomes.'
    if original.replace(before,after)!=(ROOT/'tools/research_v2/full_baseline.py').read_text(): raise Halt('coordinator_diff_changed')
    import xml.etree.ElementTree as ET
    tree=ET.parse(tests);cases=list(tree.iter('testcase'))
    if not cases or any(list(c) for c in cases): raise Halt('resume_tests_not_passed')
    required={'test_resume_unknown_carry_is_not_settled','test_resume_new_unknown_stops','test_resume_same_build_skips_successes','test_resume_query_preserves_run_and_items'}
    if not required.issubset({c.get('name') for c in cases}): raise Halt('resume_test_evidence_missing')
    directory=Path(parent['runtime_directory']);state=read(directory/'experiment.json')
    with sqlite3.connect((directory/'memory.sqlite3').as_uri()+'?mode=ro',uri=True) as db:
        if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok': raise Halt('database_integrity')
        if db.execute("SELECT COUNT(*) FROM evaluation_run_items WHERE status!='pending'").fetchone()[0]: raise Halt('unexpected_query_progress')
        failed=db.execute("SELECT task_id FROM relation_tasks WHERE status='failed'").fetchall()
        if len(failed)!=1: raise Halt('unexpected_failed_tasks')
        retry_task=failed[0][0]
    stopped=stopped_state(directory)
    if len(stopped['unknown'])!=1: raise Halt('unexpected_unknown_requests')
    paths=[directory/'memory.sqlite3',directory/'observer/budget.sqlite3',directory/'experiment.json',Path(tests).resolve(),ROOT/'tests/test_research_full_resume.py']
    manifest=dict(parent_sha256=PARENT_SHA,code_files=current,files={str(p):digest(p) for p in paths},
        stopped=stopped,run_id=state['development_run_id'],build_ids=state['builds'],retry_task=retry_task,
        authorization='Explicit user: 继续付费执行; 继续',created_at=utc_now(),
        unknown_policy='Original unknown row and full reservation retained; stop on any new unknown. No settlement or token inference.',
        parameters_changed=False,absolute_deadline_extended=False,limits=LIMITS,
        retry_rule='One explicit failed Relation task reactivation; all attempts retained; successes never repeated.')
    verify(manifest);durable(MANIFEST,(json.dumps(manifest,ensure_ascii=False,indent=2)+chr(10)).encode())
    return dict(manifest=str(MANIFEST),resume_sha256=digest(MANIFEST))


def execute(approval):
    os.umask(0o077)
    manifest=read(MANIFEST);expected=digest(MANIFEST)
    if approval!=expected: raise Halt('explicit_resume_approval_required')
    parent=verify(manifest);control=Path(parent['control_directory'])
    contract=fetch_contract(control/'resume-1-contract')
    if contract['contract']!=parent['official_contract']['contract']: raise Halt('official_contract_changed')
    with resume_claim(control,approval,expected):
        verify(manifest)
        directory=Path(parent['runtime_directory']);segment=directory/'resume-1';segment.mkdir(mode=0o700)
        ledger=ContinuedLedger(directory/'observer');pool=httpx.HTTPTransport(retries=0,trust_env=False)
        coordinator=None;tick=time.perf_counter();run=None
        try:
            ledger.activate(manifest['stopped']);ledger.watchdog();ledger.sample_resources()
            ledger.contract_guard=daily_contract_guard(parent)
            ledger.event('explicit_resume',dict(resume_sha256=expected,manifest=str(MANIFEST),
                original_unknowns=list(manifest['stopped']['unknown']),unknown_reservations_retained=True))
            settings=Settings.model_validate(parent['query_config'])
            model=ObservedDeepSeekModel(settings,ledger,pool)
            app=create_app(settings,model=model,embedder=ObservedMiniLM(settings,ledger));instrument(app,ledger)
            with TestClient(app) as client:
                coordinator=load_run(app,manifest['run_id']);experiment=Experiment(client,directory)
                coordinator.run.setdefault('explicit_resume_segments',[]).append(dict(identity_sha256=expected,started_at=utc_now()))
                coordinator.run['status']='running';coordinator.save()
                experiment.state.update(status='research_full_running',full_baseline='running');experiment.save()
                try:
                    continue_builds(app,experiment,coordinator,ledger);coordinator.query(ledger)
                finally:
                    run=coordinator.finish(coordinator.run['elapsed_seconds']+time.perf_counter()-tick)
                    experiment.state.update(status=run['status'],full_baseline=run['status']);experiment.save()
                    write_json(segment/'run.json',run);analyze(run,segment/'run.json',directory)
        finally:
            ledger.event('halt',{'code':'explicit_resume_segment_exit_no_automatic_restart'})
            pool.close();ledger.close()
            write_json(segment/'elapsed.json',dict(wall_seconds=time.perf_counter()-tick))
            archive_saved(directory,Path(parent['archive_directory']),PARENT_SHA)
        return dict(status=run['status'],run_id=run['run_id'],progress=run['progress'])


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['freeze','execute']);p.add_argument('--tests',type=Path);p.add_argument('--approve-resume');a=p.parse_args()
    try: print(json.dumps(freeze(a.tests) if a.command=='freeze' else execute(a.approve_resume),indent=2))
    except (Halt,FileExistsError) as e:
        print(json.dumps(dict(status='blocked',code=getattr(e,'code','resume_already_claimed'))));raise SystemExit(2)

if __name__=='__main__': main()
