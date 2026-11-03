"""Offline scenario estimate using every retained smoke physical attempt."""
import argparse
import json
import math
from pathlib import Path
import sqlite3

from locomo_memory.experiment import write_json
from tools.research_v2.cache_analysis import aggregate,rows


def estimate(directory,previous):
    records=rows(directory)
    build_directory=directory
    identity_path=directory/'execution-identity.json'
    if identity_path.exists():
        identity=json.loads(identity_path.read_text())
        if identity.get('build_cost_source'):
            build_directory=Path(identity['build_cost_source'])
    plan=json.loads((directory/'plan-development.json').read_text())
    outcome=json.loads((directory/'execution-outcome.json').read_text())
    state=json.loads((directory/'experiment.json').read_text())
    prior=json.loads(previous.read_text())
    source={sid:json.loads((directory/'sources'/f'{sid}.json').read_text()) for sid in plan['course_split']['dev']}
    turns={sid:len(value) for sid,value in source.items()}
    sizes={sid:len(json.dumps(value,ensure_ascii=False).encode()) for sid,value in source.items()}
    qa={sid:sum(q['sample_id']==sid for q in plan['questions']) for sid in source}
    build_records=records if build_directory==directory else rows(build_directory)
    build_rows=[r for r in build_records if r.get('scope')=='conv-26-build']
    run_id=outcome.get('run_id')
    run=json.loads((directory/'runs'/run_id/'run.json').read_text()) if run_id else None
    build_id=state.get('builds',{}).get('conv-26')
    build=json.loads((directory/'builds'/build_id/'build.json').read_text()) if build_id else {}
    build_complete=build.get('status')=='complete' and all(r['status']=='settled' for r in build_rows)
    def miss_cost(group):
        if any(any(r['usage'].get(k) is None for k in ('prompt_tokens','completion_tokens')) for r in group): return None
        return sum((r['usage']['prompt_tokens']*2+r['usage']['completion_tokens']*8)/1e6 for r in group)
    actual_build=aggregate(build_rows)
    result={'status':('measured_smoke_extrapolation_not_full_results' if run and run['progress']['succeeded']==20 else 'blocked_smoke_incomplete_query_measurement') if build_complete else 'blocked_build_incomplete_no_query_measurement','currency':'CNY',
        'development_qa':757,'development_combinations':3028,'development_conversations':list(source),
        'measured_build_id':build_id,'measured_run_id':run_id,'measured_build_complete':build_complete,
        'build_cost_source':str(build_directory.resolve()),'query_cost_source':str(directory.resolve()),
        'observed_conv26_build':actual_build,'observed_conv26_build_no_cache_peak_cny':miss_cost(build_rows),
        'embedding_external_api_cny':0,'embedding_local_compute_cny':None,
        'builds':{},'queries':{},'gross_four_builds_peak_with_observed_cache_cny':None,
        'gross_four_builds_peak_no_cache_cny':None,'full_queries_peak_with_observed_cache_cny':None,
        'full_queries_peak_no_cache_cny':None,'gross_full_peak_with_observed_cache_cny':None,
        'gross_full_peak_no_cache_cny':None,'incremental_peak_with_observed_cache_cny':None,
        'budget_proposal':None,
        'prior_scenario_if_measurement_incomplete':{k:prior[k] for k in ('build_peak_cny_scenario','query_peak_cny_scenario','total_peak_cny_scenario')},
        'limitations':[
            'Five questions from conv-26 are a service smoke, not a representative random sample or semantic acceptance set.',
            'All saved physical attempts enter cost; no best-of retry selection.',
            'Build scales by source-turn count only; future memory/relation counts and output lengths are unknown.',
            'Full Text input uses source serialization byte ratios, not provider tokenizer counts; fixed schema overhead is also scaled conservatively.',
            'RAG cost assumes conv-26 candidate/evidence/output distribution; other conversations may differ.',
            'Observed-cache extrapolation is a conditional scenario; no-cache peak is a second scenario, neither is a guaranteed invoice.',
            'Known cost is calculated from actual provider tokens and public tariffs, not obtained from an account invoice.',
            'Unknown calls keep reservations; the estimate does not impute missing usage as real measurement.',
            'Local CPU/electricity/storage cost, semantic review, provider/model changes and manual resumes are not priced.',
            'A proposed hard budget may stop before completion. It does not authorize spending and is not a completeness guarantee.',
            'Reuse of the smoke conv-26 Build is a separate decision for the future approved full run; smoke QA scores are never spliced into that run.'
        ]}
    # An incomplete relation phase cannot supply the cost of a publishable Build.
    # Retain only an explicitly arithmetic partial-phase scenario, not a new baseline estimate.
    if build_rows and not build_complete:
        relation=[r for r in build_rows if r.get('stage')=='Relation']
        extraction=[r for r in build_rows if r.get('stage')=='Extraction']
        observed_tasks=len({r.get('task_id') for r in relation if r.get('task_id')})
        with sqlite3.connect((directory/'memory.sqlite3').resolve().as_uri()+'?mode=ro',uri=True) as db:
            total_tasks=db.execute('SELECT COUNT(*) FROM relation_tasks WHERE build_id=?',(build_id,)).fetchone()[0]
        if observed_tasks:
            ratio=total_tasks/observed_tasks
            conv26=aggregate(extraction)['known_peak_upper_cny']+aggregate(relation)['known_peak_upper_cny']*ratio
            full_build=conv26*sum(turns.values())/turns['conv-26']
            result['partial_phase_arithmetic_scenario']={
                'status':'NOT_A_COMPLETED_BUILD_COST_ESTIMATE',
                'relation_tasks_with_physical_calls':observed_tasks,'planned_relation_tasks':total_tasks,
                'formula':'complete extraction cost + observed relation cost * planned tasks / observed tasks; then source-turn scaling',
                'conv26_peak_cny_with_observed_cache':conv26,
                'four_builds_peak_cny_with_observed_cache':full_build,
                'query_peak_cny_historical_proxy':prior['query_peak_cny_scenario'],
                'combined_partial_build_and_historical_query_peak_cny':full_build+prior['query_peak_cny_scenario'],
                'limitations':[
                    'Observed tasks are the first tasks in deterministic order, not a representative sample.',
                    'Later candidate histories may be larger; failed/truncated outputs cannot demonstrate the cost of valid complete outputs.',
                    'No real Query Analysis/Resolution/Answer requests were made. Query cost is inherited historical proxy, not remeasured.',
                    'Current frozen Build cannot publish without a separately authorized repair. No payable full experiment is ready.'
                ]}
        result['budget_proposal']={'status':'DEFER_UNTIL_ISSUE20_PASSES',
            'conditional_planning_max_cny':800,'conditional_max_physical_http_requests':20000,
            'conditional_max_seconds':259200,'max_concurrency':1,
            'rationale':'Planning placeholder only: round up twice the prior peak gross scenario (374.80 CNY) plus reservation margin; 20,000 exceeds the prior 18,168 maximum internal Query attempts but is not a guarantee for Build. 72 hours is an operator stop ceiling, not a measured completion time.',
            'mandatory_gates':['separately reviewed opt-in repair','new independent smoke approval and pass',
                               'remeasure Query and all five stages','recompute and obtain explicit full-run approval'],
            'safe_to_approve_now':False,'paid_authorization':None}
    if build_complete:
        for sid in source:
            ratio=turns[sid]/turns['conv-26']
            result['builds'][sid]={'turns':turns[sid],'qa':qa[sid],
                'peak_cny_observed_cache':actual_build['known_peak_upper_cny']*ratio,
                'peak_cny_no_cache':miss_cost(build_rows)*ratio,
                'physical_requests_scenario':len(build_rows)*ratio,
                'physical_seconds_scenario':actual_build['elapsed_seconds_known']*ratio,
                'scaling':'source turns'}
        result['gross_four_builds_peak_with_observed_cache_cny']=sum(v['peak_cny_observed_cache'] for v in result['builds'].values())
        result['gross_four_builds_peak_no_cache_cny']=sum(v['peak_cny_no_cache'] for v in result['builds'].values())
    if run and all(r['status']=='settled' for r in records):
        for strategy in plan['strategies']:
            group=[r for r in records if r.get('strategy')==strategy]
            n=sum(i['strategy']==strategy for i in run['items'])
            assert n==5
            succeeded=sum(i['strategy']==strategy and i['status']=='succeeded' for i in run['items'])
            totals=aggregate(group)
            if succeeded != n:
                result['queries'][strategy]={'measured_logical_items':n,'succeeded':succeeded,
                    'measured_physical':len(group),'measured_usage':totals,
                    'status':'INCOMPLETE_DO_NOT_PRICE_AS_COMPLETE_QUERY',
                    'full_peak_cny_observed_cache':None,'full_peak_cny_no_cache':None,
                    'reason':'Failed before all query stages completed; cheaper failures are not cost improvement.'}
                continue
            prompt=totals['usage']['prompt_tokens']['reported']
            hit=totals['usage']['prompt_cache_hit_tokens']['reported']
            miss=totals['usage']['prompt_cache_miss_tokens']['reported']
            completion=totals['usage']['completion_tokens']['reported']
            by_conv={}
            for sid in source:
                count=qa[sid]/n
                ratio=sizes[sid]/sizes['conv-26'] if strategy=='full_text' else 1
                cached=(hit*.04+miss*2)/1e6*count*ratio+completion*8/1e6*count
                no_cache=prompt*2/1e6*count*ratio+completion*8/1e6*count
                by_conv[sid]={'peak_cny_observed_cache':cached,'peak_cny_no_cache':no_cache,
                              'full_text_byte_ratio':ratio,'qa':qa[sid]}
            result['queries'][strategy]={'measured_logical_items':n,'measured_physical':len(group),
                'measured_usage':totals,'by_conversation':by_conv,
                'full_peak_cny_observed_cache':sum(v['peak_cny_observed_cache'] for v in by_conv.values()),
                'full_peak_cny_no_cache':sum(v['peak_cny_no_cache'] for v in by_conv.values()),
                'full_physical_requests_scenario':len(group)/n*757,
                'full_physical_seconds_scenario':totals['elapsed_seconds_known']/n*757}
        if all(v['full_peak_cny_observed_cache'] is not None for v in result['queries'].values()):
            result['full_queries_peak_with_observed_cache_cny']=sum(v['full_peak_cny_observed_cache'] for v in result['queries'].values())
            result['full_queries_peak_no_cache_cny']=sum(v['full_peak_cny_no_cache'] for v in result['queries'].values())
        else:
            result['budget_proposal']={'status':'DEFER_UNTIL_DYNAMIC_SMOKE_PASSES', 'safe_to_approve_now':False,
                'paid_authorization':None,'max_cny':None,'reason':'Resolution and dynamic Answer unmeasured; cannot price failed early exits as complete queries.',
                'mandatory_gates':['offline review of complete_resolution_input_budget_exceeded',
                                   'separate explicit authorization for any new paid repair validation',
                                   'remeasure all stages before a full-run budget approval']}
    if build_complete and result['full_queries_peak_with_observed_cache_cny'] is not None:
        gross=result['gross_four_builds_peak_with_observed_cache_cny']+result['full_queries_peak_with_observed_cache_cny']
        no_cache=result['gross_four_builds_peak_no_cache_cny']+result['full_queries_peak_no_cache_cny']
        physical=sum(v['physical_requests_scenario'] for v in result['builds'].values())+sum(v['full_physical_requests_scenario'] for v in result['queries'].values())
        seconds=sum(v['physical_seconds_scenario'] for v in result['builds'].values())+sum(v['full_physical_seconds_scenario'] for v in result['queries'].values())
        result.update(gross_full_peak_with_observed_cache_cny=gross,gross_full_peak_no_cache_cny=no_cache,
            incremental_peak_with_observed_cache_cny=gross-actual_build['known_peak_upper_cny'],
            sensitivity_observed_cache_half_to_double_cny=[gross*.5,gross*2],
            full_physical_requests_scenario=physical,full_physical_seconds_scenario=seconds,
            budget_proposal={'status':'NOT_AUTHORIZED','max_cny':int(math.ceil((no_cache*2+2.359296)/10)*10),
                'max_physical_http_requests':int(math.ceil(physical*1.5/100)*100),
                'max_seconds':int(math.ceil((seconds*2+3600)/3600)*3600),'max_concurrency':1,
                'rationale':'Two times no-cache peak scenario plus one maximum reservation; 1.5 times measured-attempt requests; twice observed physical processing duration plus one hour, rounded up. Local compute and future retry/output variation may still exceed the time scenario.'})
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--directory',type=Path,required=True)
    p.add_argument('--previous',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    write_json(a.output,estimate(a.directory,a.previous))
