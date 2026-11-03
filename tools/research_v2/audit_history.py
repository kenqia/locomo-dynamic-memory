"""Read development Build metadata from existing SQLite files without recovery."""
import argparse
import json
from pathlib import Path
import sqlite3

DEVELOPMENT = ('conv-26', 'conv-30', 'conv-41', 'conv-42')


def audit(root):
    records = []
    for path in sorted(root.rglob('*.sqlite3')):
        if any(part in {'.venv', 'browser-env', '__pycache__'} for part in path.parts):
            continue
        item = {'path': str(path.resolve()), 'bytes': path.stat().st_size, 'development_builds': []}
        try:
            with sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True) as db:
                db.row_factory = sqlite3.Row
                tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                if 'build_versions' in tables:
                    for row in db.execute('SELECT * FROM build_versions WHERE sample_id IN (?,?,?,?)', DEVELOPMENT):
                        build = dict(row)
                        config = json.loads(build['config_json'])
                        item['development_builds'].append({
                            **{k: build[k] for k in ('build_id', 'sample_id', 'status', 'phase', 'fingerprint', 'source_sha256')},
                            'config_differences_from_production_defaults': {k: {'historical': config.get(k), 'production': v}
                                for k, v in {'model_timeout_seconds': 60, 'model_max_tokens': 8192,
                                             'relation_max_tokens': None, 'resolution_input_budget': 24000}.items() if config.get(k) != v},
                        })
                item['evaluation_run_count'] = db.execute('SELECT COUNT(*) FROM evaluation_runs').fetchone()[0] if 'evaluation_runs' in tables else 0
        except sqlite3.Error as error:
            item['read_error_type'] = type(error).__name__
        records.append(item)
    return {'scope': 'Existing *.sqlite3 under explicit directory; archived tar snapshots not reopened; no evaluation answers/scores read',
            'mode': 'read_only_no_application_factory', 'databases': records,
            'distinct_complete_development_builds': sorted({(b['sample_id'], b['build_id']) for r in records for b in r['development_builds'] if b['status'] == 'complete'})}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.root)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'databases': len(result['databases']), 'distinct_complete_development_builds': result['distinct_complete_development_builds']}))
