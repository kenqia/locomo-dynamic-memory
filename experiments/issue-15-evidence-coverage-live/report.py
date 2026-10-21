"""Read-only A/B metrics and actual source delivery; no model requests."""
import argparse
import csv
import hashlib
import importlib.util
import json
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('paired_metrics', ROOT / 'experiments/issue-15-thinking-qa/report.py')
paired = importlib.util.module_from_spec(spec)
spec.loader.exec_module(paired)


def render(directory, output):
    output.mkdir(parents=True, exist_ok=True)
    plan = json.loads((directory / 'plan.json').read_text())
    outcome = json.loads((directory / 'outcome.json').read_text())
    previous = json.loads((ROOT / 'experiments/issue-15-answer-output-live/results/results.json').read_text())
    rows, summaries, candidates = [], {}, []
    for label, group in plan['experiments'].items():
        run = json.loads((directory / f'{label}-run.json').read_text())
        for item in run['items']:
            question = group['questions'][item['sample_index']]
            qa = question['official_qa']
            result = item.get('result') or {}
            trace = result.get('trace', {})
            answer = trace.get('answer', {})
            raw = trace.get('raw_fallback', {})
            gold = set(result.get('mapping', {}).get('source_ids', []))
            budgets = trace.get('resolution_budgets', {})
            def delivered(stage):
                return budgets.get(stage, {}).get('source_delivery', {}).get('delivered_source_ids')
            first = delivered('resolve')
            joint = delivered('joint_resolve')
            if item['strategy'] == 'dynamic':
                first = result.get('source_sets', {}).get('expanded')
            final = result.get('source_sets', {}).get('answer_context', [])
            old = next((r for r in previous['rows'] if r['question_id'] == question['question_id'] and r['strategy'] == item['strategy']), None) if label == 'A' else None
            rows.append({'experiment': label, 'run_id': run['run_id'], 'question_id': question['question_id'],
                'qa_index': question['qa_index'], 'purpose': question['purpose'], 'question': qa['question'],
                'category': qa['category'], 'reference_answer': qa.get('answer'), 'strategy': item['strategy'],
                'execution_status': item['status'], 'answer_status': answer.get('status'),
                'answer': answer.get('answer'), 'explanation': answer.get('explanation'),
                'qa_score': result.get('qa', {}).get('value'),
                'run_score': 0 if item['status'] == 'failed' else result.get('qa', {}).get('value'),
                'reference_source_ids': sorted(gold),
                'first_resolution_delivered_source_ids': first,
                'first_resolution_reference_coverage': len(set(first) & gold) / len(gold) if first is not None and gold else None,
                'joint_resolution_delivered_source_ids': joint,
                'joint_resolution_reference_coverage': len(set(joint) & gold) / len(gold) if joint is not None and gold else None,
                'answer_delivered_source_ids': final,
                'answer_reference_coverage': result.get('source_coverage', {}).get('answer_context'),
                'citations': answer.get('citations', []), 'raw_triggered': raw.get('triggered'),
                'raw_trigger_reasons': raw.get('trigger_reasons'),
                'raw_cited_source_ids': raw.get('cited_source_ids', []),
                'previous_score': old['run_qa_score'] if old else None,
                'previous_answer': old['answer'] if old else None,
                'error': result.get('error'), 'usage': result.get('usage_summary', {})})
        def score(group):
            if any(r['execution_status'] not in {'succeeded', 'failed'} for r in group):
                return None
            return mean(r['run_score'] for r in group) if group else None
        summaries[label] = {}
        for strategy in group['strategies']:
            selected = [r for r in rows if r['experiment'] == label and r['strategy'] == strategy]
            answerable = [r for r in selected if r['category'] != 5]
            refusal = [r for r in selected if r['category'] == 5]
            summaries[label][strategy] = {'successful': sum(r['execution_status'] == 'succeeded' for r in selected),
                'planned': len(selected), 'answerable_questions': len(answerable), 'answerable_f1': score(answerable),
                'official_refusal_matches': sum(r['execution_status'] == 'succeeded' and r['qa_score'] == 1 for r in refusal),
                'refusal_questions': len(refusal), 'all_qa_mean': score(selected),
                'generation_calls': sum(r['usage'].get('generation_calls', 0) for r in selected),
                'usage': run['summary'][strategy]['usage_summary']}
            if label == 'A':
                old_scores = [r['previous_score'] for r in answerable]
                summaries[label][strategy]['previous_matched_answerable_f1'] = (
                    mean(old_scores) if old_scores and all(s is not None for s in old_scores) else None)
        for index, question in enumerate(group['questions']):
            items = [i for i in run['items'] if i['sample_index'] == index]
            left, right = [paired.candidate_rankings(i.get('result') or {}) for i in items]
            candidates.append({'experiment': label, 'question_id': question['question_id'],
                **{stage + '_same_set': set(left[stage]) == set(right[stage]) if stage in left and stage in right else None for stage in ['initial', 'expanded']}})
    result = {'status': outcome['status'], 'summaries': summaries, 'rows': rows,
              'candidate_comparisons': candidates, 'scope': plan['selection_scope'],
              'paid_calls': outcome['budget_after']['reserved_total_calls'] - plan['budget_before']['reserved_total_calls'],
              'cumulative_calls': outcome['budget_after']['reserved_total_calls'],
              'budget_limit': outcome['budget_after']['limit'],
              'original_build_unchanged': outcome['original_build_unchanged'],
              'snapshot_build_unchanged': outcome['snapshot_build_unchanged']}
    (output / 'results.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    with (output / 'paired-qa.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    def fmt(value):
        return '未评' if value is None else f'{value:.3f}'
    lines = ['# 证据覆盖优化的真实实验 A/B', '',
             f"状态 `{outcome['status']}`。复用 Build `{plan['source_build_id']}`，未重新构建记忆库。",
             'A 为固定 5 题定向修复及时间防退化；B 为预选 10 道尚未用于调参的新问题。',
             'B 仅为同一 conv-26 内的问题级留出，底层对话事实已有开发暴露，不代表新对话或隐藏测试泛化。', '',
             '| 实验 | 策略 | 执行成功 / 计划 | 可回答题 F1 | 官方拒答匹配 | 调用数 |',
             '| --- | --- | --- | --- | --- | --- |']
    for label, values in summaries.items():
        for strategy, summary in values.items():
            lines.append(f"| {label} | {strategy} | {summary['successful']}/{summary['planned']} | {fmt(summary['answerable_f1'])} | {summary['official_refusal_matches']}/{summary['refusal_questions']} | {summary['generation_calls']} |")
    lines += ['', 'A 只与前轮同样 4 道可回答题比较，不使用前轮 8 题总均值作基点：']
    for strategy, summary in summaries['A'].items():
        lines.append(f"- `{strategy}`：{fmt(summary['previous_matched_answerable_f1'])} → {fmt(summary['answerable_f1'])}。")
    lines += ['', '适用参考规则的已知执行失败在计划均值中记 0。F1 不是语义正确率；标注来源送达也不等于完整答案。',
              '两组题目和策略不同，不能直接用 A 与 B 的均值作泛化差值；没有预设分数保证。',
              '同题初始和扩展候选比较保存在 results.json。没有独立动态真值，动态准确率仍未评。', '',
              f"本轮调用 {result['paid_calls']}/102，历史累计 {result['cumulative_calls']}/{result['budget_limit']}，失败与重试均占额度。",
              f"原库构建摘要未变：{result['original_build_unchanged']}；快照构建摘要未变：{result['snapshot_build_unchanged']}。", '',
              '## 逐题回答与实际来源', '']
    for label, group in plan['experiments'].items():
        for question in group['questions']:
            lines += [f"### {label} · QA {question['qa_index']}：{question['official_qa']['question']}", '',
                      f"参考答案：{question['official_qa'].get('answer', '无，应识别错误前提或证据不足')}。", '']
            for row in rows:
                if row['experiment'] != label or row['question_id'] != question['question_id']:
                    continue
                lines += [f"- `{row['strategy']}`：{row['execution_status']} / {row['answer_status']}，F1={fmt(row['qa_score'])}。{row['answer'] or row['error']}",
                          f"  解释：{row['explanation'] or '无'}",
                          f"  标注来源覆盖：首次解析 {fmt(row['first_resolution_reference_coverage'])}，联合解析 {fmt(row['joint_resolution_reference_coverage'])}，最终回答 {fmt(row['answer_reference_coverage'])}。原文补查：{row['raw_triggered']}。"]
                if label == 'A':
                    lines += [f"  前轮同题：{row['previous_answer']}；F1={fmt(row['previous_score'])}。"]
            lines.append('')
    (output / 'report.md').write_text('\n'.join(lines))
    files = ['plan.json', 'outcome.json', 'A-run.json', 'B-run.json', 'A-input.json', 'B-input.json',
             'campaign.sqlite3', 'question-usage-audit.json', 'validation-causes.json', 'regression-tests.txt']
    manifest = {'directory': str(directory), 'implementation_sha256': plan['implementation_sha256'],
                'files': [{'path': str(directory / name), 'bytes': (directory / name).stat().st_size,
                           'sha256': hashlib.sha256((directory / name).read_bytes()).hexdigest()}
                          for name in files if (directory / name).exists()]}
    (output / 'artifacts.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'status': result['status'], 'summaries': summaries, 'paid_calls': result['paid_calls']}, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    render(args.directory.resolve(), args.output.resolve())
