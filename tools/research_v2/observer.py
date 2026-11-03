"""Opt-in research-only physical HTTP accounting. No production imports this module."""
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import signal
import sqlite3
import threading
import time
import uuid

import httpx

from locomo_memory.model import DeepSeekModel, ModelFailure

UNITS = 1_000_000_000  # integer nano-CNY; no floating point in admission decisions
CONTEXT_CEILING = 1_048_576  # conservatively interpret documented 1M as 1024K
FIELDS = ('prompt_cache_hit_tokens', 'prompt_cache_miss_tokens', 'prompt_tokens', 'completion_tokens', 'total_tokens')
STAGES = {'extract': 'Extraction', 'relate': 'Relation', 'query_analysis': 'Query Analysis',
          'resolve': 'Resolution', 'answer': 'Answer'}


def sha(value):
    return hashlib.sha256(value).hexdigest()


def durable(path, value):
    """Exclusive private artifact, fsynced before a ledger can reference it."""
    path = Path(path)
    with path.open('xb') as stream:
        os.chmod(path, 0o600)
        stream.write(value)
        stream.flush()
        os.fsync(stream.fileno())
    fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


class Halt(ModelFailure):
    def __init__(self, code):
        super().__init__('research_' + code)


class Ledger:
    authorization_ceiling = (40 * UNITS, 500, 14400)

    def __init__(self, directory, *, clock=time.time):
        self.directory = Path(directory).resolve()
        self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        if self.directory.is_symlink() or self.directory.stat().st_mode & 0o077:
            raise Halt('private_directory_required')
        self.clock = clock
        self.closed = False
        self.path = self.directory / 'budget.sqlite3'
        self.lock = (self.directory / 'owner.lock').open('a')
        os.chmod(self.directory / 'owner.lock', 0o600)
        try:
            fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            self.lock.close()
            raise Halt('owner_already_running') from None
        self._serial = threading.Lock()
        self.local = threading.local()
        self.global_tags = {}
        self.watch_stop = threading.Event()
        with self.db() as db:
            db.executescript('''CREATE TABLE IF NOT EXISTS policy (singleton INTEGER PRIMARY KEY CHECK(singleton=1), document TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS requests (id TEXT PRIMARY KEY, status TEXT NOT NULL, reservation INTEGER NOT NULL,
                cost INTEGER, record TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY, kind TEXT NOT NULL, document TEXT NOT NULL);''')
        os.chmod(self.path, 0o600)

    @contextmanager
    def db(self):
        db = sqlite3.connect(self.path, timeout=30)
        try:
            db.execute('PRAGMA synchronous=FULL')
            with db:
                yield db
        finally:
            db.close()

    def arm(self, identity, *, money=40 * UNITS, requests=500, seconds=14400,
            max_tokens=8192, prior_requests=0, prior_cost_nano_cny=0,
            started=None, deadline=None):
        money_ceiling, request_ceiling, time_ceiling = self.authorization_ceiling
        if not (0 < money <= money_ceiling and 0 < requests <= request_ceiling and 0 < seconds <= time_ceiling):
            raise Halt('authorization_exceeded')
        if type(max_tokens) is not int or not 1 <= max_tokens <= 32768:
            raise Halt('authorization_exceeded')
        if type(prior_requests) is not int or prior_requests < 0 or prior_requests > requests:
            raise Halt('authorization_exceeded')
        if type(prior_cost_nano_cny) is not int or prior_cost_nano_cny < 0 or prior_cost_nano_cny > money:
            raise Halt('authorization_exceeded')
        with self.db() as db:
            if db.execute('SELECT COUNT(*) FROM policy').fetchone()[0]:
                raise Halt('already_armed_no_automatic_resume')
            now = self.clock()
            started = now if started is None else started
            deadline = now + seconds if deadline is None else deadline
            if started > now or deadline > started + seconds or deadline <= now:
                raise Halt('deadline')
            policy = dict(identity=identity, limit_nano_cny=money, limit_requests=requests,
                          concurrency=1, started=started, deadline=deadline,
                          max_tokens=max_tokens, prior_requests=prior_requests,
                          prior_cost_nano_cny=prior_cost_nano_cny,
                          price_nano_cny_per_token={'miss': 2000, 'hit': 40, 'output': 8000},
                          context_ceiling=CONTEXT_CEILING)
            db.execute('INSERT INTO policy VALUES (1,?)', (json.dumps(policy, sort_keys=True),))
        return policy

    def policy(self):
        with self.db() as db:
            row = db.execute('SELECT document FROM policy').fetchone()
        if not row:
            raise Halt('not_armed')
        return json.loads(row[0])

    def event(self, kind, document):
        with self.db() as db:
            db.execute('INSERT INTO events(kind,document) VALUES (?,?)',
                       (kind, json.dumps(dict(document, observed_at=self.clock()), sort_keys=True)))

    def assert_available(self):
        if self.closed:
            raise Halt('ledger_closed')
        p = self.policy()
        with self.db() as db:
            if db.execute("SELECT COUNT(*) FROM requests WHERE status != 'settled'").fetchone()[0]:
                raise Halt('unknown_billing_requires_external_reconciliation')
            if db.execute("SELECT COUNT(*) FROM events WHERE kind='halt'").fetchone()[0]:
                raise Halt('ledger_stopped')
        if self.clock() >= p['deadline']:
            raise Halt('deadline')

    def reserve(self, raw, body, tags):
        self.assert_available()
        p = self.policy()
        if body.get('model') != 'deepseek-flash' or type(body.get('max_tokens')) is not int or not 1 <= body['max_tokens'] <= p.get('max_tokens', 8192):
            raise Halt('request_identity_changed')
        if set(body) - {'model', 'messages', 'thinking', 'reasoning_effort', 'temperature', 'response_format', 'max_tokens'}:
            raise Halt('unexpected_request_features')
        if tags.get('operation') not in STAGES:
            raise Halt('operation_out_of_scope')
        reservation = CONTEXT_CEILING * 2000 + body['max_tokens'] * 8000
        request_id = uuid.uuid4().hex
        durable(self.directory / (request_id + '.request.json'), raw)
        now = self.clock()
        row = dict(tags, request_id=request_id, request_sha256=sha(raw), request_bytes=len(raw),
                   model=body['model'], max_tokens=body['max_tokens'], stage=STAGES[tags['operation']],
                   reserved_at=now, wire_path=request_id + '.request.json', method='POST',
                   url='https://api.deepseek.com/chat/completions',
                   usage={key: None for key in FIELDS}, system_fingerprint=None,
                   system_fingerprint_present=False, response_sha256=None, elapsed_seconds=None,
                   response_received=False, semantic_status='not_observed')
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            count, used = db.execute('SELECT COUNT(*), COALESCE(SUM(COALESCE(cost,reservation)),0) FROM requests').fetchone()
            if now >= p['deadline']:
                raise Halt('deadline')
            if count + p.get('prior_requests', 0) >= p['limit_requests']:
                raise Halt('request_limit')
            if used + p.get('prior_cost_nano_cny', 0) + reservation > p['limit_nano_cny']:
                raise Halt('money_limit')
            db.execute('INSERT INTO requests VALUES (?,\'reserved\',?,NULL,?)',
                       (request_id, reservation, json.dumps(row, sort_keys=True)))
        return request_id

    def annotate(self, request_id, **fields):
        with self.db() as db:
            row = db.execute('SELECT record FROM requests WHERE id=?', (request_id,)).fetchone()
            record = json.loads(row[0])
            record.update(fields)
            db.execute('UPDATE requests SET record=? WHERE id=?', (json.dumps(record, sort_keys=True), request_id))

    def finish(self, request_id, response, elapsed):
        raw = response.content
        durable(self.directory / (request_id + '.response.json'), raw)
        try:
            doc = response.json()
        except ValueError:
            doc = {}
        if not isinstance(doc, dict):
            doc = {}
        usage = doc.get('usage') if isinstance(doc.get('usage'), dict) else {}
        usage = {key: usage.get(key) if type(usage.get(key)) is int and usage[key] >= 0 else None for key in FIELDS}
        hit, miss, prompt, completion, total = [usage[key] for key in FIELDS]
        self.annotate(request_id, usage=usage, system_fingerprint=doc.get('system_fingerprint'),
                      system_fingerprint_present='system_fingerprint' in doc,
                      returned_model=doc.get('model'), provider_created=doc.get('created'),
                      http_status=response.status_code, response_received=True,
                      response_sha256=sha(raw), response_path=request_id + '.response.json',
                      elapsed_seconds=elapsed, response_observed_at=self.clock())
        with self.db() as db:
            reservation, record = db.execute('SELECT reservation,record FROM requests WHERE id=?', (request_id,)).fetchone()
            max_tokens = json.loads(record)['max_tokens']
            valid = (all(v is not None for v in usage.values()) and hit + miss == prompt
                     and total == prompt + completion and prompt <= CONTEXT_CEILING and completion <= max_tokens)
            cost = hit * 40 + miss * 2000 + completion * 8000 if valid else None
            valid = valid and cost <= reservation and response.status_code == 200 and doc.get('model') == 'deepseek-flash'
            db.execute('UPDATE requests SET status=?,cost=? WHERE id=?',
                       ('settled' if valid else 'unknown', cost if valid else None, request_id))
        if not valid:
            raise Halt('unknown_or_inconsistent_billing')

    def rows(self):
        with self.db() as db:
            return [dict(json.loads(r[3]), status=r[0], reservation_nano_cny=r[1], cost_nano_cny=r[2])
                    for r in db.execute('SELECT status,reservation,cost,record FROM requests ORDER BY rowid')]

    @contextmanager
    def scope(self, **tags):
        previous = getattr(self.local, 'tags', {})
        self.local.tags = {**self.global_tags, **previous, **tags}
        try:
            yield
        finally:
            self.local.tags = previous

    def watchdog(self):
        """SIGTERM kills even a worker blocked on a trickling response. Reservation remains."""
        deadline = self.policy()['deadline']
        remaining = min(deadline - self.clock(), self.authorization_ceiling[2])
        if remaining <= 0:
            raise Halt('deadline')
        def expire():
            if not self.watch_stop.wait(remaining):
                os.kill(os.getpid(), signal.SIGTERM)
        threading.Thread(target=expire, name='research-hard-deadline', daemon=True).start()

    def close(self):
        self.closed = True
        self.watch_stop.set()
        fcntl.flock(self.lock, fcntl.LOCK_UN)
        self.lock.close()


class ObservedTransport(httpx.BaseTransport):
    def __init__(self, ledger, underlying):
        self.ledger, self.underlying = ledger, underlying

    def close(self):
        # DeepSeekModel opens a fresh Client per physical attempt. Owner closes pool.
        pass

    def handle_request(self, request):
        ledger = self.ledger
        if not ledger._serial.acquire(blocking=False):
            raise Halt('concurrency_limit')
        request_id = None
        tick = time.perf_counter()
        try:
            if request.method != 'POST' or str(request.url) != 'https://api.deepseek.com/chat/completions':
                raise Halt('endpoint_out_of_scope')
            raw = request.read()
            # Never persist credentials accidentally reflected in a payload/response.
            secret = request.headers.get('authorization', '').removeprefix('Bearer ').encode()
            if secret and secret in raw:
                raise Halt('credential_in_body')
            tags = getattr(ledger.local, 'tags', {})
            request_id = ledger.reserve(raw, json.loads(raw), tags)
            ledger.local.physical_id = request_id
            ledger.local.physical_attempt = tags.get('attempt')
            # Recheck wall-clock after durable reservation, immediately before send.
            if ledger.clock() >= ledger.policy()['deadline']:
                ledger.annotate(request_id, not_sent=True)
                raise Halt('deadline')
            response = self.underlying.handle_request(request)
            try:
                response.read()
            finally:
                response.close()
            if secret and secret in response.content:
                raise Halt('credential_in_response')
            ledger.finish(request_id, response, time.perf_counter() - tick)
            return response
        except BaseException as error:
            if request_id:
                ledger.annotate(request_id, transport_exit=type(error).__name__, transport_elapsed_seconds=time.perf_counter() - tick)
            ledger.event('halt', {'code': error.code if isinstance(error, ModelFailure) else 'physical_outcome_unknown',
                                  'request_id': request_id})
            raise
        finally:
            ledger._serial.release()


class ObservedDeepSeekModel(DeepSeekModel):
    def __init__(self, settings, ledger, transport, **kwargs):
        super().__init__(settings, transport=ObservedTransport(ledger, transport), **kwargs)
        self.ledger = ledger

    def generate(self, operation, payload, schema, *, context=None, on_call=None):
        self.ledger.assert_available()
        logical_id = uuid.uuid4().hex
        with self.ledger.scope(operation=operation, logical_id=logical_id,
                               payload_sha256=sha(json.dumps(payload, sort_keys=True).encode())):
            def checkpoint(call):
                self.ledger.local.tags['attempt'] = call['attempt']
                if call['status'] == 'started':
                    self.ledger.local.physical_id = None
                physical_id = getattr(self.ledger.local, 'physical_id', None)
                if physical_id:
                    call['research_physical_id'] = physical_id
                    self.ledger.annotate(physical_id, semantic_status=call['status'],
                                         semantic_error_code=call.get('error_code'))
                if on_call:
                    on_call(call)
            return super().generate(operation, payload, schema, context=context, on_call=checkpoint)
