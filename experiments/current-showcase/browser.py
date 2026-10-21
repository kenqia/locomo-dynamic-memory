"""Inspect the real Streamlit app using saved real traces, without new generation."""
import argparse
import json
from pathlib import Path
import re
from urllib.request import urlopen

from playwright.sync_api import sync_playwright, expect


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--directory', required=True, type=Path)
parser.add_argument('--output', required=True, type=Path)
parser.add_argument('--ui', default='http://127.0.0.1:18521')
parser.add_argument('--api', default='http://127.0.0.1:18020')
args = parser.parse_args()
assert args.ui.startswith('http://127.0.0.1:') and args.api.startswith('http://127.0.0.1:')
args.output.mkdir(parents=True, exist_ok=True)
plan = json.loads((args.directory / 'plan.json').read_text())
run = json.loads((args.directory / 'paired-run.json').read_text())
dynamic = json.loads((args.directory / 'dynamic-results.json').read_text())
raw = [i['result']['trace'] for i in run['items'] if i['strategy'] == 'dynamic_raw_fallback'
       and i['status'] == 'succeeded']
assert raw
short = raw[0]
fallback = next((t for t in raw if t.get('raw_fallback', {}).get('triggered')), short)
insufficient = next((t for t in raw if t['answer']['status'] == 'insufficient'), short)
history = next((r['trace'] for r in dynamic if r['status'] == 'succeeded'), short)
scenarios = [('answer-and-source', short), ('history-and-effective-memory', history),
             ('incremental-raw-trace', fallback), ('insufficient-evidence', insufficient),
             ('strategy-switch-keeps-answer', short)]


def get(path):
    with urlopen(args.api + path) as response:
        return json.load(response)


results, errors, console_errors = [], [], []
with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True, args=['--no-sandbox'])
    context = browser.new_context(viewport={'width': 1440, 'height': 1100})
    page = context.new_page()
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.on('console', lambda message: console_errors.append(message.text) if message.type == 'error' else None)

    def settle():
        expect(page.get_by_test_id('stApp')).to_have_attribute('data-test-script-state', 'notRunning', timeout=60000)

    def choose(label, value):
        control = page.get_by_label(label, exact=True)
        control.click()
        page.get_by_role('option', name=value, exact=True).click()
        settle()

    page.goto(args.ui)
    settle()
    choose('数据集', plan['source_dataset_id'])
    choose('对话 sample_id', 'conv-26')
    choose('构建版本', plan['source_build_id'])
    for name, trace in scenarios:
        question_field = page.get_by_label('英文问题', exact=True)
        question_field.fill(trace['question'])
        question_field.press('Tab')
        settle()
        field = page.get_by_label('查看已有 Trace ID（含失败记录）', exact=True)
        field.fill(trace['trace_id'])
        field.press('Tab')
        settle()
        page.get_by_role('button', name='读取问答 Trace', exact=True).click()
        settle()
        caption = page.get_by_text(re.compile(r'^Trace [a-f0-9]+ · 固定构建'))
        expect(caption).to_contain_text(trace['trace_id'])
        expect(page.get_by_text(trace['answer']['answer'], exact=True).first).to_be_visible()
        if name == 'answer-and-source':
            citation = page.get_by_text('回答引用：', exact=False).first
            if citation.count():
                citation.click()
                settle()
        elif name in ('history-and-effective-memory', 'incremental-raw-trace'):
            page.get_by_text('初始候选、历史扩展、有效集合与排除理由', exact=True).click()
            if name == 'incremental-raw-trace':
                page.get_by_text('完整 Trace、实际配置、模型调用及用量', exact=True).click()
        elif name == 'strategy-switch-keeps-answer':
            radio = page.get_by_role('radio', name='Dynamic + 原文兜底', exact=True)
            (page.get_by_role('radio', name='Dynamic', exact=True) if radio.is_checked() else radio).press('Space')
            settle()
            expect(caption).to_contain_text(trace['trace_id'])
            expect(page.get_by_text(trace['answer']['answer'], exact=True).first).to_be_visible()
        caption.scroll_into_view_if_needed()
        page.screenshot(path=str(args.output / f'{name}.png'))
        results.append(dict(scenario=name, trace_id=trace['trace_id'], question=trace['question'],
            answer=trace['answer'], raw_triggered=trace.get('raw_fallback', {}).get('triggered'),
            status='passed', screenshot=f'{name}.png', mode='recorded_real_trace_no_provider_calls'))
    version = browser.version
    context.close()
    browser.close()
assert not errors and not console_errors, (errors, console_errors)
(args.output / 'results.json').write_text(json.dumps(dict(browser=version,
    mode='Unchanged Streamlit app with read-only API and saved real current-experiment traces; not new live generation',
    scenarios=results, pageerrors=errors, console_errors=console_errors), ensure_ascii=False, indent=2)+'\n')
print(json.dumps({'passed': len(results), 'browser': version, 'pageerrors': errors, 'console_errors': console_errors}))
