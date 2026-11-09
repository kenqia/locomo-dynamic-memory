"""Capture loaded 1920x1080 Console views from the local OFFLINE SYNTHETIC REPLAY (real page operations)."""
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
URL = 'http://127.0.0.1:18561'
with sync_playwright() as p:
    b = p.chromium.launch(headless=True, args=['--disable-gpu'])
    pg = b.new_page(viewport={'width': 1920, 'height': 1080}, device_scale_factor=1)
    pg.route('**/*', lambda r: r.continue_() if r.request.url.startswith(URL) else r.abort())
    def settle():
        expect(pg.get_by_test_id('stApp')).to_have_attribute('data-test-script-state', 'notRunning', timeout=30000)
        pg.wait_for_timeout(1200)
    def shot(name, full=False):
        settle(); pg.screenshot(path=str(out / name), full_page=full)
    pg.goto(URL); settle()
    # Memory: select Rome memory, show source + relations
    pg.get_by_text('Memory', exact=True).first.click(); settle()
    pg.get_by_test_id('stRadioOption').filter(has_text='Alex lives in Rome.').first.click(); settle()
    shot('01-memory-rome-source.png')
    pg.mouse.wheel(0, 700); shot('02-memory-relations.png')
    pg.get_by_test_id('stRadioOption').filter(has_text='Alex plans to visit Tokyo.').first.click(); settle()
    pg.mouse.wheel(0, -2000); shot('03-memory-plan.png')
    # Query: current fact
    pg.get_by_text('Query', exact=True).first.click(); settle()
    pg.get_by_test_id('stRadioOption').filter(has_text='当前事实').first.click(); pg.get_by_role('button', name='载入冻结案例', exact=True).click(); settle()
    pg.mouse.wheel(0, 380); shot('04-query-current.png')
    pg.mouse.wheel(0, -2000)
    pg.get_by_test_id('stRadioOption').filter(has_text='历史日期').first.click(); pg.get_by_role('button', name='载入冻结案例', exact=True).click(); settle()
    pg.mouse.wheel(0, 380); shot('05-query-historical.png')
    # Trace
    pg.get_by_text('评审详情 · 阶段 Trace', exact=True).click(); settle()
    for stage in ('initial', 'expanded', 'effective/delivered', 'answer/citations'):
        r = pg.get_by_test_id('stRadioOption').filter(has_text=stage).first
        if r.count():
            r.click(); settle()
            r.scroll_into_view_if_needed(); pg.mouse.wheel(0, 250)
            shot('06-trace-' + stage.replace('/', '-') + '.png')
    pg.mouse.wheel(0, -3000)
    pg.get_by_test_id('stRadioOption').filter(has_text='证据冲突').first.click(); pg.get_by_role('button', name='载入冻结案例', exact=True).click(); settle()
    pg.mouse.wheel(0, 380); shot('07-query-conflict.png')
    pg.get_by_text('Experiments', exact=True).first.click(); settle()
    pg.mouse.wheel(0, 650); shot('08-experiments-strategy.png')
    b.close()
print('ok')
