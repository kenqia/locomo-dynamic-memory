"""Explicit one-shot retry lineage; inherit all original smoke limits, fail closed."""
import json
from pathlib import Path

from tools.research_v2.observer import Ledger, Halt, sha


def claim_parent(identity, directory):
    parent_path = Path(identity['retry_parent'])
    if parent_path.resolve() == directory.resolve():
        raise Halt('retry_parent_invalid')
    if sha((parent_path/'execution-outcome.json').read_bytes()) != identity['retry_parent_outcome_sha256']:
        raise Halt('retry_parent_changed')
    parent = Ledger(parent_path/'observer')
    try:
        policy = parent.policy()
        records = parent.rows()
        if any(r['status'] != 'settled' or r['cost_nano_cny'] is None for r in records):
            raise Halt('unknown_billing_requires_external_reconciliation')
        if parent.clock() >= policy['deadline']:
            raise Halt('deadline')
        with parent.db() as db:
            db.execute('BEGIN IMMEDIATE')
            if db.execute("SELECT COUNT(*) FROM events WHERE kind='retry_claim'").fetchone()[0]:
                raise Halt('retry_already_claimed')
            halted = db.execute("SELECT document FROM events WHERE kind='halt'").fetchall()
            codes = [json.loads(row[0]).get('code') for row in halted]
            if codes.count('operator_stop_irrecoverable_build_failure') != 1 or set(codes) - {'operator_stop_irrecoverable_build_failure', 'research_ledger_stopped'}:
                raise Halt('retry_parent_stop_changed')
            claim = dict(child_directory=str(directory.resolve()),
                         child_identity_sha256=sha((directory/'execution-identity.json').read_bytes()),
                         authorization=identity['retry_authorization'],
                         original_deadline=policy['deadline'],
                         parent_requests=len(records),
                         parent_cost_nano_cny=sum(r['cost_nano_cny'] for r in records),
                         claimed_at=parent.clock())
            db.execute("INSERT INTO events(kind,document) VALUES ('retry_claim',?)", (json.dumps(claim,sort_keys=True),))
        # A crash after the durable claim blocks further automatic retry, including an orphan child.
        inherited = dict(money=policy['limit_nano_cny'], requests=policy['limit_requests'],
                         started=policy['started'], deadline=policy['deadline'],
                         prior_requests=len(records)+policy.get('prior_requests',0),
                         prior_cost_nano_cny=sum(r['cost_nano_cny'] for r in records)+policy.get('prior_cost_nano_cny',0))
        return parent, inherited  # Keep parent owner lock for child's entire lifetime.
    except BaseException:
        parent.close()
        raise
