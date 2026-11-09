"""Prepare a bounded holdout extraction stage; execution needs separate authorization."""
import argparse
import json
from pathlib import Path

import httpx

from locomo_memory.builds import BuildService
from locomo_memory.config import Settings
from locomo_memory.database import Database
from locomo_memory.imports import import_dataset
from locomo_memory.m5_budget import BudgetTransport
from locomo_memory.model import DeepSeekModel
from locomo_memory.schemas import ImportRequest
from tools.m5.offline import ROOT, HOLDOUT, sha, write

POLICY = dict(max_requests=204, max_usd='18', model='deepseek-flash',
    input_usd_per_million='.30', output_usd_per_million='1.20',
    max_input_bytes=160000, max_output_tokens=32768)


def prepare(output):
    output.mkdir(parents=True, exist_ok=False)
    output.chmod(0o700)
    samples, identities = [], {}
    for conv in HOLDOUT:
        path = ROOT/'var/m5-development/replay-v1/conversation-only'/f'{conv}.json'
        rows = json.loads(path.read_text())
        speakers = list(dict.fromkeys(r['speaker'] for r in rows))
        conversation = dict(speaker_a=speakers[0], speaker_b=speakers[1])
        for row in rows:
            session = row['session_id']
            conversation[session+'_date_time'] = row['session_time']
            conversation.setdefault(session, []).append({k: row[k] for k in ('dia_id', 'speaker', 'text')})
        samples.append(dict(sample_id=conv, conversation=conversation))
        identities[conv] = dict(snapshot_sha256=sha(path), turns=len(rows),
                                fragments=(len(rows)+19)//20, qa_read=False)
    settings = Settings.model_validate(json.loads(
        (ROOT/'experiments/m5-development/delivery-v1/protocol.json').read_text())['shared_settings'])
    settings = settings.model_copy(update={'db_path': output/'memory.sqlite3'})
    assert settings.fragment_turns == 20 and settings.model_retries == 2
    assert settings.model_max_tokens == POLICY['max_output_tokens']
    db = Database(settings.db_path)
    result = import_dataset(db, ImportRequest(data=samples, version='m5-holdout-conversation-only',
        license='LoCoMo upstream; provenance retained in source manifest'))
    write(output/'settings.json', settings.model_dump(mode='json'))
    write(output/'plan.json', dict(dataset_id=result.dataset_id, sources=identities, policy=POLICY,
        status='prepared_not_authorized', scope='extract only; no index/relation/publish/QA',
        upper_usd='17.8136064', request_bound='68 fragments * 3 attempts = 204',
        settings_sha256=sha(output/'settings.json'),
        implementation_sha256={name: sha(ROOT/name) for name in (
            'tools/m5/holdout_extraction.py', 'src/locomo_memory/model.py',
            'src/locomo_memory/m5_budget.py', 'src/locomo_memory/builds.py',
            'src/locomo_memory/memory_schemas.py')},
        authorization_required=True, code_stage='M5 extraction-only proposal'))
    # Create the immutable zero-use ledger now; preparation never opens a network transport.
    guard = BudgetTransport(output/'physical-requests.sqlite3', httpx.MockTransport(
        lambda request: (_ for _ in ()).throw(RuntimeError('prepare_has_no_provider'))), **POLICY)
    guard.close()
    print(json.dumps(dict(status='prepared_not_authorized', output=str(output), provider_requests=0,
                          max_requests=204, max_usd='18', upper_usd='17.8136064')))


def execute(output):
    plan = json.loads((output/'plan.json').read_text())
    if plan['policy'] != POLICY or plan['status'] != 'prepared_not_authorized':
        raise ValueError('plan_not_executable')
    if (sha(output/'settings.json') != plan['settings_sha256'] or
            any(sha(ROOT/name) != digest for name, digest in plan['implementation_sha256'].items())):
        raise ValueError('prepared_implementation_changed')
    # One invocation only; failed/unknown requests require a new explicit recovery decision.
    write(output/'execution-started.json', dict(scope=plan['scope'], max_requests=204))
    settings = Settings.model_validate_json((output/'settings.json').read_text())
    if settings.db_path.resolve() != output/'memory.sqlite3':
        raise ValueError('database_scope_changed')
    with httpx.HTTPTransport(retries=0) as delegate:
        model = DeepSeekModel(settings, transport=BudgetTransport(
            output/'physical-requests.sqlite3', delegate, **POLICY))
        builds = BuildService(Database(settings.db_path), settings, model)
        outcomes = {}
        for conv in HOLDOUT:
            build = builds.start(plan['dataset_id'], conv)
            builds.run(build['build_id'])
            result = builds.get(build['build_id'])
            outcomes[conv] = {k: result[k] for k in ('build_id', 'status', 'phase', 'progress')}
        write(output/'extraction-outcomes.json', outcomes)
    print(json.dumps(dict(scope='extract only', outcomes=outcomes, complete_builds=False)))
    if any(result['status'] != 'extracted' for result in outcomes.values()):
        raise RuntimeError('extraction_incomplete_explicit_recovery_required')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--execute-authorized', action='store_true',
                        help='Only after user approval of this exact 18 USD / 204 request stage')
    args = parser.parse_args()
    output = args.output.resolve()
    execute(output) if args.execute_authorized else prepare(output)
