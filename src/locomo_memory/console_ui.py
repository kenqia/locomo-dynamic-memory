"""Read-only Research Console over public HTTP and reviewed frozen reports."""
import json
from html import escape
from datetime import datetime, timezone
from pathlib import Path
import re
import runpy

import httpx
import streamlit as st

from locomo_memory.config import load_settings
from locomo_memory.console_theme import apply_console_theme
from locomo_memory.console_widgets import compact_choice
from locomo_memory.evidence_ui import page_items, render_memory_inspector, render_trace_inspector
from locomo_memory.frozen_report_ui import render_experiment_comparison, render_report_totals
from locomo_memory.ui_theme import apply_app_theme


ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / 'docs/team-v2/research-evidence.json'
PAGES = ('Overview', 'Memory', 'Query/Evidence', 'Experiments', 'Demo')
PAGE_LABELS = {'Query/Evidence': 'Query'}
CASE_LABELS = {'success': '当前事实', 'historical': '历史日期', 'conflict': '证据冲突',
               'insufficient': '证据不足', 'citation_anomaly': '引用异常', 'budget_failure': '预算失败'}


def render_build_selector(request, replay=False):
    with st.popover('数据与版本'):
        datasets = page_items(request, '/datasets', 'console_dataset_offset')
        if not datasets:
            st.info('当前页尚无数据集。可调整分页或检查数据导入。')
            return None
        by_id = {item['dataset_id']: item for item in datasets}
        dataset_id = compact_choice('数据集', list(by_id),
                                  format_func=lambda value: f"{by_id[value]['version']} · {value}",
                                  key='console_dataset')
        conversations = page_items(request, f'/datasets/{dataset_id}/conversations',
                                   f'console_conversation_offset_{dataset_id}')
        if not conversations:
            st.info('当前页没有对话。')
            return None
        sample_id = compact_choice('对话', [item['sample_id'] for item in conversations],
                                key=f'console_sample_{dataset_id}')
        builds = page_items(request, '/builds', f'console_build_offset_{dataset_id}_{sample_id}',
                            dataset_id=dataset_id, sample_id=sample_id)
        if not builds:
            st.info('当前页没有 Build。Console 不会自动构建或调用模型。')
            return None
        by_build = {item['build_id']: item for item in builds}
        build_id = compact_choice('冻结 / 历史 Build', list(by_build),
                                format_func=lambda value: f"版本 {list(by_build).index(value) + 1} · {by_build[value]['status']}",
                                key=f'console_build_{dataset_id}_{sample_id}')
        build = by_build[build_id]
        st.caption('完整版本身份')
        st.json({field: build[field] for field in ('dataset_id', 'sample_id', 'build_id', 'fingerprint', 'status', 'phase', 'query_ready')})
    status = {'complete': '已完成', 'related': '关系已生成', 'failed': '失败', 'interrupted': '已中断'}.get(build['status'], build['status'])
    mode = '合成回放' if replay else '只读浏览'
    st.markdown(f'<div class="console-context"><span>{mode}</span><span>当前版本：{escape(status)}</span></div>', unsafe_allow_html=True)
    if not build['query_ready']:
        st.warning('此 Build 尚未完整发布，只供检查，不作为完整问答结果。')
    return build


def render_frozen_report(evidence_path, reviewer=False, strategies=False):
    st.subheader('冻结真实实验报告')
    try:
        evidence = json.loads(Path(evidence_path).read_text(encoding='utf-8'))
        baseline = evidence['original_baseline']
        st.caption('历史实验结果，独立于当前所选版本。')
        if strategies:
            render_experiment_comparison(evidence)
        else:
            render_report_totals(baseline)
        with st.expander('冻结报告身份与原始字段', expanded=reviewer):
            st.caption(f"原 Run: {evidence['run_id']} · Source commit: {evidence['source_commit']}")
            if not strategies:
                st.json(evidence)
    except (OSError, ValueError, KeyError, TypeError):
        st.warning('冻结报告缺失或格式无法识别；没有生成或补填成绩。')


def render_runs(request):
    st.subheader('后端保存的 Run / 报告')
    st.caption('按本页已记录的完成时间排序，不代表全部报告的最新结果。')
    runs = page_items(request, '/evaluation-runs', 'console_run_offset')
    if not runs:
        st.info('当前页没有已保存的评测 Run。')
        return
    dated = []
    for run in runs:
        progress = request('GET', f"/evaluation-runs/{run['run_id']}/progress")
        stamp = progress.get('completed_at')
        try:
            timestamp = datetime.fromisoformat(stamp)
            if timestamp.tzinfo is None:
                timestamp = None
        except (ValueError, TypeError):
            timestamp = None
        dated.append((timestamp, {**run, 'completed_at': stamp or 'unknown'}))
    dated.sort(key=lambda item: item[0] or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    runs = [item[1] for item in dated]
    if dated[0][0] is not None:
        st.caption(f"本页最近完成报告：{runs[0]['run_id']} · {runs[0]['completed_at']}")
    else:
        st.caption('本页未记录可比较的完成时间：unknown；不按 ID 推断时间。')
    st.dataframe(runs, hide_index=True, width='stretch')
    run_id = compact_choice('读取保存的 Run', [run['run_id'] for run in runs], key='console_run')
    if st.button('打开保存的报告', key='console_load_report'):
        st.session_state.pop('console_saved_run', None)
        st.session_state['console_saved_run'] = request('GET', f'/evaluation-runs/{run_id}')
    run = st.session_state.get('console_saved_run')
    if run and run['run_id'] == run_id:
        st.caption(f"Run: {run['run_id']} · status: {run.get('status', 'unknown')} · 完成时间: {run.get('completed_at') or 'unknown'}")
        st.json(run)


def render_memory(request, build, reviewer=False):
    render_memory_inspector(request, build, reviewer)


def render_trace(request, build, replay_cases=(), reviewer=False):
    st.subheader('选择已有问答记录')
    if build is None:
        st.info('请先选择 Build，再读取该版本已有的 Trace。')
        return
    cases = {case['case_id']: case for case in replay_cases if case['build_id'] == build['build_id']}
    load_case = False
    if cases:
        selection, action = st.columns([3, 1], vertical_alignment='bottom')
        with selection:
            case_id = compact_choice('冻结案例', list(cases), key='console_replay_case',
                                     format_func=lambda value: CASE_LABELS.get(value, value))
        load_case = action.button('载入冻结案例', key='console_load_case', type='primary', width='stretch')
        if load_case:
            st.session_state['console_trace_id'] = cases[case_id]['trace_id']
    with st.expander('按 Trace ID 读取已有记录', expanded=not bool(cases)):
        trace_id = st.text_input('Trace ID', key='console_trace_id', placeholder='粘贴已有 Trace ID')
        load_trace = st.button('读取已有 Trace', key='console_load_trace', disabled=not trace_id.strip())
    if load_trace or load_case:
        st.session_state.pop('console_saved_trace', None)
        if not re.fullmatch(r'[A-Za-z0-9_-]+', trace_id.strip()):
            st.warning('Trace ID 格式无效：只支持字母、数字、连字符和下划线。请核对 ID 后重试。')
            return
        try:
            trace = request('GET', f'/queries/{trace_id.strip()}')
        except httpx.HTTPStatusError as error:
            if error.response.status_code != 404:
                raise
            st.warning('未找到此 Trace ID 对应的已保存记录。请核对 ID，或选择冻结案例后点击“载入冻结案例”。'
                       if cases else '未找到此 Trace ID 对应的已保存记录。请核对 ID 后重试。')
            return
        if trace['build_id'] != build['build_id']:
            st.warning('此 Trace 属于其他 Build，请切换到对应版本后读取。')
            return
        st.session_state['console_saved_trace'] = trace
    trace = st.session_state.get('console_saved_trace')
    if trace and trace['build_id'] == build['build_id'] and trace['trace_id'] == trace_id.strip():
        render_trace_inspector(request, build, trace, reviewer)
    elif not load_trace and not load_case:
        st.caption('载入后查看回答、状态和引用。')


def render_demo(replay_cases=()):
    st.subheader('Demo · 合成应用 Replay')
    st.caption('以下为合成案例，用于演示应用流程，不代表真实模型成绩。')
    if replay_cases:
        st.markdown('**约 4 分钟的连续演示**')
        st.markdown('1. Overview：确认所选版本与真实冻结报告。\n'
                    '2. Memory：选记忆、看时间和完整原文，展示计划与否定。\n'
                    '3. Query/Evidence：载入成功、历史、冲突和失败案例，查看引用与阶段。\n'
                    '4. Experiments：解释成功子集、全量失败、unknown 与成本。')
        columns = st.columns(2)
        for index, case in enumerate(replay_cases):
            with columns[index % 2].container(border=True):
                st.markdown('**' + CASE_LABELS.get(case['case_id'], '保存案例') + '**')
                st.text(case['question'])
        with st.expander('案例身份与保存记录'):
            st.json(replay_cases)
        st.code('uv run --locked python tools/team_v2/demo.py replay', language='shell')
        return
    st.markdown('选择 `OFFLINE-SYNTHETIC-v2-kickoff` / `conv-a` 的完整 Build，'
                '先看 Memory，再在 Query/Evidence 读取 seed 保存的 Trace ID。')
    st.dataframe([
        {'问题': 'Where does Alex live?', '日期': '对话截止时间', '预期': 'Rome'},
        {'问题': 'Where did Alex live?', '日期': '2023-05-01', '预期': 'Paris'},
        {'问题': "What is Sam's birth year?", '日期': '对话截止时间', '预期': '保留 1990 / 1992 冲突'},
        {'问题': "What is Alex's passport number?", '日期': '对话截止时间', '预期': '证据不足'},
    ], hide_index=True, width='stretch')
    st.caption('Trace ID 见本 clone 的 var/<output>/demo-manifest.json；只读重放不发起新问答。')
    st.code('uv run --locked python tools/team_v2/demo.py prepare\n'
            'uv run --locked python tools/team_v2/demo.py api\n'
            'uv run --locked python tools/team_v2/demo.py ui', language='shell')
    st.caption('api 和 ui 分别在两个终端运行。prepare 拒绝覆盖已有目录；更换 output 时三个命令使用相同路径。')


def render_backend(request, page, reviewer, replay_cases=()):
    health = request('GET', '/health')
    if health.get('mode') != 'REPLAY' and health.get('status') != 'ok':
        st.warning('后端健康状态不是 ok，请检查服务。')
    build = render_build_selector(request, replay=health.get('mode') == 'REPLAY')
    if reviewer and build:
        with st.expander('核对 Build 身份和全部原始字段'):
            st.json(build)
    if page == 'Overview':
        st.subheader('Overview · 工作概览')
        if replay_cases:
            st.caption('当前版本使用合成案例；下方实验报告来自独立的历史真实运行。')
        for column, title, copy, target, key in zip(st.columns(3),
                ('查看记忆与来源', '追溯回答证据', '比较已有实验'),
                ('检查时间、计划、否定和关系。', '查看保存的回答、引用和阶段 Trace。', '理解真实结果、完整分母和成本。'),
                ('Memory', 'Query/Evidence', 'Experiments'), ('overview_memory', 'overview_trace', 'overview_experiments')):
            with column.container(border=True):
                st.markdown('**' + title + '**')
                st.caption(copy)
                st.button('进入 ' + PAGE_LABELS.get(target, target), key=key, on_click=select_page, args=(target,),
                          disabled=build is None and target != 'Experiments', width='stretch')
        with st.expander('后端保存的 Run / 最近报告', expanded=False):
            render_runs(request)
    elif page == 'Memory':
        render_memory(request, build, reviewer)
    elif page == 'Query/Evidence':
        render_trace(request, build, replay_cases, reviewer)


def select_page(page):
    st.session_state['console_page'] = page


def render_console(request, evidence_path=EVIDENCE, replay_cases=()):
    apply_console_theme()
    with st.container(key='console_header'):
        brand, navigation, settings = st.columns([2, 5, 1], vertical_alignment='center')
        with brand:
            st.markdown('<div class="console-brand"><span class="console-brand-mark">DM</span>'
                        '<span class="console-brand-title">Dynamic Memory</span></div>', unsafe_allow_html=True)
        with navigation:
            with st.container(key='console_nav'):
                page = st.radio('页面导航', PAGES, format_func=lambda value: PAGE_LABELS.get(value, value),
                                horizontal=True, key='console_page', label_visibility='collapsed')
        with settings:
            with st.popover('视图设置'):
                reviewer = st.radio('使用场景', ('展示者', '评审者'), key='console_role') == '评审者'
    try:
        render_backend(request, page, reviewer, replay_cases)
    except httpx.HTTPStatusError as error:
        st.error(f'后端读取失败（HTTP {error.response.status_code}）。请检查资源和服务状态。')
    except httpx.HTTPError:
        st.error('无法读取服务数据，请检查连接。冻结报告仍可查看。')
    except (ValueError, KeyError, TypeError):
        st.error('后端返回了无法识别的数据，请核对 API 版本。')
    if page in ('Overview', 'Experiments'):
        render_frozen_report(evidence_path, reviewer, strategies=page == 'Experiments')
    elif page == 'Demo':
        render_demo(replay_cases)


def main():
    st.set_page_config(page_title='LoCoMo Research Console', layout='wide')
    apply_app_theme()
    if st.toggle('五阶段工作流', key='console_legacy_workflow', help='保留原有上传、构建、问答和评测操作。'):
        runpy.run_path(str(Path(__file__).with_name('ui.py')), run_name='__main__')
        return
    settings = load_settings()

    def request(method, path, **kwargs):
        response = httpx.request(method, f"{settings.api_url.rstrip('/')}{path}", timeout=10, **kwargs)
        response.raise_for_status()
        return response.json()

    render_console(request)


if __name__ == '__main__':
    main()
