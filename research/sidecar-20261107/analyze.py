"""Score frozen predictions against blind session-AI references; no inference."""
import argparse,collections,hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent

def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--private',type=Path,required=True);ap.add_argument('--run-id',default='run-v2');a=ap.parse_args()
    preds=json.loads((a.private/a.run_id/'predictions.json').read_text());refs={};identity=[];packets={}
    for sid in ('conv-26','conv-30'):
        packet=json.loads((a.private/(sid+'-reference-packet.json')).read_text());labels=json.loads((a.private/(sid+'-reference-labels.json')).read_text())
        assert len(labels['units'])==34 and {r['unit_id'] for r in labels['units']}=={r['unit_id'] for r in packet['units']}
        sources={s['source_id'] for u in packet['units'] for s in u['sources']}
        for r in labels['units']:
            assert r['unit_id'] not in refs;assert set(r['evidence_source_ids'])<=sources;assert r.get('rationale');refs[r['unit_id']]=r
        identity.append({'sample_id':sid,'annotator':labels['annotator'],'reference_kind':labels['reference_kind'],'labels_sha256':digest(a.private/(sid+'-reference-labels.json')),'units':len(labels['units'])})
    assert len(refs)==68 and set(preds)<=set(refs)
    missing_predictions=sorted(set(refs)-set(preds))
    for uid in missing_predictions:
        kind=refs[uid]['kind'];fields={'claim':['time_status','completion','attendance'],'pair':['event_link'],'query':['evidence_status']}[kind]
        preds[uid]={'kind':kind,'sidecar':{k:'failure' for k in fields},'control':{k:'failure' for k in fields}}
    dimensions=collections.defaultdict(lambda:collections.defaultdict(collections.Counter));units=[]
    for uid,p in preds.items():
        r=refs[uid];kind=p['kind'];fields={'claim':['time_status','completion','attendance'],'pair':['event_link'],'query':['evidence_status']}[kind]
        row={'unit_id':uid,'kind':kind,'fields':[]};informative={'sidecar':False,'control':False}
        for field in fields:
            truth=r[field];dim=kind+'.'+field;known_truth=truth not in ('unknown','failure')
            for arm in ('control','sidecar'):
                observed=p[arm][field];c=dimensions[dim][arm];c['denominator']+=1;c['reference_'+truth]+=1;c['predicted_'+observed]+=1
                if observed=='failure':grade='failure'
                elif observed=='unknown':grade='abstain_on_informative_reference' if known_truth else 'both_unknown'
                elif not known_truth:grade='definite_on_unknown_reference_unverified'
                else:
                    correct=observed==truth
                    if correct and field=='time_status':correct=p[arm]['start']==r['start'] and p[arm]['end']==r['end']
                    if correct and field=='evidence_status' and truth=='sufficient':correct=(p[arm].get('answer') or '').casefold()==(r.get('answer') or '').casefold()
                    grade='informative_correct' if correct else 'definite_incorrect'
                c[grade]+=1;informative[arm]|=grade=='informative_correct';row['fields'].append({'field':field,'arm':arm,'grade':grade})
        row['control_informative_correct']=informative['control'];row['sidecar_informative_correct']=informative['sidecar'];row['comparison']='improved' if informative['sidecar'] and not informative['control'] else 'degraded' if informative['control'] and not informative['sidecar'] else 'unchanged'
        # Further distinguish a new unsupported assertion from an abstaining control.
        row['new_definite_incorrect']=any(x['arm']=='sidecar' and x['grade']=='definite_incorrect' for x in row['fields']) and not any(x['arm']=='control' and x['grade']=='definite_incorrect' for x in row['fields'])
        units.append(row)
    serial={d:{arm:dict(c) for arm,c in arms.items()} for d,arms in dimensions.items()}
    summary={'protocol_sha256':digest(HERE/'PROTOCOL.md'),'reference_judges':identity,'reference_coverage':'68/68; one independent session-AI judge per unit, not human/teacher labels','units':68,'missing_predictions_counted_as_failure':len(missing_predictions),'dimensions':serial,'informative_correct_units':{arm:sum(u[arm+'_informative_correct'] for u in units) for arm in ('control','sidecar')},'informative_unit_coverage':{arm:sum(u[arm+'_informative_correct'] for u in units)/68 for arm in ('control','sidecar')},'unit_comparison':dict(collections.Counter(u['comparison'] for u in units)),'new_definite_incorrect_units':sum(u['new_definite_incorrect'] for u in units),'source_support_context':dict(collections.Counter(r['source_support'] for r in refs.values() if r['kind']=='claim')),'H1_passed':sum(u['sidecar_informative_correct'] for u in units)/68>=.1 and not any(u['new_definite_incorrect'] for u in units),'positive_event_link_precision':None,'positive_event_link_precision_note':'undefined: no positive event links; zero asserted errors is not high accuracy','limitations':['All data exposed development/regression, not unseen test.','One AI reference per unit; no agreement estimate, human or teacher truth.','One sufficient birth-year reference uses explicit arithmetic assumptions; it is a reference-dependent regression finding, not validated birth-year truth.','Unknown-reference definite outputs are unverified, not automatically counted as false.','No QA quality/cost claim: both study arms are diagnostic or supplied fields only.']}
    dump(a.private/a.run_id/'graded-units.json',units);dump(HERE/(a.run_id+'-analysis.json'),summary);print(json.dumps(summary,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
