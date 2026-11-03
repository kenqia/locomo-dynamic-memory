"""Synthetic continuation checks; never use a live transport."""
import json
import time
from copy import deepcopy
import httpx
import pytest
from fastapi.testclient import TestClient
from locomo_memory.api import create_app
from locomo_memory.experiment import Experiment
from tools.research_v2.full_resume import ContinuedLedger, stopped_state, resume_claim, load_run, continue_builds
from tools.research_v2.full_budget import FullLedger
from tools.research_v2.full_baseline import FullRun, instrument
from tools.research_v2.observer import ObservedTransport, ObservedDeepSeekModel, Halt
from test_research_full_baseline import send, synthetic_plan
from test_research_observer import response
from test_queries import query_provider
from test_retrieval import ControlledEmbedder
from test_builds import completion


def carried(tmp_path):
    ledger=FullLedger(tmp_path/'observer');ledger.arm({'test':True})
    ledger.local.tags={'operation':'answer'}
    def fail(request): raise httpx.ReadTimeout('synthetic timeout')
    with pytest.raises(httpx.ReadTimeout): send(ObservedTransport(ledger,httpx.MockTransport(fail)))
    state=stopped_state(tmp_path);ledger.close()
    continued=ContinuedLedger(tmp_path/'observer');continued.activate(state)
    continued.local.tags={'operation':'answer'}
    return continued,state


def test_resume_unknown_carry_is_not_settled(tmp_path):
    ledger,state=carried(tmp_path);before=ledger.rows()[0]
    send(ObservedTransport(ledger,httpx.MockTransport(lambda r:response())))
    ledger.assert_available()
    assert ledger.rows()[0]==before and before['cost_nano_cny'] is None
    now=stopped_state(tmp_path)
    assert now['requests']==2 and now['budget_occupied_nano_cny']>before['reservation_nano_cny']
    assert now['policy']==state['policy'];ledger.close()


def test_resume_new_unknown_stops(tmp_path):
    ledger,state=carried(tmp_path)
    def fail(request): raise httpx.ReadTimeout('another synthetic timeout')
    with pytest.raises(httpx.ReadTimeout): send(ObservedTransport(ledger,httpx.MockTransport(fail)))
    with pytest.raises(Halt,match='new_unknown'): ledger.assert_available()
    assert len(ledger.rows())==2 and all(r['cost_nano_cny'] is None for r in ledger.rows());ledger.close()


@pytest.mark.parametrize('boundary',['money','requests','deadline','policy','halt','resource','clock'])
def test_resume_hard_boundaries(tmp_path,boundary):
    ledger,state=carried(tmp_path);sent=[]
    if boundary=='money':
        with ledger.db() as db:
            db.execute("INSERT INTO requests VALUES ('known','settled',1,?,'{}')",(620*10**9-state['budget_occupied_nano_cny'],))
    elif boundary=='requests':
        with ledger.db() as db:
            db.executemany("INSERT INTO requests VALUES (?,'settled',1,0,'{}')",[(str(i),) for i in range(11299)])
    elif boundary=='deadline': ledger.monotonic_deadline=time.monotonic()-1
    elif boundary=='clock': ledger.last_wall=time.time()+100
    elif boundary=='policy':
        with ledger.db() as db: db.execute("UPDATE policy SET document=json_set(document,'$.limit_requests',11301)")
    elif boundary=='halt': ledger.event('halt',{'code':'new stop'})
    else: ledger.measurement_failed=True
    with pytest.raises(Halt): send(ObservedTransport(ledger,httpx.MockTransport(lambda r:sent.append(1) or response())))
    assert not sent;ledger.close()


def test_resume_receipt_and_owner_cannot_repeat(tmp_path):
    with pytest.raises(Halt):
        with resume_claim(tmp_path,'wrong','right'): pass
    with resume_claim(tmp_path,'right','right'):
        with pytest.raises(Halt,match='owner'):
            with resume_claim(tmp_path,'right','right'): pass
    with pytest.raises(FileExistsError):
        with resume_claim(tmp_path,'right','right'): pass


def provider(request):
    p=json.loads(json.loads(request.content)['messages'][1]['content'])
    if p.get('operation')=='answer' and not p['memories']:
        doc=completion({'status':p['status'],'answer':'Rome','citations':[{'memory_id':None,'source_ids':[p['sources'][-1]['source_id']]}]}).json()
    else: doc=query_provider(request).json()
    doc.update(model='deepseek-flash',system_fingerprint='synthetic')
    doc['usage'].update(prompt_cache_hit_tokens=0,prompt_cache_miss_tokens=doc['usage']['prompt_tokens'])
    return httpx.Response(200,json=doc)


def test_resume_same_build_skips_successes(settings,sample,tmp_path):
    ledger=FullLedger(tmp_path/'observer');ledger.arm({'test':True})
    calls=[];failure=[True]
    def mock(request):
        p=json.loads(json.loads(request.content)['messages'][1]['content'])
        if 'new_memory' in p:
            calls.append(p['new_memory']['memory_id'])
            if failure[0]: failure[0]=False;raise httpx.ReadTimeout('synthetic')
        return provider(request)
    model=ObservedDeepSeekModel(settings,ledger,httpx.MockTransport(mock),api_key='fixture-secret-7d538997c424')
    app=create_app(settings,model=model,embedder=ControlledEmbedder());instrument(app,ledger)
    copies=[]
    for sid in ('conv-26','conv-30','conv-41','conv-42'):
        s=deepcopy(sample[0]);s['sample_id']=sid;s['conversation']['session_2'][0]['text']='I moved from Paris to Rome on 2 May 2023.';copies.append(s)
    with TestClient(app) as client:
        imported=client.post('/imports',json={'data':copies,'version':'synthetic','license':'test-only'}).json()
        inputs=client.post('/evaluation-inputs',json={'dataset_id':imported['dataset_id'],'samples':[
            dict(sample_id=sid,question='Where does Alex live?',answer='Rome',category=4,evidence=['D2:1']) for sid in ('conv-26','conv-30','conv-41','conv-42')]}).json()
        run=FullRun(app,inputs,synthetic_plan(inputs),'synthetic')
        ex=Experiment(client,tmp_path/'artifacts');ex.state['builds']={}
        bid=app.state.builds.start(imported['dataset_id'],'conv-26')['build_id'];ex.state['builds']['conv-26']=bid;ex.save()
        app.state.builds.run(bid);app.state.retrieval.create_index(bid);app.state.relations.start(bid);app.state.relations.run(bid)
        assert app.state.builds.get(bid)['status']=='relations_failed'
        run.save();runid=run.run['run_id']
    state=stopped_state(tmp_path);ledger.close()
    ledger=ContinuedLedger(tmp_path/'observer');ledger.activate(state)
    model=ObservedDeepSeekModel(settings,ledger,httpx.MockTransport(mock),api_key='fixture-secret-7d538997c424')
    app=create_app(settings,model=model,embedder=ControlledEmbedder());instrument(app,ledger)
    with TestClient(app) as client:
        ex=Experiment(client,tmp_path/'artifacts');run=load_run(app,runid)
        with app.state.database.connect() as db: db.execute("UPDATE build_versions SET status='interrupted' WHERE build_id=?",(bid,))
        continue_builds(app,ex,run,ledger)
        assert all(run.run['pins'].values()) and run.run['pins']['conv-26']==bid
        n=len(ledger.rows());continue_builds(app,ex,run,ledger);assert len(ledger.rows())==n
        with app.state.database.connect() as db:
            history=db.execute('SELECT status FROM relation_attempts WHERE task_id LIKE ? ORDER BY logical_attempt',(bid+':%',)).fetchall()
        assert [r[0] for r in history]==['failed','succeeded']
        assert calls[0]==calls[1] and len(calls)==5
        run.query(ledger);n=len(ledger.rows());run.query(ledger);assert len(ledger.rows())==n
        assert run.finish(1)['progress']['succeeded']==16
    ledger.close()


def test_resume_query_preserves_run_and_items(settings,tmp_path):
    ledger,state=carried(tmp_path)
    app=create_app(settings,model=object(),embedder=ControlledEmbedder())
    inputs={'input_id':'synthetic','samples':[dict(sample_id='conv-26',question='?',answer='a',category=4)],'mappings':[{'scorable':False}]}
    run=FullRun(app,inputs,synthetic_plan(inputs),'synthetic');run.run['pins']['conv-26']='synthetic-build';run.save()
    app.state.evaluation.execute_item=lambda *a: {'error':None}
    loaded=load_run(app,run.run['run_id']);loaded.query(ledger)
    assert all(i['status']=='succeeded' for i in loaded.items)
    again=load_run(app,run.run['run_id']);again.query(ledger)
    assert all(len(i['attempts'])==1 for i in again.items)
    with app.state.database.connect() as db: assert db.execute('SELECT COUNT(*) FROM evaluation_runs').fetchone()[0]==1
    assert ledger.rows()[0]['cost_nano_cny'] is None;ledger.close()
