"""Present reviewed aggregates with readable precision and lossless details."""
import json

import streamlit as st

from locomo_memory.console_widgets import compact_choice


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


def render_report_totals(baseline):
    for column, label, field in zip(st.columns(4), ('原 Run 计划组合', '成功', '失败', 'unknown'),
                                    ('planned_combinations', 'succeeded', 'failed', 'unknown')):
        column.metric(label, baseline[field])
    st.caption(f"{baseline['questions']} 个问题；unknown 表示未确定的运行状态。")


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
        st.caption('该子集不能代表全量质量提升；证据语义正确性尚未独立评测。')

    render_report_totals(evidence['original_baseline'])
    st.subheader('分组结果')
    dimension = compact_choice('聚合维度', ('strategy', 'conversation', 'category'),
                             format_func={'strategy': '策略', 'conversation': '对话', 'category': '题型'}.get,
                             key='experiment_dimension')
    st.caption('按单个维度汇总；完整精度可在下方查看或下载。')
    groups = evidence['original_baseline']['groups'][dimension]

    def label(name):
        return STRATEGIES.get(name, name) if dimension == 'strategy' else f'题型 {name}' if dimension == 'category' else name

    st.table([{'分组': label(name), '计划组合': group['planned'],
                   '运行成功率': shown(group.get('execution_success_rate'), percent=True),
                   '成功子集 QA': shown(group['qa_successful_scorable'].get('mean'))}
                  for name, group in groups.items()])
    group_name = compact_choice('查看分组详情', list(groups), format_func=label,
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

    st.subheader('可比子集优势与全部运行失败')
    for column, title, field in zip(st.columns(4), ('可比成功配对', 'Dynamic 配对 QA', 'Hybrid 配对 QA', '配对平均差'),
                                    ('comparable', 'paired_dynamic_mean', 'paired_hybrid_mean', 'mean_paired_delta')):
        value = paired.get(field)
        column.metric(title, str(value) if field == 'comparable' and value is not None else shown(value))
    for column, strategy in zip(st.columns(2), ('dynamic', 'hybrid')):
        with column.container(border=True):
            st.markdown('**' + STRATEGIES[strategy] + '**')
            values = paired[strategy]
            st.write(f"完整分母：{values['n']} · 失败：{values['states'].get('failed', 'unknown')} · unknown：{values['states'].get('unknown', 'unknown')}")
            st.write('运行成功率：' + shown(values.get('success_rate'), percent=True))
            st.write('完整分母 QA：' + shown(values.get('full_denominator_score')))

    st.subheader('历史成本与缺测')
    strategy = compact_choice('成本策略', list(evidence['provider_cost_estimates']),
                            format_func=lambda name: STRATEGIES.get(name, name), key='experiment_cost')
    cost = evidence['provider_cost_estimates'][strategy]
    for column, title, value in zip(st.columns(4), ('已知峰值价估算 CNY', '未知预留 CNY', '用量缺失请求', '物理 HTTP'),
                                    (shown(cost.get('known_peak_estimate_cny')), shown(cost.get('unknown_reservation_cny')),
                                     cost.get('usage_missing_requests', 'unknown'), cost.get('physical_http', 'unknown'))):
        column.metric(title, value)
    st.caption('历史价格估算，非账户实扣。对话与题型的成本未记录。')
    with st.expander('共享 Build 成本（不重复摊入每个策略）'):
        st.json(evidence['shared_build_cost'])
    with st.expander('完整精度与成本明细'):
        st.caption('百分比保留两位，分数与成本保留四位；细小非零值用科学计数。以下保留原始精度，缺失字段不填零。')
        st.caption('已知完成率包含成功与失败；运行成功率只计成功。unknown 表示字段未记录或状态未确定。')
        st.json({'groups': groups, 'paired': paired, 'provider_cost_estimates': evidence['provider_cost_estimates']})
        st.download_button('下载冻结报告 JSON', json.dumps(evidence, ensure_ascii=False, indent=2),
                           file_name='frozen-research-report.json', mime='application/json', key='experiment_export')
