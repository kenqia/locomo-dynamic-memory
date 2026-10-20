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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=['extraction', 'candidates'])
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('new_output_required')
    # Serialize quality invocations; inherited reserve still enforces the global cap.
    with CAMPAIGN.with_suffix('.quality.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        campaign = QualityCampaign(CAMPAIGN, PRIOR)
        model = DeepSeekModel(Settings(model_retries=0))
        campaign.bind(model, {'extraction':'quality-A-extraction','candidates':'quality-B-candidates'}[args.phase])
        result = {'created_at': utc_now(), 'implementation_sha256': implementation_sha256(),
                  'before': campaign.summary(), 'phase': args.phase}
        try:
            result['cases'] = []
            for case in {'extraction':extraction,'candidates':candidates}[args.phase](model):
                result['cases'].append(case)
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
            result['status'] = 'requires_semantic_review'
        except (ModelFailure, ValueError) as error:
            result['status'] = 'stopped'
            result['error_code'] = error.code if isinstance(error, ModelFailure) else 'campaign_or_provider_stopped'
        finally:
            result['after'] = campaign.summary()
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
        print(json.dumps({'status': result['status'], 'output': str(args.output),
                          'total_calls': result['after']['reserved_total_calls']}))


if __name__ == '__main__':
    main()
