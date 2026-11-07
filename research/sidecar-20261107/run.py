"""One frozen, zero-provider study; private raw output, public aggregates only."""
import argparse, collections, hashlib, json, os, platform, resource, signal, socket, sqlite3, subprocess, time
from pathlib import Path
from tools.research_v2.sidecar_core import RULE_VERSION
from tools.research_v2.sidecar_io import input_from_export
from tools.research_v2.sidecar_research import baseline_fields, research_view

HERE=Path(__file__).resolve().parent

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,x): p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
class StudyAbort(BaseException):
    """A study stop is not a recoverable diagnostic failure."""

ATTEMPTS = {'network': 0, 'sqlite': 0}
def forbidden_network(*a,**k):
    ATTEMPTS['network'] += 1
    raise StudyAbort('Forbidden network attempt')
def forbidden_sqlite(*a,**k):
    ATTEMPTS['sqlite'] += 1
    raise StudyAbort('Forbidden SQLite attempt')
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--private',type=Path,required=True);ap.add_argument('--run-id',choices=('run-v1','run-v2'),default='run-v2');ap.add_argument('--freeze',default='freeze-v2.json');a=ap.parse_args()
    freeze=json.loads((HERE/a.freeze).read_text());plan=json.loads((HERE/'frozen-input-plan.json').read_text())
    for path,digest in freeze['files'].items(): assert sha(HERE.parents[1]/path)==digest,path
    out=a.private/a.run_id;out.mkdir(exist_ok=False) # never overwrite or pick a better run
    socket.socket.connect=forbidden_network;socket.create_connection=forbidden_network;sqlite3.connect=forbidden_sqlite
    signal.signal(signal.SIGALRM,lambda *args: (_ for _ in ()).throw(StudyAbort('Bounded study wall limit')))
    rows=[];predictions={};primary=[]
    for item in plan['builds']:
        sid=item['sample_id'];path=a.private/item['file'];before=sha(path);assert before==item['sha256']
        packet=json.loads((a.private/(sid+'-reference-packet.json')).read_text());assert sha(a.private/(sid+'-reference-packet.json'))==item['reference_packet_sha256']
        start=time.perf_counter();cpu=time.process_time()
        snap=input_from_export(json.loads(path.read_bytes()),origin='source_snapshot')
        parse={'wall_seconds':time.perf_counter()-start,'cpu_seconds':time.process_time()-cpu}
        assert snap.provenance.build_fingerprint==item['build_fingerprint'] and snap.provenance.build_id==item['build_id']
        original={'kind':'REAL_FROZEN_BUILD_IDENTITY_ONLY_NOT_QA','build_id':item['build_id'],'dataset_id':snap.provenance.dataset_id,'sample_id':sid,'build_fingerprint':item['build_fingerprint']}
        original_bytes=json.dumps(original,sort_keys=True).encode();off=research_view(original,snap,enabled=False)
        cpu=time.process_time();start=time.perf_counter();control=baseline_fields(snap);baseline_time={'wall_seconds':time.perf_counter()-start,'cpu_seconds':time.process_time()-cpu}
        cpu=time.process_time();start=time.perf_counter();signal.alarm(120)
        on=research_view(original,snap,enabled=True,max_event_pairs=50000);signal.alarm(0)
        timing={'wall_seconds':time.perf_counter()-start,'cpu_seconds':time.process_time()-cpu}
        rollback=research_view(original,snap,enabled=False)
        unchanged=all(v.response is original for v in (off,on,rollback)) and original_bytes==json.dumps(original,sort_keys=True).encode() and before==sha(path)
        assert unchanged
        if on.status!='diagnosed':
            rows.append({'sample_id':sid,'status':'failure','error_code':on.error_code,'claims_planned':len(snap.claims),'pairs_planned':len(snap.claims)*(len(snap.claims)-1)//2,'source_unchanged':unchanged});continue
        diag=on.diagnostic;claims={c.memory_id:c for c in diag.claims};pairs={frozenset((c.left_memory_id,c.right_memory_id)):c for c in diag.record.event_links}
        raw={'diagnostic':diag.model_dump(mode='json'),'control':control};dump(out/(sid+'-raw.json'),raw)
        for unit in packet['units']:
            uid=unit['unit_id'];kind=unit['kind']
            if kind=='claim':
                c=claims[unit['memory']['memory_id']];predictions[uid]={'kind':kind,'sidecar':{'time_status':c.event_time.status,'start':str(c.event_time.start) if c.event_time.start else None,'end':str(c.event_time.end) if c.event_time.end else None,'completion':c.completed,'attendance':c.attended},'control':{'time_status':'unknown','start':None,'end':None,'completion':'unknown','attendance':'unknown'}}
            elif kind=='pair':
                ids=frozenset(m['memory_id'] for m in unit['memories']);predictions[uid]={'kind':kind,'sidecar':{'event_link':pairs[ids].decision},'control':{'event_link':'unknown'}}
            else:
                data=snap.model_dump(mode='json');data.update(question=unit['question'],as_of=None)
                from tools.research_v2.sidecar_schema import SidecarInput
                q=research_view(original,SidecarInput.model_validate(data),enabled=True,max_event_pairs=0)
                pred=q.diagnostic.query.model_dump(mode='json') if q.status=='diagnosed' else {'evidence_status':'failure','answer':None}
                predictions[uid]={'kind':kind,'sidecar':pred,'control':{'evidence_status':'unknown','answer':None}}
        rows.append({'sample_id':sid,'status':'success','build_id':item['build_id'],'input_sha256':before,'input_bytes':path.stat().st_size,'claims_planned':len(snap.claims),'claims_succeeded':len(diag.claims),'claims_failed':0,'sources':len(snap.sources),'pairs_planned':len(snap.claims)*(len(snap.claims)-1)//2,'pairs_evaluated':len(diag.record.event_links),'pairs_truncated':diag.links_truncated,'times':dict(collections.Counter(c.event_time.status for c in diag.claims)),'completion':dict(collections.Counter(c.completed for c in diag.claims)),'attendance':dict(collections.Counter(c.attended for c in diag.claims)),'links':dict(collections.Counter(c.decision for c in diag.record.event_links)),'warnings':dict(collections.Counter(w for c in diag.claims for w in c.warnings)),'validation_adapter':parse,'control_timing':baseline_time,'sidecar_timing':timing,'raw_output_bytes':(out/(sid+'-raw.json')).stat().st_size,'source_unchanged':unchanged,'off_on_off':[off.status,on.status,rollback.status],'peak_rss_kib_process_cumulative':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss})
    dump(out/'predictions.json',predictions)
    report={'protocol_sha256':sha(HERE/'PROTOCOL.md'),'freeze_sha256':sha(HERE/a.freeze),'implementation_commit':freeze['implementation_commit'],'rule_version':RULE_VERSION,'python':platform.python_version(),'platform':platform.platform(),'external_provider_requests':0,'forbidden_network_attempts':ATTEMPTS['network'],'sqlite_connections':0,'forbidden_sqlite_attempts':ATTEMPTS['sqlite'],'sampling_scope':'exposed development/regression; no unseen test claim','builds':rows,'reference_units_planned':68,'reference_predictions':len(predictions),'private_prediction_sha256':sha(out/'predictions.json')}
    dump(HERE/(a.run_id+'-summary.json'),report);print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
