"""Read historical provider usage and prepare explicit, nonbinding cost scenarios."""
import argparse
import json
from pathlib import Path
import sqlite3

from locomo_memory.experiment import write_json
from locomo_memory.usage import provider_usage

HISTORICAL_BUILD = '5c7699dd6543407697ae232633154036'
# Fixed before examining quality; no selection by best score or successful items.
HISTORICAL_RUN = '70f6545c0de94cdabf5507be050a26da'
RATE_PEAK = {'input_miss_per_million_cny': 2, 'input_hit_per_million_cny': .04,
             'output_per_million_cny': 8}


def price(prompt, completion, multiplier=1):
    return (prompt * 2 + completion * 8) / 1_000_000 * multiplier


def estimate(directory, historical_database):
    readiness = json.loads((directory / 'readiness.json').read_text())
    plan = json.loads((directory / 'plan-development.json').read_text())
    # mode=ro never invokes the application factory or recovery logic on originals.
    with sqlite3.connect(historical_database.resolve().as_uri() + '?mode=ro', uri=True) as db:
        build_json, = db.execute('SELECT model_metadata_json FROM build_versions WHERE build_id=?', (HISTORICAL_BUILD,)).fetchone()
        historical_turns, = db.execute("SELECT COUNT(*) FROM source_turns WHERE sample_id='conv-26'").fetchone()
        historical_memories, = db.execute('SELECT COUNT(*) FROM memories WHERE build_id=?', (HISTORICAL_BUILD,)).fetchone()
        metadata = json.loads(build_json)
        items = [json.loads(r[0]) for r in db.execute('SELECT item_json FROM evaluation_run_items WHERE run_id=? ORDER BY ordinal', (HISTORICAL_RUN,))]
    build_usage = provider_usage(metadata['calls'])
    assert items
    historic = {}
    for strategy in {i['strategy'] for i in items}:
        selected = [i for i in items if i['strategy'] == strategy]
        calls, missing_attempts = [], 0
        for item in selected:
            for attempt in item['attempts']:
                result = attempt.get('result')
                if result is None:
                    missing_attempts += 1
                    continue
                calls.extend(c for op in result.get('trace', {}).get('operations', {}).values() for c in op.get('calls', []))
                calls.extend(result.get('model_metadata', {}).get('calls', []))
        historic[strategy] = {'logical_items': len(selected), 'usage': provider_usage(calls, missing_attempts)}
    sources = {sid: json.loads((directory / 'sources' / f'{sid}.json').read_text()) for sid in readiness['conversations']}
    # Byte ratios estimate relative Full Text size; they are not billed token counts.
    text_bytes = {sid: len(json.dumps(rows, ensure_ascii=False).encode()) for sid, rows in sources.items()}
    turns = sum(v['turns'] for v in readiness['conversations'].values())
    by_conversation = {}
    for sid, info in readiness['conversations'].items():
        costs = {}
        for strategy in plan['strategies']:
            proxy = strategy if strategy in historic else 'hybrid_no_resolution'
            reference = historic[proxy]
            tokens = reference['usage']['reported_tokens']
            # Unknown usage must never become a zero-price estimate.
            if not reference['usage']['provider_usage_complete']:
                costs[strategy] = {'peak_cny': None, 'reason': 'historical_usage_incomplete'}
                continue
            n = reference['logical_items']
            input_ratio = text_bytes[sid] / text_bytes['conv-26'] if strategy == 'full_text' else 1
            prompt = tokens['prompt_tokens'] / n * info['question_count'] * input_ratio
            completion = tokens['completion_tokens'] / n * info['question_count']
            costs[strategy] = {'peak_cny': price(prompt, completion), 'prompt_tokens_scenario': prompt,
                               'completion_tokens_scenario': completion, 'proxy_strategy': proxy,
                               'full_text_input_byte_ratio': input_ratio}
        by_conversation[sid] = costs
    build_tokens = build_usage['reported_tokens']
    build_known_peak = price(build_tokens['prompt_tokens'], build_tokens['completion_tokens'])
    reported = build_usage['usage_fields']['prompt_tokens']['calls_with_reported_usage']
    # Explicit scenario imputation, never persisted or described as measured usage.
    build_imputation_factor = build_usage['generation_calls'] / reported
    build_peak = build_known_peak * build_imputation_factor * turns / historical_turns
    query_peak = sum(v['peak_cny'] for costs in by_conversation.values() for v in costs.values())
    smoke_query_peak = sum(price(historic[s if s in historic else 'hybrid_no_resolution']['usage']['reported_tokens']['prompt_tokens'] / historic[s if s in historic else 'hybrid_no_resolution']['logical_items'] * 5,
                                   historic[s if s in historic else 'hybrid_no_resolution']['usage']['reported_tokens']['completion_tokens'] / historic[s if s in historic else 'hybrid_no_resolution']['logical_items'] * 5)
                           for s in plan['strategies'])
    result = {
        'status': 'offline_scenarios_not_a_quote_or_budget_authorization', 'currency': 'CNY',
        'price_checked_date': '2026-11-01', 'official_price_url': 'https://api-docs.deepseek.com/zh-cn/quick_start/pricing',
        'peak_prices': RATE_PEAK, 'off_peak_multiplier': .5,
        'historical_database': str(historical_database.resolve()), 'historical_build_id': HISTORICAL_BUILD,
        'historical_run_id': HISTORICAL_RUN, 'historical_build_usage': build_usage,
        'historical_turns': historical_turns, 'historical_memories': historical_memories,
        'historical_build_known_peak_cny': build_known_peak,
        'build_scenario_missing_call_imputation_factor': build_imputation_factor,
        'historical_query_usage': historic, 'development_turns': turns,
        'build_peak_cny_scenario': build_peak, 'query_peak_cny_scenario': query_peak,
        'total_peak_cny_scenario': build_peak + query_peak,
        'total_off_peak_cny_scenario': (build_peak + query_peak) * .5,
        'sensitivity_half_to_double_peak_cny': [(build_peak + query_peak) * .5, (build_peak + query_peak) * 2],
        'smoke_build_peak_cny_scenario': build_known_peak * build_imputation_factor,
        'smoke_query_peak_cny_scenario': smoke_query_peak,
        'smoke_total_peak_cny_scenario': build_known_peak * build_imputation_factor + smoke_query_peak,
        'query_by_conversation_strategy': by_conversation,
        'nominal_query_http_without_retries': {'full_text': 757, 'vector': 1514, 'hybrid_no_resolution': 1514, 'dynamic': 2271, 'total': 6056},
        'nominal_smoke_http_without_retries': 40,
        'query_http_with_all_internal_attempts': 18168,
        'query_service_context_ceiling_cny': 18168 * price(1_000_000, 8192),
        'embedding_external_api_cny': 0, 'embedding_local_compute_cny': None,
        'build_http_upper_bound': None, 'total_cost_upper_bound': None,
        'limitations': [
            'Historical Build had relation_max_tokens=16384 and 120s timeout; Production defaults are 8192 and 60s.',
            'Historical Build has one call without usage. Scenario imputes the mean reported-call cost for it; actual historical total remains unknown.',
            'The selected historical QA run has no vector arm; hybrid is an explicit input-cost proxy for vector.',
            'Prior Dynamic could use implicit raw recovery. The new default cannot; cost projections do not imply comparable quality.',
            'Build scales linearly with source turns only as a planning scenario; extracted memory and relation counts are unknown.',
            'All saved attempts, including failures, enter historical usage; no successful-only sampling.',
            'Full Text uses source byte ratios for extrapolation, not provider tokenizer counts.',
            'RAG assumes the observed conv-26 input/output distribution; new conversations can differ substantially.',
            'The factor-of-two sensitivity interval is not a confidence interval or maximum bill.',
            'No manual resume retries, probe, failed unknown requests, additional reviews or local machine charges are included in scenario totals.',
            'Query service-context ceiling is deliberately loose and conditional on 1M input/8192 output and three internal attempts; it is not a runnable budget.',
            'No finite total ceiling exists without per-send reservation, a Build cap, and explicit manual-retry accounting.',
            'Cache-hit details were discarded in historical production metadata; all inputs use cache-miss rates.',
        ],
    }
    write_json(directory / 'cost-estimate.json', result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--historical-database', type=Path, required=True)
    args = parser.parse_args()
    result = estimate(args.directory, args.historical_database)
    print(json.dumps({k: result[k] for k in ('build_peak_cny_scenario', 'query_peak_cny_scenario', 'total_peak_cny_scenario', 'total_off_peak_cny_scenario', 'smoke_total_peak_cny_scenario', 'total_cost_upper_bound')}, indent=2))
