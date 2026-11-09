"""Exercise the public Replay UI, capture synthetic screenshots and a video clip."""
import argparse
import json
import os
from pathlib import Path
import re
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
    data = json.loads((ROOT / 'demo_fixture/product-v1/snapshot.json').read_text(encoding='utf-8'))
    args.output.mkdir(parents=True, exist_ok=False)
    errors, blocked, screenshots = [], [], []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel='msedge' if os.name == 'nt' else None, headless=True, args=['--disable-gpu'])
        context = browser.new_context(viewport={'width': 1280, 'height': 900},
                                      record_video_dir=str(args.output / 'video'),
                                      record_video_size={'width': 1280, 'height': 900})
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

        def capture(name):
            settle()
            if name in ('replay-overview.png', 'replay-experiments.png'):
                expect(page.get_by_test_id('stMetric').filter(has=page.get_by_text('原 Run 计划组合', exact=True))).to_contain_text('3028')
            main = page.get_by_test_id('stMain')
            main.evaluate('(element) => { element.scrollTop = 0; }')
            page.screenshot(path=str(args.output / ('viewport-' + name)), animations='disabled')
            height = main.evaluate('(element) => element.scrollHeight')
            page.set_viewport_size({'width': 1280, 'height': min(2000, max(900, height + 20))})
            main.evaluate('(element) => { element.scrollTop = 0; }')
            settle()
            if name in ('replay-overview.png', 'replay-experiments.png'):
                expect(page.get_by_test_id('stMetric').filter(has=page.get_by_text('原 Run 计划组合', exact=True))).to_contain_text('3028')
            page.screenshot(path=str(args.output / name), full_page=True, animations='disabled')
            page.set_viewport_size({'width': 1280, 'height': 900})
            screenshots.append(name)

        def choose(label, name):
            control = page.get_by_role('combobox', name=label, exact=True)
            try:
                settle()
                control.evaluate('(el) => el.scrollIntoView({block: "center", behavior: "instant"})')
                expect(control).to_be_in_viewport()
                control.focus()
                expect(control).to_be_focused()
                control.press('Escape')
                expect(control).to_have_attribute('aria-expanded', 'false')
                for attempt in range(3):
                    control.locator('..').get_by_role('button', name='Open', exact=True).click()
                    try:
                        expect(control).to_have_attribute('aria-expanded', 'true', timeout=1000)
                        break
                    except AssertionError:
                        control.focus()
                        control.press('ArrowDown')
                        if control.get_attribute('aria-expanded') == 'true':
                            break
                expect(control).to_have_attribute('aria-expanded', 'true')
                page.get_by_role('listbox').wait_for(state='visible', timeout=10000)
                page.get_by_role('option').filter(has_text=name).click(timeout=10000)
                settle()
                expect(control).to_have_value(name)
            except Exception:
                (args.output / 'selector-state.txt').write_text(page.locator('body').inner_text(), encoding='utf-8')
                (args.output / 'page-errors.json').write_text(json.dumps(errors), encoding='utf-8')
                (args.output / 'selector-control.html').write_text(control.evaluate('(el) => el.parentElement.parentElement.outerHTML'), encoding='utf-8')
                page.screenshot(path=str(args.output / 'selector-failure.png'))
                raise
            settle()

        page.goto(args.url)
        page.add_style_tag(content='* { scroll-behavior: auto !important; }')
        expect(page.get_by_role('heading', name='Research Console', exact=True)).to_be_visible(timeout=60000)
        capture('replay-overview.png')
        page.get_by_text('Memory', exact=True).click()
        expect(page.get_by_role('heading', name=re.compile(r'^Memory ·'))).to_be_visible()
        settle()
        reworked = page.get_by_role('heading', name='Memory · 记忆与来源', exact=True).count() > 0
        if reworked:
            assert page.get_by_test_id('stDataFrame').count() == 0
        page.get_by_role('button', name='查看完整原文', exact=True).click()
        settle()
        expect(page.get_by_text('I live in Paris.', exact=True)).to_be_visible()
        capture('replay-memory-source.png')
        page.get_by_text('数据 / 对话 / Build', exact=True).click()
        older = data['builds'][1]['build_id']
        choose('冻结 / 历史 Build', '版本 2 · complete' if reworked else f'complete · {older}')
        if reworked:
            expect(page.get_by_test_id('stJson').first).to_contain_text(older)
        else:
            expect(page.locator('.dm-context')).to_contain_text(older)
        primary = data['cases'][0]['build_id']
        choose('冻结 / 历史 Build', '版本 1 · complete' if reworked else f'complete · {primary}')
        page.get_by_text('数据 / 对话 / Build', exact=True).click()
        if reworked:
            memory = page.get_by_role('radio', name='Alex plans to visit Tokyo.', exact=True)
            memory.focus()
            memory.press('Space')
            expect(memory).to_be_checked()
            settle()
        else:
            choose('检查记忆', 'Alex plans to visit Tokyo.')
        page.get_by_role('button', name='查看完整原文', exact=True).click()
        expect(page.get_by_text('I plan to visit Tokyo, but no date is decided.', exact=True)).to_be_visible()
        page.get_by_text('Query/Evidence', exact=True).click()
        for case in data['cases']:
            choose('冻结案例', case['case_id'])
            page.get_by_role('button', name='载入冻结案例', exact=True).click()
            settle()
            trace = data['traces'][case['trace_id']]
            if case['outcome'] == 'failed':
                expect(page.get_by_text('问答执行失败：', exact=False)).to_contain_text(case['error']['code'])
            else:
                answer_area = page.get_by_role('group', name='Chat message from assistant', exact=True) if reworked else page
                expect(answer_area.get_by_text(trace['answer']['answer'], exact=True)).to_be_visible()
            if case['case_id'] == 'success':
                (args.output / 'trace-state.txt').write_text(page.locator('body').inner_text(), encoding='utf-8')
                if reworked:
                    page.get_by_text('评审详情 · 阶段 Trace', exact=True).click()
                for stage in ('initial', 'expanded', 'effective/delivered', 'answer/citations'):
                    control = page.get_by_role('radio', name=stage, exact=True)
                    control.focus()
                    control.press('Space')
                    expect(control).to_be_checked()
                    settle()
                    if reworked:
                        detail = page.get_by_test_id('stExpander').filter(
                            has=page.get_by_text('评审详情 · 阶段 Trace', exact=True))
                        field = {'initial': 'initial_candidates', 'expanded': 'candidates',
                                 'effective/delivered': 'source_delivery', 'answer/citations': 'answer'}[stage]
                        expect(detail.get_by_test_id('stJson').first).to_contain_text(field)
                source_area = page.locator('.st-key-console_answer_sources') if reworked else page
                source_area.get_by_role('button', name='查看完整原文', exact=True).click()
                expect(page.get_by_text('I moved from Paris to Rome on 2 May 2023.', exact=True)).to_be_visible()
                if reworked:
                    page.get_by_text('评审详情 · 阶段 Trace', exact=True).click()
            if case['case_id'] in ('success', 'insufficient', 'citation_anomaly', 'budget_failure'):
                capture('replay-' + case['case_id'] + '.png')
        if reworked:
            page.get_by_text('按 Trace ID 读取已有记录', exact=True).click()
            trace_input = page.get_by_role('textbox', name='Trace ID', exact=True)
            trace_input.fill('not-a-saved-trace')
            trace_input.press('Tab')
            settle()
            expect(page.get_by_role('button', name='读取已有 Trace', exact=True)).to_be_enabled()
            page.get_by_role('button', name='读取已有 Trace', exact=True).click()
            expect(page.get_by_text('未找到此 Trace ID', exact=False)).to_be_visible()
            expect(page.get_by_text('后端读取失败', exact=False)).not_to_be_visible()
            trace_input.fill('../health')
            trace_input.press('Tab')
            settle()
            page.get_by_role('button', name='读取已有 Trace', exact=True).click()
            expect(page.get_by_text('Trace ID 格式无效', exact=False)).to_be_visible()
            choose('冻结案例', 'success')
            page.get_by_role('button', name='载入冻结案例', exact=True).click()
            expect(page.get_by_role('group', name='Chat message from assistant', exact=True)
                   .get_by_text('Alex lives in Rome.', exact=True)).to_be_visible()
            page.get_by_text('按 Trace ID 读取已有记录', exact=True).click()
        page.get_by_text('Experiments', exact=True).click()
        expect(page.get_by_text('可比成功配对', exact=True)).to_be_visible()
        for dimension in ('对话', '题型', '策略'):
            choose('聚合维度', dimension)
        page.get_by_text('补充 / 修复 Run', exact=True).click()
        expect(page.get_by_text('当前公开冻结快照未提供', exact=False)).to_be_visible()
        page.get_by_text('原 Run', exact=True).click()
        settle()
        expect(page.get_by_text('可比成功配对', exact=True)).to_be_visible()
        capture('replay-experiments.png')
        page.get_by_text('Demo', exact=True).click()
        expect(page.get_by_text('当前为固定快照 Replay', exact=False)).to_be_visible()
        capture('replay-demo.png')
        assert not errors, errors
        video = page.video
        context.close()
        video.save_as(args.output / 'console-replay-clip.webm')
        video.delete()
        result = {'status': 'passed', 'browser': browser.version, 'viewport': {'width': 1280, 'height': 900},
                  'cases_replayed': len(data['cases']), 'historical_build_checked': True,
                  'source_jumps_checked': True, 'api_started': False, 'database_opened': False,
                  'provider_calls': 0, 'page_errors': errors, 'external_origins_blocked': sorted(set(blocked)),
                  'screenshots': screenshots, 'video': 'console-replay-clip.webm',
                  'ui_reworked': reworked, 'invalid_trace_recovery_checked': reworked,
                  'fixed_viewport_screenshots': ['viewport-' + name for name in screenshots],
                  'human_review': 'pending; browser automation is not member acceptance'}
        (args.output / 'replay-result.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
        print(json.dumps(result))
        browser.close()


if __name__ == '__main__':
    main()
