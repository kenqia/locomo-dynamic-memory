"""Evaluation controls and side-by-side comparisons through backend HTTP only."""
import json
import streamlit as st

from locomo_memory.report_html import render_evaluation_report_html


LABELS = {'dynamic': '完整动态系统', 'dynamic_raw_fallback': 'Dynamic + 原文兜底', 'full_text': 'Full Text 原始轮次', 'vector': 'Vector RAG（无状态解析）', 'hybrid_no_resolution': 'Hybrid + 扩展（无状态解析）'}


def render_saved_comparison(request, run):
    """Switch saved answers without launching or retrying any model operation."""
    st.subheader('逐题检查结果')
    rows = run.get('results', [])
    indices = list(dict.fromkeys(row['sample_index'] for row in rows))
    if not indices:
        st.caption('尚无已保存结果。')
        return
    samples = run['input']['samples']
    position = min(st.session_state.get('comparison_question_position', 0), len(indices) - 1)
    index = indices[position]
    if len(indices) == 1:
        st.markdown(f"**题目**  \\n{samples[index]['question']}")
    else:
        navigation = st.columns([1, 4, 1])
        if navigation[0].button('上一题', disabled=position == 0, key='comparison_previous'):
            st.session_state['comparison_question_position'] = position - 1
            st.rerun()
        navigation[1].markdown(f"**题目 {position + 1} / {len(indices)}**  \\n{samples[index]['question']}")
        if navigation[2].button('下一题', disabled=position == len(indices) - 1, key='comparison_next'):
            st.session_state['comparison_question_position'] = position + 1
            st.rerun()
    strategies = [s for s in run['strategies'] if any(r['sample_index'] == index and r['strategy'] == s for r in rows)]
    strategy = st.radio('查看策略', strategies, format_func=LABELS.get, horizontal=True, key='comparison_strategy')
    st.caption('切换只读取本次 Run 的已保存结果，不会调用模型。引用原文按需读取。')
    row = next(r for r in rows if r['sample_index'] == index and r['strategy'] == strategy)
    trace = row.get('trace', {})
    answer = trace.get('answer')
    if not answer:
        st.error('该项执行失败：' + str(row.get('error', {}).get('code', 'unknown')))
    else:
        st.write({'sufficient': '证据支持', 'insufficient': '证据不足', 'conflict': '证据冲突'}[answer['status']])
        st.text(answer['answer'])
        if answer.get('explanation'):
            st.caption(answer['explanation'])
        if trace.get('time'):
            st.caption('已知证据截止：' + trace['time']['cutoff'])
        ids = list(dict.fromkeys(sid for citation in answer['citations'] for sid in citation['source_ids']))
        with st.expander('回答引用原文'):
            st.write(ids)
            if ids and st.button('读取引用原文', key='comparison_sources'):
                for source_id in ids:
                    ds, sample, dia = source_id.split('/')
                    source = request('GET', f'/datasets/{ds}/conversations/{sample}/turns/{dia}')
                    st.caption(f"{source_id} · {source['speaker']} · {source['session_time']}")
                    st.text(source['text'])
    with st.expander('此项完整证据和失败记录'):
        st.json(row)


def render_development_plan(request, dataset_id):
    artifacts = request('GET', f'/datasets/{dataset_id}/provenance', params={'limit': 100})['items']
    required = {'conv-26', 'conv-30', 'conv-41', 'conv-42'}
    artifact = None
    for item in artifacts:
        samples = item.get('provenance', {}).get('samples')
        annotated = {
            sample.get('sample_id')
            for sample in samples or []
            if isinstance(sample, dict) and sample.get('qa', 0) > 0
        }
        if required <= annotated:
            artifact = item['artifact_sha256']
            break

    with st.container(border=True):
        st.markdown('##### 课程开发集计划')
        if artifact:
            st.caption('开发集使用 conv-26、conv-30、conv-41、conv-42；5 题计划覆盖五类课程问题。计划预览不会调用生成模型。')
            plan_columns = st.columns(2)
            if plan_columns[0].button('生成 5 题冒烟计划', use_container_width=True, key='create_smoke_plan'):
                plan = request('POST', '/evaluation-plans', json={'dataset_id': dataset_id, 'artifact_sha256': artifact, 'scope': 'smoke'})
                st.session_state['evaluation_plan'] = plan
                st.session_state['evaluation_input_id'] = plan['input_id']
            if plan_columns[1].button('生成完整开发集计划', use_container_width=True, key='create_development_plan'):
                plan = request('POST', '/evaluation-plans', json={'dataset_id': dataset_id, 'artifact_sha256': artifact, 'scope': 'development'})
                st.session_state['evaluation_plan'] = plan
                st.session_state['evaluation_input_id'] = plan['input_id']
        else:
            st.info('当前数据集是自定义数据，未包含课程开发集 QA。请在第一页导入官方 LoCoMo 后创建课程计划。')

        saved_columns = st.columns([4, 1])
        plan_id = saved_columns[0].text_input(
            '读取已保存 Plan ID',
            key='evaluation_saved_plan',
            placeholder='输入已保存的 Plan ID',
            label_visibility='collapsed',
        )
        if saved_columns[1].button('读取计划', use_container_width=True):
            if not plan_id:
                st.warning('请先输入 Plan ID。')
            else:
                st.session_state['evaluation_plan'] = request('GET', f'/evaluation-plans/{plan_id}')

        plan = st.session_state.get('evaluation_plan')
        if plan and plan['dataset_id'] == dataset_id:
            st.write(f"Plan {plan['plan_id']}")
            st.write(f"{plan['question_count']} 题 · {len(plan['strategies'])} 策略 · {plan['combination_count']} 组合 · 尚未执行")
            st.dataframe(plan['questions'], hide_index=True)
            action_columns = st.columns(2)
            if action_columns[0].button('运行此开发集计划', use_container_width=True):
                run = request('POST', '/evaluation-runs', json={'plan_id': plan['plan_id']})
                st.session_state['evaluation_run'] = run
                st.session_state['evaluation_saved_run'] = run['run_id']
            action_columns[1].download_button(
                '导出计划 JSON',
                json.dumps(plan, ensure_ascii=False, indent=2),
                file_name=f"evaluation-plan-{plan['plan_id']}.json",
                mime='application/json',
                use_container_width=True,
            )


def render_evaluation(request, dataset_id):
    st.subheader('创建评测')
    render_development_plan(request, dataset_id)
    st.caption('独立动态真值缺失时动态指标未评；原文来源覆盖不能证明语义事实已被抽取。运行对照前需发布完整构建版本。')
    uploaded = st.file_uploader('独立评测 JSON（samples、kind、可选 course_split）', type=['json'], key='evaluation_upload')
    if st.button('保存独立评测输入', disabled=uploaded is None):
        try:
            body = json.loads(uploaded.getvalue())
        except (ValueError, UnicodeError):
            st.error('评测文件必须是 UTF-8 JSON。')
        else:
            if not isinstance(body, dict):
                st.error('评测文件必须是 JSON object。')
            else:
                body['dataset_id'] = dataset_id
                value = request('POST', '/evaluation-inputs', json=body)
                st.session_state['evaluation_input_id'] = value['input_id']
                st.json(value)
    input_id = st.text_input('评测 Input ID', key='evaluation_input_id')
    strategy_columns = st.columns([1, 2.35], gap='large', vertical_alignment='bottom')
    strategy_mode = strategy_columns[0].selectbox(
        '运行策略',
        ['course', 'course_with_raw_fallback'],
        format_func=lambda value: (
            '课程策略'
            if value == 'course'
            else '课程策略+原文'
        ),
        key='evaluation_strategy_mode',
    )
    strategy_columns[1].caption(
        '课程策略用于默认对照；原文作为额外实验随第二项一起运行。'
    )
    include_raw_fallback = strategy_mode == 'course_with_raw_fallback'
    strategies = ['dynamic', 'full_text', 'vector', 'hybrid_no_resolution']
    if include_raw_fallback:
        strategies.append('dynamic_raw_fallback')
    partition_label = st.selectbox(
        '评测数据范围',
        ['合成或自定义输入', '课程开发集', '本地留出集'],
        key='evaluation_partition',
    )
    partition = {'合成或自定义输入': None, '课程开发集': 'dev', '本地留出集': 'test'}[partition_label]
    if st.button('开始评测', type='primary', use_container_width=True):
        if not input_id:
            st.warning('请先上传评测文件或输入评测 Input ID。')
        else:
            created = request('POST', '/evaluation-runs', json={'input_id': input_id, 'strategies': strategies, 'partition': partition})
            st.session_state['evaluation_run'] = created
            st.session_state['evaluation_saved_run'] = created['run_id']
    run_id = st.text_input('读取已保存 Run ID', key='evaluation_saved_run')
    if st.button('读取评测记录'):
        if not run_id:
            st.warning('请先输入 Run ID。')
        else:
            st.session_state['evaluation_run'] = request('GET', f'/evaluation-runs/{run_id}')
    run = st.session_state.get('evaluation_run')
    if not run:
        return
    if st.button('刷新评测进度'):
        run = request('GET', f"/evaluation-runs/{run['run_id']}")
        st.session_state['evaluation_run'] = run
    status = run.get('status', 'completed')
    st.caption(f"Run {run['run_id']} · {run['kind']} · {status} · 耗时 {run.get('elapsed_seconds', 0):.2f}s")
    if 'progress' in run:
        st.json(run['progress'])
        if status in ('running', 'interrupted'):
            st.info('运行尚未完成，已提交结果可读取。刷新或读取记录不会调用模型。')
        st.caption('中断时外部调用可能已经计费，未知结果不代表没有调用。显式重试可能再次计费，系统不保证供应商恰好一次计费。')
        retry_failed = st.checkbox('恢复时重试已记录失败项', value=False)
        retry_unknown = st.checkbox('恢复时重试外部结果未确认项', value=False)
        if st.button('显式恢复此运行', disabled=status == 'running'):
            run = request('POST', f"/evaluation-runs/{run['run_id']}/resume", json={'retry_failed': retry_failed, 'retry_unknown': retry_unknown})
            st.session_state['evaluation_run'] = run
        st.dataframe([{'题目': i['question_id'], '策略': LABELS[i['strategy']], '状态': i['status'], '尝试次数': len(i['attempts'])} for i in run['items']], hide_index=True)

    if run['course_metrics']['status'] == 'unavailable':
        st.info('课程正式指标未评：' + str(run['course_metrics']['reason']))
    render_saved_comparison(request, run)
    columns = st.columns(max(1, len(run.get('summary', {}))))
    for column, (strategy, summary) in zip(columns, run['summary'].items()):
        with column:
            execution = summary.get('execution', {})
            qa = summary.get('qa', {})
            st.metric(LABELS[strategy], '—' if qa.get('mean') is None else f"{qa['mean']:.3f}",
                      f"成功 {execution.get('succeeded', 0)} / {execution.get('planned', 0)}")
            with st.expander('查看完整指标'):
                st.json(summary)
    if 'overall_summary' in run:
        st.caption('QA 均值只含成功且可计分项。运行成功率使用全部计划项。基线运行得分将适用参考规则的执行失败记零；未完成时最终得分为空，此指标不是教师评分。')
        st.write('总体逐项汇总')
        st.json(run['overall_summary'])
        grouped = run.get('grouped_summary', {})
        for dimension, label in (('conversation', '按对话'), ('category', '按 QA 类别')):
            rows = []
            for identity, strategies in grouped.get(dimension, {}).items():
                for strategy, summary in strategies.items():
                    execution, baseline = summary['execution'], summary['baseline_run_score']
                    rows.append({'分组': identity, '策略': LABELS[strategy],
                        '成功可计分 QA 均值': summary['qa']['mean'], 'QA计分数': summary['qa']['scored'],
                        '计划数': execution['planned'], '执行成功数': execution['succeeded'],
                        '运行成功率': execution['success_rate'], '基线运行得分': baseline['value'],
                        '得分分母': baseline['denominator'], '参考规则不可用数': baseline['excluded'],
                        '得分状态': baseline['status']})
            with st.expander(label):
                if rows:
                    st.dataframe(rows, hide_index=True)
                else:
                    st.caption('当前没有该分组的计划项。')
        with st.expander('分对话均值，单独报告'):
            st.json(grouped.get('conversation_means', {}))
        with st.expander('构建开销与全部查询尝试用量'):
            st.caption('仅合计已保存的 provider 用量。缺失字段、未知结果及未记录的历史构建开销分别标明，不据此计算完整账单。')
            st.json({'query_attempts': run.get('usage_summary', {}), 'pinned_builds': run.get('build_usage_summary', {})})
    export_columns = st.columns(2)
    with export_columns[0]:
        st.download_button('导出评测完整 JSON', json.dumps(run, ensure_ascii=False, indent=2),
            file_name=f"evaluation-run-{run['run_id']}.json", mime='application/json', use_container_width=True)
    with export_columns[1]:
        st.download_button('下载可视化 HTML 报告', render_evaluation_report_html(run),
            file_name=f"evaluation-run-{run['run_id']}.html", mime='text/html', use_container_width=True)
    st.dataframe([{'样本': r['sample_index'], '策略': LABELS[r['strategy']], 'QA': r['qa']['value'], 'QA不可计分原因': r['qa'].get('reason'), '证据不可计分原因': r['mapping']['reason'], **r['source_coverage']} for r in run['results']], hide_index=True)
    st.caption('Full Text 使用完整原始对话；RAG 保留证据预算。近似计数采用 regex，不是 provider tokenizer 或账单 token。发送后未收到响应时，来源送达情况未知。')
    contexts = []
    for row in run['results']:
        trace = row.get('trace', {})
        budget = trace.get('evidence_budget', {})
        delivery = trace.get('source_delivery', {})
        estimate = budget.get('model_metadata', {}).get('request_context_estimate', {})
        usage = row.get('usage_summary', {})
        contexts.append({'样本': row['sample_index'], '策略': LABELS[row['strategy']],
            '全文应有来源数': len(delivery['expected_source_ids']) if delivery else None,
            '已确认请求来源数': len(delivery['delivered_source_ids']) if delivery else None,
            '送达状态': delivery.get('status'), '回答证据近似计数': budget.get('token_count'),
            '完整请求近似计数': estimate.get('token_count'), '证据预算': budget.get('budget'),
            '证据截断': budget.get('truncated'), '上下文超限': budget.get('context_limit_exceeded', False),
            '生成调用数': usage.get('generation_calls'), '缺少用量的调用数': usage.get('calls_without_reported_usage'),
            'provider 已报告 token': usage.get('reported_tokens'),
            '错误': row.get('error', {}).get('code')})
    st.dataframe(contexts, hide_index=True)
    for row in run['results']:
        with st.expander(f"样本 {row['sample_index']} · {LABELS[row['strategy']]} · 结果与失败检查"):
            trace = row.get('trace', {})
            if trace.get('answer'):
                st.text(trace['answer']['answer'])
                if trace['answer'].get('explanation'):
                    st.caption(trace['answer']['explanation'])
                if trace.get('time'):
                    st.caption(f"已知证据截止：{trace['time']['cutoff']}；不能确认之后的现实状态。")
            st.json(row)
    with st.expander('固定版本、实际配置、共享 Prompt 与完整记录'):
        st.json(run)
