"""Verify changed Product pages and shared navigation at the fixed desktop viewport."""
import argparse
import json
import os
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    origin = urlparse(args.url)
    if origin.hostname not in ('localhost', '127.0.0.1', '::1'):
        raise ValueError('local_url_required')
    args.output.mkdir(parents=True, exist_ok=False)
    errors, blocked, screenshots, widths = [], [], [], []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel='msedge', headless=True, args=['--disable-gpu'])
        context = browser.new_context(viewport={'width': 1280, 'height': 900}, accept_downloads=True)
        page = context.new_page()

        def route(request):
            target = urlparse(request.request.url)
            if target.netloc == origin.netloc:
                request.continue_()
            else:
                blocked.append(target.netloc)
                request.abort()

        page.route('**/*', route)
        page.on('pageerror', lambda error: errors.append(str(error)))

        def settle():
            expect(page.get_by_test_id('stApp')).to_have_attribute('data-test-script-state', 'notRunning', timeout=20000)

        def choose(label, name):
            settle()
            control = page.get_by_role('combobox', name=label, exact=True)
            control.evaluate('(el) => el.scrollIntoView({block: "center", behavior: "instant"})')
            control.focus()
            control.press('Escape')
            for _ in range(3):
                control.locator('..').get_by_role('button', name='Open', exact=True).click()
                if control.get_attribute('aria-expanded') == 'true':
                    break
                control.focus()
                control.press('ArrowDown')
            expect(control).to_have_attribute('aria-expanded', 'true')
            page.get_by_role('option').filter(has_text=name).click()
            expect(control).to_have_value(name)
            settle()

        def capture(name, focus=None):
            settle()
            expect(page.get_by_test_id('stException')).to_have_count(0)
            main = page.get_by_test_id('stMain')
            if focus:
                focus.scroll_into_view_if_needed()
            else:
                main.evaluate('(el) => { el.scrollTop = 0; }')
            size = main.evaluate('(el) => ({client: el.clientWidth, scroll: el.scrollWidth})')
            assert size['scroll'] <= size['client'] + 1, size
            widths.append({'scene': name, **size, 'scope': 'main document; table readability also inspected in screenshots'})
            page.screenshot(path=str(args.output / (name + '.png')), animations='disabled')
            height = main.evaluate('(el) => el.scrollHeight')
            page.set_viewport_size({'width': 1280, 'height': min(2600, max(900, height + 20))})
            main.evaluate('(el) => { el.scrollTop = 0; }')
            settle()
            page.screenshot(path=str(args.output / ('full-' + name + '.png')), animations='disabled')
            page.set_viewport_size({'width': 1280, 'height': 900})
            screenshots.append(name + '.png')

        page.goto(args.url)
        page.add_style_tag(content='* { scroll-behavior: auto !important; }')
        expect(page.get_by_role('heading', name='Research Console', exact=True)).to_be_visible(timeout=60000)
        expect(page.get_by_test_id('stMetric').filter(has=page.get_by_text('原 Run 计划组合', exact=True))).to_contain_text('3028')
        final_layout = page.get_by_role('button', name='进入Memory', exact=True).count() > 0
        capture('overview')
        if final_layout:
            page.get_by_role('button', name='进入Memory', exact=True).click()
        else:
            page.get_by_text('Memory', exact=True).click()
        expect(page.get_by_role('heading', name='Memory · 记忆与来源', exact=True)).to_be_visible()
        page.get_by_role('button', name='查看完整原文', exact=True).click()
        expect(page.get_by_text('I live in Paris.', exact=True)).to_be_visible()
        page.get_by_text('Query/Evidence', exact=True).click()
        expect(page.get_by_role('heading', name='选择已有问答记录', exact=True)).to_be_visible()
        page.get_by_role('button', name='载入冻结案例', exact=True).click()
        expect(page.get_by_role('group', name='Chat message from assistant', exact=True)
               .get_by_text('Alex lives in Rome.', exact=True)).to_be_visible()
        page.locator('.st-key-console_answer_sources').get_by_role('button', name='查看完整原文', exact=True).click()
        expect(page.get_by_text('I moved from Paris to Rome on 2 May 2023.', exact=True)).to_be_visible()

        page.get_by_text('Experiments', exact=True).click()
        expect(page.get_by_text('可比成功配对', exact=True)).to_be_visible()
        capture('experiments')
        for dimension in ('对话', '题型', '策略'):
            choose('聚合维度', dimension)
        if final_layout:
            choose('查看分组详情', 'Full Text')
            full_score = page.get_by_test_id('stMetric').filter(has=page.get_by_text('完整分母 QA', exact=True))
            expect(full_score).to_contain_text('unknown')
            choose('查看分组详情', 'Dynamic')
            expect(full_score).to_contain_text('0.5151')
            choose('成本策略', 'Dynamic')
            expect(page.get_by_test_id('stMetric').filter(has=page.get_by_text('已知峰值价估算 CNY', exact=True)))\
                .to_contain_text('98.9305')
            page.get_by_text('完整精度与成本明细', exact=True).click()
            with page.expect_download() as download:
                page.get_by_role('button', name='下载冻结报告 JSON', exact=True).click()
            exported = args.output / 'frozen-research-report.json'
            download.value.save_as(exported)
            reference = json.loads((ROOT / 'demo_fixture/product-v1/research-evidence.json').read_text(encoding='utf-8'))
            assert json.loads(exported.read_text(encoding='utf-8')) == reference
            page.get_by_text('完整精度与成本明细', exact=True).click()
        capture('cost', page.get_by_role('heading', name='历史成本与缺测', exact=True))
        page.get_by_text('补充 / 修复 Run', exact=True).click()
        empty = page.get_by_text('当前公开冻结快照未提供补充 / 修复 Run；不合并、不借用原 Run 成绩填充。', exact=True)
        expect(empty).to_be_visible()
        capture('missing-run', empty)
        page.get_by_text('原 Run', exact=True).click()
        page.get_by_text('Demo', exact=True).click()
        expect(page.get_by_role('heading', name='Demo · 合成应用 Replay', exact=True)).to_be_visible()
        expect(page.get_by_text('当前为固定快照 Replay', exact=False)).to_be_visible()
        capture('demo')
        assert not errors, errors
        assert not blocked, blocked
        result = {'status': 'passed', 'commit': os.environ.get('CONSOLE_EVIDENCE_COMMIT'),
                  'browser': browser.version, 'viewport': {'width': 1280, 'height': 900},
                  'final_layout': final_layout, 'source_jumps_checked': True,
                  'dimensions_checked': ['conversation', 'category', 'strategy'],
                  'lossless_export_checked': final_layout, 'missing_run_checked': True,
                  'api_started': False, 'database_opened': False, 'provider_calls': 0,
                  'page_errors': errors, 'external_origins_blocked': blocked,
                  'width_checks': widths, 'screenshots': screenshots,
                  'scope': 'Changed Overview, Experiments, Demo and shared navigation. Six-case and legacy evidence retained at their recorded commits.',
                  'human_review': 'pending; automation is not member acceptance'}
        (args.output / 'product-final-result.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
        print(json.dumps(result))
        context.close()
        browser.close()


if __name__ == '__main__':
    main()
