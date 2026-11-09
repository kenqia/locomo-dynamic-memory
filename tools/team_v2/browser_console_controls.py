"""Check local Console controls, reviewer spacing and responsive header geometry."""
import argparse
import hashlib
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
    errors, blocked, checks = [], [], []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel='msedge' if os.name == 'nt' else None, headless=True, args=['--disable-gpu'])
        context = browser.new_context(viewport={'width': 1280, 'height': 900})
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
            expect(page.get_by_test_id('stException')).to_have_count(0)
            page.wait_for_function('() => !document.querySelector(\'[data-stale="true"]\')')

        def choose(name, group=None):
            area = page.get_by_role('radiogroup', name=group, exact=True) if group else page
            option = area.get_by_role('radio', name=name, exact=True)
            option.focus()
            option.press('Space')
            expect(option).to_be_checked()
            settle()

        def capture(name):
            settle()
            page.evaluate('() => document.activeElement.blur()')
            page.get_by_test_id('stMain').evaluate('(el) => {el.scrollTop=0;}')
            page.screenshot(path=str(args.output / (name + '.png')), animations='disabled')

        def check_layout(role, name, width):
            settle()
            layout = page.evaluate('''() => {
                const box = selector => {const r=document.querySelector(selector).getBoundingClientRect();
                    return {x:r.x,y:r.y,width:r.width,height:r.height,bottom:r.bottom};};
                const main=document.querySelector('[data-testid="stMain"]');
                return {header:box('.st-key-console_header'), brand:box('.console-brand'),
                    nav:box('.st-key-console_nav'), data:box('.st-key-console_data_context'),
                    summary:box('.st-key-console_context_summary'),
                    badges:Array.from(document.querySelectorAll('.st-key-console_context_summary [class*="st-key-console_status_"]')).map(el=>{
                        const r=el.getBoundingClientRect(),s=getComputedStyle(el);
                        return {height:r.height,bottom:r.bottom,font:getComputedStyle(el.querySelector('[data-testid="stText"]')).fontSize,background:s.backgroundColor};}),
                    mainWidth:main.clientWidth, scrollWidth:main.scrollWidth};
            }''')
            (args.output / 'latest-layout.json').write_text(json.dumps(layout), encoding='utf-8')
            capture(f'{role}-{name.lower()}-{width}')
            assert layout['scrollWidth'] <= layout['mainWidth'] + 1, layout
            assert layout['summary']['bottom'] <= layout['data']['bottom'], layout
            assert len(layout['badges']) == 3, layout
            assert all(item['height'] >= 30 and item['bottom'] <= layout['summary']['bottom'] + 1 for item in layout['badges']), layout
            assert len({item['font'] for item in layout['badges']}) == 1, layout
            assert len({item['background'] for item in layout['badges']}) == 1, layout
            assert layout['data']['y'] >= layout['header']['bottom'] + 6, layout
            if width >= 1280:
                assert 80 <= layout['header']['height'] <= 100, layout
                assert layout['brand']['x'] >= layout['header']['x'] + 18, layout
                assert layout['brand']['y'] >= layout['header']['y'] + 14, layout
                assert abs(layout['brand']['y'] + layout['brand']['height']/2 - layout['nav']['y'] - layout['nav']['height']/2) < 4, layout
            else:
                assert layout['brand']['bottom'] <= layout['nav']['y'] + 1, layout
            if role == 'reviewer':
                review = page.get_by_test_id('stExpander').filter(has=page.get_by_text('核对 Build 身份和全部原始字段', exact=True)).bounding_box()
                assert review['y'] >= layout['data']['bottom'] + 6, (layout, review)
            checks.append({'role': role, 'page': name, 'width': width, **layout})

        page.goto(args.url)
        expect(page.get_by_role('heading', name='Overview · 工作概览', exact=True)).to_be_visible(timeout=60000)
        expect(page.get_by_test_id('stMetricValue').filter(has_text='3028')).to_be_visible()
        settle()
        for width in (1280, 768, 390):
            page.set_viewport_size({'width': width, 'height': 900 if width == 1280 else 1000})
            # The version picker opens in the document, with all controls visible.
            data_toggle = page.get_by_text('数据与版本 · 更换所选记录', exact=True)
            data_toggle.click()
            expect(page.get_by_role('radiogroup', name='构建版本', exact=True)).to_be_visible()
            choose('版本 2 · 已完成', '构建版本')
            expect(page.locator('.st-key-console_context_summary')).to_contain_text('当前版本 2')
            choose('版本 1 · 已完成', '构建版本')
            expect(page.locator('.st-key-console_context_summary')).to_contain_text('当前版本 1')
            capture(f'version-panel-{width}')
            controls = page.locator('.st-key-console_data_controls')
            geometry = controls.get_by_test_id('stColumn').evaluate_all('els=>els.map(el=>({x:el.getBoundingClientRect().x,y:el.getBoundingClientRect().y}))')
            if width >= 1280:
                assert max(item['y'] for item in geometry) - min(item['y'] for item in geometry) < 2, geometry
            else:
                assert all(a['y'] < b['y'] for a, b in zip(geometry, geometry[1:])), geometry
            data_toggle.click()
            for role, label in (('presenter', '展示者'), ('reviewer', '评审者')):
                page.get_by_role('button', name='视图设置', exact=True).click()
                choose(label, '使用场景')
                buttons = page.get_by_role('radiogroup', name='使用场景', exact=True).get_by_test_id('stRadioOption')
                bounds = buttons.evaluate_all('els=>els.map(el=>({x:el.getBoundingClientRect().x,y:el.getBoundingClientRect().y}))')
                assert abs(bounds[0]['y'] - bounds[1]['y']) < 2 and bounds[0]['x'] < bounds[1]['x'], bounds
                page.screenshot(path=str(args.output / f'view-settings-{role}-{width}.png'))
                page.keyboard.press('Escape')
                for name in ('Overview', 'Memory', 'Query', 'Experiments', 'Demo'):
                    choose(name)
                    if name == 'Memory':
                        expect(page.get_by_text('共 6 条记忆 · 已全部显示', exact=True)).to_be_visible()
                        assert page.get_by_role('button', name='分页', exact=True).count() == 0
                    if name == 'Query':
                        page.get_by_role('button', name='载入冻结案例', exact=True).click()
                        expect(page.get_by_role('group', name='Chat message from assistant', exact=True)
                               .get_by_text('Alex lives in Rome.', exact=True)).to_be_visible()
                    if name in ('Overview', 'Experiments'):
                        expect(page.get_by_test_id('stMetricValue').filter(has_text='3028')).to_be_visible()
                    check_layout(role, name, width)
            # Start the next viewport in presenter mode without an open popover.
            page.get_by_role('button', name='视图设置', exact=True).click()
            choose('展示者', '使用场景')
            page.keyboard.press('Escape')
        assert not errors, errors
        assert not blocked, blocked
        root = Path(__file__).resolve().parents[2]
        files = ['console_ui.py', 'console_theme.py', 'console_widgets.py', 'evidence_ui.py']
        result = {'status': 'passed', 'source': 'local working tree; not submitted for member review',
                  'base_commit': os.environ.get('CONSOLE_EVIDENCE_COMMIT'), 'browser': browser.version,
                  'source_sha256_lf': {name: hashlib.sha256((root / 'src/locomo_memory' / name).read_bytes().replace(b'\r\n', b'\n')).hexdigest() for name in files},
                  'checks': checks, 'page_errors': errors, 'external_requests': blocked,
                  'provider_calls': 0, 'api_started': False, 'database_opened': False}
        (args.output / 'controls-result.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
        print(json.dumps({'status': 'passed', 'scenes': len(checks), 'source': result['source']}))
        context.close()
        browser.close()


if __name__ == '__main__':
    main()
