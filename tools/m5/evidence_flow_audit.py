"""Read frozen Level E evidence only; never call models or mutate the stage."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

from locomo_memory.evaluation_metrics import map_evidence, coverage
from locomo_memory.evidence_flow import evidence_flow
from tools.m5.level_e import frozen_readonly
from tools.m5.level_c import readonly, source_storage_identity


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def audit(stage, freeze_sha):
    stage = Path(stage).resolve()
    if sha(stage/'generation-freeze.json') != freeze_sha:
        raise ValueError('freeze_sha_mismatch')
    freeze = json.loads((stage/'generation-freeze.json').read_text())
    lock = json.loads((stage/'final-system-lock.json').read_text())
    if freeze['status'] != 'generation_complete' or sha(stage/'plan.json') != freeze['plan_sha256']:
        raise ValueError('generation_not_frozen')
    items = []
    for name, expected in sorted(freeze['item_hashes'].items()):
        path = stage/name
        if path.resolve().parent != stage/'items' or sha(path) != expected:
            raise ValueError('frozen_item_changed')
        items.append(json.loads(path.read_text()))
    if len(items) != freeze['planned_items']:
        raise ValueError('incomplete_generation')
    reference = lock['reference']
    ref_path = Path(reference['path'])
    if source_storage_identity(ref_path) != reference['storage_identity']:
        raise ValueError('reference_changed')
    source_maps = {}
    for conv in {item['sample_id'] for item in items}:
        with readonly(stage/(conv+'.sqlite3')) as db:
            source_maps[conv] = {s['source_id']: dict(s) for s in db.execute(
                'SELECT * FROM source_turns WHERE dataset_id=? AND sample_id=?',
                (lock['exports'][conv]['dataset_id'], conv))}
    rows = []
    with frozen_readonly(ref_path, reference['storage_identity']) as db:
        for item in items:
            if item['arm'] != 'dynamic':
                continue
            evidence = db.execute('''SELECT json_extract(q.value,'$.evidence') AS evidence
                FROM import_artifacts a, json_each(a.annotations_json) s, json_each(s.value,'$.qa') q
                WHERE a.dataset_id=? AND a.artifact_sha256=? AND json_extract(s.value,'$.sample_id')=?
                AND q.key=?''', (reference['dataset_id'], reference['artifact_sha256'],
                                item['sample_id'], item['qa_index'])).fetchall()
            if len(evidence) != 1:
                raise ValueError('reference_question_identity_changed')
            sources = source_maps[item['sample_id']]
            mapping = map_evidence(json.loads(evidence[0]['evidence'] or '[]'), list(sources.values()))
            trace = item.get('trace', {})
            flow = evidence_flow(trace)
            gold = set(mapping['source_ids']) if mapping['scorable'] else set()
            recalls = {}
            for name, record in flow['stages'].items():
                recalls[name] = None if not mapping['scorable'] or record is None else coverage(record['source_ids'], mapping)
            memories = {x['memory']['memory_id']: x['memory'] for x in trace.get('expanded', {}).get('candidates', [])}
            gold_losses = []
            for loss in flow['losses']:
                cited_gold = gold.intersection(loss['source_ids'])
                if cited_gold:
                    gold_losses.append({**loss, 'memory_content': memories[loss['memory_id']]['content'],
                        'sources': [dict(source_id=sid, speaker=sources[sid]['speaker'],
                            session_time=sources[sid]['session_time'], text=sources[sid]['text']) for sid in sorted(cited_gold)],
                        'human_applicability_review': 'pending'})
            stages = flow['stages']
            stage_sets = {name: set(record['source_ids']) if record else set() for name, record in stages.items()}
            rejected_gold_sources = gold & (stage_sets['resolver_input'] - stage_sets['effective'])
            budget_gold_sources = gold & (stage_sets['effective'] - stage_sets['delivered'])
            rows.append(dict(question_id=item['question_id'], sample_id=item['sample_id'],
                question=item['question'], outcome=item['outcome'], scorable=mapping['scorable'],
                gold_source_ids=sorted(gold), recalls=recalls, gold_losses=gold_losses,
                rejected_gold_source_ids=sorted(rejected_gold_sources) if 'resolution' in trace else [],
                budget_gold_source_ids=sorted(budget_gold_sources) if trace.get('evidence_budget', {}).get('truncated') else [],
                resolver_complete=trace.get('resolution_budgets', {}).get('resolve', {}).get('within_budget'),
                answer_truncated=trace.get('evidence_budget', {}).get('truncated'),
                flow=flow, answer=trace.get('answer'),
                expanded_memories=list(memories.values())))
    # Strata are deterministic diagnostic samples, never a representative accuracy estimate.
    chosen = []
    strata = [('answer_budget', lambda r: bool(r['budget_gold_source_ids']), 4),
              ('resolver_rejected', lambda r: bool(r['rejected_gold_source_ids']), 12),
              ('failed', lambda r: r['outcome'] != 'succeeded', 2),
              ('retained_control', lambda r: r['outcome'] == 'succeeded' and r['recalls']['expanded'] == r['recalls']['delivered'], 2)]
    for label, predicate, limit in strata:
        candidates = sorted((r for r in rows if predicate(r) and r not in [x[1] for x in chosen]),
            key=lambda r: (-(len(r['rejected_gold_source_ids']) + len(r['budget_gold_source_ids'])), r['question_id']))
        chosen.extend((label, row) for row in candidates[:limit])
    chosen.extend(('additional_rejection', row) for row in rows if row not in [x[1] for x in chosen]
                  and row['gold_losses'])
    cases = [{k: v for k, v in row.items() if k not in {'flow', 'expanded_memories'}} | dict(stratum=label)
             for label, row in chosen[:20]]
    summary = dict(planned=len(rows), scorable=sum(r['scorable'] for r in rows),
        succeeded=sum(r['outcome'] == 'succeeded' for r in rows),
        complete_resolver_inputs=sum(r['resolver_complete'] is True for r in rows),
        resolver_lost_gold_questions=sum(bool(r['rejected_gold_source_ids']) for r in rows),
        budget_lost_gold_questions=sum(bool(r['budget_gold_source_ids']) for r in rows),
        answer_truncated_questions=sum(r['answer_truncated'] is True for r in rows),
        loss_memory_counts=dict(Counter(loss['kind'] for r in rows for loss in r['flow']['losses'])))
    summary['all_memory_source_recall_successful'] = {stage_name: sum(values)/len(values) if values else None
        for stage_name in ('initial', 'expanded', 'resolver_input', 'effective', 'delivered')
        for values in [[r['recalls'][stage_name] for r in rows if r['outcome'] == 'succeeded' and r['recalls'][stage_name] is not None]]}
    # Prefix replay freezes all existing decisions. This cannot estimate changed answers.
    prefixes = []
    for k in (5, 10, 20, 40, 60):
        candidate_recalls, delivered_recalls = [], []
        for row in rows:
            if not row['scorable']:
                continue
            prefix = row['expanded_memories'][:k]
            prefix_ids = {m['memory_id'] for m in prefix}
            delivered = row['flow']['stages']['delivered']
            delivered_ids = set(delivered['memory_ids']) if delivered else set()
            gold = set(row['gold_source_ids'])
            candidate_recalls.append(len(gold & {sid for m in prefix for sid in m['source_ids']})/len(gold))
            delivered_recalls.append(0 if row['outcome'] != 'succeeded' else len(gold & {
                sid for m in prefix if m['memory_id'] in delivered_ids & prefix_ids for sid in m['source_ids']})/len(gold))
        prefixes.append(dict(k=k, scorable=len(candidate_recalls),
            candidate_source_recall=sum(candidate_recalls)/len(candidate_recalls),
            fixed_decision_delivered_source_recall=sum(delivered_recalls)/len(delivered_recalls)))
    if sha(stage/'generation-freeze.json') != freeze_sha or source_storage_identity(ref_path) != reference['storage_identity']:
        raise ValueError('frozen_input_changed_during_audit')
    return dict(version='level-e-evidence-flow-audit-v1', freeze_sha256=freeze_sha, summary=summary,
        cases=cases, prefix_replay=prefixes, model_calls=0,
        limitations=['Exposed holdout; retrospective diagnostic only.',
            'Source IDs and rejection reasons do not establish semantic applicability.',
            'Prefix replay freezes decisions; no new resolver or answer, no QA improvement estimate.',
            'Case applicability requires independent human review.'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', type=Path, required=True)
    parser.add_argument('--freeze-sha256', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.resolve().is_relative_to(args.stage.resolve()):
        raise ValueError('output_must_not_modify_frozen_stage')
    result = audit(args.stage, args.freeze_sha256)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(result['summary'], ensure_ascii=False))


if __name__ == '__main__':
    main()
