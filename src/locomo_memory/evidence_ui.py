"""Read-only timeline, source identity checks and recorded Trace stages."""
from urllib.parse import quote

import httpx
import streamlit as st


def page_items(request, path, key, **params):
    with st.popover('分页'):
        offset = int(st.number_input('列表起始位置', min_value=0, step=20, key=key))
    page = request('GET', path, params={**params, 'limit': 20, 'offset': offset})
    st.caption(f"本页 {len(page['items'])} 项 / 全部 {page['total']} 项 · offset {offset}")
    return page['items']


def recorded(value):
    return 'unknown' if value is None or value == '' else value


def render_sources(request, source_ids, build, key):
    ids = list(dict.fromkeys(source_ids))
    if not ids:
        st.info('此阶段没有记录来源引用。')
        return
    source_id = st.selectbox('来源引用', ids, key=f'{key}_id')
    parts = source_id.split('/')
    if len(parts) != 3 or parts[:2] != [build['dataset_id'], build['sample_id']]:
        st.error('来源 ID 无法映射到当前数据集 / 对话，保留异常，不猜测修正。')
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
            st.error('引用原文读取失败，保留引用异常，不生成替代原文。')
    source = st.session_state.get(f'{key}_source')
    if source and source['source_id'] == source_id:
        st.caption(f"SourceTurn: {source_id} · {source['speaker']} · 报告时间（原文）: {source['session_time']}")
        st.text(source['text'])


def memory_rows(memories):
    return [{'memory_id': m['memory_id'], 'content': m['content'],
             '陈述性质': m['statement_type'], '极性': m['polarity'], '类型': m['memory_type'],
             '报告时间（原文）': '; '.join(m.get('session_times', [])) or 'unknown',
             '事件起始': recorded(m.get('time', {}).get('event_start')),
             '事件结束': recorded(m.get('time', {}).get('event_end')),
             '有效起始': recorded(m.get('time', {}).get('valid_from')),
             '有效结束': recorded(m.get('time', {}).get('valid_to')),
             '时间表达（原文）': recorded(m.get('time', {}).get('original_expression')),
             'source_ids': ', '.join(m['source_ids'])} for m in memories]


def render_memory_inspector(request, build):
    st.subheader('Memory · 只读版本检查')
    if build is None:
        st.info('请先选择含有 Memory 的 Build。')
        return
    build_id = build['build_id']
    memories = page_items(request, f'/builds/{build_id}/memories', f'console_memory_offset_{build_id}')
    st.caption('时间线按来源记录顺序展示；报告时间不替代事件时间。plan / intention / uncertain、negative 原样保留。')
    if not memories:
        st.info('当前页尚无 Memory。')
        return
    st.dataframe(memory_rows(memories), hide_index=True, width='stretch')
    by_id = {memory['memory_id']: memory for memory in memories}
    memory_id = st.selectbox('检查记忆', list(by_id), format_func=lambda mid: by_id[mid]['content'],
                             key=f'console_memory_{build_id}')
    render_sources(request, by_id[memory_id]['source_ids'], build, f'memory_source_{build_id}')
    st.subheader('历史关系与冲突')
    relations = page_items(request, f'/builds/{build_id}/relations', f'console_relation_offset_{build_id}')
    if relations:
        st.dataframe([{field: r.get(field) for field in ('old_memory_id', 'label', 'new_memory_id', 'reason')}
                      for r in relations], hide_index=True, width='stretch')
        with st.expander('关系的适用条件与来源证据'):
            st.json(relations)
    else:
        st.info('当前页未记录关系；不根据时间较新推断替代。')
    if build['status'] in ('related', 'complete'):
        with st.expander('当前状态投影（独立于查询选择）'):
            st.json(request('GET', f'/builds/{build_id}/current-state'))
    with st.expander('Memory 原始字段（含时间与来源）'):
        st.json(memories)


def render_trace_inspector(request, build, trace):
    if trace['build_id'] != build['build_id']:
        st.warning('此 Trace 属于其他 Build，请切换到对应版本后读取。')
        return
    st.caption(f"Trace: {trace['trace_id']} · Build: {trace['build_id']} · outcome: {trace['outcome']}")
    error = trace.get('error')
    if error:
        st.error(f"问答执行失败：{error.get('stage', 'unknown')} / {error.get('code', 'unknown')}；失败不代表没有证据。")
    answer = trace.get('answer')
    if answer:
        st.write({'sufficient': '证据支持', 'insufficient': '证据不足', 'conflict': '证据冲突'}.get(answer['status'], answer['status']))
        st.text(answer['answer'])
        if answer.get('explanation'):
            st.caption(answer['explanation'])
    time = trace.get('time', {})
    st.caption(f"已知证据截止：{recorded(time.get('cutoff_source_time'))} · 请求日期：{recorded(time.get('requested_date'))}")
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
        st.caption('有效选择与实际送达分别查看；缺少送达记录时不宣称模型已经收到。')
    else:
        section, memories = {'answer': answer, 'error': error}, []
    if memories:
        st.dataframe(memory_rows(memories), hide_index=True, width='stretch')
    with st.expander('本阶段已记录字段', expanded=False):
        st.json(section)
    source_ids = ([sid for citation in (answer or {}).get('citations', []) for sid in citation['source_ids']]
                  if stage == 'answer/citations' else [sid for m in memories for sid in m['source_ids']])
    render_sources(request, source_ids, build, f"trace_source_{trace['trace_id']}_{stage}")
    with st.expander('阶段错误、耗时与预算', expanded=False):
        st.json({'error': error, 'stage_seconds': trace.get('stage_seconds'),
                 'diagnostics': trace.get('diagnostics'),
                 'initial_candidate_tokens': trace.get('initial', {}).get('candidate_token_count'),
                 'resolution_budgets': trace.get('resolution_budgets'),
                 'evidence_budget': trace.get('evidence_budget'), 'usage_summary': trace.get('usage_summary')})
    st.caption('exact wire：未记录' if 'exact_wire' not in trace else 'exact wire：已记录，本页不展示原始 wire')
    st.caption('event_ref：未记录' if 'event_ref' not in trace else f"event_ref：{trace['event_ref']}")
    with st.expander('已保存的证据与完整 Trace', expanded=False):
        # No prompts, request/response wire or credential-bearing config snapshots.
        st.json({key: trace[key] for key in ('trace_id', 'build_id', 'question', 'outcome', 'time',
                 'initial', 'expanded', 'resolution', 'effective_memories', 'answer', 'error',
                 'evidence_budget', 'resolution_budgets', 'source_delivery', 'stage_seconds', 'usage_summary') if key in trace})
