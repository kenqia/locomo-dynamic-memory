"""Check an additive Product candidate on a fixed main export; never merge branches."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile

from demo import ROOT, demo_environment

PRODUCT_FILES = ['console_ui.py', 'console_replay.py', 'evidence_ui.py', 'frozen_report_ui.py',
                 'console_theme.py', 'console_widgets.py']
CORE_FILES = ['query_ui.py', 'queries.py', 'config.py', 'ui.py', 'api.py']


def inspect(directory):
    import httpx
    import sqlite3
    from streamlit.testing.v1 import AppTest
    from locomo_memory.console_replay import ReplayStore
    import locomo_memory.console_ui as console

    calls = []

    def forbidden(*args, **kwargs):
        calls.append(True)
        raise AssertionError('integration_unexpected_network_database_or_generation')

    httpx.request = forbidden
    sqlite3.connect = forbidden
    assert Path(console.__file__).resolve().is_relative_to(directory / 'candidate/src')
    store = ReplayStore(directory / 'candidate/demo_fixture/product-v1')
    app = AppTest.from_string('''
import streamlit as st
from locomo_memory.console_ui import render_console
store = st.session_state['store']
render_console(store.request, evidence_path=store.evidence_path, replay_cases=store.cases)
''', default_timeout=30)
    app.session_state['store'] = store
    app.run()
    assert not app.exception
    for page in ('Memory', 'Query/Evidence', 'Experiments', 'Demo'):
        app.radio(key='console_page').set_value(page).run()
        assert not app.exception, page
    hybrid = AppTest.from_string('''
from locomo_memory.query_ui import render_queries
def forbidden(*args, **kwargs):
    raise AssertionError('unexpected generation')
render_queries(forbidden, 'synthetic', 'conv-a', {'query_ready': True, 'build_id': 'inspection-only'})
''', default_timeout=30).run()
    assert not hybrid.exception
    assert hybrid.selectbox(key='query_strategy').value == 'hybrid_no_resolution'
    assert not calls
    (directory / 'smoke.json').write_text(json.dumps({'status': 'passed', 'pages': ['Overview', 'Memory', 'Query/Evidence', 'Experiments', 'Demo'],
        'main_hybrid_default_preserved': True, 'network_database_generation_attempts': len(calls),
        'python': sys.version.split()[0]}) + '\n', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--main-ref', default='origin/main')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--inspect', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    output = args.output.absolute()
    if any(path.is_symlink() for path in (output, *output.parents)):
        raise ValueError('integration_output_symlink_forbidden')
    output = output.resolve()
    output.relative_to((ROOT / 'var').resolve())
    if args.inspect:
        inspect(output)
        return
    output.mkdir(parents=True, exist_ok=False)
    revision = subprocess.check_output(['git', 'rev-parse', args.main_ref + '^{commit}'], cwd=ROOT, text=True).strip()
    product = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    merge_base = subprocess.run(['git', 'merge-base', revision, product], cwd=ROOT, capture_output=True, text=True)
    archive = output / 'main.zip'
    subprocess.run(['git', 'archive', '--format=zip', f'--output={archive}', revision, 'src'], cwd=ROOT, check=True)
    candidate = output / 'candidate'
    with zipfile.ZipFile(archive) as bundle:
        bundle.extractall(candidate)
    package = candidate / 'src/locomo_memory'
    core_hashes = {name: hashlib.sha256((package / name).read_bytes()).hexdigest() for name in CORE_FILES}
    for name in PRODUCT_FILES:
        path = package / name
        if path.exists():
            raise ValueError('main_product_module_collision:' + name)
        path.write_bytes(subprocess.check_output(['git', 'show', f'{product}:src/locomo_memory/{name}'], cwd=ROOT))
    for name in ('manifest.json', 'snapshot.json', 'research-evidence.json'):
        path = candidate / 'demo_fixture/product-v1' / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(subprocess.check_output(['git', 'show', f'{product}:demo_fixture/product-v1/{name}'], cwd=ROOT))
    env = demo_environment(ROOT / 'config.example.toml')
    env.pop('LOCOMO_CONFIG', None)
    env['PYTHONPATH'] = str(candidate / 'src') + os.pathsep + str(ROOT / 'tools/integration/offline_guard')
    temporary = output / 'temporary'
    temporary.mkdir()
    env.update(TEMP=str(temporary), TMP=str(temporary))
    with (output / 'inspection.log').open('w', encoding='utf-8') as log:
        subprocess.run([sys.executable, str(Path(__file__).resolve()), '--output', str(output), '--inspect'],
                       cwd=ROOT, env=env, stdout=log, stderr=log, check=True)
    assert all(hashlib.sha256((package / name).read_bytes()).hexdigest() == digest for name, digest in core_hashes.items())
    result = {**json.loads((output / 'smoke.json').read_text(encoding='utf-8')), 'main_commit': revision,
              'product_commit': product, 'merge_base': merge_base.stdout.strip() if merge_base.returncode == 0 else None,
              'added_product_modules': PRODUCT_FILES, 'unchanged_main_core_sha256': core_hashes,
              'scope': 'Unmerged additive source candidate smoke only; not full main regression, production acceptance or a merge recommendation.'}
    (output / 'integration-result.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
