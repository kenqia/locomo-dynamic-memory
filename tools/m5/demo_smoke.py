"""Run the frozen-development demo in an owned offline Streamlit process."""
import argparse
import json
from pathlib import Path
import socket
import subprocess
import sys
import time

import httpx

from tools.integration.run_local import offline_environment
from tools.m5.offline import ROOT, ORIGIN, sha

BROWSER = r'''
import json, sys
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
output = Path(sys.argv[2]); errors = []; console = []
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width':1440, 'height':1100})
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.on('console', lambda m: console.append(m.text) if m.type == 'error' else None)
    page.goto(sys.argv[1])
    expect(page.get_by_text('开发对话', exact=True)).to_be_visible(timeout=30000)
    page.get_by_text('Bonus · 状态演化与 Graph Memory', exact=True).click()
    page.get_by_text('开启只读图浏览', exact=True).click()
    expect(page.get_by_text('查看节点及原文来源', exact=True)).to_be_visible(timeout=30000)
    expect(page.get_by_text('状态维度', exact=True)).to_be_visible(timeout=30000)
    assert page.get_by_test_id('stGraphVizChart').count() == 1
    page.screenshot(path=str(output/'real-development-graph.png'), full_page=True)
    # The default selected node is a real Memory and renders its cited source.
    expect(page.get_by_test_id('stJson').first).to_be_visible(timeout=30000)
    expect(page.get_by_text('· D', exact=False).first).to_be_visible(timeout=30000)
    page.screenshot(path=str(output/'real-development-source.png'), full_page=True)
    assert not errors, errors
    assert not console, console
    result = dict(status='passed', browser=browser.version, pageerrors=errors,
                  console_errors=console, dataset='conv-26', provider_requests=0,
                  mode='frozen real development Build; read-only production Bonus routes in process')
    (output/'result.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result))
    browser.close()
'''


def run(output, browser_python):
    output.mkdir(parents=True, exist_ok=False)
    initial = sha(ORIGIN)
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    env = offline_environment(ROOT, output/'unused-config.toml')
    env['PYTHONPATH'] += ':' + str(ROOT)
    with (output/'streamlit.log').open('x') as log:
        process = subprocess.Popen([sys.executable, '-m', 'streamlit', 'run',
            str(ROOT/'tools/m5/demo.py'), '--server.address', '127.0.0.1', '--server.port', str(port),
            '--server.headless', 'true', '--browser.gatherUsageStats', 'false'],
            cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
        try:
            with httpx.Client(trust_env=False) as client:
                for _ in range(100):
                    if process.poll() is not None:
                        raise RuntimeError('demo exited')
                    try:
                        if client.get(f'http://127.0.0.1:{port}/_stcore/health').status_code == 200:
                            break
                    except httpx.HTTPError:
                        pass
                    time.sleep(.1)
                else:
                    raise RuntimeError('demo health timeout')
            subprocess.run([str(browser_python), '-c', BROWSER, f'http://127.0.0.1:{port}', str(output)],
                           check=True, env=env)
        finally:
            process.terminate()
            process.wait(timeout=15)
    final = sha(ORIGIN)
    (output/'source-identity.json').write_text(json.dumps(dict(before=initial, after=final,
        unchanged=initial == final, holdout_access=False), indent=2))
    if initial != final:
        raise RuntimeError('historical_source_changed')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--browser-python', type=Path, required=True)
    args = parser.parse_args()
    run(args.output.resolve(), args.browser_python)
