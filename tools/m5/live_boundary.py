"""Prepare, execute, blind-review and score one explicitly budgeted diagnostic."""
import argparse
from decimal import Decimal
import hashlib
import io
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[2]
BASELINE = 'd3c4ae10fb73d70eabea42f5333e721168574190'
CANDIDATE = 'b3c9d0f4f4929de55df714523fff2edcd28f6548'
FREEZE = '3cab5d1b486290184e67906d61427f18803b415d82fe18f5f5f7190ae89664a6'
SELECTION = {'conv-43':(24,32,46,95,147,195), 'conv-44':(8,22,70,81,115,128)}
TARGETS = ('D5:11','D5:12','D8:14','D20:2','D24:3','D25:26')
POLICY = dict(max_requests=64,max_usd='15',model='deepseek-flash',
    input_usd_per_million='0.30',output_usd_per_million='1.20',
    max_input_bytes=640000,max_output_tokens=32768)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
    path.chmod(0o600)


def conversations_only():
    # Project only conversation fields in SQL. Gold values are not decoded in Python.
    raw = (ROOT/'data/raw/locomo/locomo10.json').read_text()
    with sqlite3.connect(':memory:') as db:
        return {r[0]:json.loads(r[1]) for r in db.execute(
            "SELECT json_extract(value,'$.sample_id'),json_extract(value,'$.conversation') FROM json_each(?)",(raw,))}


def settings(config):
    from locomo_memory.config import Settings
    return Settings.model_validate({**config,'model_retries':0,'model_max_tokens':32768,
        'resolution_input_budget':192000,'model_timeout_seconds':90,
        **{f'{stage}_thinking_effort':'disabled' for stage in ('extraction','relation','query_analysis','resolution','answer')}}).snapshot()


def runner_hashes():
    return {p.name:sha(p) for p in (Path(__file__),Path(__file__).with_name('live_boundary_worker.py'))}


def prepare(private, stage):
    from tools.m5.level_c import readonly
    if private.exists():
        raise ValueError('private_run_already_exists')
    if sha(stage/'generation-freeze.json')!=FREEZE:
        raise ValueError('unexpected_freeze')
    freeze = json.loads((stage/'generation-freeze.json').read_text())
    plan = json.loads((stage/'plan.json').read_text())
    if (sha(stage/'plan.json')!=freeze['plan_sha256']
        or sha(stage/'final-system-lock.json')!=plan['final_lock_sha256']
        or sha(stage/'inputs.json')!=plan['inputs_sha256']):
        raise ValueError('frozen_identity_changed')
    public = conversations_only()
    public_text = {(conv,t['dia_id']):t['text'] for conv,c in public.items()
        for key,turns in c.items() if key.startswith('session_') and isinstance(turns,list) for t in turns}
    selected = {f'{conv}:qa:{n}' for conv,nums in SELECTION.items() for n in nums}
    packets = {}
    for name,expected in sorted(freeze['item_hashes'].items()):
        # The deterministic selection is by original question ID, never its Gold or score.
        if not name.endswith('-dynamic.json'):
            continue
        item = json.loads((stage/name).read_text())
        if item['question_id'] not in selected:
            continue
        if sha(stage/name)!=expected:
            raise ValueError('selected_frozen_item_changed')
        trace = item['trace']
        with readonly(stage/(item['sample_id']+'.sqlite3')) as db:
            sources = [dict(r) for r in db.execute('SELECT * FROM source_turns WHERE dataset_id=? AND sample_id=? ORDER BY position',
                (trace['dataset_id'],item['sample_id']))]
        if any(public_text.get((item['sample_id'],s['dia_id']))!=s['text'] for s in sources):
            raise ValueError('source_text_not_public')
        packets[item['question_id']] = {**{k:trace[k] for k in ('question','sample_id','dataset_id','build_id',
            'initial','expanded','relations','projection_fingerprint')},'sources':sources,'config':settings(trace['config'])}
    if set(packets)!=selected:
        raise ValueError('selected_questions_incomplete')
    private.mkdir(parents=True,mode=0o700)
    (private/'jobs').mkdir(mode=0o700);(private/'results').mkdir(mode=0o700)
    snapshots = {}
    for arm,commit in [('baseline',BASELINE),('candidate',CANDIDATE)]:
        target = private/arm;target.mkdir(mode=0o700)
        data = subprocess.check_output(['git','archive',commit,'src/locomo_memory'],cwd=ROOT)
        with tarfile.open(fileobj=io.BytesIO(data)) as archive:
            archive.extractall(target,filter='data')
        snapshots[arm] = {str(p.relative_to(target)):sha(p) for p in sorted((target/'src/locomo_memory').glob('*.py'))}
    jobs = []
    # Alternate execution order to reduce a systematic arm/time ordering effect.
    for ordinal,qid in enumerate(sorted(packets)):
        for arm in (('baseline','candidate') if ordinal%2==0 else ('candidate','baseline')):
            packet = packets[qid]
            job = dict(job_id=f'q{ordinal:02d}-{arm}',kind='query',producer=arm,
                question_id=qid,packet=packet,settings=packet['config'])
            file = private/'jobs'/(job['job_id']+'.json');write(file,job);jobs.append(file.name)
    conv = public['conv-42']; sources = []
    for key,turns in conv.items():
        if not key.startswith('session_') or not isinstance(turns,list):continue
        for t in turns:
            sources.append(dict(source_id='public/conv-42/'+t['dia_id'],dataset_id='public',sample_id='conv-42',
                session_id=key,dia_id=t['dia_id'],speaker=t['speaker'],session_time=conv[key+'_date_time'],
                text=t['text'],position=len(sources)))
    config = settings(next(iter(packets.values()))['config'])
    for ordinal,dia in enumerate(TARGETS):
        target = next(s for s in sources if s['dia_id']==dia)
        for arm in (('baseline','candidate') if ordinal%2==0 else ('candidate','baseline')):
            window = arm=='candidate'
            context = [s for s in sources if s['source_id']==target['source_id'] or (window
                and s['session_id']==target['session_id'] and abs(s['position']-target['position'])<=1)]
            job = dict(job_id=f'e{ordinal:02d}-{arm}',kind='extract',producer=arm,sample_id='conv-42',
                target_ids=[target['source_id']],window=window,sources=context,settings=config)
            file=private/'jobs'/(job['job_id']+'.json');write(file,job);jobs.append(file.name)
    result = dict(version='bounded-live-boundary-v1',baseline_commit=BASELINE,candidate_commit=CANDIDATE,
        freeze_sha256=FREEZE,policy=POLICY,snapshots=snapshots,runner_hashes=runner_hashes(),
        jobs={name:sha(private/'jobs'/name) for name in jobs},order=jobs,
        public_source_sha256=sha(ROOT/'data/raw/locomo/locomo10.json'),
        public_protocol_sha256=sha(ROOT/'experiments/live-boundary-20261109/PROTOCOL.md'),
        user_budget='2026-11-09 explicit reply: 64 requests and USD15; no retries',human_reviewer='user; pending')
    write(private/'plan.json',result)
    write(private/'authorization.json',dict(approved=True,policy=POLICY,plan_sha256=sha(private/'plan.json'),
        source='Explicit user answer in current chat on 2026-11-09'))
    return dict(status='prepared',query_pairs=12,extraction_pairs=6,max_requests=64,max_usd='15')


def checked_plan(private):
    plan = json.loads((private/'plan.json').read_text())
    auth = json.loads((private/'authorization.json').read_text())
    if (auth!=dict(approved=True,policy=POLICY,plan_sha256=sha(private/'plan.json'),
            source='Explicit user answer in current chat on 2026-11-09')
        or plan['policy']!=POLICY or plan['runner_hashes']!=runner_hashes()):
        raise ValueError('plan_or_authorization_changed')
    for arm,files in plan['snapshots'].items():
        if any(sha(private/arm/name)!=expected for name,expected in files.items()):
            raise ValueError('producer_snapshot_changed')
    for name,expected in plan['jobs'].items():
        if sha(private/'jobs'/name)!=expected:raise ValueError('planned_job_changed')
    if sha(ROOT/'data/raw/locomo/locomo10.json')!=plan['public_source_sha256']:
        raise ValueError('public_sources_changed')
    return plan


def run_one(private,job):
    result = private/'results'/(job['job_id']+'.json')
    marker = result.with_suffix('.started.json')
    if result.exists():raise ValueError('job_already_executed')
    if marker.exists():raise ValueError('interrupted_job_requires_manual_audit_no_retry')
    write(marker,dict(job_id=job['job_id']))
    subprocess.run([sys.executable,str(Path(__file__).with_name('live_boundary_worker.py')),
        '--producer',str(private/job['producer']),'--job',str(private/'jobs'/(job['job_id']+'.json')),
        '--output',str(result),'--ledger',str(private/'physical-requests.sqlite3')],check=True,cwd=ROOT)
    value=json.loads(result.read_text())
    stop = any(c.get('http_status') in {401,402,403} or c.get('error_code')=='physical_request_budget_exhausted'
        for o in value['observations'] for c in o.get('metadata',{}).get('calls',[]))
    return stop


def execute(private):
    plan=checked_plan(private)
    if (private/'generation-freeze.json').exists() or (private/'execution-started.json').exists():
        raise ValueError('execution_already_started_no_automatic_resume')
    write(private/'execution-started.json',dict(plan_sha256=sha(private/'plan.json')))
    stopped=False
    for name in plan['order']:
        job=json.loads((private/'jobs'/name).read_text())
        if stopped:
            write(private/'results'/name,dict(job_id=job['job_id'],kind=job['kind'],outcome='not_executed',
                reason='prior_balance_auth_or_budget_stop',observations=[]))
        else:
            stopped=run_one(private,job)
    freeze=dict(status='generation_complete',plan_sha256=sha(private/'plan.json'),
        results={name:sha(private/'results'/name) for name in plan['order']})
    write(private/'generation-freeze.json',freeze)
    return dict(status='generation_complete',results=len(freeze['results']),stopped_early=stopped)


def frozen_results(private):
    plan=checked_plan(private); freeze=json.loads((private/'generation-freeze.json').read_text())
    if (freeze['plan_sha256']!=sha(private/'plan.json') or set(freeze['results'])!=set(plan['jobs'])
        or any(sha(private/'results'/n)!=h for n,h in freeze['results'].items())):
        raise ValueError('generation_not_frozen_or_changed')
    return plan,{n:json.loads((private/'results'/n).read_text()) for n in plan['order']}


REVIEW_INSTRUCTIONS = '''Independently audit the supplied original conversation evidence and blinded outputs X/Y.
Do not infer which variant is newer. No Gold/reference answer is supplied. Return one judgment for each
packet_id and each variant. Person ownership, actual facts vs wishes/plans, event identity, negation,
time precision and source entailment must be checked separately. Kind extract: audit every extracted
memory's entity and fact, especially liking another person's pets vs owning pets. An empty valid
extraction has uncertain support; do not count it as a correct ownership fact. Kind query: judge
answer and explanation against the shown original sources; IDs alone prove nothing. Missing facts
can only be judged within the shown union of delivered evidence, not the full conversation. A failed
or not executed output must be not_executed. Keep uncertain when context cannot decide. Quote exact
original words with source_id; never invent a quote. The original question's narrower calendar
constraints outrank any coarse interval. Do not treat a plan as accomplished or silence as a negative.'''


def review(private):
    plan,results=frozen_results(private)
    if (private/'review-freeze.json').exists() or (private/'review-started.json').exists():
        raise ValueError('review_already_started')
    packets=[]; keys={}
    groups={}
    for name in plan['order']:
        job=json.loads((private/'jobs'/name).read_text());pid=job['job_id'].split('-')[0]
        groups.setdefault(pid,{})[job['producer']]=(job,results[name])
    for pid,arms in sorted(groups.items()):
        # Deterministic blinding, recorded separately and not included in model payload.
        order=('candidate','baseline') if int(hashlib.sha256(pid.encode()).hexdigest(),16)%2 else ('baseline','candidate')
        keys[pid]=dict(zip(('X','Y'),order)); variants={}; sources={}
        for variant,arm in keys[pid].items():
            job,r=arms[arm]
            if job['kind']=='query':
                packet=job['packet']; ids={sid for m in r.get('effective_memories',[]) for sid in m['source_ids']}
                sources.update({s['source_id']:s for s in packet['sources'] if s['source_id'] in ids})
                variants[variant]=dict(outcome=r['outcome'],answer=r.get('answer'),
                    memories=r.get('effective_memories',[]),time=r.get('time'))
            else:
                sources.update({s['source_id']:s for s in job['sources']})
                variants[variant]=dict(outcome=r['outcome'],extraction=r.get('extraction'))
        packets.append(dict(packet_id=pid,kind=job['kind'],question=job.get('packet',{}).get('question'),
            target_ids=job.get('target_ids'),sources=list(sources.values()),variants=variants))
    write(private/'blind-key.json',keys)
    write(private/'review-packets.json',packets)
    write(private/'review-started.json',dict(generation_freeze_sha256=sha(private/'generation-freeze.json')))
    stopped=False; names=[]
    for i in range(4):
        job=dict(job_id=f'r{i:02d}',kind='review',producer='candidate',instructions=REVIEW_INSTRUCTIONS,
            packets=packets[i::4],settings=settings({}))
        file=private/'jobs'/(job['job_id']+'.json');write(file,job);names.append(file.name)
        if stopped:
            write(private/'results'/file.name,dict(job_id=job['job_id'],kind='review',outcome='not_executed',observations=[]))
        else:stopped=run_one(private,job)
    write(private/'review-freeze.json',dict(generation_freeze_sha256=sha(private/'generation-freeze.json'),
        jobs={n:sha(private/'jobs'/n) for n in names},results={n:sha(private/'results'/n) for n in names},
        packets_sha256=sha(private/'review-packets.json'),blind_key_sha256=sha(private/'blind-key.json')))
    return dict(status='ai_review_frozen',batches=4,human_review='pending')


def score(private,public):
    from locomo_memory.evaluation_metrics import qa_score,map_evidence,coverage,normalize
    from tools.m5.level_c import ledger_summary
    from tools.m5.offline import paired
    plan,results=frozen_results(private)
    data=json.loads((ROOT/'data/raw/locomo/locomo10.json').read_text()); reference={s['sample_id']:s['qa'] for s in data}
    rows=[]
    for ordinal,qid in enumerate(sorted(f'{c}:qa:{n}' for c,ns in SELECTION.items() for n in ns)):
        arms={};conv,index=qid.split(':qa:');gold=reference[conv][int(index)]
        for arm in ('baseline','candidate'):
            name=f'q{ordinal:02d}-{arm}.json';r=results[name];job=json.loads((private/'jobs'/name).read_text())
            if job['question_id']!=qid or gold['question']!=job['packet']['question']:
                raise ValueError('reference_identity_mismatch')
            success=r['outcome']=='succeeded'; answer=r.get('answer',{}).get('answer','')
            score=qa_score(answer,gold); value=score['value'] if success else 0
            mapping=map_evidence(gold.get('evidence',[]),job['packet']['sources'])
            delivered={sid for m in r.get('effective_memories',[]) for sid in m['source_ids']}
            arms[arm]=dict(outcome=r['outcome'],answer=r.get('answer'),score=value,
                em=float(normalize(answer)==normalize(str(gold.get('answer','')))) if success and gold['category']!=5 else None,
                delivered_source_recall=coverage(delivered,mapping) if success else 0,
                elapsed_seconds=r.get('elapsed_seconds'),error=r.get('error'))
        rows.append(dict(question_id=qid,question=gold['question'],category=gold['category'],
            reference_answer=gold.get('answer'),arms=arms))
    ordinary=[r for r in rows if r['category']!=5];diagnostic=[r for r in rows if r['category']==5]
    summary=dict(scope='12 exposed temporal questions; fixed retrieval; paired live regression only',
        questions=len(rows),ordinary=len(ordinary),adversarial=len(diagnostic),
        arms={arm:dict(succeeded=sum(r['arms'][arm]['outcome']=='succeeded' for r in rows),
            ordinary_f1=sum(r['arms'][arm]['score'] for r in ordinary)/len(ordinary),
            ordinary_em=sum(r['arms'][arm]['em'] or 0 for r in ordinary)/len(ordinary),
            adversarial_refusal=sum(r['arms'][arm]['score'] for r in diagnostic)/len(diagnostic) if diagnostic else None)
            for arm in ('baseline','candidate')},
        paired=paired([r['arms']['candidate']['score']-r['arms']['baseline']['score'] for r in ordinary]),
        budget=ledger_summary(private/'physical-requests.sqlite3'),model_calls_scope='generation plus AI review',
        human_review='pending_user',rows=rows)
    summary['paired']['scope']='exploratory bootstrap; 12 preselected exposed temporal questions; ordinary subset only'
    public.mkdir(parents=True,exist_ok=True)
    write(public/'results.json',summary);write(public/'plan.json',plan)
    write(public/'generation-freeze.json',json.loads((private/'generation-freeze.json').read_text()))
    # Validated application outputs and publicly matched source evidence only; never HTTP logs.
    write(public/'outputs.json',results)
    for name in ('review-packets.json','blind-key.json','review-freeze.json'):
        if (private/name).exists():write(public/name,json.loads((private/name).read_text()))
    review_results={p.name:json.loads(p.read_text()) for p in sorted((private/'results').glob('r*.json'))
        if '.progress.' not in p.name and '.started.' not in p.name}
    write(public/'ai-review.json',dict(reviewer='deepseek-flash; identity blinded; AI only',
        independent_human_truth=False,results=review_results))
    return {k:v for k,v in summary.items() if k not in {'rows'}}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('prepare','execute','review','score'))
    parser.add_argument('--private',type=Path,required=True)
    parser.add_argument('--stage',type=Path)
    parser.add_argument('--public',type=Path)
    args=parser.parse_args();private=args.private.resolve()
    if args.action=='prepare':result=prepare(private,args.stage.resolve())
    elif args.action=='execute':result=execute(private)
    elif args.action=='review':result=review(private)
    else:result=score(private,args.public.resolve())
    print(json.dumps(result,ensure_ascii=False,indent=2),flush=True)


if __name__=='__main__':main()
