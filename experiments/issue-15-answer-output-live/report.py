"""Compare saved paired runs; never send a model request or change a run."""
import argparse
from contextlib import redirect_stdout
import hashlib
import importlib.util
import io
import json
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parents[2]
REFERENCE = ROOT / 'experiments/issue-15-thinking-qa/results/results.json'
spec = importlib.util.spec_from_file_location('paired_report', ROOT / 'experiments/issue-15-thinking-qa/report.py')
paired = importlib.util.module_from_spec(spec)
spec.loader.exec_module(paired)


def render(directory, output):
    with redirect_stdout(io.StringIO()):
        paired.render(directory, output)
    current = json.loads((output / 'results.json').read_text())
    previous = json.loads(REFERENCE.read_text())
    plan = json.loads((directory / 'plan.json').read_text())
    run = json.loads((directory / 'evaluation-run.json').read_text())
    outcome = json.loads((directory / 'outcome.json').read_text())
    by_key = {(q['question_id'], item['strategy']): item for item in run['items']
              for q in [plan['questions'][item['sample_index']]]}
    rows = []
    for row in current['rows']:
        old = next(r for r in previous['rows'] if (r['question_id'], r['strategy']) == (row['question_id'], row['strategy']))
        item = by_key[row['question_id'], row['strategy']]
        trace = (item.get('result') or {}).get('trace', {})
        rows.append({**row, 'explanation': trace.get('answer', {}).get('explanation'),
                     'previous_execution_status': old['execution_status'], 'previous_answer': old['answer'],
                     'previous_run_qa_score': old['run_qa_score'],
                     'qa_delta': row['run_qa_score'] - old['run_qa_score'] if row['run_qa_score'] is not None else None})
    comparisons = {}
    for strategy, values in current['strategies'].items():
        old = previous['strategies'][strategy]
        group = [r for r in rows if r['strategy'] == strategy]
        comparisons[strategy] = {
            'before_success': old['successful'], 'after_success': values['successful'],
            'planned': values['planned'], 'before_answerable_f1': old['answerable_qa_mean'],
            'after_answerable_f1': values['answerable_qa_mean'],
            'answerable_f1_delta': values['answerable_qa_mean'] - old['answerable_qa_mean'],
            'official_refusal_matches': sum(r['execution_status'] == 'succeeded' and r['qa_score'] == 1 for r in group if r['category'] == 5),
            'canonical_refusal_count': sum(r['execution_status'] == 'succeeded' and r['answer'] == 'No information available.' for r in group if r['category'] == 5),
            'mean_answer_words_before': mean(len(r['answer'].split()) for r in previous['rows'] if r['strategy'] == strategy and r['answer']),
            'mean_answer_words_after': mean(len(r['answer'].split()) for r in group if r['answer'])}
    saved = {'run_id': current['run_id'], 'reference_run_id': previous['run_id'],
             'comparison': comparisons, 'rows': rows,
             'source_build_reused': plan['source_build_id'],
             'build_artifacts_unchanged': outcome['snapshot_build_unchanged'] and outcome['original_build_unchanged'],
             'new_paid_calls': outcome['budget_after']['reserved_total_calls'] - plan['budget_before']['reserved_total_calls'],
             'cumulative_calls': outcome['budget_after']['reserved_total_calls'],
             'candidate_audit': current['candidate_audit'], 'full_text_delivery': current['full_text_delivery']}
    (output / 'comparison.json').write_text(json.dumps(saved, ensure_ascii=False, indent=2) + '\n')
    lines = ['# 答案优化后的 conv-26 真实复验', '',
             f"新 Run `{current['run_id']}`；前轮 `{previous['run_id']}`。",
             '相同 10 道开发集原题、四策略，共 40 项；原 272 条 Memory、4902 条模型关系及索引均复用。',
             '本轮只改变查询实现；不重新抽取或判断关系，未读取本地测试集成绩。', '',
             '| 策略 | 执行成功：前 → 后 | 可回答 8 题 F1：前 → 后 | F1 变化 | 本轮两道拒答匹配 |',
             '| --- | --- | --- | --- | --- |']
    for strategy, c in comparisons.items():
        lines.append(f"| {strategy} | {c['before_success']}/10 → {c['after_success']}/10 | {c['before_answerable_f1']:.3f} → {c['after_answerable_f1']:.3f} | {c['answerable_f1_delta']:+.3f} | {c['official_refusal_matches']}/2 |")
    lines += ['', '已知执行失败在计划均值中记 0。F1 是原有类别词重叠评分，不能直接作为语义正确率；单次小样本不证明统计显著性。',
              '主答案压缩、截断契约与原文修订约束同时变化，不能分别估计三项改动的独立效果。', '',
              '## 主答案长度', '', '| 策略 | 前轮平均词数 | 本轮平均词数 |', '| --- | --- | --- |']
    for strategy, c in comparisons.items():
        lines.append(f"| {strategy} | {c['mean_answer_words_before']:.1f} | {c['mean_answer_words_after']:.1f} |")
    lines += ['', '只统计各轮成功产出主答案的样本。解释仍保存在 Trace 的 explanation，不参与 F1。', '',
              '## QA 53 时间核对', '',
              '原始会话于 2023-08-23 说 this week。正确语义为包含 8 月 23 日的一周，不能解释为此前一周。以下保留真实输出供核查：', '']
    for row in rows:
        if row['question_id'] == 'conv-26:qa:53':
            lines += [f"- `{row['strategy']}`，{row['execution_status']}：{row['answer'] or row['error']}",
                      f"  解释：{row['explanation'] or '无'}"]
    lines += ['', '## 来源与执行审计', '',
              f"构建及原库产物保持相同：`{saved['build_artifacts_unchanged']}`。本轮实际付费调用 {saved['new_paid_calls']}/200，历史累计 {saved['cumulative_calls']}。",
              f"Full Text 完整 419 轮且 HTTP 200：{current['full_text_delivery']['complete_sources_with_http_200_items']}/10；通过答案校验：{current['full_text_delivery']['accepted_complete_items']}/10。",
              '初始与扩展候选的逐题比较保存在 results.json，失败原因仅依据本轮安全诊断，不假定与前轮全部同因。',
              '完整逐题答案、引用和用量见 [report.md](report.md)；结构化前后对比见 [comparison.json](comparison.json)。',
              'UI 的策略切换与来源读取使用本地 Streamlit 交互测试验证，浏览器端到端情况另行记录。', '']
    (output / 'comparison.md').write_text('\n'.join(lines))
    report_path = output / 'report.md'
    report_path.write_text(report_path.read_text().replace('# conv-26：分阶段思考与四策略对照', '# conv-26：答案输出优化后的四策略复验', 1))
    files = ['plan.json', 'outcome.json', 'evaluation-run.json', 'evaluation-input.json', 'campaign.sqlite3', 'validation-causes.json']
    manifest = {'directory': str(directory), 'implementation_sha256': plan['implementation_sha256'],
                'source_directory': plan['source_directory'],
                'files': [{'path': str(directory / name), 'bytes': (directory / name).stat().st_size,
                           'sha256': hashlib.sha256((directory / name).read_bytes()).hexdigest()}
                          for name in files if (directory / name).exists()]}
    (output / 'artifacts.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'strategies': comparisons, 'new_paid_calls': saved['new_paid_calls']}, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--directory', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    render(args.directory.resolve(), args.output.resolve())
