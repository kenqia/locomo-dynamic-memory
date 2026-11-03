import json
import time

import httpx
import pytest

from tools.research_v2.observer import Ledger, Halt, ObservedTransport, sha
from tools.research_v2.retry import claim_parent
from test_research_observer import BODY, response


def parent_fixture(tmp_path, *, unknown=False):
    parent_path=tmp_path/'parent'
    ledger=Ledger(parent_path/'observer')
    policy=ledger.arm({'original':True})
    ledger.local.tags={'operation':'relate'}
    rid=ledger.reserve(b'{}',BODY,ledger.local.tags)
    if not unknown:
        ledger.finish(rid,response(),.1)
    ledger.event('halt',{'code':'operator_stop_irrecoverable_build_failure'})
    ledger.event('halt',{'code':'research_ledger_stopped','request_id':None})
    ledger.close()
    (parent_path/'execution-outcome.json').write_text('{"status":"stopped"}')
    child=tmp_path/'child'
    child.mkdir()
    (child/'execution-identity.json').write_text('{}')
    identity={'retry_parent':str(parent_path),
              'retry_parent_outcome_sha256':sha((parent_path/'execution-outcome.json').read_bytes()),
              'retry_authorization':'user explicitly quadrupled tokens and authorized retry'}
    return parent_path,child,identity,policy


def test_retry_retains_deadline_cost_requests_and_consumes_claim_once(tmp_path):
    path,child,identity,old=parent_fixture(tmp_path)
    parent,inherited=claim_parent(identity,child)
    assert inherited['deadline']==old['deadline']
    assert inherited['started']==old['started']
    assert inherited['prior_requests']==1
    assert inherited['prior_cost_nano_cny']==216000
    with pytest.raises(Halt,match='owner_already_running'):
        Ledger(path/'observer')
    ledger=Ledger(child/'observer')
    policy=ledger.arm({'child':True},max_tokens=32768,**inherited)
    sent=[]
    def receive(request):
        assert ledger.rows()[-1]['reservation_nano_cny']==2359296000
        sent.append(request)
        return response()
    ledger.local.tags={'operation':'relate'}
    transport=ObservedTransport(ledger,httpx.MockTransport(receive))
    with httpx.Client(transport=transport) as client:
        client.post('https://api.deepseek.com/chat/completions',json={**BODY,'max_tokens':32768})
    assert len(sent)==1 and policy['limit_requests']==500
    ledger.close()
    parent.close()
    with pytest.raises(Halt,match='retry_already_claimed'):
        claim_parent(identity,child)
    original=Ledger(path/'observer')
    with pytest.raises(Halt,match='ledger_stopped'):
        original.assert_available()
    original.close()


@pytest.mark.parametrize('limit',['money','requests','deadline'])
def test_retry_cannot_reset_original_limits(tmp_path,limit):
    ledger=Ledger(tmp_path/'child')
    policy=ledger.arm({'child':True},max_tokens=32768,prior_requests=500 if limit=='requests' else 84,
                      prior_cost_nano_cny=39_000_000_000 if limit=='money' else 3_211_692_960,
                      started=time.time()-100,deadline=time.time()+10)
    if limit=='deadline':
        ledger.clock=lambda:policy['deadline']+1
    sent=[]
    transport=ObservedTransport(ledger,httpx.MockTransport(lambda request:sent.append(request)))
    ledger.local.tags={'operation':'relate'}
    with httpx.Client(transport=transport) as client, pytest.raises(Halt):
        client.post('https://api.deepseek.com/chat/completions',json={**BODY,'max_tokens':32768})
    assert not sent
    ledger.close()


def test_retry_cannot_bypass_unknown_parent(tmp_path):
    _,child,identity,_=parent_fixture(tmp_path,unknown=True)
    with pytest.raises(Halt,match='unknown_billing'):
        claim_parent(identity,child)


def test_retry_rejects_higher_output_and_extended_duration(tmp_path):
    ledger=Ledger(tmp_path/'child')
    with pytest.raises(Halt,match='authorization_exceeded'):
        ledger.arm({},max_tokens=32769)
    with pytest.raises(Halt,match='deadline'):
        ledger.arm({},started=time.time()-100,deadline=time.time()+14400)
    ledger.close()
