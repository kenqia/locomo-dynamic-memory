"""Freeze an exploratory screening design; this module has no live executor."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import subprocess

from .postbaseline import BASELINE, DEVELOPMENT, file_sha, load_ledger, readonly, write

SEED='phase3-exploratory-screening-20261103-v1'
ARMS=('fixed_hybrid','fixed_dynamic','e1_router')


def select_samples(rows,excluded,per_conversation=12):
    selected=[]
    for sid in sorted(DEVELOPMENT):
        groups=defaultdict(list)
        for r in rows:
            if r['conversation']==sid and r['question_id'] not in excluded:groups[r['category']].append(r)
        categories=sorted({r['category'] for r in rows if r['conversation']==sid})
        if any(not groups[c] for c in categories):raise ValueError('A real category has no non-diagnostic samples')
        for c in categories:
            groups[c].sort(key=lambda r:hashlib.sha256((SEED+':'+r['question_id']).encode()).hexdigest())
        counts={c:1 for c in categories}
        if sum(map(len,groups.values()))<per_conversation or len(categories)>per_conversation:
            raise ValueError('Insufficient samples for frozen strata')
        # Deterministic balanced allocation; scores and outcomes never enter.
        while sum(counts.values())<per_conversation:
            c=min((c for c in categories if counts[c]<len(groups[c])),key=lambda c:(counts[c],c))
            counts[c]+=1
        for c in categories:selected.extend(groups[c][:counts[c]])
    return sorted(selected,key=lambda r:(r['conversation'],r['category'],hashlib.sha256((SEED+r['question_id']).encode()).hexdigest()))


def frozen_producer(runtime,meta):
    """Coordinator Runs keep Prompt contracts in the linked execution identity."""
    path=Path(runtime)/'execution-identity.json'
    if file_sha(path)!=meta['execution_identity_sha256']:raise ValueError('Producer identity changed')
    historical=json.loads(path.read_text())
    from locomo_memory.model import ANSWER_PROMPT, QUERY_ANALYSIS_PROMPT, RESOLUTION_PROMPT, KNOWN_MODEL_VERSION
    from locomo_memory.query_schemas import EffectiveResolution, EvidenceAnswer
    from locomo_memory.retrieval_schemas import QueryAnalysis
    current={stage:dict(prompt_sha256=hashlib.sha256(prompt.encode()).hexdigest(),
                       schema_sha256=hashlib.sha256(json.dumps(schema.model_json_schema(),sort_keys=True).encode()).hexdigest())
             for stage,prompt,schema in [('Query Analysis',QUERY_ANALYSIS_PROMPT,QueryAnalysis),
                ('Resolution',RESOLUTION_PROMPT,EffectiveResolution),('Answer',ANSWER_PROMPT,EvidenceAnswer)]}
    if any(current[s]!=historical['stage_contracts'][s] for s in current):raise ValueError('Query contract changed')
    return dict(execution_identity_path=str(path.resolve()),execution_identity_sha256=file_sha(path),
        stage_contracts=current,known_service_version=KNOWN_MODEL_VERSION,metric_version='locomo-official-category-v1')


def freeze(root,runtime,controlled,output):
    root,runtime,controlled,output=map(lambda p:Path(p).resolve(),(root,runtime,controlled,output))
    rows=json.loads((output/'paired-items.json').read_text());reg=json.loads((output/'failure-regression.json').read_text())
    excluded={c['question_id'] for c in reg['cases']}
    selected=select_samples(rows,excluded)
    with readonly(runtime/'memory.sqlite3') as db:
        meta=json.loads(db.execute('SELECT result_json FROM evaluation_runs WHERE run_id=?',(BASELINE,)).fetchone()[0])
    physical=[r for r in load_ledger(runtime/'observer/budget.sqlite3') if r.get('scope')=='development-query' and r.get('run_id')==BASELINE]
    chosen={r['question_id'] for r in selected};proxy=[]
    for r in physical:
        # E1 is all-Dynamic in OOF. Duplicate historic Dynamic for an exploratory
        # cost scenario only, never relabel this as newly observed billing.
        if r['question_id'] in chosen and r['strategy'] in ('dynamic','hybrid_no_resolution'):
            proxy.extend([r]*(2 if r['strategy']=='dynamic' else 1))
    complete=[r for r in proxy if all(type((r.get('usage') or {}).get(k)) is int for k in ('prompt_tokens','completion_tokens','prompt_cache_hit_tokens','prompt_cache_miss_tokens'))]
    prompt=sum(r['usage']['prompt_tokens'] for r in complete);completion=sum(r['usage']['completion_tokens'] for r in complete)
    hit=sum(r['usage']['prompt_cache_hit_tokens'] for r in complete);miss=sum(r['usage']['prompt_cache_miss_tokens'] for r in complete)
    cold=prompt*2e-6+completion*8e-6;warm=miss*2e-6+hit*4e-8+completion*8e-6
    sample_records=[];schedule=[]
    for n,r in enumerate(selected):
        sample_records.append({k:r[k] for k in ('question_id','conversation','qa_index','sample_index','category')})
        arm_order=sorted(ARMS,key=lambda a:hashlib.sha256((SEED+r['question_id']+a).encode()).hexdigest())
        schedule.extend(dict(ordinal=3*n+i,question_id=r['question_id'],arm=a) for i,a in enumerate(arm_order))
    code={str(p.relative_to(root)):file_sha(p) for pattern in ('src/locomo_memory/*.py','tools/research_v2/*.py','tests/test_phase3*.py') for p in sorted(root.glob(pattern))}
    code['uv.lock']=file_sha(root/'uv.lock');code['pyproject.toml']=file_sha(root/'pyproject.toml')
    scorer={str(p.relative_to(root)):file_sha(p) for p in (root/'src/locomo_memory/evaluation_metrics.py',root/'data/raw/locomo/upstream/task_eval/evaluation.py')}
    manifest=dict(version='phase3-screening-design-v1',status='frozen_design_not_authorized_to_execute',seed=SEED,
        baseline_run_id=BASELINE,git_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),
        samples=sample_records,schedule=schedule,qa=48,logical_items=144,strata=dict(Counter(r['conversation']+':'+r['category'] for r in selected)),
        diagnostic_question_ids=sorted(excluded),diagnostic_case_manifest_sha256=file_sha(output/'failure-regression.json'),
        exposure='All 757 dev outcomes and four conversations were previously exposed. Sample excludes fixed diagnosis set but is exploratory; no independent generalization claim.',
        builds=meta['pins'],build_artifacts=meta.get('build_artifacts'),build_indexes=meta.get('build_indexes'),
        original_source_hashes={sid:file_sha(runtime/'sources'/f'{sid}.json') for sid in DEVELOPMENT},producer_config=meta['config'],
        config={**meta['config'],'db_path':str(root/'var/research-v2-phase3-screening-unapproved-20261103/memory.sqlite3')},
        runtime_policy='Future execution must SQLite-backup fixed Builds into this separate query-writable DB; source/Memory/index content must match frozen pins and hashes. Original runtime remains read-only. This freeze creates neither DB nor ledger.',
        producer_identity=frozen_producer(runtime,meta),
        code_files=code,scorers=scorer,router=dict(version='e1-source-gated-router-v1',coverage_threshold=.75,
            role='Exploratory fixed policy chosen in advance; OOF result gives no paid-screening justification',embedding_cache=False),
        e5=dict(role='Separate zero-paid experiment; never co-enabled with E1 to infer either effect',embedding_cache=True,router=False),
        controls=dict(model_alias=meta['config']['model_name'],rebuild=False,concurrency=1,inter_item_order='frozen schedule',
            logical_retry=0,internal_retries=meta['config']['model_retries'],resolution_input_budget=96000,model_max_tokens=32768),
        budget=dict(authority='Proposal only; old authorization expired',proposed_limit_cny=60,proposed_limit_http=1152,
            proposed_limit_wall_seconds=7200,maximum_initial_stage_calls=384,maximum_with_internal_retries=1152,
            historic_selected_request_proxy=len(proxy),historic_proxy_usage_complete=len(complete)==len(proxy),
            historic_selected_pair_states=dict(Counter(r['pair_state'] for r in selected)),
            historic_proxy_prompt_tokens=prompt,historic_proxy_completion_tokens=completion,
            historic_proxy_cache_hit_tokens=hit,historic_proxy_cache_miss_tokens=miss,
            historic_cache_mix_estimate_cny=warm,no_input_cache_estimate_cny=cold,
            tripled_cold_token_scenario_cny=3*cold,price_basis='Historical frozen peak tariff: miss 2, hit 0.04, output 8 CNY/million. Recheck before any new authorization.',
            absolute_worst_case_reservation_cny=1152*(1048576*2e-6+32768*8e-6),
            note='Proxy retains historical retries; selected sample outcome states are recorded separately. It cannot upper-bound new output lengths, retries or failures. 60 CNY is a stop cap, not a guarantee of completing 144 items. Unknown reservations count in full; no billing unknown is retried.'),
        amortization=dict(shared_historical_build_known_cny=89.65501696,unknown_build_reservation_cny=7.077888,
            formula='Total for deployment Q queries = shared Build cost + all query costs + measured local compute. Average = total/Q. Same fixed Build charged once, not once per arm. Unknown Build cost remains separate.',
            deployment_query_counts=[48,757,10000],cold_warm='Provider cache cold/warm distinct from embedding cache cold/warm; no provider cache savings credited to E5.'),
        adoption=dict(answer_quality='QA paired 95% interval lower bound >= -0.01; every conversation point delta >= -0.02; report all failed/unknown denominators.',
            evidence='Independent non-author source review of all 48 QA x arms; no newly severe factual errors, incorrect refusals, identity mistakes or citation deterioration. Semantic disagreements => inconclusive.',
            operating_cost='Only after quality/evidence gates pass: E1 total cost reduction >=10%; E5 isolated local CPU reduction >=15% and exact vector/candidate/answer-input equivalence.',
            uncertainty='48 exploratory QA and four conversations cannot establish hidden-test generalization. Insufficient intervals => inconclusive, never automatic adoption.'),
        stops=['new unknown usage or external outcome','budget/money/request/time cap','Build/config/code/scorer mismatch','unapproved model or price contract drift','source/citation scope breach','new severe factual error or incorrect refusal under review'],
        execution_gate=['Separate explicit paid authorization binding this manifest hash and fresh absolute deadline',
            'New isolated runtime and ledger; read-only original Builds; never resume original Run',
            'Non-author review of code and semantic regression; E1 currently does not justify paid screening',
            'Review model alias/pricing and new per-call reservations; 60 CNY cap may yield incomplete screening'])
    write(output/'screening-freeze.json',manifest)
    write(output/'screening-freeze-sha256.json',dict(path=str((output/'screening-freeze.json').resolve()),sha256=file_sha(output/'screening-freeze.json')))
    return manifest


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('root','runtime','controlled','output'):p.add_argument('--'+name,required=True,type=Path)
    result=freeze(**vars(p.parse_args()));print(json.dumps(dict(qa=result['qa'],strata=result['strata'],budget=result['budget']),indent=2))
