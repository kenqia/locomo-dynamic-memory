"""Explicit experiment transport cap, shared across retries/processes via SQLite.

Authorization is an external user decision. This object never supplies it. Missing
usage and transport failures retain the full reservation; no automatic refunds.
"""
from decimal import Decimal
import json
from pathlib import Path
import sqlite3
import uuid

import httpx

from .model import ModelFailure


class BudgetTransport(httpx.BaseTransport):
    def __init__(self, path: Path, delegate, *, max_requests: int, max_usd: str,
                 model: str, input_usd_per_million: str, output_usd_per_million: str,
                 max_input_bytes: int, max_output_tokens: int):
        self.path, self.delegate = path, delegate
        self.policy = dict(max_requests=max_requests, max_usd=str(Decimal(max_usd)), model=model,
            input_rate=str(Decimal(input_usd_per_million)), output_rate=str(Decimal(output_usd_per_million)),
            max_input_bytes=max_input_bytes, max_output_tokens=max_output_tokens)
        if (max_requests < 0 or Decimal(max_usd) < 0 or max_input_bytes < 1 or max_output_tokens < 1
                or Decimal(input_usd_per_million) < 0 or Decimal(output_usd_per_million) < 0):
            raise ValueError('invalid_budget_policy')
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS policy (singleton INTEGER PRIMARY KEY CHECK(singleton=1), json TEXT)')
            db.execute('CREATE TABLE IF NOT EXISTS physical_requests (id TEXT PRIMARY KEY, reserved_usd TEXT, status TEXT, usage_json TEXT)')
            db.execute('INSERT OR IGNORE INTO policy VALUES(1,?)', (json.dumps(self.policy, sort_keys=True),))
            stored = db.execute('SELECT json FROM policy WHERE singleton=1').fetchone()[0]
            if json.loads(stored) != self.policy:
                raise ValueError('budget_policy_changed')
        path.chmod(0o600)

    def _connect(self):
        return sqlite3.connect(self.path, timeout=30)

    def handle_request(self, request):
        body = json.loads(request.content)
        encoded = json.dumps(body.get('messages'), ensure_ascii=False).encode()
        output = body.get('max_tokens')
        if (request.url.scheme != 'https' or request.url.host != 'api.deepseek.com'
                or request.url.path != '/chat/completions' or body.get('model') != self.policy['model']
                or len(encoded) > self.policy['max_input_bytes'] or type(output) is not int
                or not 1 <= output <= self.policy['max_output_tokens'] or body.get('stream')):
            raise ModelFailure('physical_request_policy_rejected', {'calls': []})
        # Conservative byte upper reservation, rather than regex tokens. Rates use
        # cache miss + peak, so caching and time-of-day never reduce the reserve.
        reserve = (Decimal(len(encoded))*Decimal(self.policy['input_rate']) +
                   Decimal(output)*Decimal(self.policy['output_rate']))/Decimal(1000000)
        rid = uuid.uuid4().hex
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            rows = db.execute('SELECT reserved_usd FROM physical_requests').fetchall()
            if len(rows) >= self.policy['max_requests'] or sum((Decimal(r[0]) for r in rows), Decimal(0)) + reserve > Decimal(self.policy['max_usd']):
                raise ModelFailure('physical_request_budget_exhausted', {'calls': []})
            db.execute('INSERT INTO physical_requests VALUES(?,?,?,?)', (rid,str(reserve),'reserved','null'))
        try:
            response = self.delegate.handle_request(request)
            response.read()
            usage = {}
            try:
                raw = response.json().get('usage', {})
                usage = {k:v for k,v in raw.items() if k in ('prompt_tokens','completion_tokens','total_tokens') and type(v) is int and v >= 0}
            except (ValueError, AttributeError):
                pass
            with self._connect() as db:
                db.execute('UPDATE physical_requests SET status=?, usage_json=? WHERE id=?',
                           ('response_received' if usage else 'response_usage_unknown',json.dumps(usage),rid))
            return response
        except BaseException:
            with self._connect() as db:
                db.execute("UPDATE physical_requests SET status='transport_unknown' WHERE id=?", (rid,))
            raise

    def close(self):
        # Caller owns delegate; httpx.Client closes this wrapper after each retry.
        pass
