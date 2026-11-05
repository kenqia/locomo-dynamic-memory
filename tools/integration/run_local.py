"""Run a candidate or fixed-baseline app against an isolated database copy.

This launcher creates only new sandbox files. It never points the app at a source
historical database, overwrites config, or changes Git state.
"""
import argparse
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
BASE = 'f5a5dfdec5235d1c411cb5d4b525467e40fef415'


def preserve_or_create(path, data):
    if path.exists():
        if path.is_symlink() or path.read_bytes() != data:
            raise ValueError('existing_sandbox_file_differs:' + str(path))
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(data)


def prepare(version, seed):
    sandbox = ROOT / 'var/integration-sandbox'
    sandbox.mkdir(parents=True, exist_ok=True)
    database = sandbox / 'memory.sqlite3'
    if seed:
        seed = seed.resolve(strict=True)
        if database.exists() or database.is_symlink():
            raise ValueError('sandbox_database_already_exists; omit --seed-db to reuse it')
        with sqlite3.connect(seed.as_uri() + '?mode=ro&immutable=1', uri=True) as source, sqlite3.connect(database) as target:
            source.backup(target)
    elif database.is_symlink():
        raise ValueError('sandbox_database_must_not_be_symlink')
    config = sandbox / 'config.toml'
    text = 'db_path = ' + json.dumps(str(database)) + '\napi_url = "http://127.0.0.1:8000"\n'
    preserve_or_create(config, text.encode())
    code_root = ROOT
    if version == 'baseline':
        code_root = sandbox / ('baseline-' + BASE[:12])
        files = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', BASE, 'src', 'data/raw/locomo'], cwd=ROOT, text=True).splitlines()
        for filename in files:
            preserve_or_create(code_root / filename, subprocess.check_output(['git', 'show', BASE + ':' + filename], cwd=ROOT))
        preserve_or_create(code_root / 'BASE_COMMIT', (BASE + '\n').encode())
    return sandbox, database, config, code_root


def offline_environment(code_root, config):
    """Review apps inherit neither account credentials nor external networking."""
    blocked = {'DEEPSEEK_API_KEY', 'OPENAI_API_KEY', 'CODEX_ACCESS_TOKEN',
               'LOCOMO_CONFIG', 'LOCOMO_LIVE_MODEL', 'LOCOMO_LOCAL_EMBEDDING'}
    env = {key: value for key, value in os.environ.items() if key not in blocked}
    env['PYTHONPATH'] = str(ROOT / 'tools/integration/offline_guard') + os.pathsep + str(code_root / 'src')
    env['LOCOMO_CONFIG'] = str(config)
    env['HF_HUB_OFFLINE'] = env['TRANSFORMERS_OFFLINE'] = '1'
    return env


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('version', choices=['candidate', 'baseline'])
    parser.add_argument('component', choices=['prepare', 'api', 'ui'], default='api', nargs='?')
    parser.add_argument('--seed-db', type=Path)
    args = parser.parse_args()
    sandbox, database, config, code_root = prepare(args.version, args.seed_db)
    summary = {'version': args.version, 'baseline_commit': BASE, 'database_copy': str(database),
               'config': str(config), 'code': str(code_root), 'component': args.component,
               'mode': 'offline_review_no_account_credentials_or_external_network'}
    print(json.dumps(summary, ensure_ascii=False), flush=True)
    if args.component == 'prepare':
        return
    env = offline_environment(code_root, config)
    if args.component == 'api':
        command = [sys.executable, '-m', 'uvicorn', 'locomo_memory.api:create_app', '--factory', '--host', '127.0.0.1', '--port', '8000']
    else:
        command = [sys.executable, '-m', 'streamlit', 'run', str(code_root / 'src/locomo_memory/ui.py'),
                   '--server.address', '127.0.0.1', '--server.port', '8501', '--browser.gatherUsageStats', 'false']
    os.chdir(sandbox)
    os.execve(sys.executable, command, env)


if __name__ == '__main__':
    main()
