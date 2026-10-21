"""Report existing evaluator outputs and prepare source review packets; no LLM judge."""
import argparse
from collections import Counter
import csv
import json
from pathlib import Path
import sqlite3
from statistics import mean

from locomo_memory.evaluation_metrics import coverage


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def render(directory, output):
    output.mkdir(exist_ok=True, parents=True)
    plan = json.loads((directory / 'plan.json').read_text())
    outcome = json.loads((directory / 'outcome.json').read_text())
    run = json.loads((directory / 'paired-run.json').read_text())
    questions = plan['experiments']['paired']['questions']
    sources = {s['source_id']: s for s in json.loads((directory / 'source-turns.json').read_text())}
    rows, packets = [], []
    for item in run['items']:
        q = questions[item['sample_index']]
        result = item.get('result') or {}
        trace = result.get('trace') or {}
        answer = trace.get('answer') or {}
        row = dict(qa_index=q['qa_index'], question=q['official_qa']['question'],
            category=q['official_qa']['category'], reference=q['official_qa'].get('answer'),
            strategy=item['strategy'], status=item['status'], score=result.get('qa', {}).get('value'),
            score_rule=result.get('qa', {}).get('rule'), trace_id=trace.get('trace_id'),
            answer=answer.get('answer'), answer_status=answer.get('status'),
            explanation=answer.get('explanation'), citations=answer.get('citations', []),
            error=result.get('error') or item.get('error'), source_coverage=result.get('source_coverage'),
            source_sets=result.get('source_sets'), raw_triggered=trace.get('raw_fallback', {}).get('triggered'),
            strategy_recovery=trace.get('strategy_recovery'), usage=result.get('usage_summary'))
        rows.append(row)
        if item['strategy'] == 'dynamic_raw_fallback':
            delivered = set(result.get('source_sets', {}).get('answer_context', []))
            memory_sources = {m['memory_id']: set(m['source_ids']) for m in trace.get('effective_memories', [])}
            citation_sources = list(dict.fromkeys(s for c in row['citations'] for s in c['source_ids']))
            valid = all(s in sources and s in delivered for s in citation_sources)
            valid = valid and all(c['memory_id'] is None or (
                c['memory_id'] in memory_sources and set(c['source_ids']) <= memory_sources[c['memory_id']])
                for c in row['citations'])
            cite_positions = {sources[s]['position'] for s in citation_sources if s in sources}
            context = [s for s in sources.values() if any(abs(s['position']-p) <= 1 for p in cite_positions)]
            packets.append(dict(**row, citation_identity_valid=valid if row['status'] == 'succeeded' else None,
                cited_sources=[sources[s] for s in citation_sources if s in sources],
                neighboring_context=context, semantic_judgment='pending_author_source_review'))
    summary = {}
    for strategy in plan['experiments']['paired']['strategies']:
        rs = [r for r in rows if r['strategy'] == strategy]
        scored = [r for r in rs if r['status'] == 'succeeded' and r['score'] is not None]
        answerable = [r for r in rs if r['category'] != 5]
        values = [0 if r['status'] == 'failed' else r['score'] for r in answerable]
        refusals = [r for r in rs if r['category'] == 5]
        rv = [0 if r['status'] == 'failed' else r['score'] for r in refusals]
        summary[strategy] = dict(planned=20, observed=len(rs), states=dict(Counter(r['status'] for r in rs)),
            success_rate=sum(r['status'] == 'succeeded' for r in rs)/20,
            answerable_planned=len(answerable), answerable_f1_failures_zero=mean(values) if values and all(v is not None for v in values) else None,
            success_only_answerable_f1=mean(r['score'] for r in scored if r['category'] != 5) if any(r['category'] != 5 for r in scored) else None,
            adversarial_planned=len(refusals), adversarial_official_refusal=mean(rv) if rv and all(v is not None for v in rv) else None,
            evaluator_summary=run.get('summary', {}).get(strategy))
    recall_path = directory / 'recall-results.json'
    recall = json.loads(recall_path.read_text()) if recall_path.exists() else []
    with sqlite3.connect((directory / 'memory.sqlite3').as_uri() + '?mode=ro', uri=True) as db:
        memory_sources = {m['memory_id']: m['source_ids'] for (raw,) in db.execute(
            'SELECT memory_json FROM memories WHERE build_id=?', (plan['source_build_id'],))
            for m in [json.loads(raw)]}
    for r in recall:
        r['channel_recall_at'] = {channel: {str(k): coverage([sid for c in r['result']['channels'][channel][:k]
            for sid in memory_sources[c['memory_id']]], r['mapping']) for k in (5,10,20)}
            for channel in ('dense', 'bm25')}
    recall_summary = dict(planned=40, completed=len(recall), mapping='Source Turn coverage from first K Memory candidates in actual initial RRF ranking',
        recall_at={str(k): mean(r['recall_at'][str(k)] for r in recall) if recall else None for k in (5,10,20)},
        query_analysis_states=dict(Counter(r['result']['analysis']['status'] for r in recall)))
    recall_summary['channel_diagnostics'] = {channel: {str(k): mean(r['channel_recall_at'][channel][str(k)]
        for r in recall) if recall else None for k in (5,10,20)} for channel in ('dense', 'bm25')}
    dynamics_path = directory / 'dynamic-results.json'
    dynamics = json.loads(dynamics_path.read_text()) if dynamics_path.exists() else []
    dynamic_packets = []
    for case in plan['dynamic_cases']:
        result = next((r for r in dynamics if r['case_id'] == case['case_id']), {})
        trace = result.get('trace') or {}
        ids = list(dict.fromkeys(case['old_memory']['source_ids']+case['new_memory']['source_ids']+case['relation']['source_ids']))
        dynamic_packets.append(dict(**case, query_status=result.get('status', 'not_executed'),
            trace_id=trace.get('trace_id'), answer=trace.get('answer'), effective_memories=trace.get('effective_memories', []),
            resolution=trace.get('resolution'), actual_query_relations=trace.get('relations', []),
            evidence_sources=[sources[s] for s in ids], semantic_judgment='pending_author_source_review'))
    save(output / 'paired-results.json', dict(summary=summary, rows=rows, evaluator_run_id=run['run_id']))
    with (output / 'paired-differences.csv').open('w', newline='') as stream:
        strategies = list(summary)
        writer = csv.DictWriter(stream, fieldnames=['qa_index', 'category', 'question', *strategies,
            'raw_minus_dynamic', 'raw_minus_hybrid'])
        writer.writeheader()
        for q in questions:
            scores = {}
            for strategy in strategies:
                row = next(r for r in rows if r['qa_index'] == q['qa_index'] and r['strategy'] == strategy)
                scores[strategy] = 0 if row['status'] == 'failed' else row['score']
            def difference(other):
                a, b = scores['dynamic_raw_fallback'], scores[other]
                return a-b if a is not None and b is not None else None
            writer.writerow(dict(qa_index=q['qa_index'], category=q['official_qa']['category'],
                question=q['official_qa']['question'], **scores,
                raw_minus_dynamic=difference('dynamic'), raw_minus_hybrid=difference('hybrid_no_resolution')))
    save(output / 'recall-results.json', dict(summary=recall_summary, rows=recall))
    save(output / 'answer-source-packets.json', packets)
    save(output / 'dynamic-packets.json', dynamic_packets)
    save(output / 'outcome.json', outcome)
    lines = ['# 当前系统展示实验', '',
        '固定conv-26开发对话、20题分层配对、同一完整Build。每类别4题；同题依次运行五策略，单轮、有限重试。未执行四对话3,028项全量或本地测试集。', '',
        'F1仅汇总类别1–4的既有官方类别计分；类别5另报官方拒答匹配。失败记0，未完成不冒称成功。此为开发集展示，不证明泛化或统计显著性。', '',
        '| 策略 | 成功/20 | 可回答题F1，失败记0 | 成功可回答题F1 | 类别5拒答匹配 |',
        '| --- | --- | --- | --- | --- |']
    for strategy, s in summary.items():
        lines.append(f"| {strategy} | {s['states'].get('succeeded',0)}/20 | {s['answerable_f1_failures_zero']} | {s['success_only_answerable_f1']} | {s['adversarial_official_refusal']} |")
    lines += ['', '## 分题配对', '', '| QA | 类别 | '+ ' | '.join(summary)+' |', '| --- | --- | '+' | '.join('---' for _ in summary)+' |']
    for q in questions:
        values = []
        for strategy in summary:
            r = next(r for r in rows if r['qa_index'] == q['qa_index'] and r['strategy'] == strategy)
            values.append('失败' if r['status'] == 'failed' else str(r['score']))
        lines.append(f"| {q['qa_index']} | {q['official_qa']['category']} | "+' | '.join(values)+' |')
    lines += ['', '## 来源Recall@K', '', f"完成 {len(recall)}/40。K为Memory排名数，分子是映射后命中的去重gold Source Turns，先逐题计算再平均。", '',
        '主指标为实际初始RRF；Dense与BM25诊断从同40次候选请求保存的通道排序计算，不另跑模型。', '',
        '| K | 初始RRF | Dense通道 | BM25通道 |', '| --- | --- | --- | --- |']
    lines += [f"| {k} | {v} | {recall_summary['channel_diagnostics']['dense'][k]} | {recall_summary['channel_diagnostics']['bm25'][k]} |" for k,v in recall_summary['recall_at'].items()]
    lines += ['', '语义核验和动态场景结论见独立审阅记录；引用合法不等于语义支持。未以模型自标作为独立真值。', '',
        f"调用 {outcome['budget_after']['reserved_new_calls']}/{plan['call_limit']}，历史累计 {outcome['budget_after']['reserved_total_calls']}。",
        f"原Build未改变：{outcome['source_build_unchanged']}；快照Build未改变：{outcome['snapshot_build_unchanged']}。"]
    (output / 'report.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({'paired':summary, 'recall':recall_summary}, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    render(args.directory.resolve(), args.output.resolve())
