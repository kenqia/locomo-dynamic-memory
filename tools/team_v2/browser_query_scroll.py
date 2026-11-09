"""Exercise native wheel scrolling after loading cases and expanding saved Trace."""
import argparse
import hashlib
import json
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
    snapshot = json.loads((Path(__file__).resolve().parents[2] / 'demo_fixture/product-v1/snapshot.json').read_text(encoding='utf-8'))
    source_texts = {entry['dia_id']: entry['text'] for entry in snapshot['sources']}
    errors, blocked, results = [], [], []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel='msedge', headless=True, args=['--disable-gpu'])
        page = browser.new_page(viewport={'width': 1280, 'height': 900})

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

        def state():
            return page.evaluate('''() => {
                const main=document.querySelector('[data-testid="stMain"]');
                return {top:main.scrollTop,height:main.clientHeight,scroll:main.scrollHeight,
                    bodyStyle:document.body.getAttribute('style'),
                    scrollers:Array.from(document.querySelectorAll('main *')).filter(el=>{
                        const s=getComputedStyle(el),r=el.getBoundingClientRect();
                        return r.height>0 && el.scrollHeight>el.clientHeight+1 && ['auto','scroll'].includes(s.overflowY);
                    }).map(el=>({testid:el.dataset.testid,class:el.className,height:el.clientHeight,
                        scroll:el.scrollHeight,top:el.scrollTop,overflow:getComputedStyle(el).overflowY}))};
            }''')

        def probe(name, target=None, must_scroll=False):
            settle()
            page.evaluate('''() => {
                window.__wheelEvents=[];window.__lastScroll=null;window.__scrollSamples=0;
                if(!window.__wheelListener){window.__wheelListener=true;
                    document.addEventListener('wheel', e=>{
                        const record={target:e.target.outerHTML.slice(0,300),delta:e.deltaY,x:e.clientX,y:e.clientY};
                        window.__wheelEvents.push(record);
                        setTimeout(()=>{record.prevented=e.defaultPrevented;},100);
                    }, {capture:true,passive:true});}
            }''')
            if target is not None:
                target.evaluate('(el)=>el.scrollIntoView({block:"start",behavior:"instant"})')
                bounds = target.bounding_box()
                page.mouse.move(bounds['x'] + min(200, bounds['width']/2),
                                min(max(20, bounds['y'] + min(60, bounds['height']/2)), page.viewport_size['height'] - 20))
            else:
                page.mouse.move(500, 700)
            before = state()
            delta = 600 if before['top'] < before['scroll'] - before['height'] - 5 else -600
            page.mouse.wheel(0, delta)
            # Wait for the browser's asynchronous wheel dispatch, without changing scrollTop.
            page.wait_for_function('''() => {
                const m=document.querySelector('[data-testid="stMain"]');
                const v=[m.scrollTop, ...Array.from(document.querySelectorAll('[data-testid="stJson"]')).map(e=>e.scrollTop)];
                const s=JSON.stringify(v);window.__scrollSamples=window.__lastScroll===s?(window.__scrollSamples||0)+1:0;
                window.__lastScroll=s;return window.__scrollSamples>5;
            }''')
            after = state()
            results.append({'name': name, 'before': before, 'after': after, 'delta':delta,
                            'wheel':page.evaluate('window.__wheelEvents')})
            (args.output / 'scroll-probes.json').write_text(json.dumps(results, indent=2), encoding='utf-8')
            page.screenshot(path=str(args.output / (name + '.png')), animations='disabled')
            if must_scroll:
                assert before['scroll'] > before['height'] + 2, (name, before)
                assert (after['top'] - before['top']) * delta > 0, (name, before, after)
                assert not after['scrollers'], (name, after['scrollers'])

        page.goto(args.url)
        expect(page.get_by_role('heading', name='Overview · 工作概览', exact=True)).to_be_visible(timeout=60000)
        (args.output / 'summary-dom.html').write_text(page.locator('.st-key-console_context_summary').evaluate('(el)=>el.outerHTML'), encoding='utf-8')
        choose('Query')
        choose('证据冲突', '冻结案例')
        page.get_by_text('按 Trace ID 读取已有记录', exact=True).click()
        probe('case-selection-then-id-panel')
        page.get_by_role('button', name='载入冻结案例', exact=True).click()
        expect(page.get_by_role('heading', name='回答与来源', exact=True)).to_be_visible()
        probe('case-loaded', must_scroll=True)
        page.get_by_text('评审详情 · 阶段 Trace', exact=True).click()
        choose('expanded', '证据阶段')
        detail = page.get_by_test_id('stExpander').filter(has=page.get_by_text('评审详情 · 阶段 Trace', exact=True))
        fields = detail.get_by_test_id('stExpander').filter(has=page.get_by_text('本阶段已记录字段', exact=True)).last
        assert fields.locator('details').first.get_attribute('open') is None
        page.screenshot(path=str(args.output / 'stage-fields-default-collapsed.png'))
        fields.locator('summary').first.click()
        probe('trace-expanded', detail.get_by_role('radiogroup', name='证据阶段', exact=True), must_scroll=True)
        page.get_by_text('阶段错误、耗时与预算', exact=True).click()
        page.get_by_text('版本身份与完整 Trace（已保存字段）', exact=True).click()
        probe('wheel-over-trace-json', fields.get_by_test_id('stJson'), must_scroll=True)
        complete = page.get_by_test_id('stExpander').filter(has=page.get_by_text('版本身份与完整 Trace（已保存字段）', exact=True))
        probe('wheel-over-complete-json', complete.get_by_test_id('stJson'), must_scroll=True)
        # Repeated source changes must always show the selected original, without a load button.
        sources = detail.get_by_role('radiogroup', name='来源引用', exact=True)
        expect(page.get_by_role('button', name='查看完整原文', exact=True)).to_have_count(0)
        expect(detail.get_by_text('My birth year is 1990.', exact=True)).to_be_visible()
        source_options = sources.get_by_role('radio')
        for step, index in enumerate((1, 0, 1, 0)):
            source_options.nth(index).focus()
            source_options.nth(index).press('Space')
            settle()
            expect(detail.get_by_text(source_texts[('D2:2', 'D2:3')[index]], exact=True)).to_be_visible()
            expect(detail.get_by_text(source_texts[('D2:2', 'D2:3')[1-index]], exact=True)).to_have_count(0)
            page.screenshot(path=str(args.output / f'auto-source-{step}-{index + 1}.png'))
        for width in (1280, 390):
            page.set_viewport_size({'width':width, 'height':900 if width == 1280 else 844})
            for label in ('当前事实', '证据不足', '预算失败'):
                choose(label, '冻结案例')
                page.get_by_role('button', name='载入冻结案例', exact=True).click()
                settle()
                detail = page.get_by_test_id('stExpander').filter(has=page.get_by_text('评审详情 · 阶段 Trace', exact=True))
                if detail.locator('details').first.get_attribute('open') is None:
                    detail.locator('summary').first.click()
                errors_panel = page.get_by_test_id('stExpander').filter(has=page.get_by_text('阶段错误、耗时与预算', exact=True))
                if errors_panel.locator('details').get_attribute('open') is None:
                    errors_panel.locator('summary').click()
                fields = detail.get_by_test_id('stExpander').filter(has=page.get_by_text('本阶段已记录字段', exact=True)).last
                if fields.locator('details').first.get_attribute('open') is None:
                    fields.locator('summary').first.click()
                probe(f'switch-{label}-{width}', fields.get_by_test_id('stJson'), must_scroll=True)
        assert not errors, errors
        assert not blocked, blocked
        source = Path(__file__).resolve().parents[2] / 'src/locomo_memory/console_theme.py'
        (args.output / 'environment.json').write_text(json.dumps({'browser':browser.version,
            'theme_sha256_lf':hashlib.sha256(source.read_bytes().replace(b'\r\n',b'\n')).hexdigest(),
            'source':'local working tree; not published','page_errors':errors,'external_requests':blocked}), encoding='utf-8')
        print(json.dumps({'scenes':len(results),'page_errors':errors}))
        browser.close()


if __name__ == '__main__':
    main()
