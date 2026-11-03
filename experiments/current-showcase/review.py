"""Bind explicit author source decisions to exact saved answers; no automated judge."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--results', required=True, type=Path)
args = parser.parse_args()
here = Path(__file__).parent
packets = json.loads((args.results / 'answer-source-packets.json').read_text())
decisions = json.loads((here / 'answer-review-decisions.json').read_text())
by_index = {d['qa_index']: d for d in decisions['records']}
assert len(packets) == len(by_index) == 20
assert {p['qa_index'] for p in packets} == set(by_index)
records = []
for packet in packets:
    assert packet['status'] == 'succeeded', 'failed_answer_needs_explicit_review_update'
    assert packet['citation_identity_valid'], 'invalid_citation_requires_explicit_failure_review'
    decision = by_index[packet['qa_index']]
    records.append(dict(qa_index=packet['qa_index'], trace_id=packet['trace_id'], question=packet['question'],
        answer=packet['answer'], answer_status=packet['answer_status'],
        answer_sha256=hashlib.sha256(packet['answer'].encode()).hexdigest(),
        source_ids=[s['source_id'] for s in packet['cited_sources']], citation_identity_valid=True,
        source_support=decision['source_support'], adequacy=decision['adequacy'], reason=decision['reason']))
summary = dict(planned=20, reviewed=len(records), citation_identity_valid=sum(r['citation_identity_valid'] for r in records),
    source_support=dict(Counter(r['source_support'] for r in records)),
    adequacy=dict(Counter(r['adequacy'] for r in records)), reviewer=decisions['reviewer'],
    limitation='Developer source inspection, not independent course ground truth. No-positive-claim refusals are separate from supported positive answers. Citation identity is distinct from entailment and completeness.')
(args.results / 'answer-source-review.json').write_text(json.dumps(dict(summary=summary, records=records), ensure_ascii=False, indent=2)+'\n')
lines = ['# 20条回答的来源语义核验', '',
    '由当前开发助手逐条核对实际引用和相邻原文，未调用独立LLM评估器，不作为独立人类gold或课程动态准确率。全部20条均保留，不替换低分或保守拒答。', '',
    '引用身份合法20/20。14条正面回答中，12条有直接或跨来源文本支持，1条为明确保留不确定性的推断，1条仅部分支持；另6条无正面事实断言的拒答单列。', '',
    '完整性和问答适用性另查：QA51漏sunrise且部分分组超出明确文本；QA69只覆盖一个已支持特征；QA144报告事故结局而非儿子的应对。QA14/59保守拒答丢失官方参考答案允许的推断。', '',
    '| QA | 来源支持 | 回答适用性 | 核验说明 |', '| --- | --- | --- | --- |']
for r in records:
    lines.append(f"| {r['qa_index']} | {r['source_support']} | {r['adequacy']} | {r['reason']} |")
lines += ['', '确切答案、Trace ID、来源ID及答案摘要见answer-source-review.json；完整引用原文及邻轮见answer-source-packets.json。']
(args.results / 'answer-source-review.md').write_text('\n'.join(lines)+'\n')
print(json.dumps(summary, ensure_ascii=False))

# Dynamic decisions are explicit author judgments, never inferred from stored labels.
dynamic_packets = json.loads((args.results / 'dynamic-packets.json').read_text())
dynamic_decisions = json.loads((here / 'dynamic-review-decisions.json').read_text())
pre_review = json.loads((here / 'dynamic-source-review.json').read_text())
by_case = {r['case_id']: r for r in dynamic_decisions['records']}
pre_by_case = {r['case_id']: r for r in pre_review['records']}
assert len(dynamic_packets) == len(by_case) == 10
assert {p['case_id'] for p in dynamic_packets} == set(by_case) == set(pre_by_case)
dynamic_records = []
for packet in dynamic_packets:
    assert packet['query_status'] == 'succeeded'
    case_id = packet['case_id']
    effective = {m['memory_id'] for m in packet['effective_memories']}
    pair = packet['relation']
    actual_pair = [r for r in packet['actual_query_relations']
                   if r['old_memory_id'] == pair['old_memory_id']
                   and r['new_memory_id'] == pair['new_memory_id']]
    dynamic_records.append(dict(case_id=case_id, trace_id=packet['trace_id'],
        answer_sha256=hashlib.sha256(packet['answer']['answer'].encode()).hexdigest(),
        question=packet['question'], answer=packet['answer'],
        source_relation_review=pre_by_case[case_id], query_review=by_case[case_id],
        actual_pair_relations=actual_pair,
        old_memory_effective=pair['old_memory_id'] in effective,
        new_memory_effective=pair['new_memory_id'] in effective,
        effective_memories=packet['effective_memories']))
dynamic_summary = dict(reviewed=10, queries_succeeded=10,
    query_verdict=dict(Counter(r['query_review']['query_verdict'] for r in dynamic_records)),
    stored_relation_source_judgment=dict(Counter(r['source_relation_review']['stored_relation_source_judgment'] for r in dynamic_records)),
    reviewer=dynamic_decisions['reviewer'],
    limitation='Author qualitative source inspection, not independent dynamic accuracy. No real SUPERSEDE/CONFLICT in this Build. Query correctness and stored relation semantics are separate judgments.')
(args.results / 'dynamic-review.json').write_text(json.dumps(dict(summary=dynamic_summary, records=dynamic_records), ensure_ascii=False, indent=2)+'\n')
lines = ['# 10个真实动态场景的来源核验', '',
    '10次查询全部运行成功；作者来源审阅判定9条回答正确、1条部分支持。该判断不是独立人类gold，不报告为课程动态准确率。', '',
    '存储关系分开审阅为8条支持、2条语义异议。state-04泛泛意图到艺术倡导未充分证明同一具体过程的阶段推进；state-10相邻对话已积极确认家庭支持，存储未确定遗漏了RETAIN。查询结论与存储关系质量分开记录。', '',
    '真实样本为4 UPDATE、3 RETAIN、3未确定。本Build没有SUPERSEDE或CONFLICT，合成浏览器冲突检查不能替代这两类真实质量评价。', '',
    '| 案例 | 存储/来源审阅期望 | 查询审阅 | 旧/新端点实际有效 | 说明 |', '| --- | --- | --- | --- | --- |']
for r in dynamic_records:
    pre, decision = r['source_relation_review'], r['query_review']
    lines.append(f"| {r['case_id']} | {pre['stored_label']} / {pre['expected_label']} | {decision['query_verdict']} | {r['old_memory_effective']} / {r['new_memory_effective']} | {decision['reason']} |")
lines += ['', '实际查询关系、有效Memory的ID与完整内容、答案摘要和Trace ID见 [dynamic-review.json](dynamic-review.json)；原文与完整解析见 [dynamic-packets.json](dynamic-packets.json)。端点未进入最终有效集合不等于未交付，计划可以被正确排除。']
(args.results / 'dynamic-review.md').write_text('\n'.join(lines)+'\n')
print(json.dumps(dynamic_summary, ensure_ascii=False))
