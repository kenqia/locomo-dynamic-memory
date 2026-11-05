"""Strict paired accounting of the entire frozen denominator; no model requests."""
from collections import defaultdict
import json
import sqlite3
import sys
from run import OUT, read, durable_json, sha, verify


def preserved_result(task_id):
    path=OUT/'execution'/(task_id+'.json')
    if path.exists():
        return json.loads(path.read_text())['result']
    result={}
    for stage in ('initial','revision'):
        checkpoint=OUT/'execution'/(task_id+'-'+stage+'-checkpoint.json')
        if checkpoint.exists():result.update(json.loads(checkpoint.read_text())['result'])
    return result


def pair_changes(initial, revised):
    lost=sorted(set(initial['covered_fact_ids'])-set(revised['covered_fact_ids']))
    gained=sorted(set(revised['covered_fact_ids'])-set(initial['covered_fact_ids']))
    before={json.dumps(e,sort_keys=True) for e in initial['severe_error_details']}
    after={json.dumps(e,sort_keys=True) for e in revised['severe_error_details']}
    introduced=sorted(after-before)
    return dict(lost_fact_ids=lost,gained_fact_ids=gained,
                fact_coverage_delta=len(gained)-len(lost),
                new_severe=len(introduced),new_severe_error_descriptions=introduced,
                new_wrong_refusal=revised['wrong_refusal'] and (not initial['wrong_refusal'] or bool(lost)))


def main():
    plan=verify()
    execution_report=json.loads((OUT/'execution/report.json').read_text())
    key=read('blind-key-author-only.json')
    expected={(t['id'],stage,t['case']) for t in plan['schedule'] for stage in (('initial','revision') if t['kind']=='reader' else ('answer',))}
    actual={(k['task_id'],k.get('stage','answer'),k['case']) for k in key}
    assert len(actual)==len(key) and actual==expected,'Paired scoring identity differs from frozen schedule'
    scheduled={t['id']:t for t in plan['schedule']}
    for k in key:
        t=scheduled[k['task_id']]
        assert t['kind']==k['kind'] and t.get('repeat')==k.get('repeat') and t.get('budget')==k.get('budget')
    judgments=[]
    for name in ('review-development-and-history.json','review-boundaries-and-known-four.json'):
        review=read(name)
        assert review['non_author_ai'] and not review['human_review'] and not review['arm_key_read']
        assert all(sha(OUT/name)==h for name,h in review['input_sha256'].items()),'Blind review input identity changed'
        judgments.extend(review['judgments'])
    by_id={j['blind_id']:j for j in judgments}
    assert len(by_id)==len(judgments)==len(key)==132
    adjudicated=[]
    for group in ('development-and-history','boundaries-and-known-four'):
        second=read('adjudication-'+group+'.json')
        assert second['non_author_ai'] and not second['human_review'] and not second['arm_key_read']
        declared=second['input_sha256']
        declared=declared if isinstance(declared,dict) else {'adjudication-input-'+group+'.json':declared}
        assert all(sha(OUT/name)==h for name,h in declared.items()),'Adjudication input identity changed'
        for j in second['judgments']:
            first=by_id[j['blind_id']]
            assert first['semantic_verdict'] in {'uncertain','fail'}
            # One pre-unblinding cross-adjudication. A conflicting confident
            # judgement stays uncertain; it cannot silently erase a clear fail.
            if first['semantic_verdict']=='fail' and j['semantic_verdict']=='pass':
                j={**first,'semantic_verdict':'uncertain','reason':'Conflicting confident independent verdicts; no author override.'}
            by_id[j['blind_id']]=j;adjudicated.append(j['blind_id'])
    packets={}
    for name in ('blind-development-and-history.json','blind-boundaries-and-known-four.json'):
        for case in read(name):
            for output in case['outputs']:packets[output['blind_id']]=(case,output)
    assert set(packets)==set(by_id),'Review packet population differs'
    refs={r['case_id']:r for r in read('reference-accepted.json')}
    hrefs={r['case_id']:r for r in read('historical-reference-accepted.json')}
    for k in key:
        case,output=packets[k['blind_id']]
        result=preserved_result(k['task_id'])
        assert case['case_id']==k['case']
        assert case['reference']==(refs if k['kind']=='reader' else hrefs)[k['case']]
        if k['kind']=='reader':
            original=next(c for c in read('cases.json') if c['id']==k['case'])
            assert output['response']==result.get(k['stage']) and output['sources']==original['payload']['sources']
            assert output['evidence_audit']==result.get(k['stage']+'_audit',[])
        else:
            assert output['response']==result.get('answer') and output['sources']==result.get('answer_input',{}).get('sources',[])
    groups=defaultdict(list);rows=[]
    for k in key:
        j=by_id[k['blind_id']];case,output=packets[k['blind_id']]
        assert j['semantic_verdict'] in {'pass','fail','uncertain','not_evaluable'}
        facts={f['fact_id'] for f in case['reference']['facts'] if f.get('required_for_substantive_coverage',True)}
        states=j['fact_states'];assert len({f['fact_id'] for f in states})==len(states)
        fs={f['fact_id']:f['state'] for f in states}
        assert facts<=fs.keys(),(k['blind_id'],facts-fs.keys())
        assert all(s in {'covered','missing','incorrect','ambiguous','not_evaluable'} for s in fs.values())
        if output['response'] is None:assert j['semantic_verdict']=='not_evaluable'
        covered=sum(fs[f]=='covered' for f in facts)
        complete=(j['semantic_verdict']=='pass' and j['citation_support'] in {'pass','not_applicable'} and covered==len(facts) and not j['severe_errors'] and not j['unsupported_claims'])
        group=k['cohort']+':'+k['stage'] if k['kind']=='reader' else ('history-resolve' if k['has_resolution'] else 'history-answer-negative-control')+':'+str(k['budget'])
        row=dict(**k,complete_correct=complete,verdict=j['semantic_verdict'],facts_required=len(facts),facts_covered=covered,covered_fact_ids=sorted(f for f in facts if fs[f]=='covered'),fact_states=fs,severe_error_details=j['severe_errors'],severe_errors=len(j['severe_errors']),wrong_refusal=j['wrong_refusal'],citation_support=j['citation_support'])
        groups[group].append(row);rows.append(row)
    stats={}
    for group,rr in groups.items():
        total=len(rr);den=sum(r['facts_required'] for r in rr);num=sum(r['facts_covered'] for r in rr)
        stats[group]=dict(planned_outputs=total,complete_correct=sum(r['complete_correct'] for r in rr),complete_correct_rate=sum(r['complete_correct'] for r in rr)/total,required_fact_coverage=dict(covered=num,denominator=den,rate=num/den if den else None),severe_errors=sum(r['severe_errors'] for r in rr),wrong_refusals=sum(r['wrong_refusal'] for r in rr),not_evaluable=sum(r['verdict']=='not_evaluable' for r in rr),uncertain=sum(r['verdict']=='uncertain' for r in rr))
    with sqlite3.connect((OUT/'execution/ledger.sqlite3').as_uri()+'?mode=ro&immutable=1',uri=True) as db:
        calls=[dict(task=t,state=s,cost_micro_cny=c,reserved_micro_cny=r,usage=json.loads(u) if u else {}) for t,s,c,r,u in db.execute('SELECT task,state,cost,reserved,usage_json FROM calls ORDER BY id')]
    all_usage_known=all(c['state']=='settled' for c in calls)
    stagecost={c['task']:c for c in calls}
    assert len(stagecost)==len(calls),'Duplicate physical stages'
    tokens={};paired=[]
    reader_by_pair=defaultdict(dict)
    for row in rows:
        if row['kind']=='reader':reader_by_pair[(row['task_id'],row['case'],row['repeat'],row['cohort'])][row['stage']]=row
    for cohort in {r['cohort'] for r in rows if r['kind']=='reader'}:
        pairs=[(key,r) for key,r in reader_by_pair.items() if key[3]==cohort]
        initial=sum(stagecost.get(k[0]+':initial',{}).get('usage',{}).get('total_tokens',0) for k,r in pairs)
        revised=sum(stagecost.get(k[0]+':revision',{}).get('usage',{}).get('total_tokens',0) for k,r in pairs)
        tokens[cohort]=dict(single_logical_tokens=initial,revised_logical_tokens=initial+revised,actual_shared_tokens=initial+revised,logical_pipeline_ratio=(initial+revised)/initial if initial else None)
        for k,r in pairs:
            a,b=r['initial'],r['revision'];paired.append(dict(task_id=k[0],case=k[1],repeat=k[2],cohort=cohort,initial_complete=a['complete_correct'],revision_complete=b['complete_correct'],lost_complete=a['complete_correct'] and not b['complete_correct'],gained_complete=not a['complete_correct'] and b['complete_correct'],**pair_changes(a,b)))
    cohort='existing-development-exposure-unknown';a=stats[cohort+':initial'];b=stats[cohort+':revision']
    gain=100*(b['complete_correct_rate']-a['complete_correct_rate'])
    gate=dict(real_development_gain_at_least_10pp=gain>=10,observed_development_gain_pp=gain,real_fact_coverage_not_lower=b['required_fact_coverage']['rate']>=a['required_fact_coverage']['rate'],all_paired_facts_no_loss=not any(r['lost_fact_ids'] for r in paired),no_new_severe=not any(r['new_severe'] for r in paired),no_new_wrong_refusal=not any(r['new_wrong_refusal'] for r in paired),synthetic_no_regression=not any(r['lost_complete'] or r['lost_fact_ids'] for r in paired if r['cohort']=='synthetic-boundary'),known_four_no_regression=not any(r['lost_complete'] or r['lost_fact_ids'] for r in paired if r['cohort']=='known-four-regression'),logical_pipeline_ratio_at_most_2_2=all(t['logical_pipeline_ratio'] is not None and t['logical_pipeline_ratio']<=2.2 for t in tokens.values()),all_planned_outputs_reviewed=len(judgments)==132,all_planned_attempts_completed=execution_report['stop_reason'] is None and len(execution_report['items'])==len(plan['schedule']) and all(t['outcome']=='completed' for t in execution_report['items']),no_unresolved_semantics=not any(r['verdict']=='uncertain' for r in rows),all_physical_usage_known=all(c['state']=='settled' for c in calls))
    gate['local_acceptance_passed']=all(v for k,v in gate.items() if k!='observed_development_gain_pp')
    result=dict(plan_id=read('frozen-plan.json')['id'],full_planned_outputs=132,reviewed_outputs=len(judgments),cross_adjudicated_outputs=len(adjudicated),statistics=stats,paired=paired,logical_and_shared_tokens=tokens,physical_cost=dict(http=len(calls),prompt_tokens=sum(c['usage'].get('prompt_tokens',0) for c in calls),completion_tokens=sum(c['usage'].get('completion_tokens',0) for c in calls),total_tokens=sum(c['usage'].get('total_tokens',0) for c in calls),estimated_peak_upper_cny=sum(c['cost_micro_cny'] or 0 for c in calls)/1000000 if all_usage_known else None,known_usage_estimated_upper_cny=sum(c['cost_micro_cny'] or 0 for c in calls)/1000000,unsettled_reserved_cny=sum(c['reserved_micro_cny'] for c in calls if c['state']!='settled')/1000000,unknown_usage_calls=sum(c['state']!='settled' for c in calls),actual_account_bill='not_read_or_claimed'),gates=gate,rows=rows,scoring_identity=dict(frozen_plan_sha256=sha(OUT/'frozen-plan.json'),scorer_sha256=sha(__file__),blind_key_sha256=sha(OUT/'blind-key-author-only.json'),ledger_sha256=sha(OUT/'execution/ledger.sqlite3'),execution_audit_sha256=sha(OUT/'execution-audit-final.json') if (OUT/'execution-audit-final.json').exists() else None,matched_frozen_schedule_and_business_outputs=True,review_and_adjudication_input_hashes_verified=True),review_authority='Two non-author AI reviewers with disclosed code/reference exposure, blinded arm/stage/order; no human acceptance.',interpretation='Correlated development observations, not 12 new independent questions or overall/hidden-set accuracy. No automatic default promotion, no Top7 parent resolution. Physical spend counts shared initial once; logical refinement cost includes the same initial and revision.')
    durable_json(OUT/(sys.argv[1] if len(sys.argv)>1 else 'semantic-and-cost-results-final.json'),result)
    print(json.dumps(dict(physical_cost=result['physical_cost'],gates=gate),ensure_ascii=False,indent=2))

if __name__=='__main__':main()
