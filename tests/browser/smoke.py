"""Run with an isolated Playwright installation; only known localhost URLs.

The API and Streamlit processes must already use the isolated smoke configuration.
No authenticated browser profile, secret files, or direct database access is used.
"""
import argparse
import json
import re
import subprocess
import time
from pathlib import Path
from urllib.request import urlopen
from playwright.sync_api import sync_playwright, expect
from diagnostics import browser_diagnostics

parser = argparse.ArgumentParser()
parser.add_argument('--ui', default='http://127.0.0.1:18501')
parser.add_argument('--api', default='http://127.0.0.1:18000')
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--app-python', required=True, help='Isolated application interpreter used for export validation')
args = parser.parse_args()
assert args.ui.startswith('http://127.0.0.1:') and args.api.startswith('http://127.0.0.1:')
args.output.mkdir(parents=True, exist_ok=True)

def get(path):
    with urlopen(args.api + path) as response:
        return json.load(response)

sample = json.loads(Path(__file__).with_name("sample.json").read_text())
with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True, args=['--no-sandbox'])
    with browser_diagnostics(browser, args.output) as (page, errors, console_errors):
        def settle():
            page.wait_for_timeout(300)
            expect(page.get_by_test_id('stApp')).to_have_attribute('data-test-script-state', 'notRunning', timeout=30000)

        def click(name):
            print('UI action:', name, flush=True)
            settle()
            page.get_by_role('button', name=name, exact=True).click()
            settle()

        def fill(label, value):
            settle()
            field = page.get_by_label(label, exact=True)
            field.fill(value)
            field.press('Tab')
            settle()
            expect(field).to_have_value(value)

        def open_expander(name):
            settle()
            summary = page.get_by_text(name, exact=True)
            details = summary.locator('xpath=ancestor::details')
            if details.get_attribute('open') is None:
                summary.click()
                settle()

        page.goto(args.ui)
        expect(page.get_by_role('heading', name='上传一份对话数据', exact=True)).to_be_visible()
        page.get_by_test_id('stFileUploader').first.locator('input[type=file]').set_input_files({'name': 'browser-synthetic.json', 'mimeType': 'application/json', 'buffer': json.dumps(sample).encode()})
        click('上传并继续')
        expect(page.get_by_role('heading', name='选择要处理的对话', exact=True)).to_be_visible()
        click('使用 conv-a')
        expect(page.get_by_role('heading', name='构建这段对话的记忆', exact=True)).to_be_visible()
        dataset = get('/datasets')['items'][0]['dataset_id']
        original = get(f'/datasets/{dataset}/conversations/conv-a/turns')
        open_expander('检查原始对话')
        page.get_by_label('按 dia_id 定位原文', exact=True).fill('D1:1')
        click('读取这一轮')
        expect(page.get_by_text('I live in Paris.', exact=False).first).to_be_visible()
        page.wait_for_timeout(1000)
        click('开始构建 Memory')
        page.wait_for_timeout(1500)
        click('刷新当前状态')
        expect(page.get_by_text('抽取失败', exact=True)).to_be_visible(timeout=20000)
        build = get('/builds')['items'][0]['build_id']
        assert get(f'/builds/{build}')['progress']['failed'] == 1
        page.screenshot(path=str(args.output / 'issue-12-build-failure.png'), full_page=True)
        click('重试未完成片段')
        page.wait_for_timeout(1500)
        click('刷新当前状态')
        expect(page.get_by_text('Memory 已生成', exact=True)).to_be_visible(timeout=20000)
        click('建立检索索引')
        expect(page.get_by_text('检索索引已建立', exact=True)).to_be_visible(timeout=20000)
        fill('检索问题', 'Where does Alex live?')
        click('运行检索诊断')
        expect(page.get_by_text(re.compile(r'^Query [a-f0-9]+ · 初始候选'))).to_be_visible()
        click('生成历史关系')
        click('刷新当前状态')
        expect(page.get_by_text('关系与当前状态已生成', exact=True)).to_be_visible(timeout=20000)
        click('重新计算当前状态')
        click('校验并发布版本')
        expect(page.get_by_text('完整版本已发布', exact=True)).to_be_visible()
        assert get('/versions/pin?dataset_id=' + dataset + '&sample_id=conv-a')['build_id'] == build
        click('扩展相关历史')
        state = get(f'/builds/{build}/current-state')
        trace_ids = []
        relations = get(f'/builds/{build}/relations')
        conflicts = [r for r in relations['items'] if r['label'] == 'CONFLICT']
        assert len(conflicts) == 1
        conflict_sources = {f'{dataset}/conv-a/D2:2', f'{dataset}/conv-a/D2:3'}
        assert set(conflicts[0]['source_ids']) == conflict_sources
        click('进入证据问答')
        for question, date, expected in [('Where does Alex live?', None, 'Rome'), ('Where did Alex live?', '2023-05-01', 'Paris'), ("What is Sam's birth year?", None, '证据冲突'), ("What is Alex's passport number?", None, '证据不足')]:
            fill('英文问题', question)
            fill('指定日期，可留空', date or '')
            click('分析证据并回答')
            caption = page.get_by_text(re.compile(r'^Trace [a-f0-9]+ · 固定构建')).inner_text()
            trace_id = caption.split()[1]
            trace = get('/queries/' + trace_id)
            assert trace_id not in trace_ids
            trace_ids.append(trace_id)
            assert trace['question'] == question
            assert trace['build_id'] == build
            assert trace['time']['requested_date'] == ('2023-05-01' if date else None)
            if expected in {'Rome', 'Paris'}:
                assert trace['answer']['status'] == 'sufficient'
                assert expected in trace['answer']['answer']
                assert len(trace['effective_memories']) == 1
            else:
                assert trace['answer']['status'] == ('conflict' if expected == '证据冲突' else 'insufficient')
                if expected == '证据冲突':
                    assert {m['state_value'] for m in trace['effective_memories']} == {'1990', '1992'}
                    assert {sid for c in trace['answer']['citations'] for sid in c['source_ids']} == conflict_sources
                    assert any(r['label'] == 'CONFLICT' for r in trace['relations'])
                    assert len(trace['initial']['initial_candidates']) == 1
                    assert len(trace['expanded']['added_candidates']) == 1
                else:
                    assert trace['effective_memories'] == []
                    assert trace['answer']['citations'] == []
            expect(page.get_by_text('证据支持' if expected in {'Rome', 'Paris'} else expected, exact=True).filter(visible=True)).to_be_visible(timeout=20000)
            if expected == 'Rome':
                page.get_by_text('回答引用：', exact=False).first.click()
                expect(page.get_by_text('I moved from Paris to Rome on 2 May 2023.', exact=True).filter(visible=True).last).to_be_visible()
            if expected == 'Paris':
                page.get_by_text('完整 Trace、实际配置、模型调用及用量', exact=True).click()
                page.get_by_text('初始候选、历史扩展、有效集合与排除理由', exact=True).click()
                page.screenshot(path=str(args.output / 'issue-12-history-trace.png'), full_page=True)
            scenario = {'Rome': 'current', 'Paris': 'historical', '证据冲突': 'conflict', '证据不足': 'insufficient'}[expected]
            page.get_by_text(re.compile(r'^Trace [a-f0-9]+ · 固定构建')).scroll_into_view_if_needed()
            page.screenshot(path=str(args.output / f'query-{scenario}.png'), full_page=True)
        assert get(f'/builds/{build}/current-state') == state
        assert get(f'/builds/{build}/relations') == relations
        assert get(f'/datasets/{dataset}/conversations/conv-a/turns') == original
        click('进入评测与报告')
        click('准备所选版本 JSON')
        with page.expect_download() as download:
            click('下载完整 Memory JSON')
        download.value.save_as(str(args.output / 'issue-12-memory.json'))
        bundle = json.loads((args.output / 'issue-12-memory.json').read_text())
        subprocess.run([args.app_python, '-c',
                        'import sys; from pathlib import Path; from locomo_memory.export_schemas import MemoryExport; MemoryExport.model_validate_json(Path(sys.argv[1]).read_text())',
                        str(args.output / 'issue-12-memory.json')], check=True)
        assert bundle['schema_version'] == 'memory-export-v2'
        assert bundle['build']['build_id'] == bundle['index']['build_id'] == bundle['projection']['build_id'] == build
        evaluation = {'kind': 'synthetic', 'samples': [{'sample_id': 'conv-a', 'question': q, 'answer': 'Rome', 'category': 4, 'evidence': ['D2:1']} for q in ['Where does Alex live?', 'Trigger failure.']]}
        page.get_by_test_id('stFileUploader').last.locator('input[type=file]').set_input_files({'name': 'evaluation.json', 'mimeType': 'application/json', 'buffer': json.dumps(evaluation).encode()})
        click('保存独立评测输入')
        click('开始评测')
        expect(page.get_by_text(re.compile(r'^Run [a-f0-9]+ ·'))).to_be_visible(timeout=30000)
        run_id = page.get_by_text(re.compile(r'^Run [a-f0-9]+ ·')).inner_text().split()[1]
        deadline = time.monotonic() + 30
        while get('/evaluation-runs/' + run_id + '/progress')['status'] == 'running':
            assert time.monotonic() < deadline, 'evaluation did not finish'
            time.sleep(.1)
        click('刷新评测进度')
        expect(page.get_by_text('课程正式指标未评：', exact=False)).to_be_visible(timeout=30000)
        for name in ['完整动态系统', 'Full Text 原始轮次', 'Vector RAG（无状态解析）', 'Hybrid + 扩展（无状态解析）']:
            expect(page.get_by_test_id('stMarkdownContainer').get_by_text(name, exact=True).filter(visible=True).first).to_be_visible()
        caption = page.get_by_text(re.compile(r'^Run [a-f0-9]+ ·')).inner_text()
        run_id = caption.split()[1]
        run = get('/evaluation-runs/' + run_id)
        assert set(run['summary']) == {'dynamic', 'full_text', 'vector', 'hybrid_no_resolution'}
        assert len(run['results']) == 8
        assert sum(row.get('error') is not None for row in run['results']) == 4
        assert all(row.get('error') is None for row in run['results'] if row['sample_index'] == 0)
        assert run['course_metrics']['status'] == 'unavailable'
        assert all(summary['qa']['scored'] == 1 and summary['qa']['unscored'] == 1 for summary in run['summary'].values())
        page.get_by_text('样本 1 · 完整动态系统 · 结果与失败检查', exact=True).click()
        page.get_by_text('固定版本、实际配置、共享 Prompt 与完整记录', exact=True).click()
        page.get_by_text('课程正式指标未评：', exact=False).scroll_into_view_if_needed()
        page.mouse.wheel(0, 300)
        page.screenshot(path=str(args.output / 'issue-12-evaluation.png'), full_page=True)
        assert not errors, errors
        assert not console_errors, console_errors
        browser_version = browser.version
    browser.close()
result = {'browser': 'Chromium', 'pageerrors': errors, 'console_errors': console_errors, 'build_id': build, 'download_schema': bundle['schema_version'], 'scenarios': ['current', 'historical', 'conflict', 'insufficient', 'build failure/retry', 'evaluation failure'], 'evaluation_rows': len(run['results']), 'failed_rows': sum(row.get('error') is not None for row in run['results']), 'adapters': 'controlled LLM and Embedding only'}
result['browser_version'] = browser_version
(args.output / 'issue-12-result.json').write_text(json.dumps(result, indent=2))
print(json.dumps(result, indent=2))
