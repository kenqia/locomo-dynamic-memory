"""Read-only timeline, source identity checks and recorded Trace stages."""
from urllib.parse import quote

import httpx
import streamlit as st

from locomo_memory.console_widgets import compact_choice


def page_items(request, path, key, compact=False, **params):
    controls, summary = st.columns([1, 6], vertical_alignment='center') if compact else (st, st)
    with controls.popover('分页'):
        offset = int(st.number_input('列表起始位置', min_value=0, step=20, key=key))
    page = request('GET', path, params={**params, 'limit': 20, 'offset': offset})
    summary.caption(f"本页 {len(page['items'])} 项 / 共 {page['total']} 项")
    return page['items']


def recorded(value):
    return 'unknown' if value is None or value == '' else value


def render_sources(request, source_ids, build, key):
    ids = list(dict.fromkeys(source_ids))
    if not ids:
        st.info('此阶段没有记录来源引用。')
        return
    source_id = compact_choice('来源引用', ids,
                             format_func=lambda sid: f'来源 {ids.index(sid) + 1} · {sid.rsplit("/", 1)[-1]}',
                             key=f'{key}_id')
    parts = source_id.split('/')
    if len(parts) != 3 or parts[:2] != [build['dataset_id'], build['sample_id']]:
        st.error('来源不属于当前数据集或对话，无法展示原文。')
        return
    if st.button('查看完整原文', key=f'{key}_open'):
        st.session_state.pop(f'{key}_source', None)
        ds, sample, dia = (quote(part, safe='') for part in parts)
        try:
            source = request('GET', f'/datasets/{ds}/conversations/{sample}/turns/{dia}')
            if (source.get('source_id'), source.get('dataset_id'), source.get('sample_id'), source.get('dia_id')) != (
                    source_id, parts[0], parts[1], parts[2]):
                st.error('后端返回的来源身份与引用不一致，未展示原文。')
                return
            st.session_state[f'{key}_source'] = source
        except httpx.HTTPError:
            st.error('无法读取引用原文，请核对来源或连接。')
    source = st.session_state.get(f'{key}_source')
    if source and source['source_id'] == source_id:
        st.caption(f"{source['speaker']} · 报告时间（原文）: {source['session_time']}")
        st.text(source['text'])
        with st.expander('核对来源身份'):
            st.json({field: source[field] for field in ('source_id', 'dataset_id', 'sample_id', 'dia_id')})


def render_memory_summary(memory):
    """Readable content with the original statement and time boundaries intact."""
    st.text(memory['content'])
    statement = {'fact': '事实陈述', 'plan': '计划', 'intention': '意愿', 'uncertain': '不确定'}.get(
        memory['statement_type'], memory['statement_type'])
    polarity = {'positive': '肯定', 'negative': '否定'}.get(memory['polarity'], memory['polarity'])
    kind = {'state': '状态', 'event': '事件'}.get(memory['memory_type'], memory['memory_type'])
    st.caption(f"{statement} · {polarity} · {kind}")
    time = memory.get('time', {})
    st.caption('报告时间（原文）：' + ('；'.join(memory.get('session_times', [])) or 'unknown'))
    st.caption(f"事件时间：{recorded(time.get('event_start'))} → {recorded(time.get('event_end'))}")
    st.caption(f"有效区间：{recorded(time.get('valid_from'))} → {recorded(time.get('valid_to'))}")
    if time.get('original_expression'):
        st.caption(f"时间表达（原文）：{time['original_expression']}")


def render_memory_inspector(request, build, reviewer=False):
    st.subheader('Memory · 记忆与来源')
    if build is None:
        st.info('请先选择含有 Memory 的 Build。')
        return
    build_id = build['build_id']
    memories = page_items(request, f'/builds/{build_id}/memories', f'console_memory_offset_{build_id}', compact=True)
    st.caption('列表按记录顺序展示，未按事件时间排序。')
    if not memories:
        st.info('当前页尚无 Memory。')
        return
    by_id = {memory['memory_id']: memory for memory in memories}
    with st.container(key='console_memory_layout'):
        selection, detail = st.columns([1, 1.6], gap='large')
    with selection:
        st.markdown('**记忆列表**')
        memory_id = st.radio('检查记忆', list(by_id), format_func=lambda mid: by_id[mid]['content'],
                             key=f'console_memory_{build_id}', label_visibility='collapsed')
    with detail:
        with st.container(border=True):
            st.markdown('**选中记忆**')
            render_memory_summary(by_id[memory_id])
            st.markdown('**原文证据**')
            render_sources(request, by_id[memory_id]['source_ids'], build, f'memory_source_{build_id}')
    st.subheader('这条记忆的关系与冲突')
    relations = page_items(request, f'/builds/{build_id}/relations', f'console_relation_offset_{build_id}', compact=True)
    selected_relations = [r for r in relations if memory_id in (r['old_memory_id'], r['new_memory_id'])]
    if selected_relations:
        for relation in selected_relations:
            with st.container(border=True):
                st.markdown('**' + {'RETAIN': '保留', 'UPDATE': '阶段推进', 'SUPERSEDE': '替代',
                                   'CONFLICT': '未消解冲突'}.get(relation['label'], '关系') + '**')
                for field, label in (('old_memory_id', '先前记录'), ('new_memory_id', '关联记录')):
                    memory = by_id.get(relation[field])
                    st.text(f"{label}：{memory['content'] if memory else '内容不在当前 Memory 页，请在评审详情核对引用 ID'}")
                st.text(relation.get('reason') or '关系理由：unknown')
    else:
        st.caption('当前关系页没有与这条记忆相连的记录。')
    with st.expander('评审详情 · 关系的适用条件与来源证据', expanded=reviewer):
        st.json(relations)
    if build['status'] in ('related', 'complete'):
        with st.expander('当前状态投影（独立于查询选择）'):
            st.json(request('GET', f'/builds/{build_id}/current-state'))
    with st.expander('评审详情 · Memory 原始字段（含时间与来源）'):
        st.json(memories)


def render_trace_inspector(request, build, trace, reviewer=False):
    if trace['build_id'] != build['build_id']:
        st.warning('此 Trace 属于其他 Build，请切换到对应版本后读取。')
        return
    st.subheader('回答与来源')
    with st.chat_message('user'):
        st.text(trace['question'])
    error = trace.get('error')
    if error:
        st.error(f"问答执行失败：{error.get('stage', 'unknown')} / {error.get('code', 'unknown')}")
    answer = trace.get('answer')
    if answer:
        with st.chat_message('assistant'):
            status = {'sufficient': '证据支持', 'insufficient': '证据不足', 'conflict': '证据冲突'}.get(answer['status'], answer['status'])
            if answer['status'] in ('insufficient', 'conflict'):
                st.warning(status)
            else:
                st.write(status)
            st.text(answer['answer'])
            if answer.get('explanation'):
                st.caption(answer['explanation'])
    time = trace.get('time', {})
    st.caption(f"已知证据截止：{recorded(time.get('cutoff_source_time'))} · 请求日期：{recorded(time.get('requested_date'))}")
    source_ids = [sid for citation in (answer or {}).get('citations', []) for sid in citation['source_ids']]
    if source_ids:
        with st.container(border=True, key='console_answer_sources'):
            st.markdown('**回答引用 · 原文证据**')
            render_sources(request, source_ids, build, f"answer_source_{trace['trace_id']}")
    elif not error:
        st.caption('此回答未记录来源引用。')
    with st.expander('评审详情 · 阶段 Trace', expanded=reviewer):
        render_trace_stages(request, build, trace)
    with st.expander('阶段错误、耗时与预算'):
        st.json({'error': error, 'stage_seconds': trace.get('stage_seconds'),
                 'diagnostics': trace.get('diagnostics'),
                 'initial_candidate_tokens': trace.get('initial', {}).get('candidate_token_count'),
                 'initial_candidate_budget': trace.get('initial', {}).get('config', {}).get('candidate_token_budget'),
                 'resolution_budgets': trace.get('resolution_budgets'),
                 'evidence_budget': trace.get('evidence_budget'), 'usage_summary': trace.get('usage_summary')})
    with st.expander('版本身份与完整 Trace（已保存字段）'):
        st.caption(f"Trace: {trace['trace_id']} · Build: {trace['build_id']} · outcome: {trace['outcome']}")
        st.caption('exact wire：未记录' if not trace.get('exact_wire') else 'exact wire：已记录，本页不展示原始 wire')
        st.caption('event_ref：未记录' if not trace.get('event_ref') else f"event_ref：{trace['event_ref']}")
        # No prompts, request/response wire or credential-bearing config snapshots.
        st.json({key: trace[key] for key in ('trace_id', 'build_id', 'question', 'outcome', 'time',
                 'initial', 'expanded', 'resolution', 'effective_memories', 'answer', 'error',
                 'evidence_budget', 'resolution_budgets', 'source_delivery', 'stage_seconds', 'usage_summary') if key in trace})


def render_trace_stages(request, build, trace):
    stage = st.radio('证据阶段', ('initial', 'expanded', 'effective/delivered', 'answer/citations'),
                     horizontal=True, key=f"trace_stage_{trace['trace_id']}")
    if stage == 'initial':
        section = trace.get('initial', {})
        candidates = section.get('initial_candidates', [])
        memories = [item['memory'] for item in candidates]
    elif stage == 'expanded':
        section = trace.get('expanded', {})
        candidates = section.get('candidates', [])
        memories = [item['memory'] for item in candidates]
    elif stage == 'effective/delivered':
        section = {'resolution': trace.get('resolution'), 'source_delivery': trace.get('source_delivery'),
                   'resolution_budgets': trace.get('resolution_budgets')}
        memories = trace.get('effective_memories', [])
        st.caption('有效记忆与送达记录分别列出；未记录送达时，无法确认模型是否收到。')
    else:
        section, memories = {'answer': trace.get('answer'), 'error': trace.get('error')}, []
    if memories:
        for memory in memories:
            with st.container(border=True):
                render_memory_summary(memory)
        render_sources(request, [sid for m in memories for sid in m['source_ids']], build,
                       f"trace_source_{trace['trace_id']}_{stage}")
    st.caption('本阶段已记录字段')
    st.json(section)
