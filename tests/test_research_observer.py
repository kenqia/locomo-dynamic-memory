import json
import os
from pathlib import Path
import subprocess
import sys
import threading

import httpx
import pytest
from pydantic import BaseModel

from locomo_memory.config import Settings
from locomo_memory.model import ModelFailure
from tools.research_v2.observer import Ledger, Halt, ObservedTransport, ObservedDeepSeekModel, UNITS


BODY = {'model': 'deepseek-flash', 'max_tokens': 8192, 'messages': [{'role':'system','content':'synthetic fixture'}, {'role':'user','content':'{}'}], 'thinking': {'type': 'disabled'}}


def response(**overrides):
    doc = dict(model='deepseek-flash', system_fingerprint='mock-fp', usage=dict(
        prompt_cache_hit_tokens=0, prompt_cache_miss_tokens=100,
        prompt_tokens=100, completion_tokens=2, total_tokens=102),
        choices=[{'finish_reason': 'stop', 'message': {'content': '{"value": 1}'}}])
    doc.update(overrides)
    return httpx.Response(200, json=doc)


def setup(tmp_path, callback=None, **limits):
    ledger = Ledger(tmp_path / 'controlled')
    ledger.arm({'test': True}, **limits)
    ledger.local.tags = dict(operation='extract', attempt=1)
    sent = []
    def receive(request):
        # Physical send is never reachable before durable reservation.
        assert ledger.rows()[-1]['status'] == 'reserved'
        assert Path(ledger.directory / ledger.rows()[-1]['wire_path']).exists()
        sent.append(request)
        return callback(request) if callback else response()
    transport = ObservedTransport(ledger, httpx.MockTransport(receive))
    return ledger, transport, sent


def send(transport):
    with httpx.Client(transport=transport) as client:
        return client.post('https://api.deepseek.com/chat/completions', json=BODY,
                           headers={'Authorization': 'Bearer synthetic-secret-very-distinct'})


def test_reserve_before_send_cost_and_zero_vs_missing(tmp_path):
    ledger, transport, sent = setup(tmp_path)
    send(transport)
    row = ledger.rows()[0]
    assert row['cost_nano_cny'] == 100 * 2000 + 2 * 8000
    assert row['usage']['prompt_cache_hit_tokens'] == 0
    assert row['system_fingerprint'] == 'mock-fp'
    assert row['status'] == 'settled' and len(sent) == 1
    for p in ledger.directory.iterdir():
        assert p.stat().st_mode & 0o077 == 0
        if p.suffix == '.json':
            assert b'synthetic-secret-very-distinct' not in p.read_bytes()
    ledger.close()


@pytest.mark.parametrize('limit', ['money', 'requests', 'deadline'])
def test_three_limits_independent_and_persistent(tmp_path, limit):
    kwargs = {'money': 1} if limit == 'money' else {'requests': 1} if limit == 'requests' else {}
    ledger, transport, sent = setup(tmp_path, **kwargs)
    if limit == 'requests':
        send(transport)
    if limit == 'deadline':
        ledger.clock = lambda: ledger.policy()['deadline'] + 1
    with pytest.raises(Halt):
        send(transport)
    assert len(sent) == (1 if limit == 'requests' else 0)
    directory = ledger.directory
    ledger.close()
    reopened = Ledger(directory)
    with pytest.raises(Halt, match='already_armed'):
        reopened.arm({'different': True})
    assert len(reopened.rows()) == len(sent)
    reopened.close()


@pytest.mark.parametrize('failure', ['timeout', 'missing_usage', 'inconsistent', 'http_error', 'crash'])
def test_unknown_is_reserved_and_blocks_all_retries_and_recovery(tmp_path, failure):
    def fail(request):
        if failure == 'timeout':
            raise httpx.ReadTimeout('synthetic')
        if failure == 'crash':
            raise KeyboardInterrupt()
        if failure == 'missing_usage':
            return response(usage={'prompt_tokens': 100, 'completion_tokens': 2, 'total_tokens': 102})
        if failure == 'inconsistent':
            return response(usage=dict(prompt_cache_hit_tokens=0, prompt_cache_miss_tokens=1,
                                      prompt_tokens=100, completion_tokens=2, total_tokens=102))
        return httpx.Response(503, json={'error': 'synthetic'})
    ledger, transport, sent = setup(tmp_path, fail)
    with pytest.raises((Halt, httpx.ReadTimeout, KeyboardInterrupt)):
        send(transport)
    row = ledger.rows()[0]
    assert row['cost_nano_cny'] is None and row['reservation_nano_cny'] > 0
    if failure == 'missing_usage':
        assert row['usage']['prompt_cache_hit_tokens'] is None
        assert row['system_fingerprint'] == 'mock-fp'
    with pytest.raises(Halt):
        send(transport)
    assert len(sent) == 1
    directory = ledger.directory
    ledger.close()
    recovered = Ledger(directory)
    with pytest.raises(Halt, match='unknown_billing'):
        recovered.assert_available()
    assert recovered.rows()[0]['cost_nano_cny'] is None
    recovered.close()


def test_concurrency_and_second_process_owner(tmp_path):
    entered, release = threading.Event(), threading.Event()
    def blocked(request):
        entered.set()
        assert release.wait(5)
        return response()
    ledger, transport, sent = setup(tmp_path, blocked)
    def work():
        ledger.local.tags = dict(operation='extract', attempt=1)
        send(transport)
    worker = threading.Thread(target=work)
    worker.start()
    assert entered.wait(5)
    with pytest.raises(Halt, match='concurrency'):
        send(transport)
    with pytest.raises(Halt, match='owner_already_running'):
        Ledger(ledger.directory)
    release.set()
    worker.join(5)
    assert not worker.is_alive() and len(sent) == 1
    ledger.close()


def test_watchdog_kills_trickling_or_blocked_worker(tmp_path):
    script = '''
import time, threading
from tools.research_v2.observer import Ledger
from pathlib import Path
l = Ledger(Path(__import__('sys').argv[1]))
l.arm({'test':True},seconds=0.4)
l.local.tags = {'operation':'extract'}
l.reserve(b'{}', {'model':'deepseek-flash','max_tokens':8192}, l.local.tags)
l.watchdog()
threading.Thread(target=lambda: time.sleep(50),daemon=True).start()
time.sleep(50)
'''
    result = subprocess.run([sys.executable, '-c', script, str(tmp_path / 'deadline')], timeout=5,
                            capture_output=True, env=dict(os.environ, PYTHONPATH='src:.'))
    assert result.returncode == -15, result.stderr.decode()
    recovered = Ledger(tmp_path / 'deadline')
    assert recovered.rows()[0]['status'] == 'reserved'
    with pytest.raises(Halt):
        recovered.assert_available()
    recovered.close()


def test_adapter_retry_each_physical_attempt_is_counted(tmp_path):
    class Output(BaseModel):
        value: int
    responses = iter([response(choices=[{'finish_reason':'length','message':{'content':'{}'}}]), response()])
    ledger, transport, sent = setup(tmp_path, lambda request: next(responses))
    model = ObservedDeepSeekModel(Settings(), ledger, transport.underlying, api_key='synthetic-secret-very-distinct')
    generation = model.generate('answer', {}, Output)
    assert generation.value.value == 1
    rows = ledger.rows()
    assert len(rows) == 2 and len(sent) == 2
    assert rows[0]['semantic_status'] == 'invalid_output'
    assert rows[1]['semantic_status'] == 'succeeded'
    assert [row['attempt'] for row in rows] == [1, 2]
    assert all(call['research_physical_id'] for call in generation.metadata['calls'])
    ledger.close()


def test_unknown_transport_failure_never_becomes_internal_retry(tmp_path):
    class Output(BaseModel):
        value: int
    def timeout(request):
        raise httpx.ReadTimeout('synthetic')
    ledger, transport, sent = setup(tmp_path, timeout)
    model = ObservedDeepSeekModel(Settings(), ledger, transport.underlying, api_key='synthetic-secret-very-distinct')
    with pytest.raises(ModelFailure):
        model.generate('answer', {}, Output)
    assert len(sent) == 1 and len(ledger.rows()) == 1
    ledger.close()


def test_runner_limits_and_manifest(tmp_path, monkeypatch):
    from tools.research_v2 import smoke
    # Admission is never configurable beyond this chat's explicit authorization.
    for key, value in [('money',40*UNITS+1),('requests',501),('seconds',14401)]:
        ledger = Ledger(tmp_path / key)
        with pytest.raises(Halt, match='authorization_exceeded'):
            ledger.arm({'test':True}, **{key:value})
        ledger.close()
    path = tmp_path/'frozen'
    path.mkdir()
    settings = Settings(db_path=path/'memory.sqlite3')
    identity = {'code_files':smoke.code_identity(), 'implementation_sha256':smoke.implementation_sha256(),
                'config':settings.snapshot(), 'plans':{}, 'tests':{'path':str(path/'tests.xml'),'sha256':'bad'},
                'official_sources':{}}
    (path/'tests.xml').write_text('<testsuites/>')
    (path/'execution-identity.json').write_text(json.dumps(identity))
    with pytest.raises(Halt, match='gate_evidence_changed'):
        smoke.verify_frozen(path)
    identity['code_files']['nonexistent']='changed'
    (path/'execution-identity.json').write_text(json.dumps(identity))
    with pytest.raises(Halt, match='execution_identity_changed'):
        smoke.verify_frozen(path)


def test_instrumented_build_run_trace_correlates_physical_requests(settings, sample, tmp_path):
    from fastapi.testclient import TestClient
    from locomo_memory.api import create_app
    from tools.research_v2.smoke import instrument
    from test_queries import query_provider
    from test_retrieval import ControlledEmbedder
    sample[0]['sample_id']='conv-26'
    sample[0]['conversation']['session_2'][0]['text']='I moved from Paris to Rome on 2 May 2023.'
    ledger=Ledger(tmp_path/'controlled')
    ledger.arm({'test':True})
    def provider(request):
        doc=query_provider(request).json()
        doc['model']='deepseek-flash'
        doc['system_fingerprint']='test-only'
        doc['usage'].update(prompt_cache_hit_tokens=0,prompt_cache_miss_tokens=doc['usage']['prompt_tokens'])
        return httpx.Response(200,json=doc)
    model=ObservedDeepSeekModel(settings,ledger,httpx.MockTransport(provider),api_key='synthetic-secret-very-distinct')
    app=create_app(settings,model=model,embedder=ControlledEmbedder())
    instrument(app,ledger)
    with TestClient(app) as client:
        ds=client.post('/imports',json={'data':sample,'version':'fixture','license':'synthetic'}).json()['dataset_id']
        bid=client.post('/builds',json={'dataset_id':ds,'sample_id':'conv-26'}).json()['build_id']
        assert client.get('/builds/'+bid).json()['status']=='extracted'
        assert client.post('/builds/'+bid+'/index').status_code==201
        client.post('/builds/'+bid+'/relations')
        assert client.post('/builds/'+bid+'/publish').status_code==200
        inputs=client.post('/evaluation-inputs',json={'dataset_id':ds,'samples':[
            {'sample_id':'conv-26','question':'Where does Alex live?','answer':'Rome','category':4,'evidence':['D2:1']}]}).json()
        # Fixture-only original question identity; no real dataset/experiment is altered.
        inputs['question_identities']=[{'sample_id':'conv-26','qa_index':0,'question_id':'conv-26:qa:0'}]
        with app.state.database.connect() as db:
            db.execute('UPDATE evaluation_inputs SET result_json=? WHERE input_id=?',(json.dumps(inputs),inputs['input_id']))
        run=client.post('/evaluation-runs',json={'input_id':inputs['input_id'],'build_ids':{'conv-26':bid},
                                               'strategies':['dynamic'],'wait':True}).json()
        assert run['status']=='completed',run
        assert run['progress']['succeeded']==1
        rows=ledger.rows()
        assert {r['stage'] for r in rows}=={'Extraction','Relation','Query Analysis','Resolution','Answer'}
        assert all(r['build_id']==bid and r['status']=='settled' for r in rows)
        query=[r for r in rows if r.get('run_id')==run['run_id']]
        assert len(query)==3 and all(r['question_id']=='conv-26:qa:0' and r['strategy']=='dynamic' for r in query)
        assert run['items'][0]['result']['trace']['operations']['answer']['calls'][0]['research_physical_id']==query[-1]['request_id']
    ledger.close()


def test_peak_reservation_never_crosses_40_cny_with_repeated_large_usage(tmp_path):
    def large(request):
        return response(usage=dict(prompt_cache_hit_tokens=0,prompt_cache_miss_tokens=1_000_000,
                                   prompt_tokens=1_000_000,completion_tokens=8192,total_tokens=1_008_192))
    ledger,transport,sent=setup(tmp_path,large)
    for _ in range(19):
        send(transport)
    with pytest.raises(Halt,match='money_limit'):
        send(transport)
    assert len(sent)==19
    assert sum(r['cost_nano_cny'] for r in ledger.rows()) <= 40*UNITS
    ledger.close()


def test_exact_500_physical_ceiling(tmp_path):
    ledger,transport,sent=setup(tmp_path,requests=500)
    for _ in range(500):
        send(transport)
    with pytest.raises(Halt,match='request_limit'):
        send(transport)
    assert len(sent)==500 and len(ledger.rows())==500
    ledger.close()


def test_response_persistence_failure_keeps_full_reservation(tmp_path,monkeypatch):
    ledger,transport,sent=setup(tmp_path)
    import tools.research_v2.observer as module
    original=module.durable
    def fail_response(path,value):
        if str(path).endswith('.response.json'):
            raise OSError('synthetic full disk')
        original(path,value)
    monkeypatch.setattr(module,'durable',fail_response)
    with pytest.raises(OSError):
        send(transport)
    assert len(sent)==1 and ledger.rows()[0]['cost_nano_cny'] is None
    with pytest.raises(Halt):
        send(transport)
    ledger.close()


def test_offline_cache_summary_preserves_missing_zero_and_has_no_body(tmp_path):
    from tools.research_v2.cache_analysis import aggregate,static_structure,summarize
    directory=tmp_path/'experiment'
    ledger,transport,sent=setup(directory)
    send(transport)
    # setup uses controlled/; offline reader deliberately opens only read-only SQLite.
    (directory/'controlled').rename(directory/'observer')
    ledger.directory=directory/'observer'
    ledger.path=ledger.directory/'budget.sqlite3'
    result=summarize(directory)
    assert result['overall']['token_weighted_cache_hit_rate']==0
    assert result['overall']['usage']['prompt_cache_hit_tokens']['missing_requests']==0
    assert 'synthetic-secret' not in json.dumps(result)
    assert 'messages' not in result['request_summaries'][0]
    assert len(static_structure()['operations'])==5
    missing=aggregate([{'status':'unknown','usage':{},'cost_nano_cny':None,'reservation_nano_cny':1}])
    assert missing['token_weighted_cache_hit_rate'] is None
    assert missing['usage']['prompt_cache_hit_tokens']['missing_requests']==1
    ledger.close()


def test_operator_halt_finishes_inflight_without_unknown_or_new_send(tmp_path):
    entered,release=threading.Event(),threading.Event()
    def blocked(request):
        entered.set()
        assert release.wait(5)
        return response()
    ledger,transport,sent=setup(tmp_path,blocked)
    errors=[]
    def work():
        ledger.local.tags={'operation':'relate'}
        try:
            send(transport)
        except BaseException as e:
            errors.append(type(e).__name__)
    worker=threading.Thread(target=work)
    worker.start()
    assert entered.wait(5)
    ledger.event('halt',{'code':'operator_stop_irrecoverable_build_failure'})
    release.set()
    worker.join(5)
    assert not errors and ledger.rows()[0]['status']=='settled'
    with pytest.raises(Halt,match='ledger_stopped'):
        send(transport)
    assert len(sent)==1
    ledger.close()
