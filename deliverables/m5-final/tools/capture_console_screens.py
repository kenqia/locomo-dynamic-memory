import sys
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
out=Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
with sync_playwright() as p:
    b=p.chromium.launch(headless=True,args=['--disable-gpu'])
    pg=b.new_page(viewport={'width':1920,'height':1080})
    pg.route('**/*', lambda r: r.continue_() if '127.0.0.1:18561' in r.request.url else r.abort())
    def settle():
        expect(pg.get_by_test_id('stApp')).to_have_attribute('data-test-script-state','notRunning',timeout=30000)
        pg.wait_for_timeout(1500)
    pg.goto('http://127.0.0.1:18561'); settle()
    pg.screenshot(path=str(out/'1920-overview.png'))
    for name in ['Memory','Query','Experiments','Demo']:
        pg.get_by_text(name, exact=True).first.click(); settle()
        pg.screenshot(path=str(out/f'1920-{name.lower()}.png'))
        pg.screenshot(path=str(out/f'1920-{name.lower()}-full.png'), full_page=True)
    b.close()
print('ok')
