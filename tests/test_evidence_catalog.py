from copy import deepcopy
import pytest
from pydantic import ValidationError

from locomo_memory.evidence_catalog import EvidenceCatalog, CatalogAnswer, sentence_spans
from locomo_memory.layered_evidence import ContractViolation


def source(sid='s1', text='I interviewed yesterday. I still like painting.', position=0):
    return dict(source_id=sid, sample_id='c1', dataset_id='d1', session_id='session_1',
                dia_id='D1:1', speaker='Alex', session_time='12:00 pm on 3 July, 2023',
                position=position, text=text)


def fact(**kwargs):
    return dict(content='Alex interviewed.', memory_type='event', statement_type='fact',
                polarity='positive', entity_id='Alex', state_dimension='application',
                evidence_refs=['E0'], time_refs=['T0'], **kwargs)


def test_exact_lossless_text_with_unicode_and_newline():
    text='Hello!\n\nI saw 👩🏽‍🎨. This is U.S. art.\tEnd'
    c=EvidenceCatalog([source(text=text)])
    assert ''.join(u['text'] for u in c.turns[0]['units']) == text
    for u in c.units.values():
        assert u['text'] == text[u['start']:u['end']]
    assert sentence_spans('') == []


def test_backend_dates_not_model_arithmetic():
    c=EvidenceCatalog([source()])
    m,a=c.bind_fact(fact())
    assert str(m.time.event_start)=='2023-07-02'
    assert m.time.anchor_source_id=='s1'
    assert a['semantic_support']=='not_established_by_binding'


def test_cross_turn_anchor_requires_selected_fact_evidence():
    c=EvidenceCatalog([source(text='Something happened yesterday.'),
                       source('s2','A car hit us. Everyone is okay.',1)])
    r=fact();r['evidence_refs']=['E1']
    with pytest.raises(ContractViolation,match='time_not_in_selected_fact_evidence'):
        c.bind_fact(r)
    r['evidence_refs']=['E0','E1']
    m,_=c.bind_fact(r)
    assert m.source_ids==['s1','s2']
    assert str(m.time.event_start)=='2023-07-02'


@pytest.mark.parametrize('field,refs,error',[
    ('evidence_refs',['forged'],'unknown_catalog_evidence'),
    ('time_refs',['forged'],'unknown_catalog_time'),
    ('evidence_refs',['E0','E0'],'duplicate_catalog_evidence'),
    ('time_refs',['T0','T0'],'duplicate_catalog_time'),
    ('evidence_refs',['E1'],'time_not_in_selected_fact_evidence'),
])
def test_no_scope_or_anchor_auto_repair(field,refs,error):
    c=EvidenceCatalog([source()]);r=fact();r[field]=refs
    with pytest.raises(ContractViolation,match=error):c.bind_fact(r)


def test_unrecognized_time_preserved_as_unknown():
    c=EvidenceCatalog([source(text='I interviewed a while ago.')])
    r=fact();r.update(time_refs=[],uncatalogued_time='a while ago')
    m,a=c.bind_fact(r)
    assert m.time.event_start is None
    assert 'a while ago' in a['source_spans'][0]['text']
    assert a['uncatalogued_time']=='a while ago'


def answer_fixture():
    sources=[source('wrong','I like painting.'),source('right','I painted a lake sunrise.',1)]
    memory=dict(memory_id='m1',source_ids=['wrong','right'],content='Alex painted.',
                statement_type='fact',polarity='positive',time={})
    c=EvidenceCatalog(sources,[memory])
    context=dict(status='sufficient',memories={'m1':memory})
    candidate=dict(status='sufficient',claims=[dict(text='A lake sunrise.',evidence_refs=['M0.E1'])])
    return sources,memory,c,context,candidate


def test_multi_source_specific_second_source_not_first():
    sources,memory,c,context,candidate=answer_fixture()
    before=deepcopy((sources,memory))
    a,claims=c.bind_answer(candidate,context)
    assert a.citations[0].source_ids==['right']
    assert claims[0]['supports'][0]['text']=='I painted a lake sunrise.'
    assert (sources,memory)==before


@pytest.mark.parametrize('ref',['M1.E1','M0.E99','R.E1','m1','right'])
def test_forged_or_cross_scope_edge_rejected(ref):
    _,_,c,context,candidate=answer_fixture();candidate['claims'][0]['evidence_refs']=[ref]
    with pytest.raises(ContractViolation,match='unknown_catalog_edge'):c.bind_answer(candidate,context)


def test_payload_keeps_every_delivered_source_and_memory_semantics():
    sources,memory,c,context,_=answer_fixture()
    p=c.answer_payload(dict(question='What?',time={'cutoff':'2023-07-03'},status='sufficient',memories=[memory],sources=sources))
    assert p['question']=='What?' and p['time']['cutoff']=='2023-07-03'
    assert p['memories'][0]['content']==memory['content']
    assert p['memories'][0]['polarity']==memory['polarity']
    assert [x['text'] for t in p['turns'] for x in t['units']]==[s['text'] for s in sources]
    assert p['memories'][0]['evidence_refs']==['M0.E0','M0.E1']


def test_raw_and_memory_do_not_cross_scope():
    sources,memory,_,context,candidate=answer_fixture()
    c=EvidenceCatalog(sources,[memory],raw_source_ids=['right'])
    candidate['claims'][0]['evidence_refs']=['R.E1']
    with pytest.raises(ValidationError):c.bind_answer(candidate,context)
    context['raw_sources']={'right':sources[1]}
    a,_=c.bind_answer(candidate,context)
    assert a.citations[0].memory_id is None


@pytest.mark.parametrize('status',['conflict','insufficient'])
def test_no_false_status_upgrade(status):
    _,_,c,context,candidate=answer_fixture();context['status']=status
    with pytest.raises(ValidationError):c.bind_answer(candidate,context)


def test_legal_citation_does_not_prove_semantics():
    _,_,c,context,candidate=answer_fixture()
    candidate['claims'][0]['text']='Alex painted a horse with a partner.'
    # Deliberate counterexample: provenance checker MUST NOT be described as a
    # semantic support checker. Independent review must mark this unsupported.
    a,_=c.bind_answer(candidate,context)
    assert 'partner' in a.answer


def test_duplicate_input_and_missing_memory_source_rejected():
    with pytest.raises(ContractViolation,match='duplicate_catalog_source'):
        EvidenceCatalog([source(),source()])
    with pytest.raises(ContractViolation,match='missing_catalog_memory_source'):
        EvidenceCatalog([source()],[dict(memory_id='m1',source_ids=['not-present'])])


def test_blank_claim_and_duplicate_refs_rejected():
    _,_,c,context,candidate=answer_fixture()
    candidate['claims'][0]['text']=' '
    with pytest.raises(ContractViolation):c.bind_answer(candidate,context)
    candidate['claims'][0].update(text='A lake.',evidence_refs=['M0.E1','M0.E1'])
    with pytest.raises(ContractViolation):c.bind_answer(candidate,context)


def test_entity_label_encoding_never_collapses_distinct_labels():
    from locomo_memory.evidence_catalog import labeled_fact
    record=fact();record.pop('entity_id');record['entity_label']="Maria's cousin"
    encoded,label=labeled_fact(record)
    assert label=="Maria's cousin"
    import re
    assert re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*',encoded['entity_id'])
    assert encoded==labeled_fact(record)[0]
    other={**record,'entity_label':'Maria s cousin'}
    assert encoded['entity_id']!=labeled_fact(other)[0]['entity_id']
    memory,audit=EvidenceCatalog([source()]).bind_fact(encoded)
    assert memory.entity_id==encoded['entity_id']
    assert encoded['content']==record['content'] and encoded['polarity']==record['polarity']
