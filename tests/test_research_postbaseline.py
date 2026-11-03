"""Synthetic offline fixtures; these are not LoCoMo quality results."""
import copy
import json
import sqlite3

import pytest

from tools.research_v2 import postbaseline as p


def judgment(ticket='t', reviewer=1):
    return dict(ticket=ticket, reviewer=f'independent-ai-reviewer-{reviewer}',
                review_kind='non_author_ai_research_review', fact_support=1.,
                citation_correctness=1., incorrect_refusal=False, partial_answer=False,
                omissions=False, temporal_identity=None, person_identity=True,
                event_identity=True, severe_error=False, provisional_type='Unknown',
                pattern=None, rationale='Synthetic source supports this answer.',
                evidence=[dict(source_id='s', quote='A dog named Coco.', role='supports_answer')],
                limitations='Synthetic non-author AI research fixture, not human truth.')


def answer():
    return dict(answer_observed=True,answer='Coco',status='sufficient',explanation='Synthetic',
                citations=[dict(source_ids=['s'])])


def test_stratified_selection_does_not_depend_on_scores_or_answers():
    meta={'input':{'samples':[{'sample_id':sid,'category':cat,'score':i,'answer':'x'}
                             for sid in ('conv-26','conv-30') for cat in (1,2) for i in range(6)]}}
    first=p.select_questions(meta)
    for row in meta['input']['samples']:
        row.update(score=100,answer='changed',question='changed')
    assert p.select_questions(meta)==first
    assert len(first)==4
    assert len({(meta['input']['samples'][i]['sample_id'],meta['input']['samples'][i]['category']) for i in first})==4


def test_blind_answer_removes_strategy_run_memory_and_preserves_missing():
    item={'strategy':'secret-arm','run_id':'secret-run','result':{'trace':{'answer':{
        'answer':'Coco','status':'sufficient','explanation':'Synthetic',
        'citations':[{'source_ids':['s'],'memory_id':'secret-memory'}]}}}}
    assert p.neutral_answer(item)==answer()
    assert 'secret' not in json.dumps(p.neutral_answer(item))
    missing=p.neutral_answer({'status':'failed'})
    assert missing['answer_observed'] is False and missing['answer'] is None


def test_readonly_connection_rejects_mutation(tmp_path):
    path=tmp_path/'db.sqlite'
    with sqlite3.connect(path) as db: db.execute('CREATE TABLE t (n)')
    before=p.file_sha(path)
    with p.readonly(path) as db, pytest.raises(sqlite3.OperationalError):
        db.execute('INSERT INTO t VALUES (1)')
    assert p.file_sha(path)==before


def test_cost_keeps_unknown_reservation_and_zero_usage_separate():
    zero={k:0 for k in ('prompt_cache_hit_tokens','prompt_cache_miss_tokens','prompt_tokens','completion_tokens')}
    rows=[dict(status='settled',cost=0,reservation=100,usage=zero,elapsed_seconds=0),
          dict(status='unknown',cost=None,reservation=200,usage=None)]
    result=p.ledger_cost(rows)
    assert result['physical_http']==2
    assert result['usage_missing_requests']==1
    assert result['unknown_reservation_cny']==2e-7
    assert result['known_peak_estimate_cny']==0
    assert result['token_weighted_cache_hit_rate'] is None


def test_failed_and_unknown_denominators_are_not_success_only():
    rows=[dict(status='succeeded',candidate=True,qa_success=.8,cost={'known_peak_estimate_cny':0,'unknown_reservation_cny':0}),
          dict(status='failed',candidate=True,qa_success=None,cost={'known_peak_estimate_cny':0,'unknown_reservation_cny':0})]
    assert p.summarize_rows(rows)['full_denominator_qa_score']==.4
    assert p.summarize_rows(rows)['execution_success_rate']==.5
    rows[1]['status']='unknown'
    assert p.summarize_rows(rows)['full_denominator_qa_score'] is None
    assert p.summarize_rows(rows)['qa_successful_scorable']['mean']==.8


@pytest.mark.parametrize('mutation',['quote','source','numeric','boolean','reviewer','missing','no_citation'])
def test_review_rejects_corrupt_evidence_and_invalid_fields(mutation):
    review=judgment();observed=answer()
    if mutation=='quote': review['evidence'][0]['quote']='Fabricated sentence'
    elif mutation=='source': review['evidence'][0]['source_id']='wrong-source'
    elif mutation=='numeric': review['fact_support']=float('nan')
    elif mutation=='boolean': review['severe_error']=1
    elif mutation=='reviewer': review['reviewer']='author'
    elif mutation=='missing': del review['event_identity']
    else: observed['citations']=[]
    with pytest.raises(ValueError):
        p.validate_review(review,observed,{'s':{'text':'A dog named Coco.'}},'independent-ai-reviewer-1')


def test_missing_answer_cannot_be_judged_as_semantic_failure():
    with pytest.raises(ValueError,match='No observed answer'):
        p.validate_review(judgment(),p.neutral_answer({}),{'s':{'text':'A dog named Coco.'}},'independent-ai-reviewer-1')


def test_crosscheck_disagreement_remains_unknown():
    initial=judgment();initial.update(temporal_identity=False,provisional_type='Temporal Failure',severe_error=True)
    cross=judgment(reviewer=2)
    result=p.review_consensus(initial,cross)
    assert result['disagreements']['temporal_identity']==[False,None]
    assert result['root_cause_type']=='Unknown'
    assert 'temporal_identity' not in result['agreed_fields']


def test_explicit_citation_agreement_classifies_only_the_visible_output():
    initial=judgment();cross=judgment(reviewer=2)
    for r in (initial,cross): r['provisional_type']='Citation Failure'
    result=p.review_consensus(initial,cross)
    assert result['supported_output_type']=='Citation Failure'
    assert result['root_cause_type']=='Unknown'
    for r in (initial,cross): r['provisional_type']='Temporal Failure'
    assert p.review_consensus(initial,cross)['supported_output_type']=='Unknown'


@pytest.fixture
def saved(tmp_path):
    runtime=tmp_path/'runtime';out=tmp_path/'atlas'
    runtime.mkdir();out.mkdir();(runtime/'sources').mkdir();(runtime/'observer').mkdir()
    source=dict(source_id='s',speaker='Person',session_time='2023-01-01',text='A dog named Coco.',position=0)
    for sid in p.DEVELOPMENT: p.write(runtime/'sources'/f'{sid}.json',[source])
    p.write(runtime/'experiment.json',{})
    database=runtime/'memory.sqlite3'
    samples=[dict(sample_id='conv-26',category=1,question='Synthetic dog?',answer='Coco')]
    metas={rid:dict(input={'samples':samples},pins={'conv-26':'b'},strategies=list(p.STRATEGIES)) for rid in p.RUNS}
    with sqlite3.connect(database) as db:
        db.execute('CREATE TABLE evaluation_run_items (run_id, ordinal, item_json)')
        for rid in p.RUNS:
            for ordinal in range(2 if rid==p.BASELINE else 1):
                status='failed' if rid==p.SUPPLEMENT else 'succeeded'
                item=dict(ordinal=ordinal,sample_id='conv-26',sample_index=0,qa_index=0,
                    question_id='q'+str(ordinal),strategy='dynamic',status=status,attempts=[],
                    result={'qa':{'value':1 if ordinal==0 else 0},'trace':{'answer':answer(),
                        'initial':{},'effective_memories':[]},'source_coverage':{'initial':1,'answer_context':1}})
                db.execute('INSERT INTO evaluation_run_items VALUES (?,?,?)',(rid,ordinal,json.dumps(item)))
    with sqlite3.connect(runtime/'observer/budget.sqlite3') as db:
        db.execute('CREATE TABLE requests (status,reservation,cost,record)')
        for index in range(2):
            wire=runtime/'observer'/f'wire-{index}.json'
            p.write(wire,{'messages':[{'role':'system','content':'Synthetic stable system'},
                {'role':'user','content':json.dumps({'question':str(index),'sources':['A dog named Coco.']})}]})
            record=dict(request_id=str(index),scope='development-query',run_id=p.BASELINE,
                question_id='q'+str(index),strategy='dynamic',stage='Answer',wire_path=wire.name,
                request_sha256=p.file_sha(wire),usage=None,build_id='b')
            db.execute('INSERT INTO requests VALUES (?,?,?,?)',
                       ('unknown' if index else 'settled',3000000000,None if index else 1000000000,json.dumps(record)))
    p.write(out/'input-integrity-before.json',{str(f):p.file_sha(f) for f in
        (database,runtime/'observer/budget.sqlite3',runtime/'experiment.json')})
    p.write(out/'run-identities.json',metas)
    p.audit(runtime,out)
    blind=out/'blind';(blind/'sources').mkdir(parents=True)
    for sid in p.DEVELOPMENT:
        (blind/'sources'/f'{sid}.jsonl').write_text(json.dumps(source)+'\n')
    key=[]
    for n,(rid,ordinal) in enumerate([(p.BASELINE,0),(p.BASELINE,1),(p.REPAIR,0)],1):
        ticket=f't{n}';a=dict(ticket=ticket,**answer());review=judgment(ticket,n)
        if n==3: review.update(incorrect_refusal=True,fact_support=0)
        packet=dict(packet_id=f'p{n}',question='Synthetic dog?',official_reference='Coco',
                    official_category=1,sources_file=str(blind/'sources/conv-26.jsonl'),answers=[a])
        p.write(blind/f'reviewer-{n}.json',[packet]);p.write(blind/f'reviewer-{n}-results.json',[review])
        p.write(blind/f'crosscheck-{n}.json',[packet] if n==3 else [])
        cross=copy.deepcopy(review);cross['reviewer']='independent-ai-reviewer-1'
        # Rotate the flagged third review to a different reviewer.
        if n==3:
            (blind/'crosscheck-3.json').write_text('[]')
            (blind/'crosscheck-1.json').write_text(json.dumps([packet]))
        key.append(dict(ticket=ticket,run_id=rid,ordinal=ordinal,strategy='dynamic'))
    p.write(blind/'crosscheck-1-results.json',[cross])
    p.write(blind/'crosscheck-2-results.json',[]);p.write(blind/'crosscheck-3-results.json',[])
    p.write(out/'sealed-review-key.json',key)
    return runtime,out


def test_audit_keeps_runs_separate_and_missing_physical_request_explicit(saved):
    runtime,out=saved
    report=json.loads((out/'summary.json').read_text())
    assert [report['runs'][rid]['logical_denominator'] for rid in p.RUNS]==[2,1,1]
    assert report['physical_cost']['unknown_reservation_cny']==3
    case=json.loads((out/p.SUPPLEMENT/'failure-atlas.jsonl').read_text())
    assert case['lineage']['actual_model_context']['status']=='no_physical_request_observed'
    assert case['diagnosis']['type']=='Unknown'
    assert json.loads((out/'input-integrity-after.json').read_text())['unchanged'] is True


def test_wire_structure_measures_order_without_exporting_source_text(saved):
    runtime,_=saved
    report=p.wire_structure(runtime)
    assert report['stages']['Answer']['requests']==2
    assert report['stages']['Answer']['first_differing_user_key']=={'question':1}
    assert 'Coco' not in json.dumps(report)
    assert report['provider_calls']==0


def test_reviews_import_validates_provenance_and_adds_score_one_errors(saved):
    runtime,out=saved
    report=p.finalize_reviews(runtime,out)
    assert report['ai_review']['primary_answers']==3
    assert report['ai_review']['crosschecked_answers']==1
    assert report['ai_review']['crosscheck_agreed_incorrect_refusals']==1
    assert report['reviewed_atlas'][p.REPAIR]['review_discovered_additions']==1
    assert report['complete_semantic_metrics'] is None
    case=json.loads((out/'reviewed'/f'{p.REPAIR}-failure-atlas.jsonl').read_text())
    assert case['qa_score']==1 and case['diagnosis']['type']=='Unknown'
    assert len(case['lineage'])==11
    assert json.loads((out/'reviewed/input-integrity.json').read_text())['unchanged'] is True
    with pytest.raises(FileExistsError): p.finalize_reviews(runtime,out)


@pytest.mark.parametrize('mutation',['ticket','self_review','source','cross_answer','original_answer','category','reference','input_hash'])
def test_reviews_reject_corrupt_or_unblinded_provenance(saved,mutation):
    runtime,out=saved;blind=out/'blind'
    path=blind/'crosscheck-1-results.json';reviews=json.loads(path.read_text())
    if mutation=='ticket': reviews[0]['ticket']='other-ticket'
    elif mutation=='self_review': reviews[0]['reviewer']='independent-ai-reviewer-3'
    elif mutation=='source': reviews[0]['evidence'][0]['quote']='invented'
    elif mutation in ('cross_answer','original_answer','category','reference'):
        packets_path=blind/('crosscheck-1.json' if mutation=='cross_answer' else 'reviewer-3.json')
        packets=json.loads(packets_path.read_text())
        if mutation=='category': packets[0]['official_category']=5
        elif mutation=='reference': packets[0]['official_reference']='Changed'
        else: packets[0]['answers'][0]['answer']='changed'
        packets_path.write_text(json.dumps(packets))
    else: (runtime/'experiment.json').write_text('{"changed":true}')
    path.write_text(json.dumps(reviews))
    with pytest.raises(ValueError): p.finalize_reviews(runtime,out)
