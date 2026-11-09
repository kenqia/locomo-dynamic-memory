"""Aggregate safe ledger fields from frozen database files, without response text."""
import json
from pathlib import Path
import sqlite3

ROOT = Path(__file__).resolve().parents[2]
D = ROOT / 'docs/integration/20261031'
records = []
for item in json.loads((D / 'historical-databases.json').read_text()):
    path = Path(item['path'])
    with sqlite3.connect(path.as_uri() + '?mode=ro&immutable=1', uri=True) as db:
        names = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        tables = []
        for table in ('calls', 'generation_calls', 'provider_calls', 'replay_calls', 'relation_provider_calls'):
            if table not in names:
                continue
            columns = {r[1] for r in db.execute('PRAGMA table_info(' + table + ')')}
            metadata = next((c for c in ('metadata_json', 'metadata', 'diagnostics_json') if c in columns), None)
            row = {'table': table, 'reserved_or_saved_rows': db.execute('SELECT COUNT(*) FROM ' + table).fetchone()[0]}
            if metadata:
                valid = 'json_valid(' + metadata + ')'
                row['valid_metadata_rows'] = db.execute('SELECT COUNT(*) FROM ' + table + ' WHERE ' + valid).fetchone()[0]
                for key in ('completed_at', 'outcome'):
                    row['rows_with_' + key] = db.execute('SELECT COUNT(*) FROM ' + table + ' WHERE ' + valid + " AND json_extract(" + metadata + ", '$." + key + "') IS NOT NULL").fetchone()[0]
                row['reported_tokens'] = {}
                for field in ('prompt_tokens', 'completion_tokens', 'total_tokens'):
                    where = valid + " AND json_type(" + metadata + ", '$.usage." + field + "') IN ('integer','real')"
                    count, total = db.execute('SELECT COUNT(*), SUM(json_extract(' + metadata + ", '$.usage." + field + "')) FROM " + table + ' WHERE ' + where).fetchone()
                    row['reported_tokens'][field] = {'reported_sum': total, 'rows_reported': count, 'rows_without_value': row['reserved_or_saved_rows'] - count}
            tables.append(row)
        if tables:
            records.append({'path': str(path), 'source_sha256': item['sha256'], 'tables': tables})
print(json.dumps({'scope': 'Whitelisted metadata aggregates only; missing usage stays null. Rows may be reservations, historical linked ledgers or duplicate snapshots; never sum these into project requests/cost.', 'databases_with_ledger_tables': len(records), 'databases_scanned': 57, 'records': records}, ensure_ascii=False, indent=2))
