"""Plan-aware experimental reports without changing the official QA scorer."""

from .evaluation_metrics import aggregate, qa_score
from .usage import provider_usage

STAGES = ('initial', 'expanded', 'effective', 'answer_context')
STATES = ('pending', 'running', 'succeeded', 'failed', 'interrupted', 'unknown')


def query_usage(items):
    attempts = [attempt for item in items for attempt in item['attempts']]
    calls, embeddings, stages = [], [], {}
    for item in items:
        for attempt in item['attempts']:
            result = attempt.get('result')
            if result is None:
                embeddings.append(0 if item['strategy'] == 'full_text' else None)
                continue
            trace = result.get('trace', {})
            calls.extend(call for operation in trace.get('operations', {}).values() for call in operation.get('calls', []))
            calls.extend(result.get('model_metadata', {}).get('calls', []))
            embeddings.append(result.get('usage_summary', {}).get('embedding_calls'))
            for stage, seconds in trace.get('stage_seconds', {}).items():
                stages[stage] = stages.get(stage, 0) + seconds
    report = provider_usage(calls, sum(attempt.get('result') is None for attempt in attempts))
    report.update(logical_attempts=len(attempts), logical_retries=sum(max(0, len(item['attempts']) - 1) for item in items),
        running_attempts=sum(a['status'] == 'running' for a in attempts),
        failed_attempts=sum(a['status'] == 'failed' for a in attempts),
        first_attempt_failures=sum(bool(item['attempts']) and item['attempts'][0]['status'] == 'failed' for item in items),
        reported_embedding_calls=sum(value for value in embeddings if value is not None),
        samples_with_unknown_embedding_call_count=sum(value is None for value in embeddings),
        reported_attempt_seconds=sum(a['elapsed_seconds'] for a in attempts if a.get('elapsed_seconds') is not None),
        attempts_without_elapsed_seconds=sum(a.get('elapsed_seconds') is None for a in attempts),
        reported_stage_seconds=stages, scope='all_saved_query_attempts')
    return report


def build_usage(builds):
    unique = {build['build_id']: build for build in builds.values()}
    by_build = {}
    for build_id, build in unique.items():
        report = provider_usage(build.get('model_metadata', {}).get('calls', []))
        report.update(embedding_calls=None, active_wall_seconds=None,
            note='Build metadata retains extraction and relation calls; historical embedding call counts and active wall time were not recorded.')
        by_build[build_id] = report
    report = provider_usage([call for build in unique.values() for call in build.get('model_metadata', {}).get('calls', [])])
    report.update(by_build=by_build, builds_with_unknown_embedding_call_count=len(unique),
        scope='saved_calls_for_unique_pinned_builds; reused across queries',
        billing_notice='Reported usage covers retained calls only; unrecorded or unknown external outcomes cannot be reconstructed.')
    return report


def group_report(items, inputs):
    samples = [inputs['samples'][item['sample_index']] for item in items]
    results = [item.get('result') if item['status'] == 'succeeded' else None for item in items]
    counts = {state: sum(item['status'] == state for item in items) for state in STATES}
    complete = all(item['status'] in ('succeeded', 'failed') for item in items)
    applicability = [qa_score('', sample) for sample in samples]
    eligible = [i for i, score in enumerate(applicability) if score['value'] is not None]
    numerator = sum(results[i]['qa']['value'] for i in eligible if results[i] is not None)
    return {
        'qa': aggregate([row['qa']['value'] if row else None for row in results]),
        'execution': {'planned': len(items), **counts,
            'success_rate': counts['succeeded'] / len(items) if items else None, 'complete': complete},
        'baseline_run_score': {'value': numerator / len(eligible) if complete and eligible else None,
            'numerator': numerator, 'denominator': len(eligible), 'excluded': len(items) - len(eligible),
            'status': 'complete' if complete else 'incomplete',
            'failure_zero_count': sum(items[i]['status'] == 'failed' for i in eligible)},
        'source_coverage': {stage: aggregate([row.get('source_coverage', {}).get(stage) if row else None for row in results]) for stage in STAGES},
        'dynamic': aggregate([row.get('dynamic_metric', {}).get('value') if row else None for row in results]),
        'relations': aggregate([row.get('relation_metric', {}).get('value') if row else None for row in results]),
        'missing_gold': sum(sample.get('answer') is None or not str(sample['answer']).strip() for sample in samples),
        'unknown_category': sum(sample.get('category') not in (1, 2, 3, 4, 5) for sample in samples),
        'invalid_evidence': sum(not inputs['mappings'][item['sample_index']]['scorable'] for item in items),
        'usage_summary': query_usage(items),
    }


def summarize_run(run):
    inputs, items = run['input'], run['items']
    run['summary'] = {strategy: group_report([i for i in items if i['strategy'] == strategy], inputs) for strategy in run['strategies']}
    run['overall_summary'] = group_report(items, inputs)
    run['grouped_summary'] = {}
    for name, identity in (('conversation', lambda i: i['sample_id']),
                           ('category', lambda i: str(inputs['samples'][i['sample_index']].get('category')))):
        groups = {}
        for key in dict.fromkeys(identity(item) for item in items):
            groups[key] = {strategy: group_report([i for i in items if identity(i) == key and i['strategy'] == strategy], inputs)
                for strategy in run['strategies'] if any(identity(i) == key and i['strategy'] == strategy for i in items)}
        run['grouped_summary'][name] = groups
    conversations = run['grouped_summary']['conversation']
    run['grouped_summary']['conversation_means'] = {
        strategy: {'qa': aggregate([group[strategy]['qa']['mean'] for group in conversations.values() if strategy in group]),
            'baseline_run_score': aggregate([group[strategy]['baseline_run_score']['value'] for group in conversations.values() if strategy in group])}
        for strategy in run['strategies']}
    for strategy, means in run['grouped_summary']['conversation_means'].items():
        complete = all(group[strategy]['baseline_run_score']['status'] == 'complete' for group in conversations.values() if strategy in group)
        means['baseline_run_score']['status'] = 'complete' if complete else 'incomplete'
        if not complete:
            means['baseline_run_score']['mean'] = None
    run['usage_summary'] = query_usage(items)
    run['build_usage_summary'] = build_usage(run['builds'])
    return run
