"""Real Chromium acceptance of the isolated no-key file replay UI."""
import argparse
import json
import os
from pathlib import Path
import re
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright, expect

p = argparse.ArgumentParser()
p.add_argument('--ui', default='http://127.0.0.1:18510')
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
assert a.ui.startswith('http://127.0.0.1:')
a.output.mkdir(parents=True, exist_ok=True)
errors, external, requests = [], [], []
with sync_playwright() as playwright:
    executable = os.environ.get('LOCOMO_CHROMIUM_EXECUTABLE')
    browser = playwright.chromium.launch(headless=True, **({'executable_path': executable} if executable else {}), args=['--no-sandbox'])
    page = browser.new_page(viewport={'width': 1440, 'height': 1100}, accept_downloads=True)
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.on('console', lambda m: errors.append(m.text) if m.type == 'error' else None)
    def route(request):
        host = urlsplit(request.request.url).hostname
        requests.append({'method': request.request.method, 'host': host})
        if host not in {'127.0.0.1', 'localhost'}:
            external.append(host)
            request.abort()
        else:
            request.continue_()
    page.route('**/*', route)
    page.goto(a.ui)
    expect(page.get_by_role('heading', name='LoCoMo · 只读离线演示')).to_be_visible(timeout=30000)
    expect(page.get_by_text(re.compile('Synthetic / Offline Replay：'))).to_be_visible()
    expect(page.get_by_role('heading', name='历史状态与关系')).to_be_visible()
    page.get_by_text('显示有来源的 Graph', exact=True).click()
    expect(page.get_by_test_id('stGraphVizChart')).to_be_visible(timeout=30000)
    page.screenshot(path=str(a.output/'offline-graph.png'), full_page=True)
    page.get_by_role('combobox').last.press('ArrowDown')
    page.get_by_role('option', name='Historical', exact=True).click()
    expect(page.get_by_text('Alex lives in Paris.', exact=True)).to_be_visible(timeout=10000)
    page.screenshot(path=str(a.output/'offline-historical.png'), full_page=True)
    page.get_by_role('combobox').last.press('ArrowDown')
    page.get_by_role('option', name='Failed Trace', exact=True).click()
    expect(page.get_by_text(re.compile('预录失败 Trace：invalid_source_id'))).to_be_visible()
    page.get_by_text('演示可逆分组（默认关闭，非 QA 增益）', exact=True).click()
    with page.expect_download() as download_info:
        page.get_by_role('button', name='导出 Memory JSON').click()
    download = download_info.value
    download.save_as(str(a.output/'synthetic-export.json'))
    assert json.loads((a.output/'synthetic-export.json').read_text())['schema_version'] == 'memory-export-v2'
    page.screenshot(path=str(a.output/'offline-failed-trace.png'), full_page=True)
    assert not errors, errors
    assert not external, external
    assert all(r['method'] == 'GET' for r in requests), requests
    browser.close()
report = {'status': 'PASS', 'ui': a.ui, 'browser': 'Chromium isolated profile', 'page_errors': errors,
          'external_requests': external, 'http_methods': sorted({r['method'] for r in requests}),
          'provider_requests': 0, 'checked': ['Build selection', 'Memory', 'historical projection', 'relations', 'Graph provenance', 'Source Turn', 'historical answer and citations', 'failed Trace', 'real aggregate separation', 'lossless grouping', 'JSON download']}
(a.output/'browser-result.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report,indent=2))
