"""Offline, bounded audit of persisted development runs and blinded AI review.

Only stdlib imports. No app startup, credentials, provider calls or Run writes.
"""
import argparse
from collections import Counter, defaultdict
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import random
import sqlite3
import statistics
import uuid

ROOT = Path(__file__).resolve().parents[2]
BASELINE = 'a2abe1fb49be45ccba291728e1f6b3c9'
SUPPLEMENT = 'df096a57752f496d86facefe75eaf423'
REPAIR = 'a9c2024b9b444224ad79cb5075f671ad'
RUNS = (BASELINE, SUPPLEMENT, REPAIR)
DEVELOPMENT = {'conv-26': (419,199), 'conv-30': (369,105), 'conv-41': (663,193), 'conv-42': (629,260)}
STRATEGIES = ('full_text','vector','hybrid_no_resolution','dynamic')
SEED = 'research-v2-ai-review-20261103-v1'
TYPES = ('Extraction Failure','Temporal Failure','Event Identity Failure','State Failure',
         'Retrieval Failure','Ranking Failure','Expansion Failure','Evidence Failure',
         'Reasoning Failure','Citation Failure','Cost Failure','Unknown')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def file_sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''): h.update(block)
    return h.hexdigest()


def write(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    with path.open('x') as f: json.dump(value,f,ensure_ascii=False,indent=2);f.write('\n')
    os.chmod(path,0o600)


@contextmanager
def readonly(path):
    db=sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro',uri=True)
    db.execute('PRAGMA query_only=ON')
    try: yield db
    finally: db.close()


def pointer(value,path):
    for key in path.lstrip('/').split('/') if path else []:
        key=key.replace('~1','/').replace('~0','~')
        value=value[int(key)] if isinstance(value,list) else value[key]
    return value


def at(item,path):
    try: return pointer(item,path)
    except (KeyError,IndexError,TypeError,ValueError): return None


def item_ref(database,db_sha,run_id,item,raw,path=''):
    present=not path or at(item,path) is not None
    return dict(status='available' if present else 'not_recorded',kind='sqlite_json_row',
        path=str(Path(database).resolve()),database_sha256=db_sha,table='evaluation_run_items',
        key=dict(run_id=run_id,ordinal=item['ordinal']),column='item_json',
        row_sha256=sha(raw.encode()),pointer=path if present else None)


def select_questions(meta):
    strata=defaultdict(list)
    for index,s in enumerate(meta['input']['samples']):
        strata[(s['sample_id'],s['category'])].append(index)
    # Selection depends only on official identity and a fixed seed, not scores.
    return [min(indices,key=lambda i:sha((SEED+':'+str(i)).encode()))
            for _,indices in sorted(strata.items())]


def neutral_answer(item):
    answer=at(item,'/result/trace/answer')
    if not isinstance(answer,dict):
        return dict(answer_observed=False,answer=None,status=None,explanation=None,citations=[])
    return dict(answer_observed=True,answer=answer.get('answer'),status=answer.get('status'),
        explanation=answer.get('explanation'),citations=[
            dict(source_ids=c.get('source_ids',[])) for c in answer.get('citations',[]) if isinstance(c,dict)])


def prepare_blind(database,runtime,out,metas):
    selected=select_questions(metas[BASELINE]);rng=random.SystemRandom()
    reviewer=out/'blind';reviewer.mkdir(mode=0o700)
    sources={};source_paths={}
    for sid in DEVELOPMENT:
        raw=json.loads((runtime/'sources'/f'{sid}.json').read_text())
        sources[sid]=[dict(source_id=s['source_id'],speaker=s['speaker'],session_time=s['session_time'],
                           text=s['text'],position=s['position']) for s in raw]
        path=reviewer/'sources'/f'{sid}.jsonl';path.parent.mkdir(exist_ok=True,mode=0o700)
        with path.open('x') as f:
            for s in sources[sid]: f.write(json.dumps(s,ensure_ascii=False)+'\n')
        source_paths[sid]=str(path.resolve())
    packets=[];key=[]
    with readonly(database) as db:
        for index in selected:
            sample=metas[BASELINE]['input']['samples'][index]
            entries=list(db.execute("SELECT item_json FROM evaluation_run_items WHERE run_id=? AND json_extract(item_json,'$.sample_index')=? ORDER BY ordinal",(BASELINE,index)))
            if len(entries)!=4: raise ValueError('Four arms required for paired audit')
            rng.shuffle(entries);answers=[]
            for raw, in entries:
                item=json.loads(raw);ticket=uuid.uuid4().hex
                answers.append(dict(ticket=ticket,**neutral_answer(item)))
                key.append(dict(ticket=ticket,run_id=BASELINE,ordinal=item['ordinal'],strategy=item['strategy']))
            packets.append(dict(packet_id=uuid.uuid4().hex,question=sample['question'],
                official_reference=sample['answer'],official_category=sample['category'],
                reference_notice='Reference answers can be incomplete; verify against full original sources.',
                sources_file=source_paths[sample['sample_id']],answers=answers))
        # Separately stratified targeted follow-up: all 8 repaired answers.
        for raw, in db.execute('SELECT item_json FROM evaluation_run_items WHERE run_id=? ORDER BY ordinal',(REPAIR,)):
            item=json.loads(raw);sample=metas[REPAIR]['input']['samples'][item['sample_index']]
            ticket=uuid.uuid4().hex
            packets.append(dict(packet_id=uuid.uuid4().hex,question=sample['question'],
                official_reference=sample['answer'],official_category=sample['category'],
                reference_notice='Reference answers can be incomplete; verify against full original sources.',
                sources_file=source_paths[sample['sample_id']],answers=[dict(ticket=ticket,**neutral_answer(item))]))
            key.append(dict(ticket=ticket,run_id=REPAIR,ordinal=item['ordinal'],strategy=item['strategy']))
    rng.shuffle(packets)
    # Paired answers stay together, neutral packet order is independent of official order.
    shards=[[] for _ in range(3)]
    for index,p in enumerate(packets): shards[index%3].append(p)
    for index,part in enumerate(shards): write(reviewer/f'reviewer-{index+1}.json',part)
    write(out/'sealed-review-key.json',key)
    write(out/'sampling.json',dict(seed=SEED,selection='One official QA per nonempty conversation/category stratum; no score filtering',
        baseline_question_indices=selected,baseline_answers=4*len(selected),targeted_repair_answers=8,
        total_answers=len(key),independent_ai_review='pending',human_review='not_evaluated',
        caveat='Targeted repairs are separate; neither subset estimates the full population. Content can partially reveal method.'))
    return reviewer


def ledger_cost(records):
    hit=miss=completion=prompt=0;missing=0;cost=reservation=0;seconds=0
    states=Counter();retries=0
    for r in records:
        states[r['status']]+=1;cost+=r['cost'] or 0
        if r['cost'] is None: reservation+=r['reservation']
        u=r.get('usage') or {}
        if all(type(u.get(k)) is int for k in ('prompt_cache_hit_tokens','prompt_cache_miss_tokens','prompt_tokens','completion_tokens')):
            hit+=u['prompt_cache_hit_tokens'];miss+=u['prompt_cache_miss_tokens'];prompt+=u['prompt_tokens'];completion+=u['completion_tokens']
        else: missing+=1
        seconds+=r.get('elapsed_seconds') or r.get('transport_elapsed_seconds') or 0
        retries+=int((r.get('attempt') or 1)>1)
    return dict(physical_http=sum(states.values()),states=dict(states),known_peak_estimate_cny=cost/1e9,
        unknown_reservation_cny=reservation/1e9,usage_missing_requests=missing,
        prompt_cache_hit_tokens=hit,prompt_cache_miss_tokens=miss,prompt_tokens=prompt,completion_tokens=completion,
        token_weighted_cache_hit_rate=hit/prompt if prompt else None,http_seconds_known=seconds,
        physical_internal_retries=retries,billing_notice='Frozen peak tariff estimate; not account debit. Missing differs from zero.')


def load_ledger(path):
    with readonly(path) as db:
        return [dict(json.loads(raw),status=status,cost=cost,reservation=reservation)
                for status,reservation,cost,raw in db.execute('SELECT status,reservation,cost,record FROM requests ORDER BY rowid')]


def initialize(runtime,out):
    os.umask(0o077);runtime=Path(runtime).resolve();out=Path(out).resolve()
    out.mkdir(parents=True,mode=0o700)  # exclusive, no overwriting earlier exports
    database=runtime/'memory.sqlite3';ledger=runtime/'observer/budget.sqlite3'
    before={str(p):file_sha(p) for p in (database,ledger,runtime/'experiment.json')}
    with readonly(database) as db:
        metas={rid:json.loads(db.execute('SELECT result_json FROM evaluation_runs WHERE run_id=?',(rid,)).fetchone()[0]) for rid in RUNS}
        builds=[dict(build_id=bid,conversation=sid,status=status,phase=phase) for bid,sid,status,phase in db.execute('SELECT build_id,sample_id,status,phase FROM build_versions')]
    if metas[BASELINE]['strategies']!=list(STRATEGIES): raise ValueError('Strategy identity changed')
    if len(metas[BASELINE]['input']['samples'])!=757: raise ValueError('QA denominator changed')
    if {b['conversation'] for b in builds}!=set(DEVELOPMENT) or any(b['status']!='complete' for b in builds):
        raise ValueError('Four complete Builds required')
    write(out/'input-integrity-before.json',before);write(out/'run-identities.json',metas)
    write(out/'build-identities.json',builds)
    prepare_blind(database,runtime,out,metas)
    return before,metas


def trace_lineage(database,db_sha,rid,item,raw,runtime,wire):
    def ref(path): return item_ref(database,db_sha,rid,item,raw,path)
    trace=at(item,'/result/trace') or {}
    bid=item.get('build_id') or next((r['build_id'] for r in wire if r.get('build_id')),None)
    initial='initial' if isinstance(trace.get('initial'),dict) else 'retrieval'
    expanded='expanded' if isinstance(trace.get('expanded'),dict) else 'expansion'
    final=next((k for k in ('effective_memories','delivered_memories','answer_context_sources','answer_context') if trace.get(k) is not None),None)
    bid_ref=dict(status='available' if bid else 'not_linked',kind='sqlite_table',
        path=str(database),database_sha256=db_sha,table='build_versions',key=dict(build_id=bid))
    return dict(
        original_source_turns=dict(status='available',path=str(runtime/'sources'/f"{item['sample_id']}.json"),
            sha256=file_sha(runtime/'sources'/f"{item['sample_id']}.json")),
        build_version=bid_ref,
        extracted_memory=dict(status='available' if bid else 'not_linked',kind='sqlite_table',path=str(database),
            database_sha256=db_sha,table='memories',where=dict(build_id=bid)),
        memory_source_mapping=dict(status='available' if bid else 'not_linked',kind='sqlite_join',path=str(database),
            database_sha256=db_sha,tables=['memories','memory_sources','source_turns'],where=dict(build_id=bid)),
        initial_bm25_dense_rrf=dict(applicability='input_coverage_only' if item['strategy']=='full_text' else 'retrieval',
            artifact=ref('/result/trace/'+initial)),
        history_expansion=ref('/result/trace/'+expanded),
        final_effective_evidence=ref('/result/trace/'+final) if final else dict(status='not_recorded'),
        actual_model_context=dict(status='exact_wire_recorded' if wire else 'no_physical_request_observed',
            stages={s:('physical_request_observed' if any(r['stage']==s for r in wire)
                       else 'no_physical_request_observed') for s in ('Query Analysis','Resolution','Answer')},
            physical_requests=[dict(request_id=r['request_id'],stage=r['stage'],status=r['status'],
                request=dict(path=str(runtime/'observer'/r['wire_path']),sha256=r['request_sha256']),
                response=dict(path=str(runtime/'observer'/r['response_path']),sha256=r.get('response_sha256'))
                    if r.get('response_path') else None,
                response_observed=r.get('response_received',False)) for r in wire],
            notice='Stored request proves intended bytes; timeout does not prove model receipt or understanding.'),
        model_answer=ref('/result/trace/answer'),final_citations=ref('/result/trace/answer/citations'),
        cost_and_trace=dict(attempts=ref('/attempts'),trace=ref('/result/trace'),physical=ledger_cost(wire)))


def summarize_rows(rows):
    def measure(field):
        known=[r[field] for r in rows if r.get(field) is not None]
        return dict(mean=sum(known)/len(known) if known else None,measured=len(known),unknown=len(rows)-len(known))
    states=Counter(r['status'] for r in rows)
    unknown=any(r['status'] not in ('succeeded','failed') or
                (r['status']=='succeeded' and r.get('qa_success') is None) for r in rows)
    return dict(planned=len(rows),states=dict(states),
        execution_success_rate=states['succeeded']/len(rows) if rows else None,
        full_denominator_qa_score=None if unknown or not rows else sum(r.get('qa_success') or 0 for r in rows)/len(rows),
        full_denominator_score_status='unknown_outcomes_or_missing_scores' if unknown else 'all_planned_outcomes_known',
        candidates=sum(r['candidate'] for r in rows),qa_successful_scorable=measure('qa_success'),
        initial_retrieval_source_overlap=measure('initial_coverage'),
        final_evidence_source_overlap=measure('final_coverage'),full_text_input_coverage=measure('full_text_coverage'),
        known_query_peak_estimate_cny=sum(r['cost']['known_peak_estimate_cny'] for r in rows),
        unknown_query_reservation_cny=sum(r['cost']['unknown_reservation_cny'] for r in rows),
        per_item_query_peak_estimate_cny=measure('complete_cost'),
        semantic_citation_correctness=None,severe_error_ratio=None,
        semantic_review_status='not_evaluated_full_denominator')


def observations(item):
    trace=at(item,'/result/trace') or {};qa=at(item,'/result/qa/value')
    result=[]
    code=at(item,'/result/error/code') or (item.get('error') or {}).get('code')
    if code: result.append(dict(kind='execution_error',code=code,proof='/result/error' if at(item,'/result/error') else '/error'))
    if item['status']=='unknown': result.append(dict(kind='unknown_logical_outcome',proof='/status'))
    if item['status']=='succeeded' and isinstance(qa,(int,float)) and qa<1:
        result.append(dict(kind='score_discrepancy',code='qa_below_one',proof='/result/qa',
            notice='Scorer discrepancy is not a semantic root cause.'))
    answer=trace.get('answer') or {}
    if answer.get('status')=='insufficient':
        result.append(dict(kind='answer_status',code='insufficient',proof='/result/trace/answer/status',
            notice='Refusal correctness requires source review.'))
    if trace.get('evidence_budget',{}).get('truncated'):
        result.append(dict(kind='delivery_budget',code='evidence_truncated',proof='/result/trace/evidence_budget',
            notice='Truncation does not alone prove a wrong answer.'))
    return result


def audit(runtime,out):
    os.umask(0o077)
    runtime=Path(runtime).resolve();out=Path(out).resolve()
    before=json.loads((out/'input-integrity-before.json').read_text())
    metas=json.loads((out/'run-identities.json').read_text())
    database=runtime/'memory.sqlite3';records=load_ledger(runtime/'observer/budget.sqlite3')
    physical=defaultdict(list);wire_issues=[];verified=0
    for r in records:
        if r.get('scope')=='development-query':
            physical[(r.get('run_id'),r.get('question_id'),r.get('strategy'))].append(r)
        for field,hfield in [('wire_path','request_sha256'),('response_path','response_sha256')]:
            if not r.get(field): continue
            name=r[field]
            if Path(name).name!=name: raise ValueError('Wire path escapes controlled observer')
            path=runtime/'observer'/name
            if not path.is_file() or file_sha(path)!=r.get(hfield):
                wire_issues.append(dict(request_id=r['request_id'],side=field))
            else: verified+=1
    if wire_issues: raise ValueError('Original wire hash mismatch')
    summaries={};case_refs={};all_observations=Counter()
    with readonly(database) as db:
        for rid in RUNS:
            meta=metas[rid];rows=[];seen=set();cases=0;scope=out/rid;scope.mkdir(mode=0o700)
            initial_gaps=Counter();lineage_counts=Counter();errors=Counter();patterns=Counter()
            with (scope/'failure-atlas.jsonl').open('x') as atlas,(scope/'item-metrics.jsonl').open('x') as metrics:
                for ordinal,raw in db.execute('SELECT ordinal,item_json FROM evaluation_run_items WHERE run_id=? ORDER BY ordinal',(rid,)):
                    item=json.loads(raw);sid=item['sample_id'];strategy=item['strategy']
                    if item['ordinal']!=ordinal: raise ValueError('SQLite ordinal disagrees with item')
                    if sid not in DEVELOPMENT or strategy not in STRATEGIES: raise ValueError('Out-of-development item')
                    key=(item['question_id'],strategy)
                    if key in seen: raise ValueError('Duplicate logical combination in one Run')
                    seen.add(key)
                    sample=meta['input']['samples'][item['sample_index']]
                    if sample['sample_id']!=sid: raise ValueError('QA sample identity mismatch')
                    wire=physical.get((rid,item['question_id'],strategy),[])
                    cost=ledger_cost(wire);result=item.get('result') or {};trace=result.get('trace') or {}
                    cover=result.get('source_coverage') or {};qa=(result.get('qa') or {}).get('value')
                    obs=observations(item);candidate=item['status']!='succeeded' or (qa is not None and qa<1)
                    counts=result.get('source_sets',{});nsources=len(set(counts['answer_context'])) if 'answer_context' in counts else None
                    row=dict(run_id=rid,ordinal=ordinal,conversation=sid,category=str(sample['category']),strategy=strategy,
                        question_id=item['question_id'],status=item['status'],candidate=candidate,
                        qa_success=qa if item['status']=='succeeded' else None,
                        initial_coverage=cover.get('initial') if strategy!='full_text' else None,
                        final_coverage=cover.get('answer_context') if strategy!='full_text' else None,
                        full_text_coverage=cover.get('answer_context') if strategy=='full_text' else None,
                        memory_source_count='not_applicable' if strategy=='full_text' else str(nsources) if nsources is not None else 'unknown',
                        cost=cost,complete_cost=cost['known_peak_estimate_cny'] if wire and not cost['unknown_reservation_cny'] else None)
                    rows.append(row);metrics.write(json.dumps(row)+'\n')
                    if result.get('error'): errors[result['error'].get('code','missing_code')]+=1
                    for ob in obs: patterns[ob.get('code',ob['kind'])]+=1
                    if not candidate: continue
                    caseid=f'{rid}:{ordinal}';cases+=1
                    lineage=trace_lineage(database,before[str(database)],rid,item,raw,runtime,wire)
                    if lineage['build_version']['key']['build_id'] is None:
                        bid=meta['pins'].get(sid)
                        lineage['build_version']['key']['build_id']=bid;lineage['build_version']['status']='available'
                        lineage['extracted_memory']['where']['build_id']=bid;lineage['extracted_memory']['status']='available'
                        lineage['memory_source_mapping']['where']['build_id']=bid;lineage['memory_source_mapping']['status']='available'
                    for stage,p in lineage.items():
                        status=p.get('status') or (p.get('artifact') or {}).get('status') or ('available' if stage=='cost_and_trace' else 'unknown')
                        lineage_counts[stage+':'+status]+=1
                    diagnosis=dict(type='Unknown',status='unreviewed',pattern=None,evidence=[],
                        reviewer=None,severe=None,citation_correctness=None,
                        reason='Execution observations and score discrepancy do not identify semantic root cause.')
                    case=dict(atlas_version='failure-atlas-v2',case_id=caseid,run_id=rid,build_id=meta['pins'].get(sid),
                        question_id=item['question_id'],qa_index=item['qa_index'],conversation=sid,
                        category=sample['category'],strategy=strategy,execution_status=item['status'],qa_score=qa,
                        observations=obs,diagnosis=diagnosis,lineage=lineage,metrics=row,
                        run_artifact=item_ref(database,before[str(database)],rid,item,raw),
                        source_run_id=item.get('source_run_id'),source_ordinal=item.get('source_ordinal'),
                        notice='Independent Run; never splice follow-ups into original baseline.')
                    atlas.write(json.dumps(case,ensure_ascii=False)+'\n');case_refs[caseid]=dict(run_id=rid,ordinal=ordinal)
            groups={}
            for dim in ('conversation','category','strategy','memory_source_count'):
                values=defaultdict(list)
                for row in rows: values[row[dim]].append(row)
                groups[dim]={k:summarize_rows(v) for k,v in sorted(values.items())}
            query=[r for r in records if r.get('run_id')==rid and r.get('scope')=='development-query']
            summaries[rid]=dict(run_id=rid,configuration=meta.get('supplemental') or
                dict(resolution_input_budget=96000,model_max_tokens=32768,research_configuration=True),
                logical_denominator=len(rows),review_candidates=cases,all_items=summarize_rows(rows),
                groups=groups,execution_errors=dict(errors),observed_signals=dict(patterns),
                lineage_counts=dict(lineage_counts),query_cost=ledger_cost(query),
                query_cost_by_strategy={s:ledger_cost([r for r in query if r.get('strategy')==s]) for s in STRATEGIES},
                semantic_root_causes='Unknown pending supported independent review',
                top_10_confirmed_semantic_patterns=[],full_text_notice='Full Text overlap is input completeness, never retrieval quality.')
            write(scope/'summary.json',summaries[rid])
    build_records=[r for r in records if r.get('scope')=='development-build']
    report=dict(version='postbaseline-atlas-v2',runs=summaries,live_model_calls=0,
        physical_cost=ledger_cost(records),cost_by_stage={s:ledger_cost([r for r in records if r['stage']==s]) for s in sorted({r['stage'] for r in records})},
        build_cost=ledger_cost(build_records),
        build_cost_by_conversation={s:ledger_cost([r for r in build_records if r.get('sample_id')==s]) for s in DEVELOPMENT},
        wire_verification=dict(verified_files=verified,mismatches=wire_issues),
        semantic_review_status='pending_independent_ai_subset',human_review_status='not_evaluated',
        complete_semantic_metrics=None,top_10_confirmed_full_population_patterns=[],
        scope='Four development conversations only; separate original baseline, 59 and 8 follow-ups; no hidden-test claims.')
    write(out/'summary.json',report)
    after={path:file_sha(path) for path in before}
    write(out/'input-integrity-after.json',dict(before=before,after=after,unchanged=before==after))
    if before!=after: raise ValueError('Original inputs changed during offline analysis')
    return report


NUMERIC_REVIEW_FIELDS = ('fact_support','citation_correctness')
BOOLEAN_REVIEW_FIELDS = ('incorrect_refusal','partial_answer','omissions','temporal_identity',
                         'person_identity','event_identity','severe_error')


def validate_review(review, answer, sources, reviewer):
    """Validate provenance and shape, not the truth of the semantic judgment."""
    if review.get('reviewer') != reviewer or review.get('review_kind') != 'non_author_ai_research_review':
        raise ValueError('Unexpected reviewer identity or kind')
    for field in NUMERIC_REVIEW_FIELDS:
        value=review.get(field)
        if field not in review or (value is not None and
                (type(value) not in (int,float) or not math.isfinite(value) or not 0<=value<=1)):
            raise ValueError('Invalid numeric review field: '+field)
    for field in BOOLEAN_REVIEW_FIELDS:
        if field not in review or (review[field] is not None and type(review[field]) is not bool):
            raise ValueError('Invalid nullable boolean: '+field)
    if review.get('provisional_type') not in TYPES: raise ValueError('Invalid failure type')
    if not isinstance(review.get('rationale'),str) or not review['rationale'].strip():
        raise ValueError('Review rationale required')
    if not isinstance(review.get('limitations'),str) or not review['limitations'].strip():
        raise ValueError('Review limitations required')
    if review.get('pattern') is not None and not isinstance(review['pattern'],str):
        raise ValueError('Invalid pattern')
    evidence=review.get('evidence')
    if not isinstance(evidence,list): raise ValueError('Evidence list required')
    for e in evidence:
        if not isinstance(e,dict) or not isinstance(e.get('quote'),str) or not e['quote'].strip():
            raise ValueError('Nonempty verbatim quote required')
        if e.get('source_id') not in sources or e['quote'] not in sources[e['source_id']]['text']:
            raise ValueError('Evidence quote is not in the identified original source')
        if not isinstance(e.get('role'),str) or not e['role']: raise ValueError('Evidence role required')
    if not answer['answer_observed']:
        if any(review[f] is not None for f in NUMERIC_REVIEW_FIELDS+BOOLEAN_REVIEW_FIELDS) or review['provisional_type']!='Unknown':
            raise ValueError('No observed answer cannot receive a semantic outcome judgment')
    elif not evidence:
        raise ValueError('Observed answer review requires original-source evidence')
    if not answer.get('citations') and review['citation_correctness'] is not None:
        raise ValueError('No citations must remain unscored, not zero')


def review_set(blind, prefix, primary=None):
    """Require exact ticket allocation; cross-checks cannot be self-reviews."""
    found={};assigned={};inputs={}
    source_cache={}
    for number in range(1,4):
        packets_path=blind/f'{prefix}-{number}.json'
        results_path=blind/f'{prefix}-{number}-results.json'
        packets=json.loads(packets_path.read_text());results=json.loads(results_path.read_text())
        expected={}
        for packet in packets:
            source_path=Path(packet['sources_file']).resolve()
            if source_path.parent != (blind/'sources').resolve(): raise ValueError('Source path escapes blind sources')
            if source_path not in source_cache:
                source_rows=[json.loads(s) for s in source_path.read_text().splitlines()]
                source_cache[source_path]={s['source_id']:s for s in source_rows}
                if len(source_cache[source_path])!=len(source_rows): raise ValueError('Duplicate source identity')
            inputs[str(source_path)]=file_sha(source_path)
            for answer in packet['answers']:
                ticket=answer['ticket']
                if ticket in expected or ticket in assigned: raise ValueError('Duplicate ticket allocation')
                expected[ticket]=(answer,source_cache[source_path],packet)
        if not isinstance(results,list): raise ValueError('Review results must be an array')
        actual=[r.get('ticket') for r in results]
        if len(set(actual))!=len(actual) or set(actual)!=set(expected): raise ValueError('Ticket coverage mismatch')
        for review in results:
            ticket=review['ticket'];answer,sources,packet=expected[ticket]
            validate_review(review,answer,sources,f'independent-ai-reviewer-{number}')
            if primary is not None:
                if ticket not in primary or primary[ticket]['reviewer']==review['reviewer']:
                    raise ValueError('Cross-check must have a different primary reviewer')
            found[ticket]=review;assigned[ticket]=packet
        inputs[str(packets_path)]=file_sha(packets_path);inputs[str(results_path)]=file_sha(results_path)
    return found,assigned,inputs


def review_consensus(first, second=None):
    fields=NUMERIC_REVIEW_FIELDS+BOOLEAN_REVIEW_FIELDS+('provisional_type',)
    agreements={k:first[k] for k in fields if second is not None and first[k]==second[k] and first[k] is not None}
    disagreements={k:[first[k],second[k]] for k in fields if second is not None and first[k]!=second[k]}
    return dict(status='crosschecked_ai' if second else 'single_ai_review',
        agreed_fields=agreements,disagreements=disagreements,
        supported_output_type='Citation Failure' if agreements.get('provisional_type')=='Citation Failure' else 'Unknown',
        root_cause_type='Unknown',root_cause_status='internal_stage_not_independently_reviewed',
        notice='Agreement of AI reviewers is not human ground truth; no stage root cause inferred.')


def review_metrics(rows):
    result=dict(answers=len(rows))
    for field in NUMERIC_REVIEW_FIELDS+BOOLEAN_REVIEW_FIELDS:
        values=[r[field] for r in rows if r[field] is not None]
        result[field]=dict(mean=sum(values)/len(values) if values else None,
                           measured=len(values),unknown=len(rows)-len(values))
    return result


def needs_review(review):
    return (any(review[f] is not None and review[f]<1 for f in NUMERIC_REVIEW_FIELDS) or
            any(review[f] is True for f in ('incorrect_refusal','partial_answer','omissions','severe_error')) or
            any(review[f] is False for f in ('temporal_identity','person_identity','event_identity')) or
            review['provisional_type']!='Unknown')


def wire_structure(runtime):
    """Bounded consecutive-request comparison; exports hashes and shapes only."""
    runtime=Path(runtime).resolve();groups={};previous={}
    for record in load_ledger(runtime/'observer/budget.sqlite3'):
        name=record['wire_path']
        if Path(name).name!=name: raise ValueError('Wire path escapes controlled directory')
        raw=(runtime/'observer'/name).read_bytes()
        if sha(raw)!=record['request_sha256']: raise ValueError('Request wire hash mismatch')
        messages=json.loads(raw)['messages'];system=messages[0]['content'];user=json.loads(messages[1]['content'])
        stage=record['stage'];system_hash=sha(system.encode())
        group=groups.setdefault(stage,dict(requests=0,system_hashes=Counter(),key_orders=Counter(),
            first_differing_user_key=Counter(),prefix_lengths=[],additional_message_requests=0))
        group['requests']+=1;group['system_hashes'][system_hash]+=1
        group['key_orders'][' / '.join(user)]+=1;group['additional_message_requests']+=int(len(messages)>2)
        encoded=json.dumps(messages,ensure_ascii=False,separators=(',',':')).encode()
        value_hashes={key:sha(json.dumps(value,ensure_ascii=False,separators=(',',':')).encode()) for key,value in user.items()}
        if stage in previous:
            old_system,old_hashes,old_bytes=previous[stage]
            group['prefix_lengths'].append(len(os.path.commonprefix([old_bytes,encoded])))
            if old_system!=system_hash: difference='system_changed_before_user'
            elif list(old_hashes)!=list(value_hashes): difference='user_key_order_changed'
            else: difference=next((key for key in value_hashes if old_hashes[key]!=value_hashes[key]),'no_user_value_changed')
            group['first_differing_user_key'][difference]+=1
        previous[stage]=(system_hash,value_hashes,encoded)
    for group in groups.values():
        lengths=group.pop('prefix_lengths')
        group['consecutive_comparisons']=len(lengths)
        group['consecutive_message_prefix_bytes_median']=statistics.median(lengths) if lengths else None
    return dict(stages=groups,provider_calls=0,
        method='Compare immediately previous same-stage request in persistent ledger order. Canonical message bytes, not wire token prefix.',
        limitations='Byte similarities do not identify provider cache TTL, routing, tokenization or eviction; no causal cache claim.',
        mutation='No Prompt, Schema, source order, evidence scope or generation parameter changed.')


def finalize_reviews(runtime,out,version='reviewed'):
    os.umask(0o077)
    runtime=Path(runtime).resolve();out=Path(out).resolve();blind=out/'blind'
    if Path(version).name!=version or version in ('.','..',''): raise ValueError('Invalid review version directory')
    first,packets,inputs=review_set(blind,'reviewer')
    second,cross_packets,cross_inputs=review_set(blind,'crosscheck',first)
    inputs.update(cross_inputs)
    expected_cross={t for t,r in first.items() if r['provisional_type']!='Unknown' or
                    r['incorrect_refusal'] is True or r['severe_error'] is True}
    if set(second)!=expected_cross: raise ValueError('All primary flagged cases must be cross-checked')
    for ticket,packet in cross_packets.items():
        original=packets[ticket]
        a=next(a for a in original['answers'] if a['ticket']==ticket)
        b=next(a for a in packet['answers'] if a['ticket']==ticket)
        if a!=b or any(packet[k]!=original[k] for k in ('question','official_reference','official_category','sources_file')):
            raise ValueError('Cross-check packet content differs from initial review')
    # Blind source files must match the original evaluator snapshot exactly.
    for sid in DEVELOPMENT:
        original=json.loads((runtime/'sources'/f'{sid}.json').read_text())
        projected=[{k:s[k] for k in ('source_id','speaker','session_time','text','position')} for s in original]
        saved=[json.loads(s) for s in (blind/'sources'/f'{sid}.jsonl').read_text().splitlines()]
        if projected!=saved: raise ValueError('Blind source snapshot changed')
    key_path=out/'sealed-review-key.json';key=json.loads(key_path.read_text())
    if len(key)!=len(first) or {k['ticket'] for k in key}!=set(first): raise ValueError('Sealed key coverage mismatch')
    if len({(k['run_id'],k['ordinal']) for k in key})!=len(key): raise ValueError('Duplicate Run item in sealed key')
    inputs[str(key_path)]=file_sha(key_path)
    integrity=json.loads((out/'input-integrity-before.json').read_text())
    if any(file_sha(p)!=h for p,h in integrity.items()): raise ValueError('Original inputs changed')
    report=json.loads((out/'summary.json').read_text());metas=json.loads((out/'run-identities.json').read_text())
    database=runtime/'memory.sqlite3';db_sha=integrity[str(database)]
    records=load_ledger(runtime/'observer/budget.sqlite3');wire=defaultdict(list)
    for r in records:
        if r.get('scope')=='development-query': wire[(r.get('run_id'),r.get('question_id'),r.get('strategy'))].append(r)
    destination=out/version;destination.mkdir(mode=0o700)
    reviews={};metrics_by_run={}
    for rid in RUNS:
        rows=[json.loads(s) for s in (out/rid/'item-metrics.jsonl').read_text().splitlines()]
        metrics_by_run[rid]={r['ordinal']:r for r in rows}
        report['runs'][rid]['all_items']=summarize_rows(rows)
        for dimension in ('conversation','category','strategy','memory_source_count'):
            values=defaultdict(list)
            for row in rows: values[row[dimension]].append(row)
            report['runs'][rid]['groups'][dimension]={k:summarize_rows(v) for k,v in sorted(values.items())}
    with readonly(database) as db, (destination/'reviewed-items.jsonl').open('x') as review_file:
        for k in key:
            ticket=k['ticket'];rid=k['run_id'];ordinal=k['ordinal']
            raw=db.execute('SELECT item_json FROM evaluation_run_items WHERE run_id=? AND ordinal=?',(rid,ordinal)).fetchone()[0]
            item=json.loads(raw);packet=packets[ticket]
            assigned_answer=next(a for a in packet['answers'] if a['ticket']==ticket)
            sample=metas[rid]['input']['samples'][item['sample_index']]
            if (neutral_answer(item)!={n:v for n,v in assigned_answer.items() if n!='ticket'} or
                    sample['question']!=packet['question'] or sample['category']!=packet['official_category'] or
                    sample['answer']!=packet['official_reference'] or
                    Path(packet['sources_file']).name!=item['sample_id']+'.jsonl'):
                raise ValueError('Anonymous answer differs from original Run item')
            if item['strategy']!=k['strategy']: raise ValueError('Sealed strategy mismatch')
            consensus=review_consensus(first[ticket],second.get(ticket))
            review=dict(ticket=ticket,case_id=f'{rid}:{ordinal}',run_id=rid,ordinal=ordinal,
                primary=first[ticket],crosscheck=second.get(ticket),consensus=consensus,
                semantic_review_kind='non_author_ai_research_review',human_review='not_evaluated')
            review_file.write(json.dumps(review,ensure_ascii=False)+'\n')
            if needs_review(first[ticket]) or (ticket in second and needs_review(second[ticket])):
                lineage=trace_lineage(database,db_sha,rid,item,raw,runtime,wire[(rid,item['question_id'],item['strategy'])])
                bid=metas[rid]['pins'][item['sample_id']]
                lineage['build_version'].update(status='available',key=dict(build_id=bid))
                for field in ('extracted_memory','memory_source_mapping'):
                    lineage[field].update(status='available',where=dict(build_id=bid))
                reviews[(rid,ordinal)]=dict(atlas_version='failure-atlas-v2',case_id=f'{rid}:{ordinal}',
                    run_id=rid,build_id=bid,question_id=item['question_id'],qa_index=item['qa_index'],
                    conversation=item['sample_id'],category=sample['category'],strategy=item['strategy'],
                    execution_status=item['status'],qa_score=at(item,'/result/qa/value'),
                    observations=observations(item),diagnosis=dict(type=consensus['supported_output_type'],
                        status='ai_crosschecked_output_failure' if consensus['supported_output_type']!='Unknown' else 'ai_reviewed_stage_unresolved',
                        upstream_root_cause='Unknown'),
                    lineage=lineage,metrics=metrics_by_run[rid][ordinal],ai_review=review,
                    run_artifact=item_ref(database,db_sha,rid,item,raw))
    counts={}
    for rid in RUNS:
        seen=set();added=0;count=0;types=Counter()
        with (destination/f'{rid}-failure-atlas.jsonl').open('x') as f:
            for line in (out/rid/'failure-atlas.jsonl').open():
                case=json.loads(line);ordinal=case['metrics']['ordinal'];seen.add(ordinal)
                case=reviews.get((rid,ordinal),case)
                f.write(json.dumps(case,ensure_ascii=False)+'\n');count+=1;types[case['diagnosis']['type']]+=1
            for (run,ordinal),case in reviews.items():
                if run==rid and ordinal not in seen:
                    f.write(json.dumps(case,ensure_ascii=False)+'\n');added+=1;count+=1;types[case['diagnosis']['type']]+=1
        counts[rid]=dict(cases=count,review_discovered_additions=added,
                        candidate_types=dict(types),notice='AI output classification is separate from upstream root cause.')
    subsets={}
    for rid in (BASELINE,REPAIR):
        tickets=[k['ticket'] for k in key if k['run_id']==rid]
        by_dimension={}
        for dimension in ('conversation','category','strategy'):
            values=defaultdict(list)
            for k in key:
                if k['run_id']==rid:
                    row=metrics_by_run[rid][k['ordinal']];values[row[dimension]].append(first[k['ticket']])
            by_dimension[dimension]={n:review_metrics(v) for n,v in sorted(values.items())}
        subsets[rid]=dict(primary=review_metrics([first[t] for t in tickets]),
            crosschecked_answers=sum(t in second for t in tickets),primary_groups=by_dimension,
            notice='Stratified QA subset or targeted repairs; no population estimate, not independent answers within a QA.')
    report.update(semantic_review_status='independent_ai_subset_completed',human_review_status='not_evaluated',
        ai_review=dict(primary_answers=len(first),crosschecked_answers=len(second),subsets=subsets,
            crosscheck_agreed_incorrect_refusals=sum(first[t]['incorrect_refusal'] is True and second[t]['incorrect_refusal'] is True for t in second),
            crosscheck_agreed_severe_errors=sum(first[t]['severe_error'] is True and second[t]['severe_error'] is True for t in second),
            crosscheck_disagreement_answers=sum(bool(review_consensus(first[t],second[t])['disagreements']) for t in second),
            crosscheck_scope='Flagged initial AI judgments; selective cross-check, not representative.',
            review_kind='non_author_ai_research_review',facts_are_calibrated_probabilities=False),
        reviewed_atlas=counts,review_inputs_sha256=inputs,
        top_10_confirmed_full_population_patterns=[],complete_semantic_metrics=None)
    write(destination/'summary.json',report)
    after={p:file_sha(p) for p in integrity}
    write(destination/'input-integrity.json',dict(before=integrity,after=after,unchanged=integrity==after))
    if after!=integrity: raise ValueError('Original inputs changed during review import')
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('command',choices=['prepare','audit','reviews','structure'])
    p.add_argument('--runtime',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--review-version',default='reviewed',help='New, exclusive review output subdirectory')
    a=p.parse_args()
    if a.command=='prepare': initialize(a.runtime,a.output)
    elif a.command=='audit': audit(a.runtime,a.output)
    elif a.command=='structure': write(a.output/'wire-structure.json',wire_structure(a.runtime))
    else: finalize_reviews(a.runtime,a.output,a.review_version)
    print(json.dumps(dict(status=a.command+'_completed',directory=str(a.output),provider_calls=0)))


if __name__=='__main__': main()
