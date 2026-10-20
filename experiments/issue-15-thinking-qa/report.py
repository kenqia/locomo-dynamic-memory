"""Render the saved experiment without model calls or changes to its database."""
import argparse
import csv
import json
from pathlib import Path
from statistics import mean


def render(directory, output):
    plan = json.loads((directory / 'plan.json').read_text())
    outcome = json.loads((directory / 'outcome.json').read_text())
    run = json.loads((directory / 'evaluation-run.json').read_text())
    output.mkdir(parents=True, exist_ok=True)
    rows = []
    for item in run['items']:
        question = plan['questions'][item['sample_index']]
        result = item.get('result') or {}
        trace = result.get('trace', {})
        answer = trace.get('answer', {})
        usage = result.get('usage_summary', {})
        delivery = trace.get('source_delivery', {})
        raw = trace.get('raw_fallback', {})
        budget = trace.get('evidence_budget', {})
        rows.append({'question_id': question['question_id'], 'purpose': question['purpose'],
                     'question': question['official_qa']['question'],
                     'gold': question['official_qa'].get('answer'),
                     'category': question['official_qa']['category'], 'strategy': item['strategy'],
                     'execution_status': item['status'], 'answer_status': answer.get('status'),
                     'answer': answer.get('answer'), 'qa_score': result.get('qa', {}).get('value'),
                     'answer_source_coverage': result.get('source_coverage', {}).get('answer_context'),
                     'initial_source_coverage': result.get('source_coverage', {}).get('initial'),
                     'expanded_source_coverage': result.get('source_coverage', {}).get('expanded'),
                     'elapsed_seconds': sum(a.get('elapsed_seconds') or 0 for a in item['attempts']),
                     'generation_calls': usage.get('generation_calls'),
                     'total_tokens': usage.get('reported_tokens', {}).get('total_tokens'),
                     'full_text_expected_sources': len(delivery.get('expected_source_ids', [])) if delivery else None,
                     'full_text_delivered_sources': len(delivery.get('delivered_source_ids', [])) if delivery else None,
                     'provider_accepted': delivery.get('provider_accepted'),
                     'evidence_truncated': budget.get('truncated'),
                     'context_limit_exceeded': budget.get('context_limit_exceeded', False),
                     'raw_fallback_triggered': raw.get('triggered'),
                     'raw_fallback_selected_sources': len(raw.get('source_ids', [])),
                     'raw_fallback_effective_sources': len(raw.get('effective_source_ids', [])),
                     'raw_fallback_cited_sources': len(raw.get('cited_source_ids', [])),
                     'error': result.get('error'),
                     'citations': answer.get('citations', [])})
    summary = {}
    for strategy in plan['strategies']:
        group = [r for r in rows if r['strategy'] == strategy]
        answerable = [r for r in group if r['category'] != 5]
        refusal = [r for r in group if r['category'] == 5]
        # Failed known outcomes count zero. Pending/unknown outcomes never become zero.
        def score(items):
            if any(r['execution_status'] not in {'succeeded', 'failed'} for r in items):
                return None
            return mean(r['qa_score'] if r['execution_status'] == 'succeeded' else 0 for r in items)
        summary[strategy] = {'successful': sum(r['execution_status'] == 'succeeded' for r in group),
                             'planned': len(group), 'answerable_qa_mean': score(answerable),
                             'official_refusal_mean': score(refusal),
                             'all_qa_mean': score(group),
                             'raw_fallback_triggered_items': sum(r['raw_fallback_triggered'] is True for r in group),
                             'mean_attempt_seconds': mean(r['elapsed_seconds'] for r in group),
                             'usage': run['summary'][strategy]['usage_summary']}
    comparisons = []
    for index, question in enumerate(plan['questions']):
        results = {i['strategy']: i.get('result') or {} for i in run['items'] if i['sample_index'] == index}
        base = results['dynamic'].get('memory_rankings', {})
        for other in ['dynamic_raw_fallback', 'hybrid_no_resolution']:
            candidate = results[other].get('memory_rankings', {})
            comparisons.append({'question_id': question['question_id'], 'comparison': 'dynamic vs ' + other,
                                **{stage + '_same_order': base.get(stage) == candidate.get(stage)
                                   if stage in base and stage in candidate else None for stage in ['initial', 'expanded']},
                                **{stage + '_same_set': set(base[stage]) == set(candidate[stage])
                                   if stage in base and stage in candidate else None for stage in ['initial', 'expanded']}})
    saved = {'status': outcome['status'], 'build_id': outcome['build_id'], 'run_id': run['run_id'],
             'strategies': summary, 'rows': rows, 'budget': outcome['budget_after'],
             'candidate_comparisons': comparisons,
             'implementation_sha256': plan['implementation_sha256'], 'config': plan['settings'],
             'dynamic_accuracy': 'unavailable_without_independent_truth'}
    full_text = [r for r in rows if r['strategy'] == 'full_text']
    saved['full_text_delivery'] = {
        'planned': len(full_text),
        'accepted_complete_items': sum(
            r['execution_status'] == 'succeeded' and r['provider_accepted'] is True
            and r['full_text_expected_sources'] == r['full_text_delivered_sources']
            and bool(r['full_text_expected_sources']) and r['evidence_truncated'] is False
            and not r['context_limit_exceeded'] for r in full_text),
        'expected_source_counts': sorted({r['full_text_expected_sources'] for r in full_text
                                          if r['full_text_expected_sources'] is not None})}
    (output / 'results.json').write_text(json.dumps(saved, ensure_ascii=False, indent=2) + '\n')
    with (output / 'paired-qa.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    lines = ['# conv-26：分阶段思考与四策略对照', '',
             f"Build `{outcome['build_id']}`；Run `{run['run_id']}`；状态 `{outcome['status']}`。", '',
             '10 道官方原始开发集 QA，四策略共 40 项。8 道有参考答案，2 道是证据不足对抗题。',
             '同题配对、单次运行，不能推断统计显著性；未运行全关闭思考对照，不能单独归因于思考强度。', '',
             '| 策略 | 成功 / 计划 | 可回答 8 题 QA 均值 | 2 题官方拒答匹配 | 全部 10 题均值 | 平均尝试秒数 | 查询 tokens |',
             '| --- | --- | --- | --- | --- | --- | --- |']
    def fmt(value):
        return '未评' if value is None else f'{value:.3f}'
    for name, values in summary.items():
        lines.append(f"| {name} | {values['successful']}/{values['planned']} | {fmt(values['answerable_qa_mean'])} | {fmt(values['official_refusal_mean'])} | {fmt(values['all_qa_mean'])} | {values['mean_attempt_seconds']:.2f} | {values['usage']['reported_tokens']['total_tokens']} |")
    full = saved['full_text_delivery']
    budget = outcome['budget_after']
    lines += ['',
              f"Full Text 完整来源且提供方接受的项目为 {full['accepted_complete_items']}/{full['planned']}；预期来源轮次数为 {full['expected_source_counts']}。完整检查同时要求执行成功、未截断及未超出上下文。",
              f"原文兜底实际触发 {summary['dynamic_raw_fallback']['raw_fallback_triggered_items']}/10 题；逐题检索、有效与引用来源数见 CSV。",
              f"共享账本累计预留 {budget.get('reserved_total_calls')}/{budget.get('limit')} 次，包含历史、失败、重试及未知结果。",
              '', '官方 QA 采用既有类别 F1 和拒答短语规则，长答案可能因多余词扣分。',
              '拒答规则只识别 `no information available`、`not mentioned`，须结合实际回答检查。',
              '来源覆盖只说明标注轮次是否进入上下文，不证明事实正确。对抗题的标注轮次可能属于另一人物。',
              '三种 RAG 各自执行查询分析；`results.json` 的 `candidate_comparisons` 核对初始及扩展候选是否相同。候选不同的题不能把差异完全归因于解析。',
              '`dynamic` 与 `hybrid_no_resolution` 比较查询时有效证据解析，两者仍共享构建时关系与历史扩展，不能据此隔离构建关系判断的作用。',
              '动态关系与有效证据准确率缺少独立真值，保持未评。Full Text 的完整来源覆盖不算检索能力。', '',
              '## 同题得分', '',
              '| 官方 QA index | 用途 | dynamic | dynamic_raw_fallback | hybrid_no_resolution | full_text |',
              '| --- | --- | --- | --- | --- | --- |']
    for question in plan['questions']:
        group = [r for r in rows if r['question_id'] == question['question_id']]
        lines.append('| ' + ' | '.join([str(question['qa_index']), question['purpose'], *[
            fmt(next(r['qa_score'] for r in group if r['strategy'] == name)) for name in plan['strategies']]]) + ' |')
    lines += ['', '## 逐题回答', '']
    for question in plan['questions']:
        lines += [f"### QA {question['qa_index']}：{question['official_qa']['question']}", '',
                  f"参考：{question['official_qa'].get('answer', '无参考答案，应识别证据不足')}。", '']
        for row in [r for r in rows if r['question_id'] == question['question_id']]:
            lines += [f"- `{row['strategy']}`，{row['execution_status']} / {row['answer_status']}，QA={fmt(row['qa_score'])}，来源覆盖={fmt(row['answer_source_coverage'])}。{row['answer'] or row['error']}"]
        lines.append('')
    (output / 'report.md').write_text('\n'.join(lines) + '\n')
    print(json.dumps({'status': outcome['status'], 'strategies': summary}, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    render(args.directory, args.output)
