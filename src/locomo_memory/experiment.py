"""Finite local experiment commands using the application's public HTTP API."""
import argparse
from contextlib import nullcontext
from datetime import date
import json
from pathlib import Path
import sys
import time
from urllib.parse import urlsplit

import httpx

from .model import utc_now
from .experiment_report import render_report


class ExperimentError(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    temporary.replace(path)


class Experiment:
    def __init__(self, client, directory):
        self.client = client
        self.directory = directory.resolve()
        self.state_path = self.directory / 'experiment.json'
        self.state = json.loads(self.state_path.read_text()) if self.state_path.exists() else {'created_at': utc_now(), 'status': 'unprepared', 'blockers': [], 'builds': {}, 'live_smoke': 'not_run', 'full_baseline': 'not_run'}

    def request(self, method, path, **kwargs):
        initiating = method == 'POST' and path in {'/builds', '/evaluation-runs'}
        if initiating:
            body = kwargs.get('json', {})
            for receipt in self.state.get('initiation_receipts', []):
                if receipt['path'] == path and receipt['request'] == body:
                    return self.request('GET', path + '/' + receipt['resource_id'])
            if self.state.get('pending_initiation'):
                raise ExperimentError('initiation_outcome_unknown')
            self.state['pending_initiation'] = {'path': path, 'request': body, 'requested_at': utc_now(), 'status': 'unknown_until_identity_saved'}
            self.save()
        started_at, tick = utc_now(), time.perf_counter()
        try:
            response = self.client.request(method, path, **kwargs)
        except httpx.HTTPError:
            raise ExperimentError('initiation_outcome_unknown' if initiating else 'backend_unavailable') from None
        if method == 'POST':
            self.state.setdefault('phase_invocations', []).append({'path': path, 'requested_at': started_at, 'response_observed_at': utc_now(), 'http_elapsed_seconds': time.perf_counter() - tick, 'elapsed_scope': 'HTTP round-trip only; background processing can continue after response', 'http_status': response.status_code})
            self.save()
        if initiating:
            if response.status_code >= 500:
                raise ExperimentError('initiation_outcome_unknown')
            if not response.is_error:
                resource_id = response.json()['build_id' if path == '/builds' else 'run_id']
                self.state.setdefault('initiation_receipts', []).append({'path': path, 'request': body, 'resource_id': resource_id, 'observed_at': utc_now()})
            self.state.pop('pending_initiation', None)
            self.save()
        if response.is_error:
            try:
                code = response.json()['error']['code']
            except (ValueError, KeyError, TypeError):
                code = 'backend_request_failed'
            raise ExperimentError(code)
        return response.json()

    def save(self):
        self.state['updated_at'] = utc_now()
        self.state['directory'] = str(self.directory)
        write_json(self.state_path, self.state)

    def preflight(self, verify_embedding=False):
        record = self.request('GET', '/experiment-preflight', params={'verify_embedding': verify_embedding})
        if Path(record['database_path']).resolve() != self.directory / 'memory.sqlite3':
            raise ExperimentError('experiment_database_mismatch')
        write_json(self.directory / 'preflight.json', record)
        return record

    def contract(self, path=None):
        target = self.directory / 'model-contract.json'
        if path is None and not target.exists():
            raise ExperimentError('service_contract_not_recorded')
        record = json.loads((path or target).read_text())
        fields = ('checked_date', 'source_url', 'model_name', 'known_service_version', 'context_window_tokens', 'thinking_enabled', 'response_format', 'verification_scope', 'limitations')
        if (set(record) != set(fields) or record['source_url'] != 'https://api-docs.deepseek.com/quick_start/pricing'
                or record['model_name'] != 'deepseek-flash' or record['thinking_enabled'] is not False
                or record['response_format'] != 'json_object' or record['context_window_tokens'] != 1000000
                or record['known_service_version'] != 'DeepSeek-V4.1-Flash-1017'):
            raise ExperimentError('invalid_service_contract_record')
        date.fromisoformat(record['checked_date'])
        write_json(target, record)
        return record

    def verify(self):
        record = self.preflight(verify_embedding=True)
        write_json(self.directory / 'verified-preflight.json', record)
        if record['embedding']['status'] != 'verified':
            raise ExperimentError('embedding_verification_failed')
        self.state['embedding_verification'] = record['embedding']
        if record['embedding']['real_adapter']:
            self.state['blockers'] = [b for b in self.state.get('blockers', []) if b != 'real_embedding_not_verified']
        self.save()
        return record

    def require_live_prerequisites(self):
        record = self.preflight()
        if not record['credential_present']:
            raise ExperimentError('missing_credentials')
        return record

    def probe(self, preflight):
        probe = self.state.get('probe')
        if not probe:
            # Tiny raw-only check, using exactly the normal import/build APIs.
            data = [{'sample_id': 'live-probe', 'conversation': {
                'speaker_a': 'Alex', 'speaker_b': 'Sam',
                'session_1_date_time': '1:00 pm on 1 May, 2023',
                'session_1': [{'dia_id': 'D1:1', 'speaker': 'Alex', 'text': 'I live in Paris.'},
                              {'dia_id': 'D1:2', 'speaker': 'Sam', 'text': 'I work in London.'}],
                'session_2_date_time': '1:00 pm on 2 May, 2023',
                'session_2': [{'dia_id': 'D2:1', 'speaker': 'Alex', 'text': 'I moved to Rome.'}],
            }}]
            imported = self.request('POST', '/imports', json={'data': data, 'version': 'live-probe-v1', 'license': 'synthetic-check-only'})
            build = self.request('POST', '/builds', json={'dataset_id': imported['dataset_id'], 'sample_id': 'live-probe'})
            probe = {'dataset_id': imported['dataset_id'], 'artifact_sha256': imported['artifact_sha256'], 'build_id': build['build_id'], 'status': 'running', 'real_provider': not preflight['generation']['controlled_transport'] and preflight['generation']['adapter'] == 'DeepSeekModel', 'implementation_sha256': preflight['implementation_sha256'], 'config': preflight['config']}
            self.state['probe'] = probe
            self.save()
        if probe.get('implementation_sha256') != preflight['implementation_sha256'] or probe.get('config') != preflight['config']:
            raise ExperimentError('probe_execution_identity_changed')
        build = self.request('GET', '/builds/' + probe['build_id'])
        write_json(self.directory / 'probe-build.json', build)
        if build['status'] in {'failed', 'interrupted'}:
            probe.update(status=build['status'])
            self.save()
            raise ExperimentError('live_extraction_probe_failed')
        if build['status'] != 'extracted':
            self.state['status'] = 'probe_running'
            self.save()
            return self.state
        memories = self.request('GET', f"/builds/{probe['build_id']}/memories", params={'limit': 100})
        if not memories['items'] or memories['total'] > len(memories['items']):
            raise ExperimentError('live_extraction_probe_invalid')
        sources = set()
        for memory in memories['items']:
            for source_id in memory['source_ids']:
                dataset_id, sample_id, dia_id = source_id.split('/')
                self.request('GET', f'/datasets/{dataset_id}/conversations/{sample_id}/turns/{dia_id}')
                sources.add(source_id)
        returned = build['model_metadata']['returned_models']
        if not returned:
            raise ExperimentError('returned_model_identity_missing')
        probe.update(status='passed', checked_at=utc_now(), returned_models=returned,
                     source_references_checked=len(sources))
        if probe['real_provider']:
            self.state['blockers'] = [b for b in self.state.get('blockers', []) if b != 'live_extraction_not_run']
        self.state['status'] = 'probe_passed' if probe['real_provider'] else 'controlled_probe_passed'
        self.save()
        return self.state

    def page(self, path):
        items, offset = [], 0
        while True:
            page = self.request('GET', path, params={'limit': 100, 'offset': offset})
            items.extend(page['items'])
            offset += len(page['items'])
            if offset >= page['total'] or not page['items']:
                return items

    def snapshot_build(self, build_id):
        build = self.request('GET', f'/builds/{build_id}')
        observations = self.state.setdefault('build_observations', {}).setdefault(build_id, [])
        observation = {'observed_at': utc_now(), 'phase': build['phase'], 'status': build['status'], 'progress': build['progress'], 'elapsed_scope': 'Observation timestamps include time between operator commands; not pure processing time'}
        if not observations or any(observations[-1][k] != observation[k] for k in ('phase', 'status', 'progress')):
            observations.append(observation)
            self.save()
        target = self.directory / 'builds' / build_id
        write_json(target / 'build.json', build)
        write_json(target / 'fragments.json', self.page(f'/builds/{build_id}/fragments'))
        if build['phase'] in {'relations', 'complete'}:
            write_json(target / 'relation-tasks.json', self.page(f'/builds/{build_id}/relation-tasks'))
        if build['status'] == 'complete':
            write_json(target / 'export.json', self.request('GET', f'/builds/{build_id}/export'))
        return build

    def advance_build(self, sample_id):
        if sample_id not in {'conv-26', 'conv-30', 'conv-41', 'conv-42'}:
            raise ExperimentError('development_conversation_required')
        build_id = self.state['builds'].get(sample_id)
        if build_id is None:
            build = self.request('POST', '/builds', json={'dataset_id': self.state['imported']['dataset_id'], 'sample_id': sample_id})
            build_id = build['build_id']
            self.state['builds'][sample_id] = build_id
            self.save()
        # Each call advances at most the existing extraction/index/relation/publication phases.
        for _ in range(4):
            build = self.snapshot_build(build_id)
            if build['status'] == 'complete':
                return True
            if build['status'] in {'failed', 'interrupted', 'index_failed', 'relations_failed'}:
                self.state['status'] = f"build_{sample_id}_{build['phase']}_{build['status']}"
                self.save()
                raise ExperimentError('build_failed_explicit_resume_required')
            if build['status'] == 'extracted':
                self.request('POST', f'/builds/{build_id}/index')
            elif build['status'] == 'indexed':
                self.request('POST', f'/builds/{build_id}/relations')
            elif build['status'] == 'related':
                self.request('POST', f'/builds/{build_id}/publish')
            else:
                self.state['status'] = f"build_{sample_id}_{build['phase']}_running"
                self.save()
                return False
        return False

    def inspect_smoke(self, run, current):
        plan = self.request('GET', '/evaluation-plans/' + self.state['plans']['smoke'])
        if (run['plan_id'] != plan['plan_id'] or run['status'] != 'completed'
                or run['progress']['total'] != 20 or run['progress']['succeeded'] != 20
                or run['pins'] != {'conv-26': self.state['builds']['conv-26']}
                or run['strategies'] != plan['strategies']):
            raise ExperimentError('successful_live_smoke_required')
        expected = {(q['question_id'], strategy) for q in plan['questions'] for strategy in plan['strategies']}
        if {(i['question_id'], i['strategy']) for i in run['items']} != expected:
            raise ExperimentError('smoke_plan_identity_changed')
        source_ids = [s['source_id'] for s in self.page(f"/datasets/{plan['dataset_id']}/conversations/conv-26/turns")]
        for item in run['items']:
            trace = item['result']['trace']
            if item['strategy'] == 'full_text':
                delivery = trace.get('source_delivery', {})
                if any(delivery.get(key) != source_ids for key in ('expected_source_ids', 'attempted_source_ids', 'delivered_source_ids')) or not delivery.get('provider_accepted'):
                    raise ExperimentError('smoke_full_text_delivery_incomplete')
                if any(c['memory_id'] is not None or not set(c['source_ids']) <= set(source_ids) for c in trace['answer']['citations']):
                    raise ExperimentError('smoke_source_citation_invalid')
        if run['config'] != current['config'] or run['implementation_sha256'] != current['implementation_sha256']:
            raise ExperimentError('smoke_execution_identity_changed')
        if run['input'].get('source_identity', {}).get('artifact_sha256') != self.state['imported']['artifact_sha256']:
            raise ExperimentError('smoke_source_identity_changed')
        origin = self.state.get('run_origins', {}).get(run['run_id'], {})
        return (origin.get('real_provider') is True and origin.get('real_embedding') is True
                and not current['generation']['controlled_transport'] and current['generation']['adapter'] == 'DeepSeekModel'
                and current['embedding']['real_adapter'] and self.state.get('probe', {}).get('real_provider') is True)

    def require_successful_smoke(self, current):
        run_id = self.state.get('smoke_run_id')
        if not run_id:
            raise ExperimentError('successful_live_smoke_required')
        run = self.request('GET', '/evaluation-runs/' + run_id)
        if not self.inspect_smoke(run, current):
            raise ExperimentError('successful_live_smoke_required')
        return run

    def evaluate(self, scope, current):
        if not self.state.get('plans'):
            raise ExperimentError('offline_preparation_required')
        if scope == 'development':
            self.require_successful_smoke(current)
        elif self.state.get('probe', {}).get('status') != 'passed':
            return self.probe(current)
        conversations = ['conv-26'] if scope == 'smoke' else ['conv-26', 'conv-30', 'conv-41', 'conv-42']
        for sample_id in conversations:
            if not self.advance_build(sample_id):
                return self.state
        field = 'smoke_run_id' if scope == 'smoke' else 'development_run_id'
        run_id = self.state.get(field)
        if run_id is None:
            run = self.request('POST', '/evaluation-runs', json={'plan_id': self.state['plans'][scope], 'build_ids': {sid: self.state['builds'][sid] for sid in conversations}})
            run_id = run['run_id']
            self.state[field] = run_id
            self.state.setdefault('run_origins', {})[run_id] = {'real_provider': not current['generation']['controlled_transport'] and current['generation']['adapter'] == 'DeepSeekModel', 'real_embedding': current['embedding']['real_adapter'], 'implementation_sha256': current['implementation_sha256'], 'started_at': utc_now()}
            self.save()
        else:
            run = self.request('GET', '/evaluation-runs/' + run_id)
        self.state['status'] = scope + '_' + run['status']
        self.state['live_smoke' if scope == 'smoke' else 'full_baseline'] = run['status']
        if scope == 'smoke' and run['status'] == 'completed':
            qualified = self.inspect_smoke(run, current)
            self.state['live_smoke'] = 'passed' if qualified else 'controlled_validation_only'
            self.state['status'] = 'smoke_passed' if qualified else 'controlled_smoke_passed'
            if qualified:
                self.state['blockers'] = [b for b in self.state.get('blockers', []) if b != 'live_smoke_not_run']
        elif scope == 'development' and run['status'] == 'completed':
            if run['progress']['total'] != 3028 or run['progress']['succeeded'] != 3028:
                raise ExperimentError('full_development_scope_incomplete')
            self.state['full_baseline'] = 'completed'
        self.save()
        self.export(scope)
        return self.state

    def resume(self, scope, *, retry_failed=False, retry_unknown=False, build_id=None):
        self.preflight()
        if build_id:
            owned = set(self.state['builds'].values()) | {self.state.get('probe', {}).get('build_id')}
            if build_id not in owned:
                raise ExperimentError('experiment_build_not_owned')
            self.request('POST', f'/builds/{build_id}/retry-phase')
            self.snapshot_build(build_id)
            self.state['status'] = 'build_resume_started'
        else:
            field = 'smoke_run_id' if scope == 'smoke' else 'development_run_id'
            run_id = self.state.get(field)
            if not run_id:
                raise ExperimentError('experiment_run_not_started')
            run = self.request('POST', f'/evaluation-runs/{run_id}/resume', json={'retry_failed': retry_failed, 'retry_unknown': retry_unknown})
            self.state['status'] = scope + '_' + run['status']
            self.state['live_smoke' if scope == 'smoke' else 'full_baseline'] = run['status']
        self.save()
        return self.export(scope)

    def status(self, scope):
        self.preflight()
        self.state['last_builds'] = {sid: {key: build[key] for key in ('build_id', 'phase', 'status', 'progress')} for sid, bid in self.state['builds'].items() for build in [self.snapshot_build(bid)]}
        run_id = self.state.get('smoke_run_id' if scope == 'smoke' else 'development_run_id')
        if run_id:
            progress = self.request('GET', f'/evaluation-runs/{run_id}/progress')
            self.state['last_progress'] = progress
            self.save()
        return self.state

    def export(self, scope):
        self.status(scope)
        run_id = self.state.get('smoke_run_id' if scope == 'smoke' else 'development_run_id')
        run = self.request('GET', f'/evaluation-runs/{run_id}') if run_id else None
        if run:
            target = self.directory / 'runs' / run_id
            write_json(target / 'run.json', run)
            write_json(target / 'grouped-summary.json', run.get('grouped_summary', {}))
            failures = []
            for n, item in enumerate(run.get('items', [])):
                result = item.get('result') or {}
                score = result.get('qa', {}).get('value')
                if item['status'] != 'succeeded' or score is not None and score < 1:
                    trace = result.get('trace', {})
                    failures.append({'sample_id': item['sample_id'], 'qa_index': item.get('qa_index'), 'question_id': item.get('question_id'), 'strategy': item['strategy'], 'status': item['status'], 'qa': result.get('qa'), 'source_mapping': result.get('mapping'), 'memory_rankings': result.get('memory_rankings'), 'source_sets': result.get('source_sets'), 'citations': trace.get('answer', {}).get('citations'), 'diagnosis': 'undetermined', 'evidence_pointer': f"run.json#items/{n}"})
            write_json(target / 'failure-cases.json', failures)
            (target / 'report.md').write_text(render_report(self.state, scope, run))
        (self.directory / f'report-{scope}.md').write_text(render_report(self.state, scope, run))
        return self.state

    def prepare(self):
        preflight = self.preflight()
        imported = self.request('POST', '/imports/official')
        plans = {}
        for scope in ('smoke', 'development'):
            plan = self.request('POST', '/evaluation-plans', json={'dataset_id': imported['dataset_id'], 'artifact_sha256': imported['artifact_sha256'], 'scope': scope})
            write_json(self.directory / f'plan-{scope}.json', plan)
            plans[scope] = plan['plan_id']
        prior_status = self.state.get('status')
        self.state.update(status='prepared_offline' if prior_status in {'unprepared', 'prepared_offline'} else prior_status, imported=imported, plans=plans,
                          blockers=([] if preflight['credential_present'] else ['missing_credentials']) + ['real_embedding_not_verified', 'live_extraction_not_run', 'live_smoke_not_run'])
        self.save()
        return self.state


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument('command', choices=['serve', 'prepare', 'probe', 'smoke', 'full', 'status', 'export', 'verify', 'resume'])
    result.add_argument('--directory', type=Path, required=True, help='Experiment-only SQLite and artifact directory')
    result.add_argument('--api-url', default='http://127.0.0.1:8000')
    result.add_argument('--retry-failed', action='store_true')
    result.add_argument('--retry-unknown', action='store_true')
    result.add_argument('--build-id', help='Explicit phase retry for a build owned by this experiment')
    result.add_argument('--scope', choices=['smoke', 'development'], default='smoke')
    result.add_argument('--contract-record', type=Path, help='Dated public service-contract verification JSON')
    result.add_argument('--allow-paid', action='store_true', help='Explicitly allow generation calls for this command')
    result.add_argument('--port', type=int, default=8000)
    return result


def main(argv=None, *, client=None):
    args = parser().parse_args(argv)
    experiment = None
    tick = time.perf_counter()
    try:
        url = urlsplit(args.api_url)
        if url.scheme != 'http' or url.hostname not in {'127.0.0.1', 'localhost', '::1'} or url.username or url.password or url.query or url.fragment or url.path not in ('', '/'):
            raise ExperimentError('local_backend_url_required')
        if args.command == 'serve':
            import uvicorn
            from .api import create_app
            from .config import Settings
            settings = Settings(db_path=args.directory.resolve() / 'memory.sqlite3')
            uvicorn.run(create_app(settings), host='127.0.0.1', port=args.port, access_log=False)
            return 0
        with nullcontext(client) if client is not None else httpx.Client(base_url=args.api_url, timeout=60, follow_redirects=False) as transport:
            experiment = Experiment(transport, args.directory)
            if args.command in {'probe', 'smoke', 'full', 'resume'}:
                if not args.allow_paid:
                    raise ExperimentError('paid_opt_in_required')
                if args.command == 'full' and not experiment.state.get('smoke_run_id'):
                    raise ExperimentError('successful_live_smoke_required')
                if experiment.state.get('pending_initiation'):
                    raise ExperimentError('initiation_outcome_unknown')
                if not experiment.state.get('plans'):
                    raise ExperimentError('offline_preparation_required')
                experiment.require_live_prerequisites()
                experiment.contract(args.contract_record)
                verified = experiment.verify()
                if args.command == 'resume':
                    if args.scope == 'development':
                        experiment.require_successful_smoke(verified)
                    result = experiment.resume(args.scope, retry_failed=args.retry_failed, retry_unknown=args.retry_unknown, build_id=args.build_id)
                elif args.command == 'probe':
                    result = experiment.probe(verified)
                elif args.command == 'smoke':
                    experiment.probe(verified)
                    result = experiment.evaluate('smoke', verified)
                else:
                    result = experiment.evaluate('development', verified)
            elif args.command == 'status':
                result = experiment.status(args.scope)
            elif args.command == 'export':
                result = experiment.export(args.scope)
            elif args.command == 'verify':
                experiment.verify()
                result = experiment.state
            else:
                result = experiment.prepare()
            experiment.state.setdefault('commands', []).append({'argv': [sys.executable, '-m', 'locomo_memory.experiment', *(list(argv) if argv is not None else sys.argv[1:])], 'completed_at': utc_now(), 'elapsed_seconds': time.perf_counter() - tick, 'elapsed_scope': 'CLI invocation, including HTTP waits; background work may continue'})
            experiment.save()
            print(json.dumps({'status': result['status'], 'blockers': result.get('blockers', []), 'progress': result.get('last_progress'), 'builds': result.get('last_builds', {})}, ensure_ascii=False))
        return 0
    except (ExperimentError, OSError, ValueError) as error:
        code = error.code if isinstance(error, ExperimentError) else 'invalid_local_artifact'
        if experiment is not None and experiment.state_path.exists():
            experiment.state.setdefault('error_history', []).append({'command': args.command, 'code': code, 'observed_at': utc_now()})
            experiment.state['last_error'] = {'code': code, 'command': args.command}
            experiment.save()
        print(json.dumps({'status': 'blocked', 'error': {'code': error.code if isinstance(error, ExperimentError) else 'invalid_local_artifact'}}, ensure_ascii=False))
        return 2


if __name__ == '__main__':
    sys.exit(main())
