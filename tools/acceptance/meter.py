"""Single-process, fail-closed, write-ahead monetary gate for this new study."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import time

import httpx

INPUT_CAP = 1048576  # Full official 1M context; never a regex/tokenizer estimate.
OUTPUT_CAP = 8192
RESERVE_MICRO_CNY = INPUT_CAP * 2 + OUTPUT_CAP * 8


class StopStudy(RuntimeError):
    pass


def now():
    return datetime.now(timezone.utc).isoformat()


def durable_json(path, value):
    """Create only, fsync both the file and parent before returning."""
    path = Path(path)
    with path.open('x') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
    fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


class Meter(httpx.BaseTransport):
    def __init__(self, directory, plan, *, delegate=None):
        self.directory = Path(directory)
        self.directory.mkdir(exist_ok=False)
        self.plan = plan
        self.started = time.monotonic()
        self.stopped = False
        self.task = None
        self.sequence = 0
        self.delegate = delegate
        self.db = sqlite3.connect(self.directory / 'ledger.sqlite3')
        self.db.execute('PRAGMA synchronous=FULL')
        self.db.execute('PRAGMA journal_mode=DELETE')
        self.db.executescript('''CREATE TABLE calls(
            id INTEGER PRIMARY KEY, task TEXT UNIQUE, state TEXT, reserved INTEGER,
            cost INTEGER, body_sha256 TEXT, body_json TEXT, response_json TEXT,
            usage_json TEXT, returned_model TEXT, timestamp TEXT);
            CREATE TABLE events(id INTEGER PRIMARY KEY, task TEXT, event_json TEXT);''')
        self.db.commit()
        durable_json(self.directory / 'plan.json', plan)

    def event(self, value):
        try:
            with self.db:
                self.db.execute('INSERT INTO events(task,event_json) VALUES (?,?)',
                                (self.task, json.dumps(value, ensure_ascii=False)))
        except Exception as error:
            self.stopped = True
            raise StopStudy('checkpoint_persistence_failed') from error

    def summary(self):
        count, cost, unknown, reserved = self.db.execute(
            "SELECT count(*),coalesce(sum(cost),0),sum(state!='settled'),coalesce(sum(CASE WHEN state!='settled' THEN reserved ELSE 0 END),0) FROM calls").fetchone()
        return dict(physical_http=count, estimated_upper_micro_cny=cost,
                    unsettled_calls=unknown or 0, unsettled_reserved_micro_cny=reserved,
                    monetary_cap_micro_cny=self.plan['money_cap_micro_cny'])

    def check(self):
        if self.stopped:
            raise StopStudy('study_already_stopped')
        try:
            state = self.summary()
        except Exception as error:
            self.stopped = True
            raise StopStudy("ledger_persistence_failed") from error
        deadline = datetime.fromisoformat(self.plan['deadline_utc'])
        if datetime.now(timezone.utc) >= deadline or time.monotonic()-self.started >= self.plan['maximum_wall_seconds']:
            raise StopStudy('deadline_reached')
        if state['unsettled_calls']:
            raise StopStudy('unsettled_call_no_recovery')
        if state['physical_http'] >= self.plan['maximum_http']:
            raise StopStudy('physical_http_cap')
        if state['estimated_upper_micro_cny'] + RESERVE_MICRO_CNY > self.plan['money_cap_micro_cny']:
            raise StopStudy('money_reservation_cap')

    def handle_request(self, request):
        self.check()
        if self.task is None or request.method != 'POST' or str(request.url) != 'https://api.deepseek.com/chat/completions':
            raise StopStudy('unapproved_http')
        body = json.loads(request.content)
        if (body.get('model') != 'deepseek-flash' or body.get('max_tokens') != OUTPUT_CAP
                or body.get('stream', False) or set(body)-{'model','max_tokens','messages','thinking','response_format','temperature','reasoning_effort'}):
            raise StopStudy('unapproved_request_settings')
        raw = request.content.decode()
        try:
            with self.db:
                cursor = self.db.execute('INSERT INTO calls(task,state,reserved,body_sha256,body_json,timestamp) VALUES (?,?,?,?,?,?)',
                    (self.task, 'reserved_before_send', RESERVE_MICRO_CNY, hashlib.sha256(request.content).hexdigest(), raw, now()))
                cid = cursor.lastrowid
        except Exception as error:
            self.stopped = True
            raise StopStudy('reservation_persistence_failed') from error
        try:
            # No SDK/transport retries, redirects, proxy env, tools, or account probes.
            transport = self.delegate or httpx.HTTPTransport(retries=0, trust_env=False)
            try:
                response = transport.handle_request(request)
                with self.db:
                    self.db.execute('UPDATE calls SET state=?,response_json=? WHERE id=?',
                        ('http_response_observed',json.dumps({'status_code':response.status_code}),cid))
                response.read()
            finally:
                if self.delegate is None:
                    transport.close()
            document = response.json()
            usage = document.get('usage', {})
            usage = {k:v for k,v in usage.items() if k in {'prompt_tokens','completion_tokens','total_tokens'} and type(v) is int and v>=0} if isinstance(usage,dict) else {}
            returned = document.get('model')
            safe_model = returned if isinstance(returned,str) and re.fullmatch(r'[A-Za-z0-9._/-]{1,128}',returned) else None
            # Observation is durable even for partial usage and rejected responses.
            # Never persist headers, provider error bodies or reasoning_content.
            choices = [dict(finish_reason=c.get('finish_reason'),message={'content':c.get('message',{}).get('content')})
                       for c in document.get('choices',[]) if isinstance(c,dict) and isinstance(c.get('message',{}),dict)]
            safe = dict(status_code=response.status_code,model=safe_model,usage=usage,choices=choices)
            with self.db:
                self.db.execute('UPDATE calls SET state=?,response_json=?,usage_json=?,returned_model=? WHERE id=?',
                    ('response_observed',json.dumps(safe,ensure_ascii=False),json.dumps(usage),safe_model,cid))
            valid = all(type(usage.get(k)) is int for k in ('prompt_tokens','completion_tokens','total_tokens'))
            if not valid or usage['prompt_tokens']+usage['completion_tokens'] != usage['total_tokens']:
                raise StopStudy('missing_or_inconsistent_usage')
            if usage['prompt_tokens'] > INPUT_CAP or usage['completion_tokens'] > OUTPUT_CAP:
                raise StopStudy('provider_exceeded_reserved_token_caps')
            cost = usage['prompt_tokens']*2 + usage['completion_tokens']*8
            with self.db:
                self.db.execute('UPDATE calls SET state=?,cost=? WHERE id=?',('settled',cost,cid))
            if response.status_code != 200 or safe_model not in self.plan['allowed_returned_models']:
                raise StopStudy('provider_http_or_model_identity_changed')
            return response
        except Exception as error:
            self.stopped = True
            self.event(dict(status='global_stop',code=str(error) if isinstance(error,StopStudy) else 'transport_or_response_unknown',timestamp=now()))
            raise StopStudy(str(error) if isinstance(error,StopStudy) else 'transport_or_response_unknown') from None

    def close(self):
        # httpx.Client owns this interface each call; ledger spans the whole study.
        pass

    def finish(self):
        self.db.close()
