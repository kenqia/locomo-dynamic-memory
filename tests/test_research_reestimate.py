"""An incomplete real-service stage must never become a completed baseline price."""
import json
import sqlite3

from tools.research_v2.observer import Ledger
from tools.research_v2.reestimate import estimate


def test_partial_build_keeps_full_cost_unknown_and_budget_unapproved(tmp_path):
    directory=tmp_path/'run'
    ledger=Ledger(directory/'observer')
    ledger.arm({'test':True})
    # Recorded synthetic usage covers every attempt, including an invalid output.
    with ledger.db() as db:
        for n,stage in enumerate(['Extraction','Relation']):
            record={'scope':'conv-26-build','stage':stage,'task_id':'T' if n else None,
                    'usage':dict(prompt_tokens=100,completion_tokens=10,total_tokens=110,
                                 prompt_cache_hit_tokens=0,prompt_cache_miss_tokens=100),
                    'semantic_status':'invalid_output','attempt':1}
            db.execute('INSERT INTO requests VALUES (?,?,?,?,?)',(str(n),'settled',2_162_688_000,280000,json.dumps(record)))
    ledger.close()
    conversations=['conv-26','conv-30','conv-41','conv-42']
    (directory/'sources').mkdir()
    for sid in conversations:
        (directory/'sources'/f'{sid}.json').write_text(json.dumps([{'text':'synthetic'}]))
    (directory/'plan-development.json').write_text(json.dumps({'course_split':{'dev':conversations},
        'questions':[{'sample_id':sid} for sid in conversations],
        'strategies':['full_text','vector','hybrid_no_resolution','dynamic']}))
    (directory/'execution-outcome.json').write_text(json.dumps({'run_id':None,'status':'stopped'}))
    (directory/'experiment.json').write_text(json.dumps({'builds':{'conv-26':'B'}}))
    (directory/'builds/B').mkdir(parents=True)
    (directory/'builds/B/build.json').write_text(json.dumps({'status':'relations_failed'}))
    with sqlite3.connect(directory/'memory.sqlite3') as db:
        db.execute('CREATE TABLE relation_tasks(build_id TEXT)')
        db.executemany('INSERT INTO relation_tasks VALUES (?)',[('B',),('B',)])
    previous=tmp_path/'prior.json'
    previous.write_text(json.dumps({'build_peak_cny_scenario':90,'query_peak_cny_scenario':284,'total_peak_cny_scenario':374}))
    report=estimate(directory,previous)
    assert report['status']=='blocked_build_incomplete_no_query_measurement'
    assert report['observed_conv26_build']['requests']==2
    assert report['gross_four_builds_peak_with_observed_cache_cny'] is None
    assert report['full_queries_peak_with_observed_cache_cny'] is None
    assert report['gross_full_peak_with_observed_cache_cny'] is None
    assert report['queries']=={} and report['measured_run_id'] is None
    assert report['budget_proposal']['safe_to_approve_now'] is False
    assert report['budget_proposal']['paid_authorization'] is None
    partial=report['partial_phase_arithmetic_scenario']
    assert partial['status']=='NOT_A_COMPLETED_BUILD_COST_ESTIMATE'
    assert partial['relation_tasks_with_physical_calls']==1
    assert partial['planned_relation_tasks']==2


def test_complete_build_with_failed_dynamic_keeps_total_query_cost_unknown(tmp_path):
    directory=tmp_path/'run'
    ledger=Ledger(directory/'observer')
    ledger.arm({'test':True})
    conversations=['conv-26','conv-30','conv-41','conv-42']
    strategies=['full_text','vector','hybrid_no_resolution','dynamic']
    with ledger.db() as db:
        for n,strategy in enumerate([None,*strategies]):
            record={'scope':'conv-26-build' if strategy is None else 'smoke',
                    'stage':'Extraction' if strategy is None else 'Answer',
                    'strategy':strategy,'usage':dict(prompt_tokens=100,completion_tokens=10,total_tokens=110,
                        prompt_cache_hit_tokens=0,prompt_cache_miss_tokens=100),'semantic_status':'succeeded','attempt':1}
            db.execute('INSERT INTO requests VALUES (?,?,?,?,?)',(str(n),'settled',2359296000,280000,json.dumps(record)))
    ledger.close()
    (directory/'sources').mkdir()
    for sid in conversations:
        (directory/'sources'/f'{sid}.json').write_text(json.dumps([{'text':'synthetic'}]))
    (directory/'plan-development.json').write_text(json.dumps({'course_split':{'dev':conversations},
        'questions':[{'sample_id':sid} for sid in conversations],'strategies':strategies}))
    (directory/'execution-outcome.json').write_text(json.dumps({'run_id':'R','status':'completed_with_errors'}))
    (directory/'experiment.json').write_text(json.dumps({'builds':{'conv-26':'B'}}))
    (directory/'builds/B').mkdir(parents=True)
    (directory/'builds/B/build.json').write_text(json.dumps({'status':'complete'}))
    (directory/'runs/R').mkdir(parents=True)
    (directory/'runs/R/run.json').write_text(json.dumps({'status':'completed_with_errors',
        'progress':{'succeeded':15},'items':[{'strategy':s,'status':'failed' if s=='dynamic' else 'succeeded'} for s in strategies for _ in range(5)]}))
    previous=tmp_path/'prior.json'
    previous.write_text(json.dumps({'build_peak_cny_scenario':90,'query_peak_cny_scenario':284,'total_peak_cny_scenario':374}))
    result=estimate(directory,previous)
    assert result['measured_build_complete'] is True
    assert result['gross_four_builds_peak_with_observed_cache_cny']>0
    assert result['queries']['full_text']['full_peak_cny_observed_cache']>0
    assert result['queries']['dynamic']['full_peak_cny_observed_cache'] is None
    assert result['full_queries_peak_with_observed_cache_cny'] is None
    assert result['gross_full_peak_with_observed_cache_cny'] is None
    assert result['budget_proposal']['safe_to_approve_now'] is False
    # A query-only retry must price its reused Build from the original ledger.
    query_dir=tmp_path/'query-only'
    query_dir.mkdir()
    import shutil
    for name in ('sources','builds','runs'):
        shutil.copytree(directory/name,query_dir/name)
    for name in ('plan-development.json','execution-outcome.json','experiment.json'):
        shutil.copyfile(directory/name,query_dir/name)
    (query_dir/'execution-identity.json').write_text(json.dumps({'build_cost_source':str(directory)}))
    run=json.loads((query_dir/'runs/R/run.json').read_text());run['status']='completed';run['progress']['succeeded']=20
    for item in run['items']:item['status']='succeeded'
    (query_dir/'runs/R/run.json').write_text(json.dumps(run))
    qledger=Ledger(query_dir/'observer');qledger.arm({})
    with qledger.db() as db:
        for n,strategy in enumerate(strategies):
            record={'scope':'smoke','stage':'Answer','strategy':strategy,
                    'elapsed_seconds':1,'usage':dict(prompt_tokens=100,completion_tokens=10,total_tokens=110,
                    prompt_cache_hit_tokens=0,prompt_cache_miss_tokens=100),'attempt':1}
            db.execute('INSERT INTO requests VALUES (?,?,?,?,?)',(str(n),'settled',2359296000,280000,json.dumps(record)))
    qledger.close()
    completed=estimate(query_dir,previous)
    assert completed['observed_conv26_build']['requests']==1
    assert completed['observed_conv26_build']['known_peak_upper_cny']==0.00028
    assert completed['gross_full_peak_with_observed_cache_cny']>0
    assert completed['full_queries_peak_with_observed_cache_cny']>0
    assert completed['budget_proposal']['status']=='NOT_AUTHORIZED'
    assert completed['budget_proposal']['max_seconds']>0
