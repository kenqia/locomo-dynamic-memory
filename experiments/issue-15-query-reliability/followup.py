"""Freeze the seven-item follow-up, retaining the prior paid-call ledger."""
import argparse
import fcntl
import json

import live


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare', 'execute'])
    parser.add_argument('--directory', required=True, type=live.Path)
    parser.add_argument('--authorized-call-limit', type=int)
    parser.add_argument('--citation-only', action='store_true', help='Separate single-item citation fix verification')
    args = parser.parse_args()
    live.SOURCE = live.ROOT.parent / 'real-baseline-issue15-query-reliability-frozen'
    live.PRIOR = live.SOURCE / 'campaign.sqlite3'
    live.CALL_LIMIT = 32
    live.GROUPS = {'primary': ('dynamic_raw_fallback', [15, 32, 18, 53, 60, 136]),
                   'dynamic_nonregression': ('dynamic', [3])}
    if args.citation_only:
        live.SOURCE = live.ROOT.parent / 'real-baseline-issue15-query-followup-frozen'
        live.PRIOR = live.SOURCE / 'campaign.sqlite3'
        live.CALL_LIMIT = 6
        live.GROUPS = {'primary': ('dynamic_raw_fallback', [136])}
    with live.previous.ORIGINAL_LOCK.open('a+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if args.action == 'prepare':
            plan = live.prepare(args.directory.resolve())
            print(json.dumps({'status':'frozen_pending_authorization', 'call_limit':plan['call_limit'],
                'previous_calls':plan['previous_calls'], 'cumulative_ceiling':plan['cumulative_ceiling']}))
        else:
            live.execute(args.directory.resolve(), args.authorized_call_limit)
