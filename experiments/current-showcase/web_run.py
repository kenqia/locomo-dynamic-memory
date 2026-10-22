"""Launch an isolated read-only API/UI and capture saved real experiment results."""
import argparse
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from urllib.request import urlopen


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--directory', required=True, type=Path)
parser.add_argument('--output', required=True, type=Path)
parser.add_argument('--browser-python', required=True)
args = parser.parse_args()
directory, output = args.directory.resolve(), args.output.resolve()
output.mkdir(exist_ok=True, parents=True)
assert json.loads((directory / 'outcome.json').read_text())['status'] in ('completed', 'completed_with_errors')
for port in (18020, 18521):
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', port))
config = directory / 'web-display.toml'
config.write_text(f'db_path = {json.dumps(str(directory / "memory.sqlite3"))}\napi_url = "http://127.0.0.1:18020"\n')
env = dict(os.environ)
env.pop('DEEPSEEK_API_KEY', None)
env.update(LOCOMO_CONFIG=str(config), LOCOMO_SHOWCASE_DIRECTORY=str(directory),
           PYTHONPATH=str(Path(__file__).parent.resolve()), HF_HUB_OFFLINE='1')
processes = []
try:
    with (directory / 'web-api.log').open('w') as api_log, (directory / 'web-ui.log').open('w') as ui_log:
        processes.append(subprocess.Popen([sys.executable, '-m', 'uvicorn', 'web:app_factory', '--factory',
            '--host', '127.0.0.1', '--port', '18020', '--no-access-log'], env=env, stdout=api_log, stderr=subprocess.STDOUT))
        processes.append(subprocess.Popen([sys.executable, '-m', 'streamlit', 'run', 'src/locomo_memory/ui.py',
            '--server.address', '127.0.0.1', '--server.port', '18521', '--server.headless', 'true',
            '--browser.gatherUsageStats', 'false'], env=env, stdout=ui_log, stderr=subprocess.STDOUT))
        deadline = time.monotonic()+60
        while True:
            assert all(p.poll() is None for p in processes), 'isolated_web_service_exited'
            try:
                with urlopen('http://127.0.0.1:18020/health', timeout=1), urlopen('http://127.0.0.1:18521/_stcore/health', timeout=1):
                    break
            except OSError:
                assert time.monotonic() < deadline, 'isolated_web_start_timeout'
                time.sleep(.5)
        subprocess.run([args.browser_python, str(Path(__file__).with_name('browser.py')),
            '--directory', str(directory), '--output', str(output)], env=env, check=True)
finally:
    for process in processes:
        process.terminate()
    for process in processes:
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
