"""Read safe live counters without issuing application or provider requests."""

import argparse
from collections import Counter
import json
from pathlib import Path
import sqlite3

from locomo_memory.model import utc_now
from locomo_memory.usage import provider_usage


def status(directory):
    with sqlite3.connect((directory / 'provider-budget.sqlite3').as_uri() + '?mode=ro', uri=True) as db:
        db.execute('PRAGMA query_only=ON')
        header = json.loads(db.execute('SELECT value FROM header').fetchone()[0])
        rows = db.execute('SELECT operation,metadata FROM calls ORDER BY sequence').fetchall()
    calls = [json.loads(row[1]) for row in rows]
    result = {'observed_at': utc_now(), 'implementation_sha256': header['implementation_sha256'],
              'call_limit': header['limit'], 'previous_verification_calls': header['previous_calls'],
              'reserved_new_calls': len(calls), 'reserved_total_calls': len(calls) + header['previous_calls'],
              'operations': dict(Counter(row[0] for row in rows)),
              'outcomes': dict(Counter(call.get('outcome', 'unknown') for call in calls)),
              'error_codes': dict(Counter(call['error_code'] for call in calls if call.get('error_code'))),
              'usage': provider_usage(calls)}
    with sqlite3.connect((directory / 'memory.sqlite3').as_uri() + '?mode=ro', uri=True) as db:
        db.execute('PRAGMA query_only=ON')
        build = db.execute("SELECT build_id,status,phase FROM build_versions WHERE sample_id='conv-26'").fetchone()
        if build:
            result['build_id'], result['build_status'], result['build_phase'] = build
            for table, field in [('build_fragments', 'fragments'), ('relation_tasks', 'relation_tasks')]:
                result[field] = dict(db.execute(f'SELECT status,COUNT(*) FROM {table} WHERE build_id=? GROUP BY status', (build[0],)))
            result['memory_count'] = db.execute('SELECT COUNT(*) FROM memories WHERE build_id=?', (build[0],)).fetchone()[0]
            result['relation_label_counts'] = dict(db.execute('SELECT label,COUNT(*) FROM memory_relations WHERE build_id=? GROUP BY label', (build[0],)))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--compact', action='store_true')
    args = parser.parse_args()
    result = status(args.directory.resolve())
    if args.compact:
        result = {key: result.get(key) for key in ('observed_at', 'build_status', 'build_phase',
            'relation_tasks', 'reserved_total_calls', 'error_codes')}
    print(json.dumps(result, ensure_ascii=False))
