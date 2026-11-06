"""Compare reviewed aggregates without creating or merging evaluation runs."""
import streamlit as st


def shown(value):
    return 'unknown' if value is None else str(value)


def render_experiment_comparison(evidence):
    run_set = st.radio('结果集', ('original', 'supplementary'),
                       format_func=lambda value: '原 Run' if value == 'original' else '补充 / 修复 Run',
                       horizontal=True, key='experiment_run_set')
    if run_set == 'supplementary':
        st.info('当前公开冻结快照未提供补充 / 修复 Run；不合并、不借用原 Run 成绩填充。')
        return
    dimension = st.selectbox('聚合维度', ('strategy', 'conversation', 'category'),
                             format_func={'strategy': '策略', 'conversation': '对话', 'category': '题型'}.get,
                             key='experiment_dimension')
    st.caption('单维冻结聚合；没有联合明细时不伪造对话 × 题型 × 策略交叉筛选。')
    groups = evidence['original_baseline']['groups'][dimension]
    rows = []
    for name, group in groups.items():
        score = group['qa_successful_scorable']
        rows.append({dimension: name, 'planned': group['planned'],
                     **{status: shown(group['states'].get(status)) for status in ('succeeded', 'failed', 'unknown')},
                     '完成率': shown(group.get('execution_success_rate')),
                     '成功子集 QA': shown(score.get('mean')), '计分样本': shown(score.get('measured')),
                     '未计分 / 缺测': shown(score.get('unknown')),
                     '完整分母 QA': shown(group.get('full_denominator_qa_score'))})
    st.dataframe(rows, hide_index=True, width='stretch')
    st.caption('unknown 表示快照未提供该值，不能填零；QA 分数与证据语义正确性分别看待。')
    st.subheader('可比子集优势与全部运行失败')
    paired = evidence['paired']
    columns = st.columns(4)
    for column, label, field in zip(columns, ('可比成功配对', 'Dynamic 配对 QA', 'Hybrid 配对 QA', '配对平均差'),
                                    ('comparable', 'paired_dynamic_mean', 'paired_hybrid_mean', 'mean_paired_delta')):
        column.metric(label, shown(paired.get(field)))
    st.dataframe([{'策略': strategy, '完整分母': paired[strategy]['n'],
                   '成功率': shown(paired[strategy].get('success_rate')),
                   '失败': shown(paired[strategy]['states'].get('failed')),
                   'unknown': shown(paired[strategy]['states'].get('unknown')),
                   '完整分母得分': shown(paired[strategy].get('full_denominator_score'))}
                  for strategy in ('dynamic', 'hybrid')], hide_index=True, width='stretch')
    st.caption('配对优势只针对双方成功的子集；同时保留完整分母、失败与 unknown，不据此宣称全量质量提升。')
    st.subheader('历史成本与缺测')
    st.dataframe([{'策略': name, '已知峰值价估算 CNY': shown(cost.get('known_peak_estimate_cny')),
                   '未知预留 CNY': shown(cost.get('unknown_reservation_cny')),
                   '用量缺失请求': shown(cost.get('usage_missing_requests')),
                   '物理 HTTP': shown(cost.get('physical_http'))}
                  for name, cost in evidence['provider_cost_estimates'].items()], hide_index=True, width='stretch')
    st.caption('这是历史峰值价估算，不是账户实扣；未知预留不算零。对话 / 题型维度的成本未提供，保持 unknown。')
    with st.expander('共享 Build 成本（不重复摊入每个策略）'):
        st.json(evidence['shared_build_cost'])
