"""Single-owner evaluation execution with durable logical items and attempts."""
import hashlib
import json
import platform
import threading
import time
import uuid
from importlib.metadata import version
from pathlib import Path

from .builds import BuildError
from .imports import canonical_json
from .model import ANSWER_PROMPT, QUERY_ANALYSIS_PROMPT, RESOLUTION_PROMPT, KNOWN_MODEL_VERSION, utc_now
from .query_schemas import EvidenceAnswer, EffectiveResolution
from .retrieval import TOKEN_BUDGET_METHOD
from .retrieval_schemas import QueryAnalysis

STATES = ('pending', 'running', 'succeeded', 'failed', 'interrupted', 'unknown')
METRIC_VERSION = 'locomo-official-category-v1'


def digest(value):
    return hashlib.sha256(canonical_json(value).encode()).hexdigest()


class EvaluationExecution:
    def __init__(self, service):
        self.service = service
        self.database = service.database
        self.lock = threading.Lock()
        self.stop = threading.Event()
        self.worker = None
        with self.database.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS evaluation_run_items(run_id TEXT NOT NULL REFERENCES evaluation_runs(run_id), ordinal INTEGER NOT NULL, status TEXT NOT NULL, item_json TEXT NOT NULL, PRIMARY KEY(run_id,ordinal))')

    def metadata(self, run_id):
        with self.database.connect() as db:
            row = db.execute('SELECT result_json FROM evaluation_runs WHERE run_id=?', (run_id,)).fetchone()
        if row is None:
            raise BuildError('not_found', 404)
        return json.loads(row[0])

    def save_metadata(self, db, run):
        db.execute('UPDATE evaluation_runs SET result_json=? WHERE run_id=?', (canonical_json(run), run['run_id']))

    def items(self, run_id, db=None):
        if db is None:
            with self.database.connect() as connection:
                return self.items(run_id, connection)
        return [json.loads(r[0]) for r in db.execute('SELECT item_json FROM evaluation_run_items WHERE run_id=? ORDER BY ordinal', (run_id,))]

    def read(self, run_id):
        with self.database.connect() as db:
            db.execute('BEGIN')
            row = db.execute('SELECT result_json FROM evaluation_runs WHERE run_id=?', (run_id,)).fetchone()
            if row is None:
                raise BuildError('not_found', 404)
            run = json.loads(row[0])
            items = self.items(run_id, db) if 'execution_version' in run else None
        return self.view(run, items)

    def view(self, run, items=None):
        if 'execution_version' not in run:
            return run  # Historical, whole-run records remain readable.
        run = dict(run)
        run['items'] = self.items(run['run_id']) if items is None else items
        run['progress'] = {'total': len(run['items']), **{state: sum(i['status'] == state for i in run['items']) for state in STATES}}
        run['results'] = [i['result'] for i in run['items'] if i.get('result') is not None]
        return self.service.summarize(run)

    def progress(self, run_id):
        with self.database.connect() as db:
            db.execute('BEGIN')
            row = db.execute("SELECT json_extract(result_json,'$.run_id') AS run_id, json_extract(result_json,'$.status') AS status, json_extract(result_json,'$.completed_at') AS completed_at, json_extract(result_json,'$.elapsed_seconds') AS elapsed_seconds, json_extract(result_json,'$.execution_version') AS execution_version FROM evaluation_runs WHERE run_id=?", (run_id,)).fetchone()
            if row is None:
                raise BuildError('not_found', 404)
            if row['execution_version'] is None:
                return self.metadata(run_id)
            counts = {r[0]: r[1] for r in db.execute('SELECT status,COUNT(*) FROM evaluation_run_items WHERE run_id=? GROUP BY status', (run_id,))}
        return {key: row[key] for key in ('run_id', 'status', 'completed_at', 'elapsed_seconds')} | {'progress': {'total': sum(counts.values()), **{state: counts.get(state, 0) for state in STATES}}}

    def identity(self, inputs, plan, selected, pins, strategies, partition):
        q = self.service.queries
        with self.database.connect() as db:
            source = dict(db.execute('SELECT * FROM datasets WHERE dataset_id=?', (inputs['dataset_id'],)).fetchone())
        return {
            'input': inputs, 'plan': plan, 'selected_indices': selected, 'pins': pins,
            'strategies': strategies, 'partition': partition, 'source': source,
            'source_turns_sha256': {sid: digest(self.service.sources(inputs['dataset_id'], sid)) for sid in pins},
            'builds': {sid: q.versions.builds.get(bid) for sid, bid in pins.items()},
            'build_artifacts': {sid: q.versions.pin_details(inputs['dataset_id'], sid, bid) for sid, bid in pins.items()},
            'config': q.settings.snapshot(), 'answer_prompt': ANSWER_PROMPT,
            'answer_schema': EvidenceAnswer.model_json_schema(), 'resolution_prompt': RESOLUTION_PROMPT,
            'resolution_schema': EffectiveResolution.model_json_schema(), 'query_analysis_prompt': QUERY_ANALYSIS_PROMPT,
            'query_analysis_schema': QueryAnalysis.model_json_schema(),
            'known_service_version': KNOWN_MODEL_VERSION, 'metric_version': METRIC_VERSION,
            'token_budget_method': TOKEN_BUDGET_METHOD,
            'runtime': {'python': platform.python_version(), 'packages': {name: version(name) for name in ('locomo-dynamic-memory', 'nltk', 'numpy', 'rank-bm25', 'pydantic', 'fastapi')}},
            'implementation_sha256': hashlib.sha256(b''.join(p.name.encode() + p.read_bytes() for p in sorted(Path(__file__).parent.glob('*.py')))).hexdigest(),
        }

    def plan(self, plan_id):
        if not plan_id:
            return None
        with self.database.connect() as db:
            row = db.execute('SELECT result_json FROM evaluation_plans WHERE plan_id=?', (plan_id,)).fetchone()
        if row is None:
            raise BuildError('not_found', 404)
        return json.loads(row[0])

    def create(self, request):
        if not self.lock.acquire(blocking=False):
            raise BuildError('evaluation_already_running')
        try:
            plan = self.plan(request.plan_id)
            if plan and ((request.input_id and request.input_id != plan['input_id']) or (request.strategies and request.strategies != plan['strategies']) or (request.partition and request.partition != plan['partition'])):
                raise BuildError('evaluation_plan_mismatch', 422)
            input_id = plan['input_id'] if plan else request.input_id
            inputs = self.service.get('evaluation_inputs', input_id)
            # Inputs produced by a fixed plan cannot bypass its scope through the old API.
            if inputs.get('plan_id'):
                plan = self.plan(inputs['plan_id'])
                if request.strategies and request.strategies != plan['strategies'] or request.partition and request.partition != plan['partition']:
                    raise BuildError('evaluation_plan_mismatch', 422)
            strategies = request.strategies or (plan['strategies'] if plan else None)
            partition = plan['partition'] if plan else request.partition
            if not strategies:
                raise BuildError('evaluation_strategies_required', 422)
            if inputs['kind'] == 'official_structure_only':
                raise BuildError('official_structure_only_no_generation', 422)
            if inputs['kind'] == 'course' and (not inputs['course_split'] or not partition):
                raise BuildError('course_split_and_partition_required', 422)
            selected = [i for i, s in enumerate(inputs['samples']) if not partition or inputs['course_split'] and s['sample_id'] in inputs['course_split'][partition]]
            if not selected:
                raise BuildError('empty_evaluation_partition', 422)
            pins = {inputs['samples'][i]['sample_id']: self.service.queries.versions.pin(inputs['dataset_id'], inputs['samples'][i]['sample_id'], request.build_ids.get(inputs['samples'][i]['sample_id'])) for i in selected}
            identity = self.identity(inputs, plan, selected, pins, strategies, partition)
            run = {**identity, 'run_id': uuid.uuid4().hex, 'input_id': input_id,
                   'plan_id': plan['plan_id'] if plan else None, 'execution_version': 1,
                   'fingerprint': digest(identity), 'kind': inputs['kind'], 'status': 'running',
                   'started_at': utc_now(), 'completed_at': None, 'elapsed_seconds': 0,
                   'course_metrics': {'status': 'unavailable', 'reason': 'synthetic_or_structure_data_only' if inputs['kind'] != 'course' else 'independent_dynamic_truth_missing'},
                   'billing_notice': 'Interrupted external calls may already be billed. Unknown outcomes require explicit retry; exactly-once provider billing is not guaranteed.'}
            items = []
            for index in selected:
                sample = inputs['samples'][index]
                identity = inputs.get('question_identities', [])[index] if inputs.get('question_identities') else {'sample_id': sample['sample_id'], 'qa_index': index, 'question_id': f"{sample['sample_id']}:input:{index}"}
                for strategy in strategies:
                    items.append({'ordinal': len(items), 'sample_index': index, **identity, 'strategy': strategy, 'status': 'pending', 'attempts': [], 'result': None})
            with self.database.connect() as db:
                db.execute('INSERT INTO evaluation_runs VALUES (?,?)', (run['run_id'], canonical_json(run)))
                db.executemany('INSERT INTO evaluation_run_items VALUES (?,?,?,?)', [(run['run_id'], item['ordinal'], item['status'], canonical_json(item)) for item in items])
            return self.launch(run, request.wait)
        except BaseException:
            self.lock.release()
            raise

    def compatible(self, run):
        if 'execution_version' not in run:
            raise BuildError('legacy_evaluation_not_resumable')
        inputs = self.service.get('evaluation_inputs', run['input_id'])
        try:
            current = self.identity(inputs, self.plan(run.get('plan_id')), run['selected_indices'], run['pins'], run['strategies'], run['partition'])
        except BuildError:
            raise BuildError('evaluation_identity_changed') from None
        if digest(current) != run['fingerprint']:
            raise BuildError('evaluation_identity_changed')

    def resume(self, run_id, request):
        if not self.lock.acquire(blocking=False):
            raise BuildError('evaluation_already_running')
        try:
            run = self.metadata(run_id)
            self.compatible(run)
            if run['status'] == 'running':
                raise BuildError('evaluation_already_running')
            with self.database.connect() as db:
                items = self.items(run_id, db)
                for item in items:
                    if item['status'] in ('pending', 'interrupted') or item['status'] == 'failed' and request.retry_failed or item['status'] == 'unknown' and request.retry_unknown:
                        item['status'] = 'pending'
                        db.execute('UPDATE evaluation_run_items SET status=?, item_json=? WHERE run_id=? AND ordinal=?', (item['status'], canonical_json(item), run_id, item['ordinal']))
                if not any(i['status'] == 'pending' for i in items):
                    self.lock.release()
                    return self.view(run)
                run.update(status='running', completed_at=None)
                self.save_metadata(db, run)
            return self.launch(run, request.wait)
        except BaseException:
            self.lock.release()
            raise

    def launch(self, run, wait):
        self.stop.clear()
        if wait:
            self.execute(run)
        else:
            self.worker = threading.Thread(target=self.execute, args=(run,), name='evaluation-' + run['run_id'], daemon=True)
            self.worker.start()
        return self.view(self.metadata(run['run_id']))

    def execute(self, run):
        started = time.perf_counter()
        try:
            for item in self.items(run['run_id']):
                if self.stop.is_set():
                    break
                if item['status'] != 'pending':
                    continue
                attempt = {'attempt_id': uuid.uuid4().hex, 'number': len(item['attempts']) + 1, 'started_at': utc_now(), 'completed_at': None, 'status': 'running', 'elapsed_seconds': None, 'result': None}
                item['attempts'].append(attempt)
                item['status'] = 'running'
                with self.database.connect() as db:
                    db.execute('UPDATE evaluation_run_items SET status=?, item_json=? WHERE run_id=? AND ordinal=?', (item['status'], canonical_json(item), run['run_id'], item['ordinal']))
                tick = time.perf_counter()
                try:
                    index = item['sample_index']
                    result = self.service.execute_item(run['input'], index, run['input']['samples'][index], item['strategy'], run['pins'][item['sample_id']])
                    status = 'failed' if result.get('error') else 'succeeded'
                except Exception:
                    # An unexpected exit can follow a billed call. Never assert a safe retry.
                    result, status = None, 'unknown'
                if status == 'unknown':
                    attempt['error'] = {'code': 'external_outcome_unknown'}
                attempt.update(status=status, completed_at=utc_now(), elapsed_seconds=time.perf_counter() - tick, result=result)
                item.update(status=status, result=result)
                with self.database.connect() as db:
                    current = json.loads(db.execute('SELECT item_json FROM evaluation_run_items WHERE run_id=? AND ordinal=?', (run['run_id'], item['ordinal'])).fetchone()[0])
                    if current['status'] != 'running' or current['attempts'][-1]['attempt_id'] != attempt['attempt_id']:
                        raise BuildError('evaluation_attempt_superseded')
                    db.execute('UPDATE evaluation_run_items SET status=?, item_json=? WHERE run_id=? AND ordinal=?', (item['status'], canonical_json(item), run['run_id'], item['ordinal']))
                if status == 'unknown':
                    break
            items = self.items(run['run_id'])
            incomplete = any(i['status'] in ('pending', 'running', 'interrupted', 'unknown') for i in items)
            run['status'] = 'interrupted' if incomplete else 'completed_with_errors' if any(i['status'] == 'failed' for i in items) else 'completed'
            run['completed_at'] = None if incomplete else utc_now()
        except Exception:
            run.update(status='interrupted', completed_at=None)
        finally:
            run['elapsed_seconds'] += time.perf_counter() - started
            try:
                with self.database.connect() as db:
                    self.save_metadata(db, run)
            finally:
                self.lock.release()

    def recover_interrupted(self):
        # Called only while holding the exclusive backend ownership lock.
        with self.database.connect() as db:
            rows = db.execute('SELECT result_json FROM evaluation_runs').fetchall()
            for row in rows:
                run = json.loads(row[0])
                if run.get('execution_version') and run['status'] == 'running':
                    for item in self.items(run['run_id'], db):
                        if item['status'] == 'running':
                            item['status'] = 'unknown'
                            item['attempts'][-1].update(status='unknown', completed_at=utc_now(), error={'code': 'external_outcome_unknown'})
                        elif item['status'] == 'pending':
                            item['status'] = 'interrupted'
                        db.execute('UPDATE evaluation_run_items SET status=?, item_json=? WHERE run_id=? AND ordinal=?', (item['status'], canonical_json(item), run['run_id'], item['ordinal']))
                    run.update(status='interrupted', completed_at=None)
                    self.save_metadata(db, run)

    def shutdown(self):
        self.stop.set()
        if self.worker is not None:
            # Adapter timeouts/retry limits bound current work; retain DB ownership
            # until it exits so another backend cannot race a late commit.
            self.worker.join()
