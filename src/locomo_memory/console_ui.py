"""Read-only Research Console over public HTTP and reviewed frozen reports."""
import json
from datetime import datetime, timezone
from pathlib import Path
import runpy

import httpx
import streamlit as st

from locomo_memory.config import load_settings
from locomo_memory.evidence_ui import page_items, render_memory_inspector, render_trace_inspector
from locomo_memory.frozen_report_ui import render_experiment_comparison
from locomo_memory.ui_theme import apply_app_theme, render_context, render_page_header


ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / 'docs/team-v2/research-evidence.json'
PAGES = ('Overview', 'Memory', 'Query/Evidence', 'Experiments', 'Demo')


def render_build_selector(request, compact=False):
    with st.expander('数据 / 对话 / Build', expanded=False):
        datasets = page_items(request, '/datasets', 'console_dataset_offset')
        if not datasets:
            st.info('当前页尚无数据集。离线演示请先运行 prepare；已有数据时检查列表起始位置。')
            return None
        by_id = {item['dataset_id']: item for item in datasets}
        dataset_id = st.selectbox('数据集', list(by_id),
                                  format_func=lambda value: f"{by_id[value]['version']} · {value}",
                                  key='console_dataset')
        conversations = page_items(request, f'/datasets/{dataset_id}/conversations',
                                   f'console_conversation_offset_{dataset_id}')
        if not conversations:
            st.info('当前页没有对话。')
            return None
        sample_id = st.selectbox('对话', [item['sample_id'] for item in conversations],
                                key=f'console_sample_{dataset_id}')
        builds = page_items(request, '/builds', f'console_build_offset_{dataset_id}_{sample_id}',
                            dataset_id=dataset_id, sample_id=sample_id)
        if not builds:
            st.info('当前页没有 Build。Console 不会自动构建或调用模型。')
            return None
        by_build = {item['build_id']: item for item in builds}
        build_id = st.selectbox('冻结 / 历史 Build', list(by_build),
                                format_func=lambda value: (f"版本 {list(by_build).index(value) + 1} · {by_build[value]['status']}"
                                                           if compact else f"{by_build[value]['status']} · {value}"),
                                key=f'console_build_{dataset_id}_{sample_id}')
        build = by_build[build_id]
        if compact:
            st.caption('完整版本身份')
            st.json({field: build[field] for field in ('dataset_id', 'sample_id', 'build_id', 'fingerprint', 'status', 'phase', 'query_ready')})
    if compact:
        st.caption(f"当前 Build：{build['status']} · {'可用于问答' if build['query_ready'] else '仅供检查'} · 只读")
    else:
        render_context(dataset_id, sample_id, build_id)
        st.caption(f"Build status: {build['status']} · phase: {build['phase']} · query_ready: {build['query_ready']}")
        st.caption(f"Fingerprint: {build['fingerprint']}")
    if not build['query_ready']:
        st.warning('此 Build 尚未完整发布，只供检查，不作为完整问答结果。')
    return build


def render_frozen_report(evidence_path, reviewer=False, strategies=False):
    st.subheader('冻结真实实验报告')
    try:
        evidence = json.loads(Path(evidence_path).read_text(encoding='utf-8'))
        baseline = evidence['original_baseline']
        st.caption(f"原 Run: {evidence['run_id']} · Source commit: {evidence['source_commit']}")
        st.caption('此报告独立于上方本机 Build 和后端 Run；不是合成 Demo 成绩，也不是新运行。')
        columns = st.columns(4)
        for column, label, field in zip(columns, ('原 Run 计划组合', '成功', '失败', 'unknown'),
                                         ('planned_combinations', 'succeeded', 'failed', 'unknown')):
            column.metric(label, baseline[field])
        st.caption(f"{baseline['questions']} QA · unknown 原样保留；缺测不填零；无独立语义真值的指标保持未评。")
        if strategies:
            render_experiment_comparison(evidence)
        if reviewer:
            with st.expander('核对冻结报告原始字段'):
                st.json(evidence)
    except (OSError, ValueError, KeyError, TypeError):
        st.warning('冻结报告缺失或格式无法识别；没有生成或补填成绩。')


def render_runs(request):
    st.subheader('后端保存的 Run / 报告')
    st.caption('API 按 Run ID 分页；本页报告按已记录的完成时间排序，不代表全库最近；与冻结真实报告分开。')
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
    run_id = st.selectbox('读取保存的 Run', [run['run_id'] for run in runs], key='console_run')
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
            case_id = st.selectbox('冻结案例', list(cases), key='console_replay_case')
        load_case = action.button('载入冻结案例', key='console_load_case', type='primary', width='stretch')
        if load_case:
            st.session_state['console_trace_id'] = cases[case_id]['trace_id']
        st.caption('选择案例后点击“载入冻结案例”。只读取已有记录，不生成新回答。')
    with st.expander('按 Trace ID 读取已有记录', expanded=not bool(cases)):
        trace_id = st.text_input('Trace ID', key='console_trace_id', placeholder='粘贴已有 Trace ID')
        load_trace = st.button('读取已有 Trace', key='console_load_trace', disabled=not trace_id.strip())
    if load_trace or load_case:
        st.session_state.pop('console_saved_trace', None)
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
        st.caption('载入记录后，将在这里显示回答、状态和引用来源。')


def render_demo(replay_cases=()):
    st.subheader('Demo · 合成应用 Replay')
    st.info('OFFLINE SYNTHETIC DEMO 证明应用链路可运行，不代表真实模型成绩。')
    if replay_cases:
        st.success('当前为固定快照 Replay：无需启动 API、准备数据库或配置模型凭据。')
        st.dataframe(replay_cases, hide_index=True, width='stretch')
        st.code('uv run --locked python tools/team_v2/demo.py replay', language='shell')
        st.caption('操作路线：Overview → Memory/来源 → Query/Evidence/冻结案例 → Experiments。详见 demo_fixture/README.md。')
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
    focused = page in ('Memory', 'Query/Evidence')
    health = request('GET', '/health')
    if health.get('mode') == 'REPLAY':
        if not focused:
            st.success('Replay 快照已载入 · 无 API / 数据库')
    elif health.get('status') == 'ok':
        if not focused:
            st.success('后端已连接 · Console 只读')
    else:
        st.warning('后端健康状态不是 ok，请检查服务。')
    build = render_build_selector(request, compact=focused)
    if reviewer and build:
        with st.expander('核对 Build 身份和全部原始字段'):
            st.json(build)
    if page == 'Overview':
        with st.expander('后端保存的 Run / 最近报告', expanded=False):
            render_runs(request)
    elif page == 'Memory':
        render_memory(request, build, reviewer)
    elif page == 'Query/Evidence':
        render_trace(request, build, replay_cases, reviewer)


def render_console(request, evidence_path=EVIDENCE, replay_cases=()):
    if st.session_state.get('console_page') in ('Memory', 'Query/Evidence'):
        st.markdown('<div class="dm-shell-head"><div class="dm-brand">'
                    '<div class="dm-brand-mark">DM</div><div><div class="dm-brand-title">Dynamic Memory</div>'
                    '<div class="dm-brand-subtitle">Research Console · 记忆与证据检查</div></div></div></div>',
                    unsafe_allow_html=True)
        navigation, settings = st.columns([5, 1], vertical_alignment='center')
        with navigation:
            page = st.radio('导航', PAGES, horizontal=True, key='console_page', label_visibility='collapsed')
        with settings:
            with st.popover('视图设置'):
                reviewer = st.radio('使用场景', ('展示者', '评审者'), key='console_role') == '评审者'
    else:
        render_page_header('PRODUCT CONSOLE', 'Research Console', '选择固定版本，检查记忆、证据和实验记录。')
        reviewer = st.radio('使用场景', ('展示者', '评审者'), horizontal=True,
                            key='console_role', label_visibility='collapsed') == '评审者'
        page = st.radio('导航', PAGES, horizontal=True, key='console_page', label_visibility='collapsed')
    try:
        render_backend(request, page, reviewer, replay_cases)
    except httpx.HTTPStatusError as error:
        st.error(f'后端读取失败（HTTP {error.response.status_code}）。请检查资源和服务状态。')
    except httpx.HTTPError:
        st.error('无法连接后端，请先启动 FastAPI 服务。冻结报告仍可离线查看。')
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
