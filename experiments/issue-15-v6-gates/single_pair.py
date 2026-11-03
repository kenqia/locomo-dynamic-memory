"""Diagnose batch sensitivity; these reduced inputs cannot qualify a full build."""
import hashlib
import json
from pathlib import Path
import sys

from locomo_memory.config import Settings
from locomo_memory.experiment import write_json
from locomo_memory.implementation_identity import implementation_sha256
from locomo_memory.imports import canonical_json
from locomo_memory.model import DeepSeekModel, ModelFailure, RELATION_PROMPT_VERSION, utc_now
from locomo_memory.relation_replay import comparison, source_snapshot
from locomo_memory.relation_schemas import RelationBatch, RELATION_SCHEMA_VERSION
from gates import SOURCE, BUILD, PRIOR
from v6_campaign import Campaign


def run(directory):
    target = directory/'single-pair.json'
    if target.exists():
        raise ValueError('isolation_already_started')
    state = json.loads((directory/'gates.json').read_text())
    assert state['gate1']['status'] == 'passed'
    assert state['gate1']['implementation_sha256'] == implementation_sha256()
    budget = Campaign(Path(state['campaign_directory'])/'campaign.sqlite3', PRIOR)
    inputs = []
    with source_snapshot(SOURCE) as (db, source_hash):
        settings = Settings.model_validate(json.loads(db.execute(
            'SELECT config_json FROM build_versions WHERE build_id=?',(BUILD,)).fetchone()[0]))
        for ordinal, old_id in [(73,'480d91e2f9e90f04b47fa0af'), (172,'32a5b80fcfba6f409b45b842')]:
            identity, _, context = comparison(db, BUILD, ordinal)
            history = [m for m in context['history'] if m['memory_id'] == old_id]
            assert len(history) == 1
            ids = sorted(set(history[0]['source_ids'] + context['new_memory']['source_ids']))
            context = {**context, 'history': history, 'sources': {s:context['sources'][s] for s in ids}}
            payload = {**context, 'sources': list(context['sources'].values())}
            inputs.append((identity, payload, context))
    settings = settings.model_copy(update={'model_max_tokens':8192,'model_retries':0})
    report = {'started_at':utc_now(),'implementation_sha256':implementation_sha256(),
              'prompt_version': RELATION_PROMPT_VERSION, 'schema_version': RELATION_SCHEMA_VERSION,
              'source_sha256':source_hash,'status':'running','qualifies_full_build':False,
              'treatment':'one history endpoint and only endpoint sources; current prompt and schema', 'attempts':[]}
    write_json(target,report)
    try:
        for identity, payload, context in inputs:
            model=DeepSeekModel(settings)
            budget.bind(model,'gate5-single-pair-diagnosis',source_task_id=identity['task_id'])
            record={'source_task_id':identity['task_id'], 'candidate_count':1,
                    'payload_sha256':hashlib.sha256(canonical_json(payload).encode()).hexdigest()}
            try:
                result=model.generate('relate',payload,RelationBatch,context=context)
                record.update(status='succeeded',judgments=result.value.model_dump(mode='json')['judgments'],metadata=result.metadata)
            except ModelFailure as error:
                record.update(status=error.code,metadata=error.metadata)
            report['attempts'].append(record)
            write_json(target,report)
        report['status']='observations_saved'
    except Exception:
        report.update(status='blocked',error_code='isolation_requires_review')
    finally:
        report.update(finished_at=utc_now(),budget=budget.summary())
        write_json(target,report)
    print(json.dumps({'status':report['status'],'attempts':report['attempts'],'budget':report['budget']}),flush=True)


if __name__=='__main__':
    run(Path(sys.argv[1]).resolve())
