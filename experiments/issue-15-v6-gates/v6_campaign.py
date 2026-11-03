"""One durable ceiling across ordered gates and their implementation identities."""
from collections import Counter
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import threading

from locomo_memory.implementation_identity import implementation_sha256
from locomo_memory.model import utc_now
from locomo_memory.usage import provider_usage


FIELDS = ('attempt', 'timestamp', 'completed_at', 'status', 'outcome', 'response_received',
          'requested_model', 'returned_model', 'usage', 'elapsed_seconds', 'failure_stage',
          'error_code', 'field_path', 'finish_reason', 'finish_reason_status', 'validation_errors',
          'http_status', 'http_error_category', 'http_retryable', 'task_id', 'source_task_id',
          'logical_attempt', 'provider_attempt', 'call_id')


class Campaign:
    def __init__(self, path, prior_ledger, *, create=False, limit=1000):
        self.path, self.prior = Path(path).resolve(), Path(prior_ledger).resolve()
        self.lock = threading.Lock()
        with closing(sqlite3.connect(self.prior.as_uri() + '?mode=ro', uri=True)) as db:
            old = json.loads(db.execute('SELECT value FROM header').fetchone()[0])
            previous = old['previous_calls'] + db.execute('SELECT COUNT(*) FROM calls').fetchone()[0]
        self.header = {'limit': limit, 'previous_calls': previous,
                       'prior_ledger': str(self.prior), 'prior_sha256': self.prior_hash()}
        if create:
            with self.path.open('xb'):
                pass
            with sqlite3.connect(self.path) as db:
                db.executescript('CREATE TABLE header(value TEXT NOT NULL);'
                    'CREATE TABLE calls(sequence INTEGER PRIMARY KEY, phase TEXT NOT NULL, '
                    'implementation_sha256 TEXT NOT NULL, operation TEXT NOT NULL, metadata TEXT NOT NULL);')
                db.execute('INSERT INTO header VALUES (?)', (json.dumps(self.header),))
        elif not self.path.is_file():
            raise ValueError('existing_campaign_required')
        with closing(sqlite3.connect(self.path.as_uri() + '?mode=ro', uri=True)) as db:
            if json.loads(db.execute('SELECT value FROM header').fetchone()[0]) != self.header:
                raise ValueError('campaign_history_or_ceiling_changed')

    def prior_hash(self):
        return hashlib.sha256(self.prior.read_bytes()).hexdigest()

    def reserve(self, phase, identity, operation):
        if self.prior_hash() != self.header['prior_sha256']:
            raise ValueError('prior_history_changed')
        with self.lock, sqlite3.connect(self.path) as db:
            db.execute('BEGIN IMMEDIATE')
            rows = db.execute('SELECT metadata FROM calls').fetchall()
            if any(not json.loads(row[0]).get('completed_at') for row in rows):
                raise ValueError('unknown_call_requires_review')
            if len(rows) + self.header['previous_calls'] >= self.header['limit']:
                raise ValueError('campaign_ceiling_reached')
            sequence = len(rows) + 1
            db.execute('INSERT INTO calls VALUES (?,?,?,?,?)',
                       (sequence, phase, identity, operation, json.dumps({'status': 'started'})))
            return sequence

    def observe(self, sequence, call):
        safe = {key: call[key] for key in FIELDS if key in call}
        with self.lock, sqlite3.connect(self.path) as db:
            db.execute('UPDATE calls SET metadata=? WHERE sequence=?', (json.dumps(safe), sequence))

    def summary(self):
        with closing(sqlite3.connect(self.path.as_uri() + '?mode=ro', uri=True)) as db:
            rows = db.execute('SELECT phase,operation,metadata FROM calls ORDER BY sequence').fetchall()
        calls = [json.loads(row[2]) for row in rows]
        return {**self.header, 'reserved_new_calls': len(rows),
                'reserved_total_calls': self.header['previous_calls'] + len(rows),
                'phases': dict(Counter(row[0] for row in rows)),
                'operations': dict(Counter(row[1] for row in rows)),
                'outcomes': dict(Counter(c.get('outcome', 'unknown') for c in calls)),
                'usage': provider_usage(calls)}

    def bind(self, model, phase, *, source_task_id=None):
        generate, identity, halted = model.generate, implementation_sha256(), threading.Event()

        def bounded(operation, payload, schema, *, context=None, on_call=None):
            slots = {}
            def observe(call):
                if call['status'] == 'started':
                    if halted.is_set() or implementation_sha256() != identity:
                        raise ValueError('implementation_changed_or_execution_halted')
                    slots[call['attempt']] = self.reserve(phase, identity, operation)
                if source_task_id:
                    call['source_task_id'] = source_task_id
                sequence = slots[call['attempt']]
                self.observe(sequence, call)
                if on_call:
                    on_call(call)
                    self.observe(sequence, call)
                if call.get('completed_at'):
                    print(json.dumps({'event': 'provider_call_finished', 'sequence': sequence,
                        'phase': phase, 'operation': operation, 'outcome': call['outcome'],
                        'error_code': call.get('error_code'), 'http_status': call.get('http_status')}), flush=True)
                if call.get('outcome') in {'model_http_error', 'model_timeout', 'context_length_exceeded'}:
                    transient = call.get('http_retryable') is True
                    if not transient or call['attempt'] > model.settings.model_retries:
                        halted.set()
                        raise ValueError('provider_failure_requires_review')
            if halted.is_set():
                raise ValueError('execution_halted')
            return generate(operation, payload, schema, context=context, on_call=observe)
        model.generate = bounded
