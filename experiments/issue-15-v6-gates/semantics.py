"""Additional same-key probes and a fixed semantic audit packet, sharing the campaign."""
from collections import Counter
import json
from pathlib import Path
import sys

from locomo_memory.config import Settings
from locomo_memory.experiment import write_json
from locomo_memory.implementation_identity import implementation_sha256
from locomo_memory.model import DeepSeekModel, ModelFailure, RELATION_PROMPT_VERSION, utc_now
from locomo_memory.relation_replay import comparison, source_snapshot
from locomo_memory.relation_schemas import RelationBatch
from evidence import QuoteAuditTransport
from gates import SOURCE, BUILD, PRIOR
from v6_campaign import Campaign


def run(directory):
    state = json.loads((directory/'gates.json').read_text())
    assert state['gate4']['status'] == 'passed'
    assert state['gate4']['implementation_sha256'] == implementation_sha256()
    campaign_directory = Path(state.get('campaign_directory', directory))
    budget = Campaign(campaign_directory/'campaign.sqlite3', PRIOR)
    target = directory/'same-key.json'
    if target.exists():
        raise ValueError('same_key_probes_already_started')
    with source_snapshot(SOURCE) as (db, source_hash):
        original = Settings.model_validate(json.loads(db.execute(
            'SELECT config_json FROM build_versions WHERE build_id=?', (BUILD,)).fetchone()[0]))
        inputs = [comparison(db, BUILD, ordinal) for ordinal in (31, 76)]
    settings = original.model_copy(update={'model_max_tokens': 8192, 'model_retries': 0})
    report = {'started_at': utc_now(), 'status': 'running',
              'implementation_sha256': implementation_sha256(), 'prompt_version': RELATION_PROMPT_VERSION,
              'source_sha256': source_hash, 'max_tokens': 8192, 'model_retries': 0, 'attempts': []}
    write_json(target, report)
    try:
        for identity, payload, context in inputs:
            transport = QuoteAuditTransport(context)
            model = DeepSeekModel(settings, transport=transport)
            budget.bind(model, 'gate5-same-key', source_task_id=identity['task_id'])
            record = {'source_task_id': identity['task_id'], 'payload_sha256': identity['payload_sha256'],
                      'candidate_count': len(context['history'])}
            try:
                result = model.generate('relate', payload, RelationBatch, context=context)
                record.update(status='succeeded', covered_candidate_count=len(result.value.judgments),
                              judgments=result.value.model_dump(mode='json')['judgments'], metadata=result.metadata,
                              label_counts=dict(Counter(j.label for j in result.value.judgments)))
            except ModelFailure as error:
                record.update(status=error.code, metadata=error.metadata)
            record['quote_audit'] = transport.observations
            report['attempts'].append(record)
            write_json(target, report)
        report['status'] = 'observations_saved' if all(a['status'] == 'succeeded' for a in report['attempts']) else 'failed'
    except Exception:
        report.update(status='blocked', error_code='same_key_probes_require_review')
    finally:
        report['finished_at'], report['budget'] = utc_now(), budget.summary()
        write_json(target, report)
    if report['status'] != 'observations_saved':
        return report['status']

    # Keep exactly the previously audited pairs, then add all same-key pairs and
    # every determined output. Selection never changes a provider request.
    original = json.loads((campaign_directory/'audit-inputs.json').read_text())
    pairs = {(c['source_task_id'], c['old_memory']['memory_id'])
             for c in original['undetermined_cases'] + original['determined_controls']}
    reports = [json.loads((directory/name).read_text()) for name in ('lengths.json','evidence.json','same-key.json')]
    cases = []
    with source_snapshot(SOURCE) as (db, source_hash):
        for observed in reports:
            for attempt in observed['attempts']:
                if attempt.get('max_tokens', observed.get('max_tokens')) != 8192:
                    continue
                ordinal = int(attempt['source_task_id'].rsplit(':', 1)[1])
                identity, _, context = comparison(db, BUILD, ordinal)
                old_by_id = {o['memory_id']: o for o in context['history']}
                for judgment in attempt['judgments']:
                    old, new = old_by_id[judgment['old_memory_id']], context['new_memory']
                    same = old['state_key'] == new['state_key']
                    if (identity['task_id'], old['memory_id']) not in pairs and not same and judgment['label'] == 'undetermined':
                        continue
                    ids = sorted(set(old['source_ids'] + new['source_ids'] + judgment['source_ids']))
                    cases.append({'source_task_id': identity['task_id'], 'old_memory': old, 'new_memory': new,
                                  'same_state_key': same, 'judgment': judgment,
                                  'sources': [context['sources'][s] for s in ids]})
    write_json(directory/'semantic-inputs.json', {'implementation_sha256': implementation_sha256(),
        'source_sha256': source_hash, 'new_calls_for_packet': 0, 'not_human_ground_truth': True,
        'selection': 'fixed original 26 pairs, all four additional same-key pairs, and every determined output',
        'cases': cases})
    state['gate5'] = {'status': 'awaiting_independent_audit', 'packet': 'semantic-inputs.json',
                      'sample_count': len(cases), 'budget': budget.summary()}
    write_json(directory/'gates.json', state)
    return 'awaiting_independent_audit'


if __name__ == '__main__':
    try:
        status = run(Path(sys.argv[1]).resolve())
    except Exception:
        status = 'blocked'
    print(json.dumps({'status': status}), flush=True)
    raise SystemExit(2 if status in {'blocked', 'failed'} else 0)
