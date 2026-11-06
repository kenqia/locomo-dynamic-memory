"""Exercise the public Replay UI, capture synthetic screenshots and a video clip."""
import argparse
import json
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
    data = json.loads((ROOT / 'demo_fixture/product-v1/snapshot.json').read_text(encoding='utf-8'))
    args.output.mkdir(parents=True, exist_ok=False)
    errors, blocked, screenshots = [], [], []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel='msedge', headless=True, args=['--disable-gpu'])
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

        def capture(name):
            main = page.get_by_test_id('stMain')
            height = main.evaluate('(element) => element.scrollHeight')
            page.set_viewport_size({'width': 1280, 'height': min(2000, max(900, height + 20))})
            main.evaluate('(element) => { element.scrollTop = 0; }')
            page.screenshot(path=str(args.output / name), full_page=True)
            page.set_viewport_size({'width': 1280, 'height': 900})
            screenshots.append(name)

        def choose(label, name):
            control = page.get_by_role('combobox', name=label, exact=True)
            control.click()
            control.press('ArrowDown')
            try:
                page.get_by_text(name, exact=True).last.click(timeout=10000)
            except Exception:
                (args.output / 'selector-state.txt').write_text(page.locator('body').inner_text(), encoding='utf-8')
                page.screenshot(path=str(args.output / 'selector-failure.png'))
                raise

        page.goto(args.url)
        expect(page.get_by_text('Replay 快照已载入 · 无 API / 数据库', exact=True)).to_be_visible(timeout=60000)
        capture('replay-overview.png')
        page.get_by_text('Memory', exact=True).click()
        page.get_by_role('button', name='查看完整原文', exact=True).click()
        expect(page.get_by_text('I live in Paris.', exact=True)).to_be_visible()
        capture('replay-memory-source.png')
        page.get_by_text('数据 / 对话 / Build', exact=True).click()
        older = data['builds'][1]['build_id']
        choose('冻结 / 历史 Build', f'complete · {older}')
        expect(page.locator('.dm-context')).to_contain_text(older)
        primary = data['cases'][0]['build_id']
        choose('冻结 / 历史 Build', f'complete · {primary}')
        page.get_by_text('数据 / 对话 / Build', exact=True).click()
        choose('检查记忆', 'Alex plans to visit Tokyo.')
        page.get_by_role('button', name='查看完整原文', exact=True).click()
        expect(page.get_by_text('I plan to visit Tokyo, but no date is decided.', exact=True)).to_be_visible()
        page.get_by_text('Query/Evidence', exact=True).click()
        for case in data['cases']:
            choose('冻结案例', case['case_id'])
            page.get_by_role('button', name='载入冻结案例', exact=True).click()
            trace = data['traces'][case['trace_id']]
            if case['outcome'] == 'failed':
                expect(page.get_by_text('问答执行失败：', exact=False)).to_contain_text(case['error']['code'])
            else:
                expect(page.get_by_text(trace['answer']['answer'], exact=True)).to_be_visible()
            if case['case_id'] == 'success':
                (args.output / 'trace-state.txt').write_text(page.locator('body').inner_text(), encoding='utf-8')
                for stage in ('initial', 'expanded', 'effective/delivered', 'answer/citations'):
                    control = page.get_by_role('radio', name=stage, exact=True)
                    control.focus()
                    control.press('Space')
                page.get_by_role('button', name='查看完整原文', exact=True).click()
                expect(page.get_by_text('I moved from Paris to Rome on 2 May 2023.', exact=True)).to_be_visible()
            if case['case_id'] in ('success', 'insufficient', 'citation_anomaly', 'budget_failure'):
                capture('replay-' + case['case_id'] + '.png')
        page.get_by_text('Experiments', exact=True).click()
        expect(page.get_by_text('可比成功配对', exact=True)).to_be_visible()
        for dimension in ('对话', '题型', '策略'):
            choose('聚合维度', dimension)
        page.get_by_text('补充 / 修复 Run', exact=True).click()
        expect(page.get_by_text('当前公开冻结快照未提供', exact=False)).to_be_visible()
        page.get_by_text('原 Run', exact=True).click()
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
                  'human_review': 'pending; browser automation is not member acceptance'}
        (args.output / 'replay-result.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
        print(json.dumps(result))
        browser.close()


if __name__ == '__main__':
    main()
