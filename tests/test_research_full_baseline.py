"""Research full-baseline safety, real orchestration with synthetic data only."""
from copy import deepcopy
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import threading
import time

import httpx
import pytest
from fastapi.testclient import TestClient

from locomo_memory.api import create_app
from locomo_memory.config import Settings
from locomo_memory.experiment import Experiment
from tools.research_v2.full_budget import FullLedger, LIMITS
from tools.research_v2.full_baseline import FullRun, claim, instrument, build_all, validate_plan, STRATEGIES
from tools.research_v2.observer import Halt, ObservedTransport, ObservedDeepSeekModel, UNITS, CONTEXT_CEILING
from test_research_observer import BODY, response
from test_queries import query_provider
from test_builds import completion
from test_retrieval import ControlledEmbedder


def send(transport):
    with httpx.Client(transport=transport) as client:
        return client.post('https://api.deepseek.com/chat/completions',json={**BODY,'max_tokens':32768},
                           headers={'Authorization':'Bearer synthetic-secret-full-budget'})


def setup(tmp_path, callback=None, **limits):
    ledger=FullLedger(tmp_path/'observer');ledger.arm({'test':True},**limits)
    ledger.local.tags={'operation':'answer'};sent=[]
    def provider(request):
        assert ledger.rows()[-1]['status']=='reserved'
        sent.append(True)
        return callback(request) if callback else response()
    return ledger,ObservedTransport(ledger,httpx.MockTransport(provider)),sent


def test_full_request_ceiling_exact(tmp_path):
    ledger,transport,sent=setup(tmp_path)
    # Synthetic settled history at N-1, then use actual MockTransport at N and N+1.
    with ledger.db() as db:
        db.executemany('INSERT INTO requests VALUES (?,\'settled\',1,0,?)',
            [(str(i),json.dumps({'request_id':str(i),'usage':{}})) for i in range(11299)])
    send(transport)
    with pytest.raises(Halt,match='request_limit'): send(transport)
    assert len(sent)==1 and len(ledger.rows())==11300
    ledger.close()


def test_full_money_reservation_boundary(tmp_path):
    reservation=CONTEXT_CEILING*2000+32768*8000
    ledger,transport,sent=setup(tmp_path)
    with ledger.db() as db:
        db.execute('INSERT INTO requests VALUES (\'old\',\'settled\',1,?,?)',
                   (620*UNITS-reservation,json.dumps({'request_id':'old'})))
    send(transport)
    assert len(sent)==1
    # Force exactly one nano-CNY beyond the next admission threshold.
    with ledger.db() as db:
        db.execute("UPDATE requests SET cost=? WHERE id='old'",(620*UNITS-reservation+1,))
    with pytest.raises(Halt,match='money_limit'): send(transport)
    assert len(sent)==1
    ledger.close()


@pytest.mark.parametrize('field,value',[('money',620*UNITS+1),('requests',11301),('seconds',111601),('prior_requests',1)])
def test_full_limits_cannot_expand_or_inherit_smoke(tmp_path,field,value):
    ledger=FullLedger(tmp_path/'observer')
    with pytest.raises(Halt): ledger.arm({'test':True},**{field:value})
    ledger.close()


@pytest.mark.parametrize('failure',['timeout','http_error','missing_usage','crash','disk_failure'])
def test_full_unknown_keeps_reservation_and_reopen_refuses(tmp_path,failure,monkeypatch):
    def fail(request):
        if failure=='timeout': raise httpx.ReadTimeout('synthetic')
        if failure=='crash': raise KeyboardInterrupt()
        if failure=='http_error': return httpx.Response(503,json={'error':'synthetic'})
        if failure=='missing_usage': return response(usage={'prompt_tokens':100})
        return response()
    ledger,transport,sent=setup(tmp_path,fail)
    if failure=='disk_failure':
        import tools.research_v2.observer as observer
        original=observer.durable
        def disk(path,value):
            if str(path).endswith('.response.json'): raise OSError('synthetic disk full')
            original(path,value)
        monkeypatch.setattr(observer,'durable',disk)
    with pytest.raises((Halt,httpx.ReadTimeout,KeyboardInterrupt,OSError)): send(transport)
    assert len(sent)==1 and ledger.rows()[0]['cost_nano_cny'] is None
    assert ledger.rows()[0]['reservation_nano_cny']>0
    with pytest.raises(Halt): send(transport)
    path=ledger.directory;ledger.close();reopened=FullLedger(path)
    with pytest.raises(Halt,match='no_automatic_budget_recovery'): reopened.assert_available()
    with pytest.raises(Halt,match='already_armed'): reopened.arm({'new':True})
    reopened.close()


def test_crash_receipt_cannot_be_reset_by_new_ledger(tmp_path):
    identity={'control_directory':str(tmp_path/'control')}
    with pytest.raises(RuntimeError):
        with claim(identity,'hash','hash'):
            ledger=FullLedger(tmp_path/'runtime1');ledger.arm({'test':True});ledger.close()
            raise RuntimeError('synthetic coordinator crash')
    with pytest.raises(Halt,match='already_started'):
        with claim(identity,'hash','hash'): pytest.fail('must not start')
    # Choosing a fresh ledger does not change the external one-use claim.
    ledger=FullLedger(tmp_path/'runtime2');ledger.close()
    with pytest.raises(Halt):
        with claim(identity,'hash','hash'): pytest.fail('must not start')
    with pytest.raises(Halt,match='approval'):
        with claim({'control_directory':str(tmp_path/'another')},'hash',None): pass


def test_full_concurrency_process_and_thread(tmp_path):
    entered,release=threading.Event(),threading.Event()
    def blocked(request): entered.set();assert release.wait(5);return response()
    ledger,transport,sent=setup(tmp_path,blocked)
    def work(): ledger.local.tags={'operation':'answer'};send(transport)
    worker=threading.Thread(target=work);worker.start();assert entered.wait(5)
    with pytest.raises(Halt,match='concurrency'): send(transport)
    script='from pathlib import Path; from tools.research_v2.full_budget import FullLedger; FullLedger(Path(__import__("sys").argv[1]))'
    proc=subprocess.run([sys.executable,'-c',script,str(ledger.directory)],capture_output=True,env=dict(os.environ,PYTHONPATH='src:.'))
    assert proc.returncode!=0 and b'owner_already_running' in proc.stderr
    release.set();worker.join(5);assert len(sent)==1
    ledger.close()


def test_full_deadline_and_clock_regression(tmp_path):
    ledger,transport,sent=setup(tmp_path)
    assert ledger.policy()['deadline']-ledger.policy()['started']==111600
    ledger.clock=lambda:ledger.policy()['deadline']
    with pytest.raises(Halt,match='deadline'): send(transport)
    assert not sent;ledger.close()
    ledger,transport,sent=setup(tmp_path/'back')
    ledger.clock=lambda:0
    with pytest.raises(Halt,match='clock_regression'): send(transport)
    assert not sent;ledger.close()


def test_full_policy_tamper_blocks_send(tmp_path):
    ledger,transport,sent=setup(tmp_path)
    p=ledger.policy();p['limit_requests']+=1
    with ledger.db() as db: db.execute('UPDATE policy SET document=?',(json.dumps(p),))
    with pytest.raises(Halt,match='policy_changed'): send(transport)
    assert not sent;ledger.close()


def test_full_watchdog_preserves_unknown_reservation(tmp_path):
    code='''
from pathlib import Path
import sys,time
from tools.research_v2.full_budget import FullLedger
l=FullLedger(Path(sys.argv[1]));l.arm({'test':True},seconds=0.4)
l.reserve(b'{}',{'model':'deepseek-flash','max_tokens':32768},{'operation':'resolve'})
l.watchdog();time.sleep(50)
'''
    path=tmp_path/'watch'
    proc=subprocess.run([sys.executable,'-c',code,str(path)],timeout=5,capture_output=True,env=dict(os.environ,PYTHONPATH='src:.'))
    assert proc.returncode==-15
    ledger=FullLedger(path);assert ledger.rows()[0]['status']=='reserved'
    assert ledger.rows()[0]['cost_nano_cny'] is None;ledger.close()


def test_full_provider_fingerprint_change_preserves_known_cost_and_stops(tmp_path):
    ledger=FullLedger(tmp_path/'observer');ledger.arm({'expected_system_fingerprint':'frozen'})
    ledger.local.tags={'operation':'answer'}
    transport=ObservedTransport(ledger,httpx.MockTransport(lambda r:response(system_fingerprint='changed')))
    with pytest.raises(Halt,match='provider_identity_changed'): send(transport)
    assert ledger.rows()[0]['status']=='settled' and ledger.rows()[0]['cost_nano_cny']>0
    with pytest.raises(Halt,match='ledger_stopped'): send(transport)
    ledger.close()


def synthetic_plan(inputs):
    qs=[dict(sample_id=s['sample_id'],qa_index=i,question_id=f"{s['sample_id']}:qa:{i}",category=s['category']) for i,s in enumerate(inputs['samples'])]
    return dict(plan_id='synthetic-test-only',questions=qs,strategies=STRATEGIES)


def test_full_coordinator_fixed_denominator_and_failed_build(settings,sample,tmp_path):
    ledger=FullLedger(tmp_path/'observer');ledger.arm({'test':True})
    def provider(request):
        payload=json.loads(json.loads(request.content)['messages'][1]['content'])
        if payload.get('operation')=='answer' and not payload['memories']:
            doc=completion({'status':payload['status'],'answer':'Rome','citations':[{'memory_id':None,'source_ids':[payload['sources'][-1]['source_id']]}]}).json()
        else: doc=query_provider(request).json()
        doc.update(model='deepseek-flash',system_fingerprint='synthetic')
        doc['usage'].update(prompt_cache_hit_tokens=0,prompt_cache_miss_tokens=doc['usage']['prompt_tokens'])
        return httpx.Response(200,json=doc)
    model=ObservedDeepSeekModel(settings,ledger,httpx.MockTransport(provider),api_key='synthetic-key-full-test')
    app=create_app(settings,model=model,embedder=ControlledEmbedder());instrument(app,ledger)
    # All four actual service lifecycles; conv-30 is intentionally made to fail.
    copies=[]
    for sid in ('conv-26','conv-30','conv-41','conv-42'):
        s=deepcopy(sample[0]);s['sample_id']=sid;s['conversation']['session_2'][0]['text']='I moved from Paris to Rome on 2 May 2023.';copies.append(s)
    with TestClient(app) as client:
        imported=client.post('/imports',json={'data':copies,'version':'synthetic','license':'test-only'}).json()
        inputs=client.post('/evaluation-inputs',json={'dataset_id':imported['dataset_id'],'samples':[
            dict(sample_id=sid,question='Where does Alex live?',answer='Rome',category=4,evidence=['D2:1'])
            for sid in ('conv-26','conv-30','conv-41','conv-42')]}).json()
        plan=synthetic_plan(inputs);run=FullRun(app,inputs,plan,'synthetic-identity')
        assert len(run.execution.items(run.run['run_id']))==16
        ex=Experiment(client,tmp_path/'artifacts');ex.state.update(builds={},imported=imported)
        original=app.state.retrieval.create_index
        def index(bid):
            if app.state.builds.get(bid)['sample_id']=='conv-30': raise __import__('locomo_memory.builds',fromlist=['BuildError']).BuildError('synthetic_index_failure')
            return original(bid)
        app.state.retrieval.create_index=index
        build_all(app,ex,run,ledger)
        assert len(run.run['builds'])==3 and run.run['pins']['conv-30'] is None
        run.query(ledger);first=len(ledger.rows());run.query(ledger)
        assert len(ledger.rows())==first  # no repeated successful or failed item
        saved=run.finish(1)
        assert saved['progress']['total']==16 and saved['progress']['succeeded']==12 and saved['progress']['failed']==4
        assert saved['overall_summary']['execution']['success_rate']==.75
        assert saved['overall_summary']['baseline_run_score']['denominator']==16
        assert all(len(i['attempts'])==0 for i in saved['items'] if i['sample_id']=='conv-30')
        assert len({b['build_id'] for b in saved['builds'].values()})==3
        assert all(len(i['attempts'])==1 for i in saved['items'] if i['status']=='succeeded')
        from tools.research_v2.full_analysis import analyze, export_saved, archive_saved
        from locomo_memory.experiment import write_json
        for sid,bid in saved['pins'].items():
            if bid:
                sources=app.state.evaluation.sources(imported['dataset_id'],sid)
                write_json(tmp_path/'sources'/f'{sid}.json',sources)
        # Audit tool resolves Build exports from the saved experiment.
        import shutil
        shutil.copytree(tmp_path/'artifacts/builds',tmp_path/'builds')
        run_path=tmp_path/'run.json';write_json(run_path,saved)
        target=analyze(saved,run_path,tmp_path)
        summary=json.loads((target/'failure-atlas-summary.json').read_text())
        assert summary['semantic_review_status']=='not_evaluated'
        atlas=[json.loads(line) for line in (target/'failure-atlas.jsonl').read_text().splitlines()]
        failed_cases=[c for c in atlas if c['conversation']=='conv-30']
        assert all(c['build_id'] and c['lineage']['build_version']['published'] is False for c in failed_cases)
        assert all(c['diagnosis']['type']=='Unknown' for c in atlas)
        for path in ledger.directory.glob('*.request.json'):
            assert b'ANNOTATION ONLY' not in path.read_bytes()
        assert summary['top_10_confirmed_patterns']==[]
        metrics=json.loads((target/'metrics.json').read_text())
        assert 'source_coverage' not in metrics['summary']['full_text']
        exported=export_saved(tmp_path);assert (exported/'metrics.json').is_file()
        archived=archive_saved(tmp_path,tmp_path.parent/'archive','synthetic')
        with sqlite3.connect(archived/'memory.sqlite3') as db: assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        assert (archived/'manifest.json').is_file()
        # Native automatic v2 recovery is deliberately incompatible.
        with pytest.raises(Exception,match='evaluation_identity_changed'): run.execution.compatible(run.run)
    ledger.close()


def test_blind_material_hides_strategy_and_order():
    from tools.research_v2.full_analysis import blind_material
    run={'run_id':'test','input':{'samples':[{'question':'Where?','sample_id':'conv-26'}]},'items':[
        {'ordinal':i,'sample_index':0,'strategy':s,'result':{'trace':{'answer':{'answer':'Rome','citations':[{'memory_id':'should-not-appear','source_ids':['turn1']}]}}}}
        for i,s in enumerate(STRATEGIES)]}
    packets,key=blind_material(run,Path('.'))
    assert len(packets)==len(key)==4
    rendered=json.dumps(packets)
    assert all(s not in rendered for s in STRATEGIES)
    assert 'ordinal' not in rendered and 'should-not-appear' not in rendered
    assert all(p['review']['status']=='not_evaluated' for p in packets)
    assert {p['ticket'] for p in packets}=={k['ticket'] for k in key}


def test_scope_and_parameter_manifest_guard():
    q=[dict(sample_id=s,qa_index=i) for s,n in [('conv-26',199),('conv-30',105),('conv-41',193),('conv-42',260)] for i in range(n)]
    plan=dict(strategies=STRATEGIES,question_count=757,combination_count=3028,questions=q)
    validate_plan(plan)
    plan['questions'][0]['sample_id']='conv-43'
    with pytest.raises(Halt,match='scope'):validate_plan(plan)


def test_full_3028_denominator_persisted_before_any_build(settings,tmp_path):
    """Only synthetic QA counts match scope; no real Build, Run or HTTP used."""
    app=create_app(settings,model=object(),embedder=ControlledEmbedder())
    inputs={'input_id':'synthetic','kind':'synthetic','samples':[],'mappings':[]}
    qs=[]
    for sid,n in [('conv-26',199),('conv-30',105),('conv-41',193),('conv-42',260)]:
        for index in range(n):
            inputs['samples'].append(dict(sample_id=sid,question='Synthetic?',answer='synthetic',category=4,evidence=[]))
            inputs['mappings'].append({'scorable':False})
            qs.append(dict(sample_id=sid,qa_index=index,question_id=f'{sid}:qa:{index}',category=4))
    plan=dict(plan_id='synthetic-757',questions=qs,question_count=757,combination_count=3028,strategies=STRATEGIES)
    validate_plan(plan)
    coordinator=FullRun(app,inputs,plan,'synthetic-full-denominator')
    items=coordinator.execution.items(coordinator.run['run_id'])
    assert len(items)==3028 and all(i['status']=='pending' and not i['attempts'] for i in items)
    assert [i['strategy'] for i in items[:4]]==STRATEGIES
    with app.state.database.connect() as db:
        assert db.execute('SELECT COUNT(*) FROM build_versions').fetchone()[0]==0
    ledger=FullLedger(tmp_path/'ledger');ledger.arm({'test':True})
    # Every unavailable dependency remains in the score denominator, no provider request.
    coordinator.query(ledger)
    saved=coordinator.finish(0)
    assert saved['progress']['failed']==3028
    assert saved['overall_summary']['baseline_run_score']['denominator']==3028
    assert not ledger.rows();ledger.close()


def test_full_official_contract_rejects_price_change():
    from tools.research_v2.full_preflight import contract_from_pages
    # Synthetic public-page shape; portable and never fetches the network.
    pages={'pricing':('deepseek-flash DeepSeek-V4.1-Flash-1017 1M 最大 384K '
        '高峰时段 0.04元 0.30元 高峰时段 2元 9.0元 高峰时段 8元 27.0元 并发限制 2500 500').encode(),
        'chat':b'max_tokens 393216 reasoning_effort prompt_cache_hit_tokens prompt_cache_miss_tokens','cache':b'cache'}
    assert contract_from_pages(pages)['price_nano_cny_per_token']['miss']==2000
    pages['pricing']=pages['pricing'].replace(b'0.04',b'0.05')
    with pytest.raises(Halt,match='official_pricing'):contract_from_pages(pages)


def test_daily_price_guard_blocks_changed_price_before_next_send(tmp_path):
    from tools.research_v2.full_preflight import daily_contract_guard
    day=['2026-11-01'];calls=[]
    identity={'control_directory':str(tmp_path/'control'),'official_contract':{'contract':{'price':2}}}
    def fetch(path):calls.append(path);return {'contract':{'price':3}}
    guard=daily_contract_guard(identity,today=lambda:day[0],fetch=fetch)
    ledger,transport,sent=setup(tmp_path)
    ledger.contract_guard=guard
    send(transport);assert len(sent)==1 and not calls
    day[0]='2026-11-02'
    with pytest.raises(Halt,match='official_contract_changed'):send(transport)
    assert len(sent)==1 and len(ledger.rows())==1
    ledger.close()


def test_resource_measurement_failure_stops_future_calls(tmp_path,monkeypatch):
    ledger,transport,sent=setup(tmp_path)
    ledger.resource_snapshot()
    with ledger.db() as db:
        row=json.loads(db.execute("SELECT document FROM events WHERE kind='resource_sample'").fetchone()[0])
    assert row['cpu_user_seconds']>=0 and row['peak_rss_kib']>0 and row['local_compute_money_cny'] is None
    ledger.measurement_failed=True
    with pytest.raises(Halt,match='resource_measurement_failed'):send(transport)
    assert not sent;ledger.close()


def test_official_entrypoint_end_to_end_mock_only(settings,sample,tmp_path,monkeypatch):
    """Exercise the payable entry point with every external boundary replaced."""
    from tools.research_v2 import full_baseline as full, full_preflight
    from locomo_memory.experiment import write_json
    prepared=tmp_path/'prepared';prepared.mkdir()
    source_settings=settings.model_copy(update={'db_path':prepared/'memory.sqlite3'})
    app=create_app(source_settings,model=object(),embedder=ControlledEmbedder())
    copies=[]
    for sid in ('conv-26','conv-30','conv-41','conv-42'):
        s=deepcopy(sample[0]);s['sample_id']=sid;s['conversation']['session_2'][0]['text']='I moved from Paris to Rome on 2 May 2023.';copies.append(s)
    with TestClient(app) as client:
        imported=client.post('/imports',json={'data':copies,'version':'synthetic-entrypoint','license':'test-only'}).json()
        inputs=client.post('/evaluation-inputs',json={'dataset_id':imported['dataset_id'],'samples':[
            dict(sample_id=s['sample_id'],question='Where does Alex live?',answer='Rome',category=4,evidence=['D2:1']) for s in copies]}).json()
        plan=synthetic_plan(inputs);plan['input_id']=inputs['input_id']
        write_json(prepared/'plan.json',plan)
        for s in copies:write_json(prepared/'sources'/f"{s['sample_id']}.json",app.state.evaluation.sources(imported['dataset_id'],s['sample_id']))
    write_json(prepared/'experiment.json',dict(imported=imported,builds={},plans={},status='prepared_offline'))
    runtime=tmp_path/'runtime'
    config=settings.model_copy(update={'db_path':runtime/'memory.sqlite3','model_max_tokens':32768,'resolution_input_budget':96000}).snapshot()
    identity=dict(prepared_database=str(prepared/'memory.sqlite3'),prepared_state=str(prepared/'experiment.json'),
        runtime_directory=str(runtime),control_directory=str(tmp_path/'control'),archive_directory=str(tmp_path/'external-archive'),
        plan_path=str(prepared/'plan.json'),query_config=config,expected_system_fingerprint='synthetic',official_contract={'contract':{}})
    identity_path=tmp_path/'identity.json';write_json(identity_path,identity)
    monkeypatch.setattr(full,'check',lambda _:identity)
    monkeypatch.setattr(full_preflight,'fetch_contract',lambda _:{'contract':{}})
    monkeypatch.setenv('DEEPSEEK_API_KEY','synthetic-entrypoint-key')
    def provider(request):
        payload=json.loads(json.loads(request.content)['messages'][1]['content'])
        if payload.get('operation')=='answer' and not payload['memories']:
            doc=completion({'status':payload['status'],'answer':'Rome','citations':[{'memory_id':None,'source_ids':[payload['sources'][-1]['source_id']]}]}).json()
        else:doc=query_provider(request).json()
        doc.update(model='deepseek-flash',system_fingerprint='synthetic')
        doc['usage'].update(prompt_cache_hit_tokens=0,prompt_cache_miss_tokens=doc['usage']['prompt_tokens'])
        return httpx.Response(200,json=doc)
    monkeypatch.setattr(full.httpx,'HTTPTransport',lambda **_:httpx.MockTransport(provider))
    monkeypatch.setattr(full,'ObservedMiniLM',lambda *_:ControlledEmbedder())
    with pytest.raises(Halt,match='approval'):full.execute(identity_path,None)
    assert not runtime.exists()
    result=full.execute(identity_path,full.digest(identity_path))
    assert result['status']=='completed' and result['progress']['succeeded']==16
    state=json.loads((runtime/'experiment.json').read_text())
    assert state['full_baseline']=='completed' and state['development_run_id']==result['run_id']
    assert (runtime/'resource-usage.json').is_file()
    assert list((tmp_path/'external-archive').rglob('manifest.json'))
    with sqlite3.connect(runtime/'observer/budget.sqlite3') as db:
        requests=db.execute('SELECT COUNT(*) FROM requests').fetchone()[0]
        assert requests==40  # eight Build requests + fixed 4*8 Query stage requests
    with pytest.raises(Halt,match='already_started'):full.execute(identity_path,full.digest(identity_path))
    with sqlite3.connect(runtime/'observer/budget.sqlite3') as db:
        assert db.execute('SELECT COUNT(*) FROM requests').fetchone()[0]==requests


def test_freeze_artifacts_end_to_end_offline(tmp_path,monkeypatch):
    from tools.research_v2 import full_preflight as pre
    from locomo_memory.experiment import write_json
    from tools.research_v2.prepare import combinations
    root=tmp_path/'repo';pf=root/'private';prepared=pf/'prepared';public=root/'experiments/research-v2/full-baseline'
    public.parent.mkdir(parents=True)
    for k,v in {'ROOT':root,'PREFLIGHT':pf,'PUBLIC':public,'RUNTIME':root/'runtime',
                'IDENTITY':public.parent/'FULL_BASELINE_EXECUTION_IDENTITY.json'}.items():monkeypatch.setattr(pre,k,v)
    audit={'producer_config':Settings().snapshot(),'build_id':'synthetic-historical'}
    def history():write_json(pf/'history-audit.json',audit);return audit
    monkeypatch.setattr(pre,'audit_history',history)
    def prepare(directory,verify_embedding):
        directory.mkdir(parents=True,exist_ok=True)
        qs=[]
        for sid,(turns,n) in pre.DEVELOPMENT.items():
            write_json(directory/'sources'/f'{sid}.json',[{'synthetic_turn':i} for i in range(turns)])
            qs.extend(dict(sample_id=sid,qa_index=i,question_id=f'{sid}:qa:{i}',category=4) for i in range(n))
        plan=dict(plan_id='synthetic',questions=qs,question_count=757,combination_count=3028,strategies=STRATEGIES)
        write_json(directory/'plan-development.json',plan)
        write_json(directory/'evaluation-input-development.json',{'question_identities':qs})
        write_json(directory/'experiment.json',{})
        with sqlite3.connect(directory/'memory.sqlite3') as db:db.execute('CREATE TABLE synthetic (value TEXT)')
        (directory/'logical-combinations.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in combinations(plan)))
        return {'source_identity':{'synthetic':True},'scorer_sha256':'synthetic-test-only'}
    monkeypatch.setattr(pre,'prepare',prepare)
    official=pf/'official';official.mkdir(parents=True)
    (official/'pricing.html').write_text('deepseek-flash DeepSeek-V4.1-Flash-1017 1M 最大 384K 高峰时段 0.04元 0.30元 高峰时段 2元 9.0元 高峰时段 8元 27.0元 并发限制 2500 500')
    (official/'chat.html').write_text('max_tokens 393216 reasoning_effort prompt_cache_hit_tokens prompt_cache_miss_tokens')
    (official/'cache.html').write_text('synthetic cache fixture');write_json(official/'sources.json',[])
    write_json(pf/'preservation-before.json',{'passed':True})
    names=['test_full_request_ceiling_exact','test_full_money_reservation_boundary',
        'test_crash_receipt_cannot_be_reset_by_new_ledger','test_full_coordinator_fixed_denominator_and_failed_build',
        'test_full_watchdog_preserves_unknown_reservation','test_blind_material_hides_strategy_and_order',
        'test_official_entrypoint_end_to_end_mock_only','test_freeze_artifacts_end_to_end_offline']
    tests=root/'tests.xml';tests.write_text('<testsuites><testsuite>'+''.join('<testcase name="'+n+'"/>' for n in names)+'</testsuite></testsuites>')
    result=pre.freeze(tests)
    identity=json.loads(pre.IDENTITY.read_text())
    assert result['paid_calls']==0 and result['new_builds']==result['new_runs']==0
    assert identity['combination_count']==3028 and identity['question_count']==757
    assert identity['producer_config']==identity['query_config']
    assert identity['paid_authorization'] is None and identity['run']['run_id'] is None
    assert all(b['build_id'] is None for b in identity['builds'].values())
    assert len((public/'manifest.jsonl').read_text().splitlines())==3028
    assert set(identity['stage_contracts'])=={'Extraction','Relation','Query Analysis','Resolution','Answer'}
