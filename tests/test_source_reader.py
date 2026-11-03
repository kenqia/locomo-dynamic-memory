"""Source-only citations remain strict and cover the entire answer surface."""
from copy import deepcopy

import pytest
from pydantic import ValidationError

from locomo_memory.evidence_catalog import EvidenceCatalog
from locomo_memory.layered_evidence import ContractViolation
from locomo_memory.source_reader import SupportedAnswer, source_payload, bind_supported_answer


def fixture():
    def source(sid,text,pos):
        return dict(source_id=sid,sample_id='c',dataset_id='d',session_id='session_1',
                    dia_id='D1:'+str(pos),speaker='Lea',session_time='12:00 pm on 3 July, 2023',
                    position=pos,text=text)
    sources=[source('s0','I like cityscapes.',0),source('s1','My kids and I painted the moon.',1)]
    memory=dict(memory_id='m',source_ids=['s0','s1'],content='Lea painted with her partner.',time={})
    context=dict(status='sufficient',memories={'m':memory},raw_sources={'s1':sources[1]})
    return sources,memory,context,EvidenceCatalog(sources,[memory],raw_source_ids=['s1'])


def test_only_independently_delivered_sources_can_be_addressed():
    sources,memory,context,catalog=fixture();before=deepcopy((sources,memory,context))
    payload=source_payload(catalog,dict(question='What?',memories=[memory],sources=sources))
    assert payload['evidence_refs']==['E1']
    assert [u['text'] for t in payload['turns'] for u in t['units']]==[sources[1]['text']]
    assert payload['unverified_memory_hints'][0]['content']==memory['content']
    value=dict(status='sufficient',claims=[dict(text='A moon painting with her kids.',evidence_refs=['E1'])])
    answer,audit=bind_supported_answer(catalog,value,context,source_only=True)
    assert answer.citations[0].memory_id is None
    assert answer.citations[0].source_ids==['s1']
    assert audit[0]['supports'][0]['text']==sources[1]['text']
    assert (sources,memory,context)==before


@pytest.mark.parametrize('ref',['E0','R.E1','M0.E1','E99','s1'])
def test_no_implicit_scope_expansion_or_prefix_repair(ref):
    _,_,context,catalog=fixture()
    value=dict(status='sufficient',claims=[dict(text='A moon.',evidence_refs=[ref])])
    with pytest.raises(ContractViolation,match='unknown_delivered_source_excerpt'):
        bind_supported_answer(catalog,value,context,source_only=True)


def test_free_explanation_is_not_an_unchecked_output_channel():
    with pytest.raises(ValidationError):
        SupportedAnswer.model_validate(dict(status='sufficient',claims=[],explanation='A cityscape with partner.'))
    _,_,context,catalog=fixture()
    value=dict(status='sufficient',claims=[dict(text='A moon.',evidence_refs=['E1']),
        dict(text='Her children joined her.',evidence_refs=['E1'])])
    answer,_=bind_supported_answer(catalog,value,context,source_only=True)
    assert answer.explanation is None and 'Her children' in answer.answer


def test_empty_answer_allowed_only_for_actual_insufficient_status():
    _,_,context,catalog=fixture()
    answer,_=bind_supported_answer(catalog,dict(status='insufficient',claims=[]),context,source_only=True)
    assert answer.answer=='No information available.'
    with pytest.raises(ContractViolation):
        bind_supported_answer(catalog,dict(status='sufficient',claims=[]),context,source_only=True)


def test_qualified_interface_retains_memory_scope_and_raw_interface_is_new():
    _,_,context,catalog=fixture()
    value=dict(status='sufficient',claims=[dict(text='A moon.',evidence_refs=['M0.E1'])])
    answer,_=bind_supported_answer(catalog,value,context)
    assert answer.citations[0].memory_id=='m'
    # Old candidates keep their old verdict. Only the new declared interface accepts E1.
    value['claims'][0]['evidence_refs']=['E1']
    with pytest.raises(ContractViolation):catalog.bind_answer(value,context)
    assert bind_supported_answer(catalog,value,context,source_only=True)[0].citations[0].memory_id is None


def test_valid_source_address_is_not_semantic_entailment():
    _,_,context,catalog=fixture()
    value=dict(status='sufficient',claims=[dict(text='A cityscape with a partner.',evidence_refs=['E1'])])
    answer,_=bind_supported_answer(catalog,value,context,source_only=True)
    assert 'partner' in answer.answer  # Independent semantic review must reject this.
