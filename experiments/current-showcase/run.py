"""Bounded showcase using existing evaluation, query and candidate APIs.

Prepare performs no provider calls. Execute requires the frozen call limit.
"""
import argparse
from collections import Counter
import fcntl
import hashlib
import json
from pathlib import Path
import sqlite3
import sys

from fastapi.testclient import TestClient
from locomo_memory.api import create_app
from locomo_memory.config import Settings
from locomo_memory.evaluation_metrics import map_evidence, coverage
from locomo_memory.implementation_identity import implementation_sha256
from locomo_memory.model import DeepSeekModel, utc_now

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'experiments/issue-15-query-reliability'))
import live

SOURCE = ROOT.parent / 'real-baseline-issue15-citation-followup-frozen'
PRIOR = SOURCE / 'campaign.sqlite3'
STRATEGIES = ['full_text', 'vector', 'hybrid_no_resolution', 'dynamic', 'dynamic_raw_fallback']
CALL_LIMIT = 420
SEED = 'showcase-20261021'
save = live.save


def rank(value):
    return hashlib.sha256(f'{SEED}:{value}'.encode()).hexdigest()


def sources(client, dataset):
    result = []
    while True:
        response = client.get(f'/datasets/{dataset}/conversations/conv-26/turns',
                              params={'limit': 100, 'offset': len(result)})
        response.raise_for_status()
        page = response.json()
        result.extend(page['items'])
        if len(result) >= page['total']:
            return result


class NoCalls:
    def generate(self, *args, **kwargs):
        raise AssertionError('prepare_must_not_call_provider')


def prepare(directory):
    raw = json.loads((ROOT / 'data/raw/locomo/locomo10.json').read_text())
    qa = next(c for c in raw if c['sample_id'] == 'conv-26')['qa']
    paired = sorted(i for category in range(1, 6) for i in sorted(
        [i for i, q in enumerate(qa) if q['category'] == category], key=rank)[:4])
    live.SOURCE, live.PRIOR, live.CALL_LIMIT = SOURCE, PRIOR, CALL_LIMIT
    live.GROUPS = {'paired': ('dynamic_raw_fallback', paired)}
    plan = live.prepare(directory)
    plan['experiments']['paired']['strategies'] = STRATEGIES
    plan['experiments']['paired']['logical_items'] = len(paired) * len(STRATEGIES)
    plan.update(campaign_phase='current-showcase-five-strategies', selection_seed=SEED,
        selection_policy='Four questions per official category by SHA256(seed:index), then original order. No result-based reselection. Development demonstration only; not held-out evaluation.',
        runner_sha256=live.digest(Path(__file__)),
        semantic_audit_policy='Audit the 20 paired dynamic_raw_fallback answers against actual cited source text. Failed answers remain failed and are not replaced. Author source review, not independent human gold.',
        recall_policy='Forty source-mappable category 1-4 questions, ten per category by fixed hash. Rank K counts Memory candidates, map to distinct Source Turns. Use actual initial RRF order, no expansion or answer-context substitution.',
        web_policy='Five isolated browser scenarios using recorded current answers, sources, relation/history and insufficient evidence; no extra provider calls. Recorded playback is identified separately from live generation.')
    plan['helper_sha256'] = {str(Path(m.__file__).resolve()): live.digest(Path(m.__file__))
        for m in list(sys.modules.values()) if getattr(m, '__file__', None)
        and str(Path(m.__file__).resolve()).startswith(str(ROOT / 'experiments'))}
    settings = Settings.model_validate(plan['settings'])
    with TestClient(create_app(settings, model=NoCalls())) as client:
        bundle_response = client.get(f"/builds/{plan['source_build_id']}/export")
        bundle_response.raise_for_status()
        bundle = bundle_response.json()
        turns = sources(client, plan['source_dataset_id'])
    save(directory / 'source-turns.json', turns)
    memories = {m['memory_id']: m for m in bundle['memories']}
    eligible = [i for i, q in enumerate(qa) if q['category'] in (1, 2, 3, 4)
                and map_evidence(q.get('evidence', []), turns)['scorable']]
    recall = sorted(i for c in range(1, 5) for i in sorted(
        [i for i in eligible if qa[i]['category'] == c], key=rank)[:10])
    assert len(recall) == 40
    plan['recall_questions'] = [{'qa_index': i, 'question': qa[i]['question'],
        'category': qa[i]['category'], 'mapping': map_evidence(qa[i]['evidence'], turns)} for i in recall]
    cases, seen_dimensions = [], set()
    for label, count in [('UPDATE', 4), ('RETAIN', 3), ('undetermined', 3)]:
        chosen = []
        for relation in sorted(bundle['relations'], key=lambda r: rank(r['relation_id'])):
            if relation['label'] != label:
                continue
            old, new = [memories[relation[k]] for k in ('old_memory_id', 'new_memory_id')]
            dimension = (new['entity_id'], new['state_dimension'])
            if old['entity_id'] != new['entity_id'] or dimension in seen_dimensions:
                continue
            if label == 'undetermined' and old['state_key'] != new['state_key']:
                continue
            seen_dimensions.add(dimension)
            chosen.append(dict(case_id=f"state-{len(cases) + len(chosen) + 1:02}", relation=relation,
                old_memory=old, new_memory=new,
                question=f"As of the end of the conversation, what is known about {new['entity_id']}'s {new['state_dimension'].replace('_', ' ')}?"))
            if len(chosen) == count:
                break
        assert len(chosen) == count, (label, len(chosen))
        cases.extend(chosen)
    plan['dynamic_cases'] = cases
    plan['relation_population'] = dict(Counter(r['label'] for r in bundle['relations']))
    plan['dynamic_case_policy'] = 'Ten real stored relation pairs, 4 UPDATE/3 RETAIN/3 undetermined; unique entity/dimension, fixed hash order. Query dynamic once per case; inspect source meaning separately from stored model labels. No real SUPERSEDE or CONFLICT in this Build; do not fabricate coverage.'
    plan['source_turns_sha256'] = live.digest(directory / 'source-turns.json')
    save(directory / 'plan.json', plan)
    (directory / 'plan.sha256').write_text(live.digest(directory / 'plan.json') + '\n')
    return plan


def execute(directory, authorized_limit):
    assert authorized_limit == CALL_LIMIT, 'frozen_budget_confirmation_required'
    plan = json.loads((directory / 'plan.json').read_text())
    assert live.digest(directory / 'plan.json') == (directory / 'plan.sha256').read_text().strip()
    assert live.digest(Path(__file__)) == plan['runner_sha256']
    assert all(live.digest(Path(path)) == sha for path, sha in plan['helper_sha256'].items())
    assert implementation_sha256() == plan['implementation_sha256']
    assert live.digest(PRIOR) == plan['prior_ledger_sha256']
    assert live.digest(ROOT / 'data/raw/locomo/locomo10.json') == plan['official_artifact_sha256']
    assert live.digest(directory / 'source-turns.json') == plan['source_turns_sha256']
    assert not (directory / 'outcome.json').exists(), 'explicit_recovery_required'
    artifact_digest = live.previous.previous.artifact_digest
    assert artifact_digest(directory / 'memory.sqlite3') == plan['immutable_build_artifacts_sha256']
    campaign = live.v6_campaign.Campaign(directory / 'campaign.sqlite3', PRIOR, create=True,
                                       limit=plan['cumulative_ceiling'])
    assert campaign.header['previous_calls'] == plan['previous_calls']
    live.v6_campaign.FIELDS += ('thinking', 'reasoning_effort', 'max_tokens')
    audit = live.previous.previous.ValidationAudit(directory)
    settings = Settings.model_validate(plan['settings'])
    model = DeepSeekModel(settings, transport=audit)
    generate = model.generate

    def observed(operation, payload, schema, *, context=None, on_call=None):
        audit.operation, audit.schema, audit.context = operation, schema, context
        return generate(operation, payload, schema, context=context, on_call=on_call)

    model.generate = observed
    campaign.bind(model, plan['campaign_phase'])
    outcome = dict(started_at=utc_now(), status='running', runs={}, authorized_call_limit=authorized_limit)
    save(directory / 'outcome.json', outcome)
    try:
        app = create_app(settings, model=model)
        with TestClient(app) as client:
            assert client.get(f"/builds/{plan['source_build_id']}").json()['status'] == 'complete'
            live.previous.run_group(client, app, directory, plan, 'paired', outcome)
            recall = []
            for q in plan['recall_questions']:
                response = client.post('/candidate-queries', json={'build_id': plan['source_build_id'], 'question': q['question']})
                response.raise_for_status()
                result = response.json()
                scores = {str(k): coverage([sid for c in result['initial_candidates'][:k]
                    for sid in c['memory']['source_ids']], q['mapping']) for k in (5, 10, 20)}
                recall.append(dict(**q, recall_at=scores, result=result))
                save(directory / 'recall-results.json', recall)
                print(json.dumps({'event': 'recall_finished', 'qa_index': q['qa_index']}), flush=True)
            dynamic = []
            for case in plan['dynamic_cases']:
                response = client.post('/queries', json={'dataset_id': plan['source_dataset_id'],
                    'sample_id': 'conv-26', 'build_id': plan['source_build_id'],
                    'question': case['question'], 'strategy': 'dynamic', 'evidence_profile': 'expanded'})
                if response.is_error:
                    error = response.json().get('error', {})
                    trace_id = error.get('trace_id')
                    trace = client.get(f'/queries/{trace_id}').json() if trace_id else None
                    dynamic.append({'case_id': case['case_id'], 'status': 'failed', 'error': error, 'trace': trace})
                else:
                    dynamic.append({'case_id': case['case_id'], 'status': 'succeeded', 'trace': response.json()})
                save(directory / 'dynamic-results.json', dynamic)
                print(json.dumps({'event': 'dynamic_case_finished', 'case_id': case['case_id']}), flush=True)
        outcome['status'] = 'completed' if (all(r['status'] == 'completed' for r in outcome['runs'].values())
            and all(r['status'] == 'succeeded' for r in dynamic)) else 'completed_with_errors'
    except Exception as error:
        outcome.update(status='experiment_stopped', error_type=type(error).__name__)
    finally:
        outcome.update(completed_at=utc_now(), budget_after=campaign.summary(),
            source_build_unchanged=artifact_digest(SOURCE / 'memory.sqlite3') == plan['immutable_build_artifacts_sha256'],
            snapshot_build_unchanged=artifact_digest(directory / 'memory.sqlite3') == plan['immutable_build_artifacts_sha256'])
        save(directory / 'outcome.json', outcome)
    print(json.dumps({'status': outcome['status'], 'budget_after': outcome['budget_after']}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare', 'execute'])
    parser.add_argument('--directory', required=True, type=Path)
    parser.add_argument('--authorized-call-limit', type=int)
    args = parser.parse_args()
    with live.previous.ORIGINAL_LOCK.open('a+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if args.action == 'prepare':
            p = prepare(args.directory.resolve())
            print(json.dumps({'status': 'frozen_pending_authorization', 'paired': 100, 'recall': 40,
                'dynamic': 10, 'call_limit': p['call_limit'], 'previous_calls': p['previous_calls'],
                'cumulative_ceiling': p['cumulative_ceiling']}))
        else:
            execute(args.directory.resolve(), args.authorized_call_limit)
