"""Prepare an isolated, explicitly authorized conv-43 relation phase only."""
import argparse
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import sqlite3

import httpx

from locomo_memory.builds import BuildService
from locomo_memory.config import Settings
from locomo_memory.database import Database, backend_ownership
from locomo_memory.m5_budget import BudgetTransport
from locomo_memory.model import DeepSeekModel
from locomo_memory.relations import RelationService
from tools.m5.extraction_recovery import snapshot
from tools.m5.offline import ROOT, sha, write

SCOPE = 'conv-43 existing indexed Build relation phase only; no conv-44/rebuild/publish/query/QA'
BASE_POLICY = dict(model='deepseek-flash', input_usd_per_million='0.30',
    output_usd_per_million='1.20', max_input_bytes=160000, max_output_tokens=32768)


class NoProvider:
    def generate(self, *args, **kwargs):
        raise AssertionError('preparation_must_not_call_provider')


def producer_hashes():
    # Include all local production modules: transitive validation helpers matter.
    paths = [*sorted((ROOT/'src/locomo_memory').glob('*.py')),
             ROOT/'tools/m5/extraction_recovery.py', ROOT/'tools/m5/offline.py']
    return {str(p.relative_to(ROOT)): sha(p) for p in paths}


def task_rows(database, bid):
    with database.connect() as db:
        return [dict(r) for r in db.execute(
            'SELECT task_id,ordinal,new_memory_id,history_ids_json FROM relation_tasks WHERE build_id=? ORDER BY ordinal', (bid,))]


def task_sha(tasks):
    return hashlib.sha256(json.dumps(tasks, sort_keys=True).encode()).hexdigest()


def policy_for(tasks, settings):
    if (settings.model_name != BASE_POLICY['model'] or settings.model_retries != 2
            or settings.relation_thinking_effort != 'high'
            or (settings.relation_max_tokens or settings.model_max_tokens) != 32768):
        raise ValueError('relation_settings_outside_proposal')
    requests = tasks*(settings.model_retries+1)
    maximum = (Decimal(BASE_POLICY['max_input_bytes'])*Decimal('0.30') +
               Decimal(BASE_POLICY['max_output_tokens'])*Decimal('1.20'))/Decimal(1000000)*requests
    return dict(BASE_POLICY, max_requests=requests, max_usd=str(maximum))


def authorization(output):
    plan = json.loads((output/'plan.json').read_text())
    return dict(approved=True, scope=SCOPE, build_id=plan['build_id'],
        policy=plan['policy'], plan_sha256=sha(output/'plan.json'))


def prepare(index_stage, output):
    index_stage, output = index_stage.resolve(), output.resolve()
    source = index_stage/'memory.sqlite3'
    before = snapshot(source)
    settings = Settings.model_validate_json((index_stage/'settings.json').read_text())
    policy_for(0, settings)
    output.mkdir(parents=True, exist_ok=False)
    output.chmod(0o700)
    target = output/'memory.sqlite3'
    with sqlite3.connect(source.as_uri()+'?mode=ro', uri=True) as src, sqlite3.connect(target) as dst:
        src.backup(dst)
    target.chmod(0o600)
    # Preserve db_path in the producer contract; storage is explicitly routed.
    write(output/'settings.json', settings.snapshot())
    builds = BuildService(Database(target), settings, NoProvider())
    with builds.database.connect() as db:
        states = db.execute('SELECT build_id,sample_id,status FROM build_versions ORDER BY sample_id').fetchall()
    if len(states) != 2 or tuple(states[0])[1:] != ('conv-43', 'indexed') or tuple(states[1])[1:] != ('conv-44', 'failed'):
        raise ValueError('relation_build_scope_changed')
    bid = states[0]['build_id']
    relations = RelationService(builds, NoProvider())
    progress = relations.start(bid)  # Prepare tasks; do not invoke the model.
    tasks = task_rows(builds.database, bid)
    policy = policy_for(len(tasks), settings)
    BudgetTransport(output/'physical-requests.sqlite3', None, **policy)
    if snapshot(source) != before:
        raise ValueError('source_index_changed_during_preparation')
    plan = dict(status='prepared_not_authorized', scope=SCOPE, build_id=bid,
        policy=policy, relation_tasks=len(tasks), comparisons=sum(len(json.loads(t['history_ids_json'])) for t in tasks),
        tasks_sha256=task_sha(tasks), relation_thinking_effort='high', attempts_per_task=settings.model_retries+1,
        price_basis='2026-11-04 DeepSeek peak cache-miss input .30/output 1.20 USD per million; recheck before live execution',
        source_index_stage=str(index_stage), source_index_snapshot=before,
        prepared_database_snapshot=snapshot(target), ledger_snapshot=snapshot(output/'physical-requests.sqlite3'),
        settings_sha256=sha(output/'settings.json'), implementation_sha256=producer_hashes(),
        script_sha256=sha(Path(__file__)), provider_requests=0, holdout_qa_read=False,
        progress=progress, automatic_recovery=False)
    write(output/'plan.json', plan)
    return plan


def execute(output, delegate=None):
    """A matching file records prior explicit user approval; never infers approval."""
    output = output.resolve()
    if (output/'execution-started.json').exists():
        raise FileExistsError('relation_stage_already_started')
    plan = json.loads((output/'plan.json').read_text())
    if json.loads((output/'authorization.json').read_text()) != authorization(output):
        raise ValueError('relation_authorization_mismatch')
    settings = Settings.model_validate_json((output/'settings.json').read_text())
    if (plan['status'] != 'prepared_not_authorized' or plan['scope'] != SCOPE
            or plan['policy'] != policy_for(plan['relation_tasks'], settings)
            or plan['settings_sha256'] != sha(output/'settings.json')
            or plan['implementation_sha256'] != producer_hashes()
            or plan['script_sha256'] != sha(Path(__file__))):
        raise ValueError('relation_plan_changed')
    target = output/'memory.sqlite3'
    with backend_ownership(target):
        if (snapshot(target) != plan['prepared_database_snapshot']
                or snapshot(output/'physical-requests.sqlite3') != plan['ledger_snapshot']):
            raise ValueError('relation_stage_snapshot_changed')
        builds = BuildService(Database(target), settings, NoProvider())
        build = builds.get(plan['build_id'])
        builds.require_current_contract(build)
        tasks = task_rows(builds.database, plan['build_id'])
        if (build['sample_id'] != 'conv-43' or build['status'] != 'queued' or build['phase'] != 'relations'
                or len(tasks) != plan['relation_tasks'] or task_sha(tasks) != plan['tasks_sha256']):
            raise ValueError('relation_task_scope_changed')
        write(output/'execution-started.json', dict(scope=SCOPE, plan_sha256=sha(output/'plan.json')))
        owns_delegate = delegate is None
        delegate = httpx.HTTPTransport(retries=0) if owns_delegate else delegate
        try:
            guard = BudgetTransport(output/'physical-requests.sqlite3', delegate, **plan['policy'])
            model = DeepSeekModel(settings, transport=guard)
            service = RelationService(builds, model)
            service.run(plan['build_id'])
            outcome = dict(scope=SCOPE, progress=service.progress(plan['build_id']),
                status=builds.get(plan['build_id'])['status'], published=False,
                holdout_qa_read=False, automatic_recovery=False)
            write(output/'outcome.json', outcome)
        finally:
            if owns_delegate:
                delegate.close()
    if outcome['status'] != 'related':
        raise RuntimeError('relation_stage_incomplete_no_automatic_retry')
    return outcome


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--index-stage', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--execute-authorized', action='store_true')
    args = parser.parse_args()
    if args.execute_authorized:
        result = execute(args.output)
    elif args.index_stage is not None:
        result = prepare(args.index_stage, args.output)
    else:
        parser.error('--index-stage is required for preparation')
    print(json.dumps(result))
