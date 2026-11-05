"""Prepare deterministic blinded business packets; no API or provider access."""
import json
import random
import sqlite3
from run import OUT, read, durable_json


def main():
    report=json.loads((OUT/'execution/report.json').read_text())
    cases={c['id']:c for c in read('cases.json')}
    refs={c['case_id']:c for c in read('reference-accepted.json')}
    history={c['id']:c for c in read('historical-packets.json')}
    hrefs={c['case_id']:c for c in read('historical-reference-accepted.json')}
    rows=[]
    for task in report['items']:
        path=OUT/'execution'/(task['id']+'.json')
        result=json.loads(path.read_text())['result'] if path.exists() else {}
        if task['kind']=='reader':
            for stage in ('initial','revision'):
                checkpoint=OUT/'execution'/(task['id']+'-'+stage+'-checkpoint.json')
                partial=json.loads(checkpoint.read_text())['result'] if checkpoint.exists() else {}
                r={**partial,**result};case=cases[task['case']]
                rows.append(dict(key=dict(task_id=task['id'],case=task['case'],repeat=task['repeat'],stage=stage,kind='reader',cohort=case['cohort']),packet=dict(case_id=task['case'],question=case['payload']['question'],time=case['payload']['time'],sources=case['payload']['sources'],reference=refs[task['case']],response=r.get(stage),evidence_audit=r.get(stage+'_audit',[]))))
        else:
            case=history[task['case']]
            rows.append(dict(key=dict(task_id=task['id'],case=task['case'],budget=task['budget'],kind='history',has_resolution=bool(case['resolution_input'])),packet=dict(case_id=task['case'],question=case['answer_input']['question'],time=case['answer_input']['time'],sources=result.get('answer_input',{}).get('sources',[]),reference=hrefs[task['case']],response=result.get('answer'),evidence_audit=[])))
    random.Random('integration-blind-v1-separate-from-schedule').shuffle(rows)
    packets=[];mapping=[]
    for i,row in enumerate(rows):
        bid=f'blind-{i:03d}';packets.append(dict(blind_id=bid,**row['packet']));mapping.append(dict(blind_id=bid,**row['key']))
    # References and source texts shared per case in compact bundles; each output
    # retains its own actual delivered source scope (history arms can differ).
    groups={'development-and-history':[],'boundaries-and-known-four':[]}
    for packet,key in zip(packets,mapping):
        group='development-and-history' if key['kind']=='history' or key['cohort']=='existing-development-exposure-unknown' else 'boundaries-and-known-four'
        groups[group].append(packet)
    for group,packets in groups.items():
        compact={}
        for p in packets:
            cid=p['case_id'];entry=compact.setdefault(cid,dict(case_id=cid,question=p['question'],time=p['time'],reference=p['reference'],outputs=[]))
            entry['outputs'].append({k:p[k] for k in ('blind_id','response','sources','evidence_audit')})
        durable_json(OUT/('blind-'+group+'.json'),list(compact.values()))
    durable_json(OUT/'blind-key-author-only.json',mapping)
    durable_json(OUT/'blind-protocol.json',dict(expected_packets=132,packet_count=len(rows),paid_review_http=0,rules='Do not open blind key, outputs outside assigned packets, ledger, costs, arms or technical outcomes. Evaluate every explicit answer/claim/explanation against frozen reference and actual delivered sources. Every required fact gets covered/missing/incorrect/ambiguous/not_evaluable; required_for_substantive_coverage=false is optional. Empty necessary-abstention status can pass where accepted reference permits. Null output is not_evaluable and stays denominator. Validate actual citation excerpt and source entailment, time/report date, modality, negation, actor/event identity. Reference full sources cannot repair missing delivery. Never equate binding/schema with semantic support. Do not infer world negatives from absence. Answer and explanation both count. For each blind_id record semantic_verdict(pass/fail/uncertain/not_evaluable), fact_states list of fact_id/state, citation_support(pass/fail/uncertain/not_applicable), unsupported_claims list, severe_errors list, wrong_refusal boolean, reason. Non-author AI, not human ground truth. Disclose exposure to code/references, no arm key read. Full denominators by case/repeat/arm, not success-only.'))
    assert len(rows)==132
    print(json.dumps(dict(blind_packets=len(rows),bundles={k:len(v) for k,v in groups.items()},live_calls=0)))

if __name__=='__main__':main()
