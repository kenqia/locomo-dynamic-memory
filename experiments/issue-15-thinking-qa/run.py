"""One isolated conv-26 build and ten paired QA comparisons on the existing budget."""
import argparse
import fcntl
import hashlib
import json
from pathlib import Path
import sys
import time

import httpx
from pydantic import ValidationError

from fastapi.testclient import TestClient

from locomo_memory.api import create_app
from locomo_memory.config import Settings
from locomo_memory.implementation_identity import implementation_sha256
from locomo_memory.model import DeepSeekModel, utc_now
from locomo_memory.memory_schemas import ExtractionBatch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'experiments/issue-15-v6-gates'))
import v6_campaign

CAMPAIGN = ROOT.parent / 'real-baseline-issue15-relations-v6/campaign.sqlite3'
PRIOR = ROOT.parent / 'real-baseline-issue15-relations-v5/provider-budget.sqlite3'
SELECTION = [(3, 'fact'), (4, 'fact'), (13, 'cross_session'), (15, 'cross_session'),
             (0, 'time'), (16, 'time'), (53, 'state_progression'), (79, 'state_progression'),
             (153, 'insufficient'), (157, 'insufficient')]
STRATEGIES = ['dynamic', 'dynamic_raw_fallback', 'hybrid_no_resolution', 'full_text']


class ExtractionAudit(httpx.BaseTransport):
    """Observe fixed validation causes in memory; never persist response text."""
    def __init__(self, path):
        self.path = path

    def handle_request(self, request):
        with httpx.HTTPTransport() as transport:
            response = transport.handle_request(request)
            response.read()
        body = json.loads(request.content)
        payload = json.loads(body['messages'][1]['content'])
        if 'new_memory' not in payload and 'sources' in payload and 'question' not in payload and response.status_code == 200:
            try:
                content = response.json()['choices'][0]['message']['content']
                ExtractionBatch.model_validate_json(content, context={
                    'sources': {s['source_id']: s for s in payload['sources']}})
            except ValidationError as error:
                allowed = {'Duplicate source reference', 'Unknown source or source from another conversation/fragment',
                           'Time anchor must be one of the cited sources', 'Original time expression is absent from anchor text',
                           'Time interval is reversed', 'Interpreted time requires original expression, source anchor and basis'}
                causes = [str(e.get('ctx', {}).get('error', '')) for e in error.errors()]
                causes = [cause if cause in allowed else 'other_validation_error' for cause in causes]
                old = json.loads(self.path.read_text()) if self.path.exists() else []
                save(self.path, [*old, {'at': utc_now(), 'causes': causes}])
            except (ValueError, KeyError, IndexError, TypeError):
                pass
        return response

def save(path, value):
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    temporary.replace(path)


def prepare(directory, relation_max_tokens=None, model_timeout_seconds=60):
    directory.mkdir(parents=True, exist_ok=False)
    settings = Settings(db_path=directory / 'memory.sqlite3', relation_max_tokens=relation_max_tokens,
                        model_timeout_seconds=model_timeout_seconds)
    raw = (ROOT / 'data/raw/locomo/locomo10.json').read_bytes()
    conversation = next(c for c in json.loads(raw) if c['sample_id'] == 'conv-26')
    questions = []
    for index, purpose in SELECTION:
        qa = conversation['qa'][index]
        questions.append({'question_id': f'conv-26:qa:{index}', 'qa_index': index,
                          'purpose': purpose, 'official_qa': qa})
    campaign = v6_campaign.Campaign(CAMPAIGN, PRIOR)
    plan = {'created_at': utc_now(), 'sample_id': 'conv-26', 'settings': settings.snapshot(),
            'implementation_sha256': implementation_sha256(), 'questions': questions,
            'strategies': STRATEGIES, 'evidence_profile': 'expanded',
            'official_artifact_sha256': hashlib.sha256(raw).hexdigest(),
            'budget_before': campaign.summary(), 'logical_items': 40,
            'selection_note': 'Two original QA per purpose, fixed before model results. State questions probe application and interview stages; no rewritten current-state questions. Category 5 has no reference answer; report refusal behavior separately.'}
    save(directory / 'plan.json', plan)
    return plan


def execute(directory, plan, *, resume=False):
    if plan['implementation_sha256'] != implementation_sha256():
        raise ValueError('implementation_changed_since_plan')
    campaign = v6_campaign.Campaign(CAMPAIGN, PRIOR)
    if not resume and campaign.summary()['reserved_total_calls'] != plan['budget_before']['reserved_total_calls']:
        raise ValueError('campaign_changed_since_plan')
    v6_campaign.FIELDS += ('thinking', 'reasoning_effort', 'max_tokens')
    settings = Settings.model_validate(plan['settings'])
    model = DeepSeekModel(settings, transport=ExtractionAudit(directory / 'extraction-validation-causes.json') if resume else None)
    campaign.bind(model, 'thinking-conv26-build-qa')
    outcome = {'started_at': utc_now(), 'status': 'running', 'directory': str(directory)}
    if resume:
        previous = json.loads((directory / 'outcome.json').read_text())
        if previous['status'] not in {'extraction_incomplete', 'relations_incomplete'}:
            raise ValueError('only_known_incomplete_build_can_resume')
        history_path = directory / 'outcome-history.json'
        history = json.loads(history_path.read_text()) if history_path.exists() else []
        save(history_path, [*history, previous])
        outcome.update(dataset_id=previous['dataset_id'], build_id=previous['build_id'])
        outcome['resumed_at'] = utc_now()
    save(directory / 'outcome.json', outcome)
    try:
        app = create_app(settings, model=model)
        with TestClient(app) as client:
            if resume:
                dataset_id = outcome['dataset_id']
                build = app.state.builds.get(outcome['build_id'])
                if build['phase'] == 'extraction':
                    app.state.builds.retry(build['build_id'])
            else:
                imported = client.post('/imports/official')
                imported.raise_for_status()
                dataset_id = imported.json()['dataset_id']
                build = app.state.builds.start(dataset_id, 'conv-26')
            build_id = build['build_id']
            outcome.update(dataset_id=dataset_id, build_id=build_id)
            save(directory / 'outcome.json', outcome)
            if build['phase'] == 'extraction':
                app.state.builds.run(build_id)
            build = app.state.builds.get(build_id)
            if build['phase'] == 'extraction':
                save(directory / 'build-extracted.json', build)
            if build['phase'] == 'extraction' and build['status'] != 'extracted':
                raise ValueError('extraction_incomplete')
            if build['status'] == 'extracted':
                save(directory / 'index.json', app.state.retrieval.create_index(build_id))
            app.state.relations.start(build_id)
            save(directory / 'relation-plan.json', app.state.relations.progress(build_id))
            app.state.relations.run(build_id)
            save(directory / 'relation-progress.json', app.state.relations.progress(build_id))
            build = app.state.builds.get(build_id)
            save(directory / 'build-related.json', build)
            if build['status'] != 'related':
                raise ValueError('relations_incomplete')
            # This publication affects only this new local experimental database.
            app.state.versions.publish(build_id)
            exported = client.get(f'/builds/{build_id}/export')
            exported.raise_for_status()
            save(directory / 'memory-export.json', exported.json())
            samples = []
            for question in plan['questions']:
                qa = question['official_qa']
                samples.append({'sample_id': 'conv-26', 'question': qa['question'],
                                'answer': qa.get('answer'), 'category': qa['category'],
                                'evidence': qa['evidence']})
            created = client.post('/evaluation-inputs', json={
                'dataset_id': dataset_id, 'kind': 'official_structure_only', 'samples': samples})
            created.raise_for_status()
            save(directory / 'evaluation-input.json', created.json())
            response = client.post('/evaluation-runs', json={
                'input_id': created.json()['input_id'], 'strategies': STRATEGIES,
                'build_ids': {'conv-26': build_id}, 'evidence_profile': 'expanded', 'wait': False})
            response.raise_for_status()
            run_id = response.json()['run_id']
            outcome['run_id'] = run_id
            save(directory / 'outcome.json', outcome)
            while True:
                progress = app.state.evaluation.execution.progress(run_id)
                if progress['status'] != 'running':
                    break
                time.sleep(1)
            result = app.state.evaluation.get('evaluation_runs', run_id)
            save(directory / 'evaluation-run.json', result)
            outcome.update(status=result['status'], progress=result['progress'])
    except Exception as error:
        # No provider message, headers, request body, or arbitrary exception string.
        known = {'extraction_incomplete', 'relations_incomplete'}
        code = error.args[0] if isinstance(error, ValueError) and error.args and error.args[0] in known else 'experiment_stopped'
        outcome.update(status=code, error_type=type(error).__name__)
    finally:
        outcome.update(completed_at=utc_now(), budget_after=campaign.summary())
        save(directory / 'outcome.json', outcome)
        print(json.dumps({k: outcome[k] for k in ('status', 'build_id', 'run_id') if k in outcome}), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['prepare', 'execute', 'resume'])
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--relation-max-tokens', type=int)
    parser.add_argument('--model-timeout-seconds', type=float, default=60)
    args = parser.parse_args()
    directory = args.directory.resolve()
    with CAMPAIGN.with_suffix('.quality.lock').open('a+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if args.action == 'prepare':
            plan = prepare(directory, args.relation_max_tokens, args.model_timeout_seconds)
            print(json.dumps({'status': 'prepared', 'logical_items': plan['logical_items']}))
        else:
            if args.action == 'execute' and (directory / 'outcome.json').exists():
                raise ValueError('existing_execution_requires_explicit_recovery')
            execute(directory, json.loads((directory / 'plan.json').read_text()), resume=args.action == 'resume')


if __name__ == '__main__':
    main()
