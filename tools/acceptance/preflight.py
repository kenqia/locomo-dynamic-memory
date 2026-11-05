"""Full task wiring using MockTransport, synthetic output and no account credential."""
from copy import deepcopy
import json
import sys
from datetime import datetime,timedelta,timezone
from pathlib import Path
import tempfile
import httpx

import run as study
from meter import Meter
from locomo_memory.config import Settings
from locomo_memory.model import DeepSeekModel


def provider(request):
    body=json.loads(request.content)
    payload=json.loads(body['messages'][1]['content'])
    if 'turns' in payload:
        value=dict(status=payload['status'],claims=[] if payload['status']=='insufficient' else [dict(text='Synthetic mock statement, no semantic score.',evidence_refs=[payload['evidence_refs'][0]])])
    elif payload.get('operation')=='resolve':
        value=dict(status='insufficient',effective_memory_ids=[],decisions=[dict(memory_id=m['memory_id'],selected=False,reason='Synthetic mock only') for m in payload['memories']],supplemental_relations=[],explanation='Mock contract test')
    else:
        value=dict(status='insufficient',answer='Synthetic mock: insufficient evidence.',explanation='Mock contract test only.',citations=[])
    return httpx.Response(200,json=dict(model='deepseek-flash',usage=dict(prompt_tokens=100,completion_tokens=20,total_tokens=120),choices=[dict(finish_reason='stop',message=dict(content=json.dumps(value)))]))


def main():
    draft='--draft' in sys.argv
    plan=dict(schedule=study.tasks(),money_cap_micro_cny=20000000,maximum_http=152,maximum_wall_seconds=7200,deadline_utc=(datetime.now(timezone.utc)+timedelta(hours=2)).isoformat(),allowed_returned_models=['deepseek-flash']) if draft else study.verify()
    with tempfile.TemporaryDirectory(prefix='locomo-acceptance-preflight-') as tmp:
        meter=Meter(Path(tmp)/'mock',plan,delegate=httpx.MockTransport(provider))
        model=DeepSeekModel(Settings(model_retries=0),api_key='synthetic-not-a-real-key',transport=meter)
        cases={c['id']:c for c in study.read('cases.json')};history={c['id']:c for c in study.read('historical-packets.json')}
        rows=[]
        for task in plan['schedule']:
            r=study.reader_task(meter,model,task,cases[task['case']]) if task['kind']=='reader' else study.history_task(meter,model,task,history[task['case']])
            if task['kind']=='reader':
                assert r['initial_outcome']=='technical_pass' and r['revision_outcome']=='technical_pass',r
            else:
                assert r['outcome'] in ('technical_pass','input_budget_rejected'),r
            rows.append(dict(task=task,outcomes=[r.get('initial_outcome'),r.get('revision_outcome')] if task['kind']=='reader' else r['outcome']))
        result=dict(mock_tasks=len(rows),**meter.summary(),real_http_calls=0,semantic_score=False,items=rows)
        meter.finish()
    study.durable_json(study.OUT/('draft-mock-preflight.json' if draft else 'full-mock-preflight.json'),result)
    print(json.dumps({k:v for k,v in result.items() if k!='items'}))

if __name__=='__main__':main()
