"""Capture the synthetic Console with Playwright in a separate environment."""
import argparse
import json
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import expect, sync_playwright


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', required=True)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if urlparse(args.url).hostname not in ('127.0.0.1', 'localhost', '::1'):
        raise ValueError('local_demo_url_required')
    manifest = json.loads(args.manifest.read_text(encoding='utf-8'))
    if manifest['mode'] != 'OFFLINE_SYNTHETIC':
        raise ValueError('synthetic_fixture_required')
    args.output.mkdir(parents=True, exist_ok=False)
    errors = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel='msedge', headless=True, args=['--disable-gpu'])
        page = browser.new_page(viewport={'width': 1280, 'height': 900}, device_scale_factor=1)

        def offline_route(route):
            if urlparse(route.request.url).hostname in ('127.0.0.1', 'localhost', '::1'):
                route.continue_()
            else:
                route.abort()

        page.route('**/*', offline_route)
        page.on('pageerror', lambda error: errors.append(str(error)))

        def capture(name):
            # Fit Streamlit's internal scroll content into the real viewport;
            # body full_page alone clips it. Desktop width remains 1280px.
            main = page.get_by_test_id('stMain')
            height = main.evaluate('(element) => element.scrollHeight')
            page.set_viewport_size({'width': 1280, 'height': min(2000, max(900, height + 20))})
            main.evaluate('(element) => { element.scrollTop = 0; }')
            page.screenshot(path=str(args.output / name), full_page=True)
            page.set_viewport_size({'width': 1280, 'height': 900})

        page.goto(args.url)
        expect(page.get_by_role('heading', name='Research Console', exact=True)).to_be_visible(timeout=60000)
        expect(page.get_by_text('后端已连接 · Console 只读', exact=True)).to_be_visible()
        expect(page.get_by_text('Build status:', exact=False)).to_contain_text('complete')
        expect(page.get_by_text('unknown 原样保留', exact=False)).to_be_visible()
        capture('overview.png')
        page.get_by_text('评审者', exact=True).click()
        expect(page.get_by_text('核对 Build 身份和全部原始字段', exact=True)).to_be_visible()
        page.get_by_text('展示者', exact=True).click()
        page.get_by_text('Memory', exact=True).click()
        expect(page.get_by_role('heading', name='Memory · 记忆与来源', exact=True)).to_be_visible()
        page.get_by_role('button', name='查看完整原文', exact=True).click()
        expect(page.get_by_text('I live in Paris.', exact=True)).to_be_visible()
        capture('memory.png')
        page.get_by_text('Query/Evidence', exact=True).click()
        expected_answers = ('Alex lives in Rome.', 'Alex lives in Paris.',
                            'Sam reports birth years 1990 and 1992; the contradiction remains unresolved.',
                            'Insufficient evidence for the passport number.')
        for case, answer in zip(manifest['cases'], expected_answers):
            page.get_by_label('Trace ID', exact=True).fill(case['trace_id'])
            page.get_by_label('Trace ID', exact=True).press('Tab')
            page.get_by_role('button', name='读取已有 Trace', exact=True).click()
            expect(page.get_by_role('group', name='Chat message from assistant', exact=True)
                   .get_by_text(answer, exact=True)).to_be_visible()
        capture('trace.png')
        page.get_by_text('Experiments', exact=True).click()
        expect(page.get_by_text('可比成功配对', exact=True)).to_be_visible()
        capture('experiments.png')
        page.get_by_text('Demo', exact=True).click()
        expect(page.get_by_role('heading', name='Demo · 合成应用 Replay', exact=True)).to_be_visible()
        capture('demo.png')
        page.get_by_text('五阶段工作流', exact=True).click()
        expect(page.get_by_role('heading', name='上传一份对话数据', exact=True)).to_be_visible()
        page.get_by_text('五阶段工作流', exact=True).click()
        expect(page.get_by_role('heading', name='Research Console', exact=True)).to_be_visible()
        assert not errors, errors
        summary = {'status': 'passed', 'browser': browser.version,
                   'viewport': {'width': 1280, 'height': 900},
                   'screenshot_height': 'expanded to fit actual content; width remains 1280',
                   'synthetic_cases_replayed': len(manifest['cases']),
                   'legacy_workflow_opened': True, 'page_errors': errors,
                   'screenshots': ['overview.png', 'memory.png', 'trace.png', 'experiments.png', 'demo.png'],
                   'scope': 'Console smoke only; not PROD-04 full browser acceptance or human review'}
        (args.output / 'browser-result.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
        print(json.dumps(summary))
        browser.close()


if __name__ == '__main__':
    main()
