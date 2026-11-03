"""One-shot authorized Issue #20 smoke. Never resumes a prior experiment."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
import xml.etree.ElementTree as ET

import httpx
from fastapi.testclient import TestClient

from locomo_memory.api import create_app
from locomo_memory.config import Settings
from locomo_memory.embeddings import MiniLMEmbedder
from locomo_memory.experiment import Experiment, ExperimentError, write_json
from locomo_memory.implementation_identity import implementation_sha256
from tools.research_v2.observer import Ledger, ObservedDeepSeekModel, Halt, sha
from tools.research_v2.prepare import prepare, ROOT, digest

BASE = 'bf820d45b603bad43fdd66c7aa762ffcf2a7fea9'


def code_identity():
    files = [ROOT / 'pyproject.toml', ROOT / 'uv.lock']
    files += sorted((ROOT / 'tools/research_v2').glob('*.py'))
    files += sorted((ROOT / 'src/locomo_memory').glob('*.py'))
    return {str(p.relative_to(ROOT)): digest(p) for p in files}


def freeze(directory, tests, *, max_tokens=8192, official_directory=None, retry_parent=None):
    os.umask(0o077)
    directory = directory.resolve()
    directory.mkdir(parents=True, mode=0o700, exist_ok=True)
    if directory.stat().st_mode & 0o077:
        raise Halt('private_directory_required')
    if (directory / 'execution-identity.json').exists() or (directory / 'observer/budget.sqlite3').exists():
        raise Halt('already_frozen')
    base_check = subprocess.run(['git', 'merge-base', '--is-ancestor', BASE, 'HEAD'], cwd=ROOT)
    if base_check.returncode:
        raise Halt('wrong_research_base')
    tree = ET.parse(tests).getroot()
    suites = [tree] if tree.tag == 'testsuite' else list(tree.iter('testsuite'))
    if not suites or any(int(s.get('failures', '0')) or int(s.get('errors', '0')) or int(s.get('skipped', '0')) for s in suites):
        raise Halt('offline_tests_required')
    names = {c.get('name') for c in tree.iter('testcase')}
    if not {'test_watchdog_kills_trickling_or_blocked_worker', 'test_adapter_retry_each_physical_attempt_is_counted',
            'test_unknown_transport_failure_never_becomes_internal_retry', 'test_runner_limits_and_manifest'}.issubset(names):
        raise Halt('required_test_cases_missing')
    record = prepare(directory, verify_embedding=True)
    sources = {}
    for name in ('smoke-pricing', 'smoke-chat', 'smoke-cache'):
        p = (official_directory or ROOT / '.firecrawl') / (name + '.md')
        if not p.is_file():
            raise Halt('official_contract_missing')
        target = directory / (name + '.md')
        target.write_bytes(p.read_bytes())
        sources[name] = {'path': str(target), 'sha256': digest(target)}
    pricing = (directory / 'smoke-pricing.md').read_text()
    if not all(term in pricing for term in ('DeepSeek-V4.1-Flash-1017', '0.04元', '2元', '8元', '1M')):
        raise Halt('pricing_contract_changed')
    identity = dict(status='frozen_before_paid_calls', research_base=BASE,
                    git_head=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                    frozen_at=time.time(), code_files=code_identity(), implementation_sha256=implementation_sha256(),
                    config=Settings(db_path=directory / 'memory.sqlite3', model_max_tokens=max_tokens).snapshot(),
                    plans=record['plan_file_sha256'], source_identity=record['source_identity'],
                    tests={'path': str(tests.resolve()), 'sha256': digest(tests), 'test_cases': len(names)},
                    official_sources=sources, model='deepseek-flash', response_format='json_object',
                    generation_parameters='Unchanged production Settings; per-stage thinking and max_tokens in config.',
                    transport='httpx.HTTPTransport(retries=0,trust_env=False); observed physical HTTP, non-streaming',
                    allowed_scope={'probe':'existing three-turn synthetic extraction only', 'builds':['conv-26'],
                                   'qa_indices':[0,2,3,82,152],
                                   'strategies':['full_text','vector','hybrid_no_resolution','dynamic'],
                                   'logical_combinations':20},
                    authorization={'currency':'CNY','max_cny':40,'max_physical_http':500,
                                   'max_seconds':14400,'max_concurrency':1,'source':'Explicit user approval in this chat',
                                   'manual_retries':False,'full_baseline':False},
                    accounting='Peak-rate upper cost; unknown keeps reservation and halts. No invoice claim.')
    write_json(directory / 'execution-identity.json', identity)
    if retry_parent is not None:
        identity.update(retry_parent=str(retry_parent.resolve()),
                        retry_parent_outcome_sha256=digest(retry_parent / 'execution-outcome.json'),
                        generation_parameters='Research-only model_max_tokens=32768 (four times 8192); all other production parameters unchanged.',
                        retry_authorization='Explicit subsequent user instruction: quadruple output tokens and retry; original cumulative limits and deadline retained.')
        identity['authorization']['manual_retries'] = 'one newly identified Build only; not an unbounded resume'
        write_json(directory / 'execution-identity.json', identity)
    return identity


def verify_frozen(directory):
    path = directory / 'execution-identity.json'
    identity = json.loads(path.read_text())
    if identity['code_files'] != code_identity() or identity['implementation_sha256'] != implementation_sha256():
        raise Halt('execution_identity_changed')
    maximum = identity['config'].get('model_max_tokens', 8192)
    if maximum not in (8192, 32768) or identity['config'] != Settings(db_path=directory / 'memory.sqlite3', model_max_tokens=maximum).snapshot():
        raise Halt('configuration_changed')
    for scope, expected in identity['plans'].items():
        if digest(directory / f'plan-{scope}.json') != expected:
            raise Halt('plan_changed')
    for source in [identity['tests'], *identity['official_sources'].values()]:
        if digest(Path(source['path'])) != source['sha256']:
            raise Halt('gate_evidence_changed')
    return identity


class ObservedMiniLM(MiniLMEmbedder):
    def __init__(self, settings, ledger):
        super().__init__(settings)
        self.ledger = ledger

    def encode(self, texts):
        import uuid
        identifier, started = uuid.uuid4().hex, time.perf_counter()
        self.ledger.assert_available()
        self.ledger.event('embedding_started', dict(embedding_id=identifier, texts=len(texts),
                          input_sha256=sha(json.dumps(texts).encode()), **getattr(self.ledger, 'global_tags', {})))
        status = 'failed'
        try:
            result = super().encode(texts)
            status = 'succeeded'
            return result
        finally:
            self.ledger.event('embedding_finished', dict(embedding_id=identifier, texts=len(texts), status=status,
                              elapsed_seconds=time.perf_counter()-started, external_api_cny=0))


def instrument(app, ledger):
    extract = app.state.builds._extract_fragment
    def extract_fragment(build_id, fragment):
        with ledger.scope(build_id=build_id, fragment_id=fragment['fragment_id']):
            return extract(build_id, fragment)
    app.state.builds._extract_fragment = extract_fragment
    judge = app.state.relations._judge
    def judge_task(build_id, task):
        with ledger.scope(build_id=build_id, task_id=task['task_id']):
            result = judge(build_id, task)
            # A failed task cannot be repaired in this one-shot execution. Stop new sends.
            with app.state.database.connect() as db:
                failed = db.execute("SELECT status FROM relation_tasks WHERE task_id=?", (task['task_id'],)).fetchone()[0] == 'failed'
            if failed and not getattr(ledger, 'relation_failure_stopped', False):
                ledger.event('halt', {'code':'irrecoverable_relation_failure', 'task_id':task['task_id']})
                ledger.relation_failure_stopped = True
            return result
    app.state.relations._judge = judge_task
    execute = app.state.evaluation.execute_item
    def execute_item(inputs, index, sample, strategy, build_id, evidence_profile='expanded'):
        question = inputs['question_identities'][index]
        if sample['sample_id'] != 'conv-26' or question['qa_index'] not in [0,2,3,82,152] or strategy not in ['full_text','vector','hybrid_no_resolution','dynamic']:
            raise Halt('question_out_of_scope')
        with app.state.database.connect() as db:
            runs = db.execute("SELECT run_id FROM evaluation_runs WHERE json_extract(result_json,'$.status')='running'").fetchall()
        if len(runs) != 1:
            raise Halt('run_identity_ambiguous')
        with ledger.scope(run_id=runs[0][0], build_id=build_id, question_id=question['question_id'],
                          qa_index=question['qa_index'], strategy=strategy, sample_id=sample['sample_id']):
            return execute(inputs, index, sample, strategy, build_id, evidence_profile)
    app.state.evaluation.execute_item = execute_item


def execute(directory):
    os.umask(0o077)
    directory = directory.resolve()
    identity = verify_frozen(directory)
    # Before application startup/recovery: never adopt or rerun a started experiment.
    state = json.loads((directory / 'experiment.json').read_text())
    if state.get('builds') or state.get('probe') or state.get('pending_initiation') or state.get('smoke_run_id'):
        raise Halt('started_experiment_requires_external_review')
    if not os.environ.get('DEEPSEEK_API_KEY'):
        raise Halt('missing_credentials')
    ledger = Ledger(directory / 'observer')
    parent = None
    pool = httpx.HTTPTransport(retries=0, trust_env=False)
    outcome = dict(status='starting', build_id=None, run_id=None, planned=20, full_experiment_started=False)
    try:
        if identity.get('retry_parent'):
            from tools.research_v2.retry import claim_parent
            parent, inherited = claim_parent(identity, directory)
        else:
            inherited = {}
        policy = ledger.arm({'execution_identity_sha256':digest(directory / 'execution-identity.json')},
                            max_tokens=identity['config']['model_max_tokens'], **inherited)
        ledger.watchdog()
        settings = Settings.model_validate(identity['config'])
        model = ObservedDeepSeekModel(settings, ledger, pool)
        embedder = ObservedMiniLM(settings, ledger)
        app = create_app(settings, model=model, embedder=embedder)
        instrument(app, ledger)
        with TestClient(app) as client:
            experiment = Experiment(client, directory)
            current = experiment.preflight()
            # This adapter is intentionally reported as observed, never disguised as an unwrapped production adapter.
            write_json(directory / 'observed-provider-origin.json', dict(real_provider=True,
                adapter=type(model).__name__, underlying_transport=type(pool).__name__, mock_transport=False,
                credentials_in_artifacts=False, production_prompts_unchanged=True))
            try:
                ledger.global_tags = {'scope':'probe'}
                ledger.event('phase_started', {'phase':'probe'})
                experiment.probe(current)
                if experiment.state['probe']['status'] != 'passed':
                    raise Halt('probe_incomplete')
                ledger.event('phase_finished', {'phase':'probe'})
                ledger.global_tags = {'scope':'conv-26-build'}
                ledger.event('phase_started', {'phase':'conv-26-build'})
                for _ in range(3):
                    if experiment.advance_build('conv-26'):
                        break
                    ledger.assert_available()
                else:
                    raise Halt('build_incomplete')
                outcome['build_id'] = experiment.state['builds']['conv-26']
                ledger.event('phase_finished', {'phase':'conv-26-build'})
                ledger.global_tags = {'scope':'smoke'}
                ledger.event('phase_started', {'phase':'smoke'})
                run = experiment.request('POST', '/evaluation-runs', json={
                    'plan_id':experiment.state['plans']['smoke'],
                    'build_ids':{'conv-26':outcome['build_id']}, 'wait':True})
                outcome['run_id'] = run['run_id']
                experiment.state['smoke_run_id'] = run['run_id']
                experiment.state['run_origins'] = {run['run_id']:{'real_provider':True,
                    'real_embedding':True, 'observer_identity_sha256':digest(directory / 'execution-identity.json')}}
                experiment.state['live_smoke'] = run['status']
                experiment.save()
                experiment.export('smoke')
                outcome.update(status=run['status'], progress=run['progress'], metrics=run.get('summary'))
                # Existing structure/evidence/source/identity checks still apply. Its final adapter-name gate
                # returns False for this explicitly observed adapter; own origin is separately frozen above.
                if run['status'] == 'completed':
                    experiment.inspect_smoke(run, current)
                    outcome['structural_acceptance'] = 'passed; observed real transport origin recorded separately'
                else:
                    outcome['structural_acceptance'] = 'not_passed'
                ledger.event('phase_finished', {'phase':'smoke'})
            except Exception as error:
                outcome.update(status='stopped', error_code=error.code if isinstance(error,(ModelFailureAlias, ExperimentError)) else type(error).__name__)
            finally:
                # Offline snapshots through read-only API calls, before application shutdown.
                for sid, bid in experiment.state.get('builds', {}).items():
                    experiment.snapshot_build(bid)
                    outcome['build_id'] = bid
                if experiment.state.get('probe'):
                    write_json(directory/'probe-build.json', experiment.request('GET','/builds/'+experiment.state['probe']['build_id']))
                experiment.state['research_smoke_outcome'] = outcome
                experiment.save()
        outcome['physical_requests'] = len(ledger.rows())
        outcome['known_peak_upper_cny'] = sum(r['cost_nano_cny'] or 0 for r in ledger.rows()) / 1e9
        outcome['unknown_requests'] = sum(r['status']!='settled' for r in ledger.rows())
        outcome['elapsed_seconds'] = time.time() - policy['started']
        outcome['prior_physical_requests'] = policy.get('prior_requests', 0)
        outcome['prior_peak_upper_cny'] = policy.get('prior_cost_nano_cny', 0) / 1e9
        outcome['cumulative_physical_requests'] = outcome['physical_requests'] + outcome['prior_physical_requests']
        outcome['cumulative_peak_upper_cny'] = outcome['known_peak_upper_cny'] + outcome['prior_peak_upper_cny']
        write_json(directory/'execution-outcome.json', outcome)
        return outcome
    finally:
        pool.close()
        ledger.close()
        if parent is not None:
            parent.close()


# Keep safe error reporting independent from provider exception text.
from locomo_memory.model import ModelFailure as ModelFailureAlias

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['freeze','execute-approved-smoke'])
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--tests', type=Path, default=ROOT/'experiments/research-v2/observer-tests.xml')
    parser.add_argument('--retry-parent', type=Path, help='Explicit authorized 32768-token retry; inherits parent cumulative limits')
    args = parser.parse_args()
    try:
        if args.command == 'freeze':
            record = freeze(args.directory, args.tests, max_tokens=32768 if args.retry_parent else 8192,
                            official_directory=args.retry_parent, retry_parent=args.retry_parent)
        else:
            record = execute(args.directory)
        print(json.dumps({k:v for k,v in record.items() if k in ('status','physical_requests','known_peak_upper_cny','unknown_requests','elapsed_seconds','build_id','run_id','error_code')},indent=2))
    except (Halt, ExperimentError) as error:
        print(json.dumps({'status':'blocked','code':error.code}))
        raise SystemExit(2)
