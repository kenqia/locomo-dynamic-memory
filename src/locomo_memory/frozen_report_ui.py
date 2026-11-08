"""Present reviewed aggregates with readable precision and lossless details."""
import json

import streamlit as st


STRATEGIES = {'dynamic': 'Dynamic', 'hybrid': 'Hybrid', 'hybrid_no_resolution': 'Hybrid（无解析）',
              'full_text': 'Full Text', 'vector': 'Vector'}


def shown(value, percent=False):
    if value is None:
        return 'unknown'
    if percent:
        return f'{value:.2%}'
    return f'{value:.4f}' if value == 0 or abs(value) >= 0.00005 else f'{value:.2e}'


def completion_rate(group):
    states = group['states']
    if not group['planned'] or sum(states.values()) != group['planned']:
        return None
    return (states.get('succeeded', 0) + states.get('failed', 0)) / group['planned']


def render_experiment_comparison(evidence):
    run_set = st.radio('结果集', ('original', 'supplementary'),
                       format_func=lambda value: '原 Run' if value == 'original' else '补充 / 修复 Run',
                       horizontal=True, key='experiment_run_set')
    if run_set == 'supplementary':
        st.info('当前公开冻结快照未提供补充 / 修复 Run；不合并、不借用原 Run 成绩填充。')
        return

    paired = evidence['paired']
    with st.container(border=True):
        st.markdown('**如何理解结果**')
        st.write(f"在 {paired['comparable']} 个双方成功的配对中，Dynamic 与 Hybrid 的 QA 均分差为 "
                 f"{shown(paired.get('mean_paired_delta'))}。该差值只描述可比成功子集。")
        st.write(f"全量各 {paired['n']} 项中，Dynamic 记录 {paired['dynamic']['states'].get('failed', 'unknown')} 项失败，"
                 f"Hybrid 记录 {paired['hybrid']['states'].get('failed', 'unknown')} 项失败。请结合完整分母与 unknown 判断。")
        st.caption('不据成功子集宣称全量质量提升；证据语义正确性缺少独立真值，仍为未评。')

    st.subheader('分组结果')
    dimension = st.selectbox('聚合维度', ('strategy', 'conversation', 'category'),
                             format_func={'strategy': '策略', 'conversation': '对话', 'category': '题型'}.get,
                             key='experiment_dimension')
    st.caption('单维冻结聚合；没有联合明细时不伪造交叉筛选。百分比保留两位，分数与成本保留四位；完整精度在下方详情与导出中。')
    groups = evidence['original_baseline']['groups'][dimension]

    def label(name):
        return STRATEGIES.get(name, name) if dimension == 'strategy' else f'题型 {name}' if dimension == 'category' else name

    st.dataframe([{'分组': label(name), '计划组合': group['planned'],
                   '运行成功率': shown(group.get('execution_success_rate'), percent=True),
                   '成功子集 QA': shown(group['qa_successful_scorable'].get('mean'))}
                  for name, group in groups.items()], hide_index=True, width='stretch')
    group_name = st.selectbox('查看分组详情', list(groups), format_func=label,
                              key=f'experiment_group_{dimension}')
    group = groups[group_name]
    with st.container(border=True):
        st.text(label(group_name))
        for column, title, value in zip(st.columns(4), ('本组计划', '本组成功', '本组失败', '本组 unknown'),
                                        (group['planned'], *(group['states'].get(k, 'unknown') for k in ('succeeded', 'failed', 'unknown')))):
            column.metric(title, value)
        score = group['qa_successful_scorable']
        values = (shown(completion_rate(group), percent=True), shown(group.get('execution_success_rate'), percent=True),
                  shown(score.get('mean')), shown(group.get('full_denominator_qa_score')))
        for column, title, value in zip(st.columns(4), ('已知完成率（含失败）', '运行成功率', '成功子集 QA', '完整分母 QA'), values):
            column.metric(title, value)
        st.caption(f"计分样本：{score.get('measured', 'unknown')} · 未计分 / 缺测：{score.get('unknown', 'unknown')}")
        st.caption('完成率包含已知成功与失败，unknown 不算已知完成；状态未单列的字段保持 unknown，不填零。')

    st.subheader('可比子集优势与全部运行失败')
    for column, title, field in zip(st.columns(4), ('可比成功配对', 'Dynamic 配对 QA', 'Hybrid 配对 QA', '配对平均差'),
                                    ('comparable', 'paired_dynamic_mean', 'paired_hybrid_mean', 'mean_paired_delta')):
        value = paired.get(field)
        column.metric(title, str(value) if field == 'comparable' and value is not None else shown(value))
    st.dataframe([{'策略': STRATEGIES[strategy], '完整分母': paired[strategy]['n'],
                   '运行成功率': shown(paired[strategy].get('success_rate'), percent=True),
                   '失败': paired[strategy]['states'].get('failed', 'unknown'),
                   'unknown': str(paired[strategy]['states'].get('unknown', 'unknown')),
                   '完整分母 QA': shown(paired[strategy].get('full_denominator_score'))}
                  for strategy in ('dynamic', 'hybrid')], hide_index=True, width='stretch')
    st.caption('配对优势只针对双方成功的子集；同时保留完整分母、失败与 unknown。')

    st.subheader('历史成本与缺测')
    strategy = st.selectbox('成本策略', list(evidence['provider_cost_estimates']),
                            format_func=lambda name: STRATEGIES.get(name, name), key='experiment_cost')
    cost = evidence['provider_cost_estimates'][strategy]
    for column, title, value in zip(st.columns(4), ('已知峰值价估算 CNY', '未知预留 CNY', '用量缺失请求', '物理 HTTP'),
                                    (shown(cost.get('known_peak_estimate_cny')), shown(cost.get('unknown_reservation_cny')),
                                     cost.get('usage_missing_requests', 'unknown'), cost.get('physical_http', 'unknown'))):
        column.metric(title, value)
    st.caption('历史峰值价估算不是账户实扣；未知预留不算零。对话 / 题型成本未提供，保持 unknown。细小非零值用科学计数展示。')
    with st.expander('共享 Build 成本（不重复摊入每个策略）'):
        st.json(evidence['shared_build_cost'])
    with st.expander('完整精度与成本明细'):
        st.json({'groups': groups, 'paired': paired, 'provider_cost_estimates': evidence['provider_cost_estimates']})
        st.download_button('下载冻结报告 JSON', json.dumps(evidence, ensure_ascii=False, indent=2),
                           file_name='frozen-research-report.json', mime='application/json', key='experiment_export')
