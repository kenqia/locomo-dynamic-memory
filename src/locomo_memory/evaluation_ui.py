"""Evaluation controls and side-by-side comparisons through backend HTTP only."""
import json
import streamlit as st


LABELS = {'dynamic': '完整动态系统', 'full_text': 'Full Text 原始轮次', 'vector': 'Vector RAG（无状态解析）', 'hybrid_no_resolution': 'Hybrid + 扩展（无状态解析）'}


def render_development_plan(request, dataset_id):
    with st.expander('开发集评测计划预览', expanded=True):
        st.caption('开发集：conv-26、conv-30、conv-41、conv-42。本地测试：conv-43、conv-44，系统冻结后再测；教师隐藏评分集另行保密。')
        st.caption('预览只读取已导入的来源和独立 QA，不需要完整构建，不调用生成模型，也不运行本地测试。预览数量不代表已完成模型评测。')
        artifacts = request('GET', f'/datasets/{dataset_id}/provenance', params={'limit': 100})['items']
        artifact = st.selectbox('评测原件 artifact SHA256', [a['artifact_sha256'] for a in artifacts], key=f'evaluation_artifact_{dataset_id}')
        scope = st.selectbox('开发计划范围', ['development', 'smoke'], format_func=lambda value: '官方原件全量开发集：757 题 / 3,028 组合' if value == 'development' else 'conv-26：类别 1–5 各首题 / 20 组合')
        if st.button('生成开发集计划预览', disabled=not artifact):
            plan = request('POST', '/evaluation-plans', json={'dataset_id': dataset_id, 'artifact_sha256': artifact, 'scope': scope})
            st.session_state['evaluation_plan'] = plan
            st.session_state['evaluation_input_id'] = plan['input_id']
        plan_id = st.text_input('读取已保存 Plan ID', key='evaluation_saved_plan')
        if st.button('读取计划预览', disabled=not plan_id):
            st.session_state['evaluation_plan'] = request('GET', f'/evaluation-plans/{plan_id}')
        plan = st.session_state.get('evaluation_plan')
        if plan and plan['dataset_id'] == dataset_id:
            st.write(f"Plan {plan['plan_id']}")
            st.write(f"{plan['question_count']} 题 · {len(plan['strategies'])} 策略 · {plan['combination_count']} 组合 · 尚未执行")
            st.json({'course_split': plan['course_split'], 'strategies': plan['strategies'], 'input_id': plan['input_id'], 'artifact_sha256': plan['artifact_sha256']})
            st.dataframe(plan['questions'], hide_index=True)
            if st.button('运行此开发集计划'):
                run = request('POST', '/evaluation-runs', json={'plan_id': plan['plan_id']})
                st.session_state['evaluation_run'] = run
                st.session_state['evaluation_saved_run'] = run['run_id']
            st.download_button('导出开发集计划 JSON', json.dumps(plan, ensure_ascii=False, indent=2), file_name=f"evaluation-plan-{plan['plan_id']}.json", mime='application/json')
            with st.expander('完整计划与来源身份'):
                st.json(plan)


def render_evaluation(request, dataset_id):
    st.subheader('独立评测与基线比较')
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
    strategies = st.multiselect('对照策略', list(LABELS), default=list(LABELS), format_func=LABELS.get)
    partition = st.selectbox('课程划分（合成案例选择不适用）', ['不适用', 'dev', 'test'])
    if st.button('运行所选对照', disabled=not input_id or not strategies):
        created = request('POST', '/evaluation-runs', json={'input_id': input_id, 'strategies': strategies, 'partition': None if partition == '不适用' else partition})
        st.session_state['evaluation_run'] = created
        st.session_state['evaluation_saved_run'] = created['run_id']
    run_id = st.text_input('读取已保存 Run ID', key='evaluation_saved_run')
    if st.button('读取评测记录', disabled=not run_id):
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
    columns = st.columns(max(1, len(run.get('summary', {}))))
    for column, (strategy, summary) in zip(columns, run['summary'].items()):
        with column:
            st.write(LABELS[strategy])
            st.json(summary)
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
            st.json(row)
    with st.expander('固定版本、实际配置、共享 Prompt 与完整记录'):
        st.json(run)
