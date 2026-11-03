"""New, bounded acceptance only. Exclusive outputs; no recovery or replacement."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import random
import signal
import subprocess
import sys
from types import SimpleNamespace

from pydantic import ValidationError
from locomo_memory.config import Settings
from locomo_memory.evidence_catalog import EvidenceCatalog
from locomo_memory.implementation_identity import implementation_sha256
from locomo_memory.layered_evidence import ContractViolation
from locomo_memory.model import DeepSeekModel, ModelFailure, request_messages, request_token_estimate
from locomo_memory.queries import QueryService
from locomo_memory.query_schemas import EffectiveResolution
from locomo_memory.resolution_delivery import complete_resolution_input
from locomo_memory.revised_source_reader import REFINE
from locomo_memory.source_answer_reader import reading_payload
from locomo_memory.source_reader import SupportedAnswer, bind_supported_answer
from meter import Meter, StopStudy, durable_json, INPUT_CAP, OUTPUT_CAP, RESERVE_MICRO_CNY

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'experiments/integration-acceptance-20261101'


def read(name):
    return json.loads((OUT / name).read_text())


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def fingerprint(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False).encode()).hexdigest()


def tasks():
    schedule = [dict(kind='reader',case=c['id'],repeat=r) for c in read('cases.json') for r in (1,2)]
    schedule += [dict(kind='history',case=c['id'],budget=b) for c in read('historical-packets.json') for b in (12000,24000)]
    random.Random('integration-acceptance-20261101-v1').shuffle(schedule)
    for i,t in enumerate(schedule):t['id']=f'task-{i:03d}'
    return schedule


def reader_input(case):
    p=deepcopy(case['payload']); sources=p['sources']
    context=dict(status=p['status'],memories={m['memory_id']:m for m in p.get('memories',[])},raw_sources={s['source_id']:s for s in sources},input_budget=24000,max_attempts=1)
    catalog=EvidenceCatalog(sources,p.get('memories',[]),raw_source_ids=context['raw_sources'])
    return catalog,context,reading_payload(catalog,p)


def freeze():
    refs=read('reference-accepted.json'); review=read('reference-review.json')
    assert len(refs)==28 and review['status']=='accepted_with_documented_corrections' and not review['unresolved_disputes']
    assert all(sha(OUT/name)==h for name,h in review['input_sha256'].items())
    assert read('historical-reference-accepted.json') and read('historical-reference-review.json')
    rows=[]
    for case in read('cases.json'):
        _,_,wire=reader_input(case)
        n=request_token_estimate('source_statements',wire,SupportedAnswer)
        if n>24000:raise ValueError('initial_input_exceeds_frozen_budget')
        rows.append(dict(case=case['id'],initial_messages_sha256=fingerprint(request_messages('source_statements',wire,SupportedAnswer)),initial_input_proxy=n,revision='Exact REFINE + exact observed initial JSON; hash and actual input estimate persisted before sending; over24000 fails without HTTP'))
    paths=[*sorted((ROOT/'tools/acceptance').glob('*.py'))]
    paths += [ROOT/'tests/test_acceptance_meter.py']
    paths += [OUT/n for n in ('cases.json','reference-candidates.json','reference-accepted.json','reference-review.json','scoring-protocol.json','source-provenance.json','historical-packets.json','historical-reference-inputs.json','historical-reference-accepted.json','historical-reference-review.json','standards-review.json','spec-code-review.json','pricing-cny-official.txt','thinking-official.txt')]
    plan=dict(id='INT-ACCEPT-20261101-24000-v1',status='frozen_authorized',user_authority=['输入的默认预算可以再提高一倍，然后开启验收和真实实验','人民币20元（新付费总额上限）'],prior_budget_reused=False,old_experiments_resumed=False,maximum_http=152,money_cap_micro_cny=20000000,per_http_reserve_micro_cny=RESERVE_MICRO_CNY,provider_input_token_reserve=INPUT_CAP,provider_output_token_cap=OUTPUT_CAP,maximum_provider_total_tokens=152*(INPUT_CAP+OUTPUT_CAP),deadline_utc=(datetime.now(timezone.utc)+timedelta(hours=2)).isoformat(),maximum_wall_seconds=7200,model='deepseek-flash',allowed_returned_models=['deepseek-flash'],input_budget=24000,retries=0,maximum_inflight=1,resolution_thinking_effort='low',answer_thinking_effort='disabled',temperature_when_disabled=0,pricing_micro_cny_per_token=dict(input_cache_miss=2,output=8),cost='Conservative peak-price estimate from official CNY pricing; actual account bill/discount not available. Full-context reservation before each HTTP; known usage settles, unknown stops and retains reservation.',paid_review_http=0,reference_independence='non-author AI, not human ground truth',implementation_sha256=implementation_sha256(),git_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),files={str(p.relative_to(ROOT)):sha(p) for p in paths},schedule=tasks(),reader_preflight=rows,scope='Historical generation-stage replay 10x2 resolution budgets max40 HTTP, not full application query. Only four packets contain resolution, six are identical-setting answer-interface negative controls. Resolution budget is the sole 12k/24k arm difference; answer evidence budget stays original and all answer requests have the same 24k total-input guard. Both arms use common rc2 model settings (8192 output, resolution low, answer disabled, temperature0, retries0), not historical provider settings. Source-reader 28 cases x2 repeats x2 stages max112 HTTP; curated evidence, existing development exposure unknown; experiment02/03 remain unexecuted drafts.')
    durable_json(OUT/'frozen-plan.json',plan)
    return plan


def verify():
    plan=read('frozen-plan.json')
    if implementation_sha256()!=plan['implementation_sha256']:raise ValueError('implementation_changed')
    if any(sha(ROOT/p)!=h for p,h in plan['files'].items()):raise ValueError('frozen_file_changed')
    if tasks()!=plan['schedule']:raise ValueError('schedule_changed')
    for item in read('source-provenance.json'):
        if sha(item['path'])!=item['database_sha256']:raise ValueError('source_database_changed')
    for item in read('historical-packets.json'):
        if sha(item['original_path'])!=item['original_sha256']:raise ValueError('historical_trace_changed')
    return plan


def generate(meter,model,task,stage,operation,payload,schema,context):
    meter.task=task['id']+':'+stage
    meter.event(dict(status='stage_prepared',stage=stage,input_messages_sha256=fingerprint(request_messages(operation,payload,schema)),input_proxy=request_token_estimate(operation,payload,schema)))
    return model.generate(operation,payload,schema,context=context,on_call=meter.event)


def reader_task(meter,model,task,case):
    catalog,context,wire=reader_input(case)
    result=dict(initial=None,revision=None,metadata=[],cohort=case['cohort'],initial_outcome='not_attempted',revision_outcome='not_attempted')
    for stage in ('initial','revision'):
        try:
            payload=deepcopy(wire)
            if stage=='revision':payload.update(candidate_answer=result['initial_wire'],task_instructions=REFINE)
            gen=generate(meter,model,task,stage,'source_statements',payload,SupportedAnswer,deepcopy(context))
            result['metadata'].append(gen.metadata)
            result[stage+'_wire']=gen.value.model_dump(mode='json')
            answer,audit=bind_supported_answer(catalog,gen.value,context,source_only=True)
            result[stage]=answer.model_dump(mode='json');result[stage+'_audit']=audit
            result[stage+'_outcome']='technical_pass'
            durable_json(meter.directory/(task['id']+'-'+stage+'-checkpoint.json'),dict(task=task,result=deepcopy(result)))
        except (ModelFailure,ValidationError,ContractViolation) as error:
            result[stage+'_outcome']='technical_fail'
            result['error']=dict(stage=stage,code=getattr(error,'code','binding_invalid'))
            if isinstance(error,ModelFailure):result['metadata'].append(error.metadata)
            if stage=='initial':result['revision_outcome']='failed_dependency_initial'
            break
    return result


class TaggedModel:
    def __init__(self,meter,model,task):self.meter,self.model,self.task=meter,model,task
    def generate(self,operation,payload,schema,*,context):
        # Historical answer path retains its own evidence budget and strict schema;
        # this study also gives every model request a finite total input budget.
        context={**context,'input_budget':24000,'max_attempts':1}
        return generate(self.meter,self.model,self.task,'answer',operation,payload,schema,context)


def history_task(meter,model,task,case):
    settings=Settings.model_validate({**case['config'],'resolution_input_budget':task['budget'],'model_retries':0})
    original=case['answer_input']; payload=case['resolution_input']
    result=dict(answer=None,outcome='not_attempted',metadata=[],historical_answer_not_current_score=True)
    try:
        if payload:
            context,audit=complete_resolution_input(payload,settings);result['resolution_budget']=audit
            if not audit['within_budget']:
                result.update(outcome='input_budget_rejected',error='complete_resolution_input_budget_exceeded');return result
            context['max_attempts']=1
            gen=generate(meter,model,task,'resolve','resolve',payload,EffectiveResolution,context)
            result['metadata'].append(gen.metadata);result['resolution']=gen.value.model_dump(mode='json')
            selected=[m for m in payload['memories'] if m['memory_id'] in gen.value.effective_memory_ids]
            status=gen.value.status;sources={s['source_id']:s for s in payload['sources']}
        else:
            selected=original['memories'];status=original['status'];sources={s['source_id']:s for s in original['sources']}
        if original['time'].get('beyond_cutoff'):status='insufficient'
        audit={};service=SimpleNamespace(settings=settings,model=TaggedModel(meter,model,task))
        answer,delivered,budget=QueryService.generate_answer(service,original['question'],original['time'],selected,sources,status,audit=audit,record_input=True)
        result.update(answer=answer,outcome='technical_pass',answer_input=audit.get('answer_input'),evidence_budget=budget)
        result['metadata'].append(budget['model_metadata'])
    except (ModelFailure,ValidationError) as error:
        result.update(outcome='technical_fail',error=getattr(error,'code','binding_invalid'))
        if isinstance(error,ModelFailure):result['metadata'].append(error.metadata)
    return result


def execute():
    plan=verify()
    # Output directory is created before reading credentials in DeepSeekModel.
    meter=Meter(OUT/'execution',plan)
    model=DeepSeekModel(Settings(model_retries=0,model_timeout_seconds=90,model_max_tokens=OUTPUT_CAP),transport=meter)
    cases={c['id']:c for c in read('cases.json')};history={c['id']:c for c in read('historical-packets.json')}
    items=[dict(**task,outcome='not_attempted') for task in plan['schedule']]
    stop=None
    def deadline_signal(signum, frame):
        raise StopStudy('absolute_deadline')
    previous_handler=signal.signal(signal.SIGALRM,deadline_signal)
    remaining=(datetime.fromisoformat(plan['deadline_utc'])-datetime.now(timezone.utc)).total_seconds()
    signal.setitimer(signal.ITIMER_REAL,max(0.001,min(remaining,plan['maximum_wall_seconds'])))
    try:
        for item in items:
            meter.check()
            try:
                result=reader_task(meter,model,item,cases[item['case']]) if item['kind']=='reader' else history_task(meter,model,item,history[item['case']])
            except StopStudy as error:
                item['outcome']='global_stop';stop=str(error)
                durable_json(meter.directory/(item['id']+'-stop.json'),dict(task=item,stop_reason=stop))
                break
            durable_json(meter.directory/(item['id']+'.json'),dict(task={**item,'outcome':'completed'},result=result))
            item['outcome']='completed'
            meter.event(dict(status='result_saved',task=item['id']))
            print(json.dumps(dict(task=item['id'],kind=item['kind'],**meter.summary())),flush=True)
    except StopStudy as error:
        stop=str(error)
    except Exception:
        stop='persistence_or_unexpected_failure_no_recovery'
    finally:
        signal.setitimer(signal.ITIMER_REAL,0)
        signal.signal(signal.SIGALRM,previous_handler)
        report=dict(plan_id=plan['id'],stop_reason=stop,items=items,**meter.summary(),semantic_acceptance='pending_independent_blind_review',finished_utc=datetime.now(timezone.utc).isoformat())
        durable_json(meter.directory/'report.json',report);meter.finish()
    return report


if __name__=='__main__':
    command=sys.argv[1] if len(sys.argv)>1 else 'verify'
    if command not in {'freeze','verify','execute'}:raise SystemExit('invalid_command')
    value={'freeze':freeze,'verify':verify,'execute':execute}[command]()
    print(json.dumps({k:v for k,v in value.items() if k not in {'items','schedule','files','reader_preflight'}},ensure_ascii=False,indent=2))
