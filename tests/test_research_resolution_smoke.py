import json
import time

import httpx
import pytest

from locomo_memory.config import Settings
from locomo_memory.resolution_delivery import complete_resolution_input
from tools.research_v2.observer import Ledger,Halt,sha,ObservedTransport
from tools.research_v2.resolution_smoke import claim_parent,QueryOnlyModel,validated_window
from test_research_observer import BODY,response


def fixture(tmp_path,unknown=False):
    parent=tmp_path/'parent';ledger=Ledger(parent/'observer')
    old=ledger.arm({},prior_requests=84,prior_cost_nano_cny=3_211_692_960)
    ledger.local.tags={'operation':'answer'}
    rid=ledger.reserve(b'{}',BODY,ledger.local.tags)
    if not unknown:ledger.finish(rid,response(),.1)
    ledger.event('halt',{'code':'smoke_completed_with_errors_no_more_paid_calls'})
    # Model an expired original window without waiting or resetting old accounting.
    with ledger.db() as db:
        old['started']=time.time()-14500;old['deadline']=time.time()-100
        db.execute('UPDATE policy SET document=?',(json.dumps(old),))
    ledger.close();(parent/'execution-outcome.json').write_text('{}')
    child=tmp_path/'child';child.mkdir(mode=0o700);(child/'execution-identity.json').write_text('{}')
    now=time.time();window={'source':'explicit synthetic approval','approved_at':now,'deadline':now+3600,
        'max_cny':40,'max_physical_http':500,'max_concurrency':1,'resolution_input_budget':96000,'model_max_tokens':32768}
    (child/'window-authorization.json').write_text(json.dumps(window))
    identity={'retry_parent':str(parent),'retry_parent_outcome_sha256':sha(b'{}'),
        'authorization_sha256':sha((child/'window-authorization.json').read_bytes())}
    return child,identity


def test_resolution_window_inherits_all_costs_after_original_deadline(tmp_path):
    child,identity=fixture(tmp_path)
    parent,limits=claim_parent(child,identity)
    assert limits['prior_requests']==85 and limits['prior_cost_nano_cny']==3_211_908_960
    assert limits['deadline']==validated_window(child)['deadline']
    ledger=Ledger(child/'observer');ledger.arm({},**limits)
    ledger.local.tags={'operation':'resolve'};sent=[]
    def receive(request):sent.append(request);return response()
    with httpx.Client(transport=ObservedTransport(ledger,httpx.MockTransport(receive))) as client:
        client.post('https://api.deepseek.com/chat/completions',json={**BODY,'max_tokens':32768})
    assert len(sent)==1
    ledger.clock=lambda:limits['deadline']+1
    with pytest.raises(Halt,match='deadline'):ledger.assert_available()
    ledger.close();parent.close()
    with pytest.raises(Halt,match='retry_already_claimed'):claim_parent(child,identity)


def test_resolution_window_unknown_parent_cannot_resume(tmp_path):
    child,identity=fixture(tmp_path,unknown=True)
    with pytest.raises(Halt,match='unknown_billing'):claim_parent(child,identity)


def test_resolution_budget_quadruples_without_omission():
    payload={'operation':'resolve','question':'synthetic','time':{},'analysis':{},
        'memories':[{'memory_id':'m1','content':'fact '*26000,'source_ids':['s1']}],
        'sources':[{'source_id':'s1','text':'synthetic evidence'}],'relations':[],'candidates_truncated':False}
    before=complete_resolution_input(payload,Settings())[1]
    context,after=complete_resolution_input(payload,Settings(resolution_input_budget=96000))
    assert 24000<before['input_token_count']<96000
    assert not before['within_budget'] and after['within_budget']
    assert after['input_token_count']==before['input_token_count']
    assert context['memories']['m1']==payload['memories'][0] and context['sources']['s1']==payload['sources'][0]
    assert after['omitted_groups']==[] and after['truncated'] is False
    assert Settings().resolution_input_budget==24000 and Settings().model_max_tokens==8192


@pytest.mark.parametrize('change',[{'deadline':time.time()-1},{'deadline':time.time()+7200},{'max_cny':41},{'max_physical_http':501}])
def test_resolution_window_rejects_unauthorized_limits(tmp_path,change):
    child,identity=fixture(tmp_path);p=child/'window-authorization.json';doc=json.loads(p.read_text());doc.update(change);p.write_text(json.dumps(doc))
    with pytest.raises(Halt):claim_parent(child,identity)


def test_resolution_query_adapter_rejects_build_operations(tmp_path):
    ledger=Ledger(tmp_path/'observer');ledger.arm({})
    model=QueryOnlyModel(Settings(),ledger,httpx.MockTransport(lambda req:pytest.fail('unexpected send')),api_key='synthetic')
    with pytest.raises(Halt,match='query_only_scope'):model.generate('extract',{},object)
    ledger.close()
