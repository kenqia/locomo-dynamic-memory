"""Check Console navigation and readability across desktop, tablet and phone widths."""
import argparse
import json
import os
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import expect, sync_playwright


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    origin = urlparse(args.url)
    if origin.hostname not in ('localhost', '127.0.0.1', '::1'):
        raise ValueError('local_url_required')
    args.output.mkdir(parents=True, exist_ok=False)
    results, errors, blocked = [], [], []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel='msedge', headless=True, args=['--disable-gpu'])
        context = browser.new_context(viewport={'width': 1920, 'height': 1080}, accept_downloads=True)
        page = context.new_page()

        def route(request):
            if urlparse(request.request.url).netloc == origin.netloc:
                request.continue_()
            else:
                blocked.append(request.request.url)
                request.abort()

        page.route('**/*', route)
        page.on('pageerror', lambda error: errors.append(str(error)))

        def settle():
            expect(page.get_by_test_id('stApp')).to_have_attribute('data-test-script-state', 'notRunning', timeout=30000)
            expect(page.get_by_test_id('stSkeleton')).to_have_count(0)
            expect(page.get_by_test_id('stException')).to_have_count(0)
            page.wait_for_function('''() => !document.querySelector('[data-stale="true"]')''')

        def radio(name, group=None):
            area = page.get_by_role('radiogroup', name=group, exact=True) if group else page
            option = area.get_by_role('radio', name=name, exact=True)
            option.focus()
            option.press('Space')
            expect(option).to_be_checked()
            settle()

        def screenshot(name):
            settle()
            page.evaluate('() => document.activeElement.blur()')
            page.get_by_test_id('stMain').evaluate('(el) => {el.scrollTop = 0;}')
            page.screenshot(path=str(args.output / (name + '.png')), animations='disabled')

        page.goto(args.url)
        expect(page.get_by_role('radio', name='Overview', exact=True)).to_be_attached(timeout=60000)
        responsive = page.locator('.console-brand').count() > 0
        for width, height in ((390, 844), (768, 1024), (1024, 900), (1280, 900), (1920, 1080)):
            page.set_viewport_size({'width': width, 'height': height})
            for name in ('Overview', 'Memory', 'Query', 'Experiments', 'Demo'):
                radio('Query/Evidence' if name == 'Query' and not responsive else name)
                if name in ('Overview', 'Experiments'):
                    expect(page.get_by_test_id('stMetricValue').filter(has_text='3028')).to_be_visible()
                if name == 'Query':
                    page.get_by_role('button', name='载入冻结案例', exact=True).click()
                    expect(page.get_by_role('group', name='Chat message from assistant', exact=True)
                           .get_by_text('Alex lives in Rome.', exact=True)).to_be_visible()
                settle()
                main = page.get_by_test_id('stMain')
                geometry = main.evaluate('(el) => ({width: el.clientWidth, scroll: el.scrollWidth})')
                if geometry['scroll'] > geometry['width'] + 1:
                    screenshot(f'overflow-{name.lower()}-{width}')
                    overflow = page.locator('body *').evaluate_all('''els => els.filter(el => {
                        const r=el.getBoundingClientRect();return r.width && (r.right>innerWidth+1 || r.left<0);}).map(el=>({
                            tag:el.tagName, class:el.className, testid:el.dataset.testid,
                            text:el.textContent.slice(0,100), html:el.outerHTML.slice(0,500)}))''')
                    (args.output / 'overflow.json').write_text(json.dumps(overflow), encoding='utf-8')
                assert geometry['scroll'] <= geometry['width'] + 1, (width, name, geometry)
                if responsive:
                    layout = page.evaluate('''() => {
                        const box = selector => {const r = document.querySelector(selector).getBoundingClientRect();
                            return {x:r.x, y:r.y, width:r.width, height:r.height};};
                        const nav = document.querySelector('.st-key-console_nav');
                        return {brand: box('.console-brand'), nav: box('.st-key-console_nav'),
                            content: box('[data-testid="stMainBlockContainer"]'),
                            font: parseFloat(getComputedStyle(nav.querySelector('[data-testid="stRadioOption"] p')).fontSize),
                            active: getComputedStyle(nav.querySelector('[data-testid="stRadioOption"][data-selected="true"]')).borderBottomColor};
                    }''')
                    brand, nav = layout['brand'], layout['nav']
                    if width >= 1280:
                        assert abs(brand['y'] + brand['height']/2 - nav['y'] - nav['height']/2) < 12, layout
                    else:
                        assert brand['y'] + brand['height'] <= nav['y'] + 2, layout
                    assert abs(brand['x'] - layout['content']['x'] - (48 if width >= 1600 else max(16, width*.03))) < 2, layout
                    assert layout['font'] >= 14.3, layout
                    assert layout['active'] == 'rgb(37, 99, 166)', layout
                    # No navigation labels or metrics are clipped inside their own boxes.
                    overflow = page.locator('.st-key-console_nav p, [data-testid="stMetricValue"]').evaluate_all(
                        '(els) => els.filter(el => el.scrollWidth > el.clientWidth + 2).map(el => el.textContent)')
                    assert not overflow, (width, name, overflow)
                else:
                    layout = None
                screenshot(f'{name.lower()}-{width}')
                results.append({'viewport': {'width': width, 'height': height}, 'page': name,
                                'main': geometry, 'layout': layout})

        # Verify controls at the smallest width, including origin and failure boundaries.
        page.set_viewport_size({'width': 390, 'height': 844})
        radio('Memory')
        page.get_by_role('button', name='查看完整原文', exact=True).click()
        expect(page.get_by_text('I live in Paris.', exact=True)).to_be_visible()
        radio('Query' if responsive else 'Query/Evidence')
        if responsive:
            for case, code in (('引用异常', 'invalid_output'), ('预算失败', 'conflict_evidence_budget_exceeded')):
                radio(case)
                page.get_by_role('button', name='载入冻结案例', exact=True).click()
                expect(page.get_by_test_id('stAlert').filter(has_text=code)).to_be_visible()
            radio('当前事实')
            page.get_by_role('button', name='载入冻结案例', exact=True).click()
            expect(page.get_by_role('group', name='Chat message from assistant', exact=True)
                   .get_by_text('Alex lives in Rome.', exact=True)).to_be_visible()
            radio('Experiments')
            for dimension in ('对话', '题型', '策略'):
                radio(dimension)
            radio('Full Text', '查看分组详情')
            expect(page.get_by_test_id('stMetric').filter(has=page.get_by_text('完整分母 QA', exact=True))).to_contain_text('unknown')
            radio('Dynamic', '查看分组详情')
            expect(page.get_by_test_id('stMetric').filter(has=page.get_by_text('完整分母 QA', exact=True))).to_contain_text('0.5151')
            radio('Dynamic', '成本策略')
            expect(page.get_by_test_id('stMetric').filter(has=page.get_by_text('已知峰值价估算 CNY', exact=True))).to_contain_text('98.9305')
            page.get_by_text('完整精度与成本明细', exact=True).click()
            with page.expect_download() as download:
                page.get_by_role('button', name='下载冻结报告 JSON', exact=True).click()
            exported = args.output / 'frozen-research-report.json'
            download.value.save_as(exported)
            reference = Path(__file__).resolve().parents[2] / 'demo_fixture/product-v1/research-evidence.json'
            assert json.loads(exported.read_text(encoding='utf-8')) == json.loads(reference.read_text(encoding='utf-8'))
        assert not errors, errors
        assert not blocked, blocked
        result = {'status': 'passed', 'commit': os.environ.get('CONSOLE_EVIDENCE_COMMIT'),
                  'responsive_layout': responsive, 'browser': browser.version,
                  'checks': results, 'page_errors': errors, 'external_requests': blocked,
                  'provider_calls': 0, 'api_started': False, 'database_opened': False,
                  'human_review': 'pending; browser automation is not member acceptance'}
        (args.output / 'responsive-result.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
        print(json.dumps({'status': 'passed', 'responsive_layout': responsive, 'scenes': len(results)}))
        context.close()
        browser.close()


if __name__ == '__main__':
    main()
