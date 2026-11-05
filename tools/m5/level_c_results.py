"""Publish numeric Level C results from frozen outputs; never open Gold or call a model."""
import argparse
from collections import Counter
from decimal import Decimal
import json
import math
from pathlib import Path

from tools.m5.level_c import ARMS, DEV, frozen_items
from tools.m5.offline import paired, sha, write


def mean(values):
    return sum(values)/len(values) if values else None


def groups(rows):
    result = {}
    for arm in ARMS:
        selected = [r for r in rows if r['arm'] == arm]
        scorable = [r for r in selected if r['qa']['value'] is not None]
        successful = [r for r in scorable if r['outcome'] == 'succeeded']
        result[arm] = dict(planned=len(selected), scorable=len(scorable),
            succeeded=sum(r['outcome'] == 'succeeded' for r in selected),
            failed=sum(r['outcome'] == 'failed' for r in selected),
            failure_zero_mean=mean([r['qa']['value'] for r in scorable]),
            successful_only_mean=mean([r['qa']['value'] for r in successful]),
            scoring_rules=dict(Counter(r['qa'].get('rule', r['qa'].get('reason')) for r in selected)))
    return result


def comparisons(rows):
    by_id = {}
    for row in rows:
        by_id.setdefault(row['question_id'], {})[row['arm']] = row
    complete, common = [], []
    for arms in by_id.values():
        h, d = (arms[arm] for arm in ARMS)
        if h['qa']['value'] is None or d['qa']['value'] is None:
            continue
        pair = (h['qa']['value'], d['qa']['value'])
        complete.append(pair)
        if h['outcome'] == d['outcome'] == 'succeeded':
            common.append(pair)
    return dict(all_scorable=paired([d-h for h, d in complete]),
        both_succeeded=dict(pairs=len(common), hybrid_mean=mean([h for h, d in common]),
            dynamic_mean=mean([d for h, d in common]), comparison=paired([d-h for h, d in common]),
            limitation='post-outcome subset; selected by runtime success, not a causal quality estimate'))


def call_cost(calls):
    tokens = Counter()
    unknown = 0
    for call in calls:
        usage = call.get('usage', {})
        if not all(type(usage.get(k)) is int for k in ('prompt_tokens', 'completion_tokens')):
            unknown += 1
        for k in ('prompt_tokens', 'completion_tokens'):
            if type(usage.get(k)) is int:
                tokens[k] += usage[k]
    return dict(attempts=len(calls), unknown_usage_attempts=unknown, reported_tokens=dict(tokens),
        reported_usage_peak_cache_miss_upper_usd=str((Decimal(tokens['prompt_tokens'])*Decimal('.30')
            + Decimal(tokens['completion_tokens'])*Decimal('1.20'))/1000000))


def run(stage, output):
    stage, output = stage.resolve(), output.resolve()
    plan, items = frozen_items(stage)
    freeze_sha = sha(stage/'generation-freeze.json')
    scores = json.loads((stage/'scores.json').read_text())
    audit = json.loads((stage/'terminal-audit-v1.json').read_text())
    if (scores['generation_freeze_sha256'] != freeze_sha
            or audit['generation_freeze_sha256'] != freeze_sha or audit['items'] != 200
            or not audit['integrity']['build_source_memory_relation_projection_index_unchanged']):
        raise ValueError('results_freeze_or_audit_mismatch')
    scored = scores['items']
    by_id = {(r['question_id'], r['arm']):r for r in scored}
    if len(scored) != 200 or len(by_id) != 200 or set(by_id) != {(r['question_id'], r['arm']) for r in items}:
        raise ValueError('results_denominator_mismatch')
    for item in items:
        row = by_id[item['question_id'], item['arm']]
        if any(row[k] != item[k] for k in ('sample_id', 'stratum', 'outcome')):
            raise ValueError('results_identity_mismatch')
        if item['outcome'] == 'failed' and row['qa']['value'] not in (None, 0):
            raise ValueError('results_failed_item_nonzero')
        value = row['qa']['value']
        if value is not None and (type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 1):
            raise ValueError('results_invalid_score')
    calls = [(item, name, c) for item in items
             for name, operation in item.get('trace', {}).get('operations', {}).items()
             for c in operation.get('calls', []) if c.get('outcome') is not None]
    if len(calls) != audit['ledger']['physical_ledger_requests']:
        raise ValueError('results_attempt_ledger_mismatch')
    costs = {}
    for arm in ARMS:
        selected = [(i, name, c) for i, name, c in calls if i['arm'] == arm]
        costs[arm] = dict(all_attempts=call_cost([c for _, _, c in selected]),
            retries=call_cost([c for _, _, c in selected if c.get('attempt', 1) > 1]),
            failed_item_attempts=call_cost([c for i, _, c in selected if i['outcome'] == 'failed']),
            by_operation={name:call_cost([c for _, n, c in selected if n == name])
                          for name in sorted({n for _, n, _ in selected})})
    result = dict(scope=plan['scope'], planned_items=200, questions=100,
        strata={s:dict(groups=groups([r for r in scored if r['stratum'] == s]),
                      comparisons=comparisons([r for r in scored if r['stratum'] == s]))
                for s in ('ordinary', 'diagnostic')},
        per_conversation={conv:{s:groups([r for r in scored if r['sample_id'] == conv and r['stratum'] == s])
                               for s in ('ordinary', 'diagnostic')} for conv in DEV},
        per_category={s:{str(cat):groups([r for r in scored if r['stratum'] == s and r['category'] == cat])
                        for cat in sorted({r['category'] for r in scored if r['stratum'] == s})}
                      for s in ('ordinary', 'diagnostic')},
        f1_categories_1_to_4={s:groups([r for r in scored if r['stratum'] == s and r['category'] in (1,2,3,4)])
                              for s in ('ordinary', 'diagnostic')},
        category_5_refusal={s:groups([r for r in scored if r['stratum'] == s and r['category'] == 5])
                            for s in ('ordinary', 'diagnostic')},
        runtime=audit['groups'], cost_by_arm=costs, ledger=audit['ledger'],
        model_identity=audit['model_identity'], resources=audit['resources'],
        semantic_source_support='pending_independent_review',
        interpretation='fixed exposed development sample; failure-zero primary; category5 uses literal official refusal rule, not factuality; no holdout evaluation; not a new 757-question score',
        actual_invoice_usd='not_accessed', holdout_qa_read=False, bonus_enabled=False)
    output.mkdir(parents=True, exist_ok=False)
    write(output/'metrics-summary.json', result)
    write(output/'per-question-metrics.json', scored)
    write(output/'failures.json', [dict(question_id=i['question_id'], sample_id=i['sample_id'],
        stratum=i['stratum'], arm=i['arm'], error_code=i['error_code'],
        stage=i.get('trace', {}).get('error', {}).get('stage')) for i in items if i['outcome'] == 'failed'])
    write(output/'source-manifest.json', {name:sha(stage/name) for name in
        ('plan.json', 'inputs.json', 'sample.json', 'settings.json', 'build-identities.json',
         'generation-freeze.json', 'scores.json', 'terminal-audit-v1.json',
         'user-authorization-receipt.json', 'pricing-recheck.json')})
    write(output/'sha256-manifest.json', {p.name:sha(p) for p in sorted(output.iterdir()) if p.is_file()})
    return dict(output=str(output), ordinary=result['strata']['ordinary'],
                diagnostic=result['strata']['diagnostic'], physical_requests=len(calls), holdout_qa_read=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.stage, args.output)))
