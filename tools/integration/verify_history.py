"""Compare baseline and candidate APIs on independent copies, with no generation."""
import argparse
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
BASE = 'f5a5dfdec5235d1c411cb5d4b525467e40fef415'


def verify(mismatches_from=None):
    databases = json.loads((ROOT / 'docs/integration/20261031/historical-databases.json').read_text())
    selected = [item for item in databases if item.get('builds')]
    if mismatches_from:
        paths = {item['source'] for item in json.loads(mismatches_from.read_text())['results']
                 if not item['identical_api_results']}
        selected = [item for item in selected if item['path'] in paths]
    comparisons = []
    with tempfile.TemporaryDirectory(prefix='locomo-history-smoke-') as temp:
        temp = Path(temp)
        frozen_src = temp / 'baseline-src'
        for filename in subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', BASE, 'src'], cwd=ROOT, text=True).splitlines():
            target = frozen_src / Path(filename).relative_to('src')
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(subprocess.check_output(['git', 'show', BASE + ':' + filename], cwd=ROOT))
        for index, item in enumerate(selected):
            source = Path(item['path'])
            states = []
            for version, src in [('baseline', frozen_src), ('candidate', ROOT / 'src')]:
                copy = temp / f'{index}-{version}.sqlite3'
                with sqlite3.connect(source.as_uri() + '?mode=ro&immutable=1', uri=True) as old, sqlite3.connect(copy) as new:
                    old.backup(new)
                env = {k: v for k, v in os.environ.items() if k not in ('DEEPSEEK_API_KEY', 'OPENAI_API_KEY', 'CODEX_ACCESS_TOKEN', 'LOCOMO_CONFIG', 'LOCOMO_LIVE_MODEL')}
                env['PYTHONPATH'] = str(ROOT / 'tools/integration/offline_guard') + os.pathsep + str(src)
                env['HF_HUB_OFFLINE'] = env['TRANSFORMERS_OFFLINE'] = '1'
                output = temp / f'{index}-{version}.json'
                child = subprocess.run([sys.executable, str(ROOT / 'tools/integration/history_smoke_worker.py'), str(copy), str(output)], env=env, capture_output=True, text=True)
                if child.returncode:
                    # Never emit an inherited traceback containing database/provider text.
                    raise RuntimeError(f'historical_smoke_worker_failed:{index}:{version}')
                states.append(json.loads(output.read_text()))
            differing_fields = []
            for before, after in zip(*states):
                before_fields = before.pop('field_hashes')
                after_fields = after.pop('field_hashes')
                differing_fields.extend({'build_id': before['build_id'], 'endpoint': before['endpoint'], 'field_path': key}
                    for key in sorted(before_fields.keys() | after_fields.keys())
                    if before_fields.get(key) != after_fields.get(key))
            comparisons.append({'source': str(source), 'source_sha256_before': item['sha256'],
                                'build_ids': [r['build_id'] for r in item['builds']],
                                'differing_field_paths': differing_fields,
                                'identical_api_results': states[0] == states[1], 'candidate_results': states[1]})
    return {'baseline_commit': BASE, 'databases': len(selected),
            'build_snapshots': sum(len(x['build_ids']) for x in comparisons),
            'identical_api_results': all(x['identical_api_results'] for x in comparisons),
            'results': comparisons, 'live_calls': 0,
            'clock_control': 'Both builds.utc_now and relation_diagnostics.utc_now fixed to 2026-10-31T00:00:00+00:00; no response fields removed.',
            'scope': 'Read all captured historical Build snapshots through API copies. No query answers, held-out results, recovery POSTs, original database writes, or schema migration.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--mismatches-from', type=Path)
    args = parser.parse_args()
    result = verify(args.mismatches_from)
    with args.output.open('x') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'results'}, ensure_ascii=False))
    raise SystemExit(0 if result['identical_api_results'] else 1)
