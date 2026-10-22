"""Finite quality probes sharing the original issue-15 campaign, never a new ledger."""
import argparse
from contextlib import closing
import fcntl
import json
from pathlib import Path
import sqlite3
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'issue-15-v6-gates'))
from v6_campaign import Campaign
from locomo_memory.config import Settings
from locomo_memory.implementation_identity import implementation_sha256
from locomo_memory.memory_schemas import ExtractionBatch
from locomo_memory.model import DeepSeekModel, ModelFailure, utc_now

CAMPAIGN = Path('/home/kenqia/my_folder/locomo-worktrees/real-baseline-issue15-relations-v6/campaign.sqlite3')
PRIOR = Path('/home/kenqia/my_folder/locomo-worktrees/real-baseline-issue15-relations-v5/provider-budget.sqlite3')


class QualityCampaign(Campaign):
    def reserve(self, phase, identity, operation):
        with closing(sqlite3.connect(self.path.as_uri() + '?mode=ro', uri=True)) as db:
            count = db.execute('SELECT COUNT(*) FROM calls WHERE phase=?', (phase,)).fetchone()[0]
        if count >= 16:
            raise ValueError('quality_phase_ceiling_reached')
        return super().reserve(phase, identity, operation)


def extraction(model):
    cases = [
        ('plan', 'Riley', 'I intend to relocate to Oslo, but I have not moved yet.'),
        ('fact', 'Riley', 'I relocated to Oslo. I no longer work for Northwind.'),
        ('speaker', 'Riley', "Morgan said, 'I hope to start a bakery.' I still work as a nurse."),
        ('stages', 'Riley', 'I researched foster agencies, then filed my application, and later passed the interview. The placement is not finalized.'),
    ]
    for name, speaker, text in cases:
        source = {'source_id': f'synthetic/{name}', 'speaker': speaker, 'text': text,
                  'session_time': '2023-05-01', 'session_id': 'session_1'}
        generated = model.generate('extract', {'sample_id': 'synthetic', 'sources': [source]}, ExtractionBatch,
                                   context={'sources': {source['source_id']: source}})
        yield {'case': name, 'source': source, 'output': generated.value.model_dump(mode='json'),
               'metadata': generated.metadata}


def candidate_inputs():
    from locomo_memory.relation_replay import source_snapshot, comparison
    from locomo_memory.relation_selection import select_history
    source = PRIOR.parent / 'memory.sqlite3'
    build = '23f0459c5b3b47269dc1497cfc066810'
    with source_snapshot(source) as (db, digest):
        if digest != '12410a8a857e91a9e23b97280b4cbcb647278daef83200cb9907c748cd238e2d':
            raise ValueError('historical_source_changed')
        rows = db.execute('SELECT m.memory_json,MIN(s.position) AS source_order FROM memories m '
            'JOIN memory_sources ms ON m.memory_id=ms.memory_id JOIN source_turns s ON s.source_id=ms.source_id '
            'WHERE m.build_id=? GROUP BY m.memory_id ORDER BY source_order,m.rowid', (build,)).fetchall()
        all_memories = [json.loads(r[0]) for r in rows]
        for ordinal in (73, 91):
            identity, payload, context = comparison(db, build, ordinal)
            new = context['new_memory']
            before = all_memories[:next(i for i,m in enumerate(all_memories) if m['memory_id']==new['memory_id'])]
            selected, audit = select_history(new, [m for m in before if m['entity_id']==new['entity_id']], Settings())
            ids = sorted({sid for m in [new,*selected] for sid in m['source_ids']})
            sources = {sid: dict(db.execute('SELECT * FROM source_turns WHERE source_id=?', (sid,)).fetchone()) for sid in ids}
            context = {'new_memory':new,'history':selected,'sources':sources}
            yield identity, {**context, 'sources':list(sources.values())}, context, audit


def candidates(model):
    from locomo_memory.relation_schemas import RelationBatch
    for identity, payload, context, audit in candidate_inputs():
        result = model.generate('relate',payload,RelationBatch,context=context)
        yield {'case':identity['ordinal'],'selection':audit,'output':result.value.model_dump(mode='json'),
               'metadata':result.metadata}


def stages(model):
    from locomo_memory.relation_replay import source_snapshot, comparison
    from locomo_memory.relation_schemas import RelationBatch
    with source_snapshot(PRIOR.parent/'memory.sqlite3') as (db, digest):
        if digest != '12410a8a857e91a9e23b97280b4cbcb647278daef83200cb9907c748cd238e2d':
            raise ValueError('historical_source_changed')
        for ordinal in (73, 148, 172):
            identity,payload,context = comparison(db,'23f0459c5b3b47269dc1497cfc066810',ordinal)
            generated = model.generate('relate',payload,RelationBatch,context=context)
            yield {'case':ordinal,'input_identity':identity,'output':generated.value.model_dump(mode='json'),
                   'metadata':generated.metadata}


def raw_fallback(model, *, profile="expanded", include_employment=False):
    """Real resolution/answer with synthetic fixed evidence; no production Build."""
    from types import SimpleNamespace
    from locomo_memory.raw_queries import run_raw_query
    from locomo_memory.query_schemas import QueryRequest
    from locomo_memory.memory_schemas import Memory
    sources = [dict(source_id=f'synthetic/conv-probe/D1:{i+1}', dataset_id='synthetic',
        sample_id='conv-probe', session_id='session_1', dia_id=f'D1:{i+1}', speaker='Riley',
        session_time='1:00 pm on 1 May, 2023', text=text, position=i) for i,text in enumerate([
            'I live in Bergen.', 'I work for Larch. I have not said when I started.'])]
    memory = Memory(memory_id='residence', build_id='synthetic-build', dataset_id='synthetic',
        sample_id='conv-probe', state_key='conv-probe:Riley:residence', session_times=['1:00 pm on 1 May, 2023'],
        content='Riley lives in Bergen.', memory_type='state', statement_type='fact', polarity='positive',
        entity_id='Riley', state_dimension='residence', state_value='Bergen', source_ids=[sources[0]['source_id']]).model_dump(mode='json')
    request = QueryRequest(dataset_id='synthetic',sample_id='conv-probe',strategy='dynamic_raw_fallback',
        question='Where does Riley work, and on what date did Riley start that job?')
    memories = {memory['memory_id']:memory}
    if include_employment:
        employment = {**memory, 'memory_id':'employment','content':'Riley works for Larch.',
            'state_key':'conv-probe:Riley:employment','state_dimension':'employment','state_value':'Larch',
            'source_ids':[sources[1]['source_id']]}
        memories['employment'] = employment
        extra = {**sources[0], 'source_id':'synthetic/conv-probe/D1:3', 'dia_id':'D1:3',
                 'speaker':'Morgan','text':'I collect violet marbles.', 'position':2}
        sources.append(extra)
        memories['hobby'] = {**memory, 'memory_id':'hobby', 'entity_id':'Morgan',
            'content':'Morgan collects violet marbles.', 'state_key':'conv-probe:Morgan:hobby',
            'state_dimension':'hobby', 'state_value':'marbles', 'source_ids':[extra['source_id']]}
        request.question = 'Where does Riley work?'

    request.evidence_profile = profile
    trace = {'prompts':{},'schemas':{},'query_fingerprint':'synthetic-fixed-input',
        'initial':{'analysis':{'entities':['Riley'],'topic':'employment','keywords':[]},'initial_truncated':False},
        'expanded':{'truncated':False},'relations':[], 'operations':{},'stage_seconds':{},
        'time':{'requested_date':None,'anchor_date':'2023-05-01','origin':'conversation_cutoff',
                'cutoff':'2023-05-01T13:00:00','beyond_cutoff':False}}
    run_raw_query(SimpleNamespace(settings=model.settings,model=model),request,trace,
        memories,{s['source_id']:s for s in sources},
        (sources,{'scope':'synthetic-controller-probe','pinned_source_ids':[s['source_id'] for s in sources]}))
    yield {'case':'employment_and_unknown_start','profile':profile,'input_memories':list(memories.values()),'source':sources,'trace':trace,
           'acceptance':'Larch with source citation, at most two resolves; focused must retain Riley evidence and remove only unrelated Morgan component.' if include_employment else 'Recover Larch with raw citation; start date remains unknown; at most two resolves.'}


def evidence(model):
    for profile in ('expanded', 'focused'):
        yield from raw_fallback(model, profile=profile, include_employment=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=['extraction', 'candidates', 'stages', 'raw', 'evidence'])
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('new_output_required')
    # Serialize quality invocations; inherited reserve still enforces the global cap.
    with CAMPAIGN.with_suffix('.quality.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        campaign = QualityCampaign(CAMPAIGN, PRIOR)
        synthetic_outputs = []
        transport = None
        if args.phase in ('raw','evidence'):
            import httpx
            class SyntheticProbeTransport(httpx.HTTPTransport):
                def handle_request(self, request):
                    response = super().handle_request(request)
                    response.read()
                    if response.status_code == 200:
                        synthetic_outputs.append(response.json()['choices'][0]['message']['content'])
                    return response
            transport = SyntheticProbeTransport()
        model = DeepSeekModel(Settings(model_retries=0), transport=transport)
        campaign.bind(model, {'extraction':'quality-A-extraction','candidates':'quality-B-candidates','stages':'quality-C-stages','raw':'quality-D-raw','evidence':'quality-E-evidence'}[args.phase])
        result = {'created_at': utc_now(), 'implementation_sha256': implementation_sha256(),
                  'before': campaign.summary(), 'phase': args.phase}
        try:
            result['cases'] = []
            for case in {'extraction':extraction,'candidates':candidates,'stages':stages,'raw':raw_fallback,'evidence':evidence}[args.phase](model):
                result['cases'].append(case)
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
            result['status'] = 'requires_semantic_review'
        except (ModelFailure, ValueError) as error:
            result['status'] = 'stopped'
            result['error_code'] = error.code if isinstance(error, ModelFailure) else 'campaign_or_provider_stopped'
        finally:
            if args.phase in ('raw','evidence'):
                result['synthetic_provider_outputs'] = synthetic_outputs
            result['after'] = campaign.summary()
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
        print(json.dumps({'status': result['status'], 'output': str(args.output),
                          'total_calls': result['after']['reserved_total_calls']}))


if __name__ == '__main__':
    main()
