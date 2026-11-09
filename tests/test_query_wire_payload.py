"""Administrative fields cannot consume evidence capacity or leak into query retries."""
from copy import deepcopy
import json

import httpx
import pytest

from locomo_memory.model import DeepSeekModel, request_messages, request_token_estimate
from locomo_memory.query_schemas import EffectiveResolution, EvidenceAnswer
from locomo_memory.raw_queries import pack_payload
from locomo_memory.raw_schemas import MixedResolution


def evidence():
    memory = dict(memory_id='m1', content='Alex painted a lake.', entity_id='Alex',
        state_key='conv-a:Alex:painting', state_dimension='painting', state_value='lake',
        memory_type='event', statement_type='fact', polarity='positive', source_ids=['s1'],
        session_times=['2023-05-02'], time=dict(original_expression='yesterday',
        anchor_source_id='s1', event_start='2023-05-01', event_end='2023-05-01',
        basis='Day before source date'), build_id='build' * 80, dataset_id='dataset' * 80,
        sample_id='conv-a', future_semantic_field={'keep': True})
    source = dict(source_id='s1', text='I painted a lake yesterday.', speaker='Alex',
        session_time='2023-05-02', session_id='session_1', position=0, dia_id='D1:1',
        dataset_id=memory['dataset_id'], sample_id='conv-a')
    return memory, source


def compact_memory(memory):
    return {k:v for k,v in memory.items() if k not in {'build_id','dataset_id','sample_id'}}


def compact_source(source):
    return {k:v for k,v in source.items() if k not in {'dataset_id','sample_id'}}


@pytest.mark.parametrize('operation', ['resolve', 'resolve_raw', 'answer', 'answer_raw'])
def test_wire_preserves_all_semantics_and_ids_without_mutating_controller_payload(operation):
    memory, source = evidence()
    relation = dict(build_id=memory['build_id'], relation_id='r1', source_ids=['s1'],
                    update_evidence={'same_process':False}, reason='Unknown process')
    payload = dict(operation=operation, memories=[memory], sources=[source], raw_sources=[source],
        relations=[relation], analysis=dict(status='succeeded', result={'entities':['Alex']},
        model_metadata={'calls':[{'usage':{'total_tokens':1234}}]}), retry_feedback={'instruction':'Keep dates'},
        time={'origin':'conversation_cutoff'}, coverage=[{'memory_ids':['m1']}])
    original = deepcopy(payload)
    wire = json.loads(request_messages(operation,payload,EvidenceAnswer)[1]['content'])
    assert wire['memories'] == [compact_memory(memory)]
    assert wire['sources'] == wire['raw_sources'] == [compact_source(source)]
    assert wire['relations'] == [{k:v for k,v in relation.items() if k!='build_id'}]
    assert wire['analysis'] == {'status':'succeeded','result':{'entities':['Alex']}}
    assert wire['time'] == payload['time'] and wire['coverage'] == payload['coverage']
    assert wire['retry_feedback'] == payload['retry_feedback']
    assert payload == original
    assert request_messages(operation,wire,EvidenceAnswer) == request_messages(operation,payload,EvidenceAnswer)


@pytest.mark.parametrize('operation', ['extract','relate','query_analysis'])
def test_build_and_analysis_payloads_keep_their_existing_contract(operation):
    memory,source = evidence()
    payload=dict(memories=[memory],sources=[source],analysis={'model_metadata':{'calls':[]}})
    assert json.loads(request_messages(operation,payload,EffectiveResolution)[1]['content']) == payload


def test_wire_budget_reserves_real_facts_instead_of_administrative_fields(settings):
    memory,source = evidence()
    second={**memory,'memory_id':'m2','content':'Alex painted a mountain.'}
    base=dict(operation='resolve_raw',question='What has Alex painted?',time={},relations=[])
    compact={**base, 'memories':[compact_memory(memory),compact_memory(second)],
             'sources':[compact_source(source)],'raw_sources':[], 'incomplete_relations':[]}
    budget=request_token_estimate('resolve_raw',compact,MixedResolution)
    payload,audit=pack_payload(base,[memory,second],[],{'s1':source},
                              settings.model_copy(update={'resolution_input_budget':budget}))
    assert [m['memory_id'] for m in payload['memories']]==['m1','m2']
    assert audit['omitted_groups']==[] and audit['input_token_count']==budget
    # Stored objects retain full scope for the controller's endpoint validation.
    assert payload['memories'][0]['build_id']==memory['build_id']


def test_query_retry_cannot_restore_removed_administrative_metadata(settings):
    memory,source=evidence()
    requests=[]
    def provider(request):
        payload=json.loads(json.loads(request.content)['messages'][1]['content'])
        requests.append(payload)
        value=dict(status='sufficient',effective_memory_ids=['m1'],explanation='Supported',
                   decisions=[] if len(requests)==1 else [dict(memory_id='m1',selected=True,reason='Supported')])
        return httpx.Response(200,json={'choices':[{'finish_reason':'stop','message':{'content':json.dumps(value)}}]})
    model=DeepSeekModel(settings.model_copy(update={'model_retries':1}),api_key='synthetic',
                        transport=httpx.MockTransport(provider))
    payload=dict(operation='resolve',memories=[memory],sources=[source],analysis={'model_metadata':{'calls':[]}})
    result=model.generate('resolve',payload,EffectiveResolution,context={'memories':{'m1':memory},'sources':{'s1':source}})
    assert result.value.effective_memory_ids==['m1'] and len(requests)==2
    assert 'retry_feedback' in requests[1]
    for request in requests:
        assert request['memories']==[compact_memory(memory)]
        assert request['sources']==[compact_source(source)]
        assert request['analysis']=={}


def test_null_compaction_preserves_validated_memory_and_relation_meaning():
    from locomo_memory.memory_schemas import MemoryDraft
    from locomo_memory.relation_schemas import RelationDraft
    memory,source=evidence()
    memory['time'].update(valid_from=None,valid_to=None)
    relation=dict(old_memory_id='m0',new_memory_id='m1',label='undetermined',reason='No proven connection',
        source_ids=['s0','s1'],support_quote=None,update_evidence=None,applicability=dict(
        from_date=None,to_date=None,condition=None,condition_satisfied=None,condition_source_ids=[],
        time_anchor_source_id=None,original_time_expression=None,time_basis=None))
    wire=json.loads(request_messages('resolve',dict(memories=[memory],relations=[relation]),EffectiveResolution)[1]['content'])
    assert 'valid_from' not in wire['memories'][0]['time']
    assert wire['relations'][0]['applicability']=={'condition_source_ids':[]}
    assert 'support_quote' not in wire['relations'][0] and 'update_evidence' not in wire['relations'][0]
    for model,original,sent in [(MemoryDraft,memory,wire['memories'][0]),(RelationDraft,relation,wire['relations'][0])]:
        known=set(model.model_fields)
        assert model.model_validate({k:v for k,v in original.items() if k in known}) == model.model_validate({k:v for k,v in sent.items() if k in known})
    assert 'unknown' in request_messages('resolve',{},EffectiveResolution)[0]['content']


def test_false_conditions_real_dates_and_stage_quotes_are_never_compacted():
    memory,_=evidence()
    relation=dict(applicability=dict(condition='On acceptance',condition_satisfied=False,
        from_date='2023-05-01',to_date='2023-05-03',condition_source_ids=['s1'],
        original_time_expression='yesterday',time_anchor_source_id='s1',time_basis='Source date'),
        support_quote='I painted a lake yesterday.',update_evidence=dict(same_process=False,
        real_stage_changed=True,old_stage={'source_id':'s1','quote':'I painted'},
        new_stage={'source_id':'s2','quote':'I started again'}))
    payload=dict(memories=[memory],relations=[relation])
    wire=json.loads(request_messages('resolve',payload,EffectiveResolution)[1]['content'])
    assert wire['relations']==[relation]
    assert wire['memories']==[compact_memory(memory)]
