"""Summarize existing evaluation scores and source audits, without model calls."""
import argparse
import json
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parents[2]


def render(directory, output, baseline_path=None):
    plan = json.loads((directory / 'plan.json').read_text())
    outcome = json.loads((directory / 'outcome.json').read_text())
    baseline_path = baseline_path or ROOT / 'experiments/issue-15-evidence-coverage-live/results/results.json'
    baseline = json.loads(baseline_path.read_text())
    rows = []
    for label, group in plan['experiments'].items():
        run_path = directory / f'{label}-run.json'
        if not run_path.exists():
            continue
        run = json.loads(run_path.read_text())
        for item in run['items']:
            q = group['questions'][item['sample_index']]
            result = item.get('result') or {}
            trace = result.get('trace') or {}
            answer = trace.get('answer') or {}
            old = next((r for r in baseline['rows'] if (r.get('question_id') == q['question_id'] or r.get('qa_index') == q['qa_index'])
                        and r['strategy'] == item['strategy']), None)
            budgets = trace.get('resolution_budgets', {})
            raw = trace.get('raw_fallback', {})
            coverage = trace.get('initial_resolution', {}).get('coverage', [])
            prior_ids = {mid for c in coverage for mid in c['memory_ids']}
            rows.append(dict(group=label, qa_index=q['qa_index'], question=q['official_qa']['question'],
                reference_answer=q['official_qa'].get('answer'), category=q['official_qa']['category'],
                strategy=item['strategy'], status=item['status'], answer=answer.get('answer'),
                explanation=answer.get('explanation'), answer_status=answer.get('status'),
                citations=answer.get('citations', []), score=result.get('qa', {}).get('value'),
                baseline_answer=old['answer'] if old else None,
                baseline_score=(0 if old.get('status') == 'failed' else old.get('run_score', old.get('score'))) if old else None,
                first_delivered_source_ids=budgets.get('resolve', {}).get('source_delivery', {}).get('delivered_source_ids'),
                joint_delivered_source_ids=budgets.get('joint_resolve', {}).get('source_delivery', {}).get('delivered_source_ids'),
                resolution_budgets=budgets, source_sets=result.get('source_sets'),
                source_coverage=result.get('source_coverage'), memory_rankings=result.get('memory_rankings'),
                raw_triggered=raw.get('triggered'), recovery=raw.get('recovery'),
                strategy_recovery=trace.get('strategy_recovery'),
                initial_supported_memory_ids=sorted(prior_ids),
                final_effective_memory_ids=[m['memory_id'] for m in trace.get('effective_memories', [])],
                initial_resolution=trace.get('initial_resolution'), final_resolution=trace.get('resolution'),
                delivered_coverage=trace.get('delivered_coverage'), time_diagnostics=trace.get('time_diagnostics'),
                error=result.get('error'), usage=result.get('usage_summary'), trace_id=trace.get('trace_id')))
    summaries = {}
    for label in plan['experiments']:
        selected = [r for r in rows if r['group'] == label]
        answerable = [r for r in selected if r['category'] != 5]
        matched = [r for r in answerable if r['baseline_score'] is not None]
        def score(rs):
            values = [0 if r['status'] == 'failed' else r['score'] for r in rs]
            return mean(values) if values and all(v is not None for v in values) else None
        summaries[label] = dict(planned=plan['experiments'][label]['logical_items'], observed=len(selected),
            succeeded=sum(r['status'] == 'succeeded' for r in selected), answerable_f1=score(answerable),
            failed=sum(r['status'] == 'failed' for r in selected),
            successful_answerable_f1=score([r for r in answerable if r['status'] == 'succeeded']),
            matched_questions=len(matched), matched_before=mean(r['baseline_score'] for r in matched) if matched else None,
            matched_after=score(matched))
    report = dict(status=outcome['status'], baseline=str(baseline_path), summaries=summaries, rows=rows,
        budget_after=outcome['budget_after'],
        source_build_unchanged=outcome['source_build_unchanged'], snapshot_build_unchanged=outcome['snapshot_build_unchanged'])
    output.mkdir(parents=True, exist_ok=True)
    (output / 'results.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    lines = ['# 查询可靠性真实复验', '',
        '使用既有评测 API 的类别 F1；失败记 0，未完成不算成功。固定开发题单轮复验，不能作为统计显著性或隐藏测试成绩。',
        '逐题语义由作者核对原文并另记结论，不增加独立 LLM 评估器。历史对照不是同时运行的随机对照。', '',
        f"状态 `{outcome['status']}`，本轮调用 {outcome['budget_after']['reserved_new_calls']}/{plan['call_limit']}。", '',
        '| 组 | 成功 / 计划 | 失败项 | 成功可回答题 F1 | 全部可回答题 F1（失败记0） | 同题前后比较（失败记0） |',
        '| --- | --- | --- | --- | --- | --- |']
    for label, s in summaries.items():
        lines.append(f"| {label} | {s['succeeded']}/{s['planned']} | {s['failed']} | {s['successful_answerable_f1']} | {s['answerable_f1']} | {s['matched_questions']}题：{s['matched_before']} → {s['matched_after']} |")
    for row in rows:
        lines += ['', f"## QA {row['qa_index']} · {row['strategy']}", '', row['question'], '',
            f"状态 {row['status']} / {row['answer_status']}，F1 {row['score']}。", '',
            row['answer'] or '没有有效新答案。', '', f"解释：{row['explanation']}", '',
            f"前轮同题：{row['baseline_answer']}，F1 {row['baseline_score']}。"]
    (output / 'report.md').write_text('\n'.join(lines) + '\n')
    print(json.dumps(summaries, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--baseline', type=Path)
    args = parser.parse_args()
    render(args.directory.resolve(), args.output.resolve(), args.baseline)
