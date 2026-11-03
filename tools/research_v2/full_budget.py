"""Independent, opt-in full-baseline ceiling. Smoke policy remains unchanged."""
import json
import resource
import threading
import time

from tools.research_v2.observer import Ledger, Halt, UNITS, sha

LIMITS = dict(max_cny=620, max_physical_http=11300, max_seconds=111600, max_concurrency=1)


class FullLedger(Ledger):
    authorization_ceiling = (620 * UNITS, 11300, 111600)

    def arm(self, identity, *, money=620 * UNITS, requests=11300, seconds=111600,
            max_tokens=32768, **kwargs):
        if kwargs.get('prior_requests', 0) or kwargs.get('prior_cost_nano_cny', 0):
            raise Halt('independent_budget_required')
        policy = super().arm(identity, money=money, requests=requests, seconds=seconds,
                             max_tokens=max_tokens, **kwargs)
        self.bind(policy)
        return policy

    def bind(self, policy):
        self.policy_digest = sha(json.dumps(policy, sort_keys=True).encode())
        self.last_wall = self.clock()
        self.monotonic_deadline = time.monotonic() + policy['deadline'] - self.last_wall

    def assert_available(self):
        if getattr(self, 'measurement_failed', False):
            raise Halt('resource_measurement_failed')
        if not hasattr(self, 'policy_digest'):
            raise Halt('no_automatic_budget_recovery')
        if sha(json.dumps(self.policy(), sort_keys=True).encode()) != self.policy_digest:
            raise Halt('budget_policy_changed')
        now = self.clock()
        if now < self.last_wall or time.monotonic() >= self.monotonic_deadline:
            raise Halt('deadline_or_clock_regression')
        self.last_wall = now
        super().assert_available()

    def reserve(self, raw, body, tags):
        if getattr(self, 'contract_guard', None):
            self.contract_guard()
        return super().reserve(raw, body, tags)

    def resource_snapshot(self):
        usage = resource.getrusage(resource.RUSAGE_SELF)
        self.event('resource_sample', dict(cpu_user_seconds=usage.ru_utime,
            cpu_system_seconds=usage.ru_stime, peak_rss_kib=usage.ru_maxrss,
            local_compute_money_cny=None))

    def sample_resources(self, interval=30):
        self.resource_snapshot()
        def sample():
            while not self.watch_stop.wait(interval):
                try:
                    self.resource_snapshot()
                except Exception:
                    # Losing observability stops later sends; no silent free usage.
                    self.measurement_failed = True
                    return
        threading.Thread(target=sample, name='research-resource-sampler', daemon=True).start()

    def finish(self, request_id, response, elapsed):
        super().finish(request_id, response, elapsed)
        expected = self.policy()['identity'].get('expected_system_fingerprint')
        if expected and response.json().get('system_fingerprint') != expected:
            self.event('halt', {'code': 'provider_identity_changed', 'request_id': request_id})
            raise Halt('provider_identity_changed')
