"""Start and stop only owned localhost API/UI processes without credentials."""
import argparse
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time

import httpx
from run_local import offline_environment

ROOT = Path(__file__).resolve().parents[2]
SANDBOX = ROOT / 'var/integration-sandbox'
BASE = 'f5a5dfdec523'
parser = argparse.ArgumentParser()
parser.add_argument('--suffix', default='')
parser.add_argument('--output-directory', type=Path, default=ROOT / 'docs/integration/20261031')
args = parser.parse_args()
assert not args.suffix or args.suffix.isalnum()
suffix = '-' + args.suffix if args.suffix else ''
results = []
for version, root in [('candidate', ROOT), ('baseline', SANDBOX / ('baseline-' + BASE))]:
    for component in ('api', 'ui'):
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        env = offline_environment(root, SANDBOX / 'config.toml')
        if component == 'api':
            command = [sys.executable, '-m', 'uvicorn', 'locomo_memory.api:create_app', '--factory', '--host', '127.0.0.1', '--port', str(port)]
            endpoint = '/health'
        else:
            command = [sys.executable, '-m', 'streamlit', 'run', str(root / 'src/locomo_memory/ui.py'),
                       '--server.address', '127.0.0.1', '--server.port', str(port), '--server.headless', 'true',
                       '--browser.gatherUsageStats', 'false']
            endpoint = '/_stcore/health'
        log = args.output_directory / f'smoke-{version}-{component}{suffix}.txt'
        with log.open('x') as stream:
            process = subprocess.Popen(command, cwd=SANDBOX, env=env, stdout=stream, stderr=subprocess.STDOUT)
            try:
                with httpx.Client(trust_env=False, timeout=2) as client:
                    deadline = time.monotonic() + 25
                    while True:
                        try:
                            response = client.get(f'http://127.0.0.1:{port}' + endpoint)
                            if response.status_code == 200:
                                break
                        except httpx.HTTPError:
                            pass
                        if process.poll() is not None or time.monotonic() > deadline:
                            raise RuntimeError(f'local_smoke_start_failed:{version}:{component}')
                        time.sleep(0.1)
                    record = {'version': version, 'component': component, 'health_status': response.status_code}
                    if component == 'api':
                        builds = client.get(f'http://127.0.0.1:{port}/builds').json()['items']
                        complete = next(b for b in builds if b['status'] == 'complete')
                        exported = client.get(f'http://127.0.0.1:{port}/builds/{complete["build_id"]}/export')
                        assert exported.status_code == 200
                        record.update(complete_build_id=complete['build_id'], export_status=exported.status_code,
                                      export_schema=exported.json()['schema_version'])
                    results.append(record)
            finally:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
print(json.dumps({'checks': results, 'live_model_calls': 0, 'owned_processes_stopped': True}, indent=2))
