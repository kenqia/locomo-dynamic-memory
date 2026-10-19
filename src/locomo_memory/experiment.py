"""Finite local experiment commands using the application's public HTTP API."""
import argparse
from contextlib import nullcontext
from datetime import date
import json
from pathlib import Path
import sys
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
        self.state = json.loads(self.state_path.read_text()) if self.state_path.exists() else {'created_at': utc_now(), 'builds': {}, 'live_smoke': 'not_run', 'full_baseline': 'not_run'}

    def request(self, method, path, **kwargs):
        try:
            response = self.client.request(method, path, **kwargs)
        except httpx.HTTPError:
            raise ExperimentError('backend_unavailable') from None
        if response.is_error:
            try:
                code = response.json()['error']['code']
            except (ValueError, KeyError, TypeError):
                code = 'backend_request_failed'
            raise ExperimentError(code)
        return response.json()

    def save(self):
        self.state['updated_at'] = utc_now()
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
            probe = {'dataset_id': imported['dataset_id'], 'artifact_sha256': imported['artifact_sha256'], 'build_id': build['build_id'], 'status': 'running'}
            self.state['probe'] = probe
            self.save()
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
                     source_references_checked=len(sources), real_provider=not preflight['generation']['controlled_transport'] and preflight['generation']['adapter'] == 'DeepSeekModel')
        self.state['status'] = 'probe_passed' if probe['real_provider'] else 'controlled_probe_passed'
        self.save()
        return self.state

    def status(self, scope):
        self.preflight()
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
            failures = [{'sample_id': i['sample_id'], 'question_id': i.get('question_id'), 'strategy': i['strategy'], 'status': i['status'], 'diagnosis': 'undetermined', 'evidence_pointer': f"run.json#items/{n}"} for n, i in enumerate(run.get('items', [])) if i['status'] != 'succeeded']
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
        self.state.update(status='prepared_offline', imported=imported, plans=plans,
                          blockers=([] if preflight['credential_present'] else ['missing_credentials']) + ['real_embedding_not_verified', 'live_extraction_not_run', 'live_smoke_not_run'])
        self.save()
        return self.state


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument('command', choices=['serve', 'prepare', 'probe', 'smoke', 'full', 'status', 'export', 'verify'])
    result.add_argument('--directory', type=Path, required=True, help='Experiment-only SQLite and artifact directory')
    result.add_argument('--api-url', default='http://127.0.0.1:8000')
    result.add_argument('--scope', choices=['smoke', 'development'], default='smoke')
    result.add_argument('--contract-record', type=Path, help='Dated public service-contract verification JSON')
    result.add_argument('--allow-paid', action='store_true', help='Explicitly allow generation calls for this command')
    result.add_argument('--port', type=int, default=8000)
    return result


def main(argv=None, *, client=None):
    args = parser().parse_args(argv)
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
            if args.command in {'probe', 'smoke', 'full'}:
                if not args.allow_paid:
                    raise ExperimentError('paid_opt_in_required')
                if args.command == 'full' and not experiment.state.get('smoke_run_id'):
                    raise ExperimentError('successful_live_smoke_required')
                experiment.require_live_prerequisites()
                experiment.contract(args.contract_record)
                verified = experiment.verify()
                result = experiment.probe(verified)
            elif args.command == 'status':
                result = experiment.status(args.scope)
            elif args.command == 'export':
                result = experiment.export(args.scope)
            elif args.command == 'verify':
                experiment.verify()
                result = experiment.state
            else:
                result = experiment.prepare()
            print(json.dumps({'status': result['status'], 'blockers': result.get('blockers', [])}, ensure_ascii=False))
        return 0
    except (ExperimentError, OSError, ValueError) as error:
        print(json.dumps({'status': 'blocked', 'error': {'code': error.code if isinstance(error, ExperimentError) else 'invalid_local_artifact'}}, ensure_ascii=False))
        return 2


if __name__ == '__main__':
    sys.exit(main())
