"""Own a fresh offline fixture, API/UI processes and Console browser artifacts."""
import argparse
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time

import httpx

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/integration'))
from run_local import offline_environment


def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def wait_for(url, process):
    for _ in range(120):
        if process.poll() is not None:
            raise RuntimeError('demo_process_exited')
        try:
            if httpx.get(url, timeout=1, trust_env=False).status_code == 200:
                return
        except httpx.HTTPError:
            pass
        time.sleep(0.5)
    raise RuntimeError('demo_startup_timed_out')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--browser-python', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.absolute()
    if any(path.is_symlink() for path in (output, *output.parents)):
        raise ValueError('output_symlink_forbidden')
    output = output.resolve()
    output.relative_to((ROOT / 'var').resolve())
    browser_python = args.browser_python.resolve(strict=True)
    output.mkdir(parents=True, exist_ok=False)
    fixture = output / 'fixture'
    api_port, ui_port = free_port(), free_port()
    command = [sys.executable, str(ROOT / 'tools/team_v2/demo.py')]
    options = ['--output', str(fixture), '--api-port', str(api_port), '--ui-port', str(ui_port)]
    subprocess.run(command + ['prepare'] + options, cwd=ROOT, check=True)
    processes, logs = [], []
    env = offline_environment(ROOT, fixture / 'config.toml')
    env['PYTHONPATH'] += os.pathsep + str(ROOT / 'tests') + os.pathsep + str(ROOT / 'tests/browser')
    try:
        for component, port, health in (('api', api_port, '/health'), ('ui', ui_port, '/_stcore/health')):
            log = (output / f'{component}.log').open('w', encoding='utf-8')
            logs.append(log)
            if component == 'api':
                server = [sys.executable, '-m', 'uvicorn', 'server:app_factory', '--factory',
                          '--host', '127.0.0.1', '--port', str(port)]
            else:
                server = [sys.executable, '-m', 'streamlit', 'run', str(ROOT / 'tools/team_v2/demo_ui.py'),
                          '--server.address', '127.0.0.1', '--server.port', str(port),
                          '--server.headless', 'true', '--browser.gatherUsageStats', 'false']
            process = subprocess.Popen(server, cwd=ROOT, env=env, stdout=log, stderr=log)
            processes.append(process)
            wait_for(f'http://127.0.0.1:{port}{health}', process)
        browser_command = [str(browser_python), str(ROOT / 'tools/team_v2/browser_console.py'),
                           '--url', f'http://127.0.0.1:{ui_port}', '--manifest', str(fixture / 'demo-manifest.json'),
                           '--output', str(output / 'screenshots')]
        subprocess.run(browser_command, cwd=ROOT, env=offline_environment(ROOT, fixture / 'config.toml'), check=True)
        manifest = json.loads((fixture / 'demo-manifest.json').read_text(encoding='utf-8'))
        print(json.dumps({'api_health': 'passed', 'ui_health': 'passed',
                          'provider_calls': manifest['provider_calls'], 'output': str(output)}))
    finally:
        for process in reversed(processes):
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10)
        for log in logs:
            log.close()


if __name__ == '__main__':
    main()
