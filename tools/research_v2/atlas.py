"""Build an offline Failure Atlas from one exported persisted Run.

No application/model imports are needed. Scores identify review candidates;
they never establish a semantic root cause. Inputs are restricted to development.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
from functools import lru_cache

DEVELOPMENT = {'conv-26', 'conv-30', 'conv-41', 'conv-42'}
STRATEGIES = {'full_text', 'vector', 'hybrid_no_resolution', 'dynamic'}
FAILURES = ('Extraction Failure', 'Temporal Failure', 'Event Identity Failure',
            'State Failure', 'Retrieval Failure', 'Ranking Failure', 'Expansion Failure',
            'Evidence Failure', 'Reasoning Failure', 'Citation Failure', 'Cost Failure', 'Unknown')


@lru_cache(maxsize=64)
def file_hash(path, size, mtime_ns):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def artifact(path, pointer=''):
    if not path.is_file():
        return {'status': 'missing', 'path': str(path), 'pointer': pointer, 'sha256': None}
    info = path.stat()
    return {'status': 'available', 'path': str(path.resolve()), 'pointer': pointer,
            'sha256': file_hash(path, info.st_size, info.st_mtime_ns)}


def mean(values):
    known = [v for v in values if v is not None]
    return {'value': sum(known) / len(known) if known else None,
            'measured': len(known), 'unknown': len(values) - len(known)}


def attempt_usage(item):
    calls, unknown_attempts = [], 0
    for attempt in item.get('attempts', []):
        result = attempt.get('result')
        if result is None:
            unknown_attempts += 1
            continue
        calls.extend(c for operation in result.get('trace', {}).get('operations', {}).values()
                     for c in operation.get('calls', []))
        calls.extend(result.get('model_metadata', {}).get('calls', []))
    complete = not unknown_attempts and all(all(type(c.get('usage', {}).get(k)) is int
                                               and c['usage'][k] >= 0
                                               for k in ('prompt_tokens', 'completion_tokens', 'total_tokens')) for c in calls)
    prompt = sum(c.get('usage', {}).get('prompt_tokens', 0) for c in calls)
    completion = sum(c.get('usage', {}).get('completion_tokens', 0) for c in calls)
    # No attempts means no measurement, rather than proof of free execution.
    complete = complete and bool(item.get('attempts'))
    return {'saved_physical_calls': len(calls), 'unknown_attempts': unknown_attempts,
            'calls_missing_any_usage': sum(any(k not in c.get('usage', {}) for k in ('prompt_tokens', 'completion_tokens', 'total_tokens')) for c in calls),
            'known_prompt_tokens': prompt, 'known_completion_tokens': completion,
            'known_usage_peak_cny_estimate': (2 * prompt + 8 * completion) / 1_000_000,
            'complete_usage_peak_cny_estimate': (2 * prompt + 8 * completion) / 1_000_000 if complete else None,
            'usage_complete': complete, 'logical_attempts': len(item.get('attempts', [])),
            'logical_retries': max(0, len(item.get('attempts', [])) - 1),
            'elapsed_seconds_all_reported_attempts': sum(a.get('elapsed_seconds') or 0 for a in item.get('attempts', [])),
            'attempts_missing_elapsed': sum(a.get('elapsed_seconds') is None for a in item.get('attempts', [])),
            'price_basis': '2026-11-01 peak/cache-miss scenario; not an account bill'}


def diagnosis(review, run_path):
    if review is None:
        return {'type': 'Unknown', 'status': 'unreviewed', 'reason': 'Stage evidence and independent semantic review required',
                'reviewer': None, 'evidence': [], 'pattern': None, 'severe': None, 'citation_correctness': None}
    if review.get('type') not in FAILURES or not review.get('reviewer') or review.get('independent') is not True:
        raise ValueError('Review needs a supported type, identified independent reviewer and evidence')
    pointers = review.get('evidence', [])
    if review['type'] != 'Unknown' and (not pointers or not review.get('reason') or not review.get('pattern')):
        raise ValueError('Confirmed diagnosis requires stage evidence, rationale and a reusable pattern')
    evidence = []
    for entry in pointers:
        path = Path(entry['path'])
        if not path.is_absolute():
            path = run_path.parent / path
        saved = artifact(path, entry.get('pointer', ''))
        if saved['status'] != 'available' or saved['sha256'] != entry['sha256']:
            raise ValueError('Review evidence missing or hash mismatch')
        # Review pointers refer to structured artifacts, never arbitrary prose.
        value = json.loads(path.read_text())
        pointer = entry.get('pointer', '')
        if pointer:
            if not pointer.startswith('/'):
                raise ValueError('Use an RFC 6901 JSON pointer')
            for part in pointer[1:].split('/'):
                key = part.replace('~1', '/').replace('~0', '~')
                value = value[int(key)] if isinstance(value, list) else value[key]
        evidence.append(saved)
    severe, citation = review.get('severe'), review.get('citation_correctness')
    if severe is not None and type(severe) is not bool:
        raise ValueError('Severity must be boolean or unknown')
    if citation is not None and (type(citation) not in (int, float) or not 0 <= citation <= 1):
        raise ValueError('Citation correctness must be a reviewed fraction or unknown')
    return {'type': review['type'], 'status': 'reviewed_unknown' if review['type'] == 'Unknown' else 'confirmed_by_declared_independent_review',
            'reason': review.get('reason'), 'reviewer': review['reviewer'], 'evidence': evidence,
            'pattern': review.get('pattern'), 'severe': severe, 'citation_correctness': citation,
            'authority_limit': 'Independence is a reviewer declaration, not automatically verified by this tool'}


def make_atlas(run, run_path, directory, reviews=None):
    items, cases, metric_rows = run.get('items', []), [], []
    review_map = {r['case_id']: r for r in (reviews or [])}
    if len(review_map) != len(reviews or []):
        raise ValueError('Duplicate review IDs')
    seen = set()
    for index, item in enumerate(items):
        if item['sample_id'] not in DEVELOPMENT or item['strategy'] not in STRATEGIES:
            raise ValueError('Only four official development conversations and four baseline strategies are allowed')
        identity = (item['question_id'], item['strategy'])
        if identity in seen:
            raise ValueError('Duplicate logical combination; do not splice runs')
        seen.add(identity)
        result = item.get('result') or {}
        trace = result.get('trace') or {}
        score = (result.get('qa') or {}).get('value')
        category = run['input']['samples'][item['sample_index']].get('category')
        cost = attempt_usage(item)
        case_id = f"{run['run_id']}:{item['ordinal']}"
        reviewed = diagnosis(review_map.get(case_id), run_path)
        coverage = result.get('source_coverage') or {}
        source_sets = result.get('source_sets') or {}
        source_count = len(set(source_sets['answer_context'])) if 'answer_context' in source_sets else None
        row = {'conversation': item['sample_id'], 'category': str(category), 'strategy': item['strategy'],
               'failure_type': reviewed['type'], 'memory_source_count': 'not_applicable' if item['strategy'] == 'full_text' else str(source_count) if source_count is not None else 'unknown',
               'score': score, 'status': item['status'], 'cost': cost,
               'initial_coverage': None if item['strategy'] == 'full_text' else coverage.get('initial'),
               'full_text_input_coverage': coverage.get('initial') if item['strategy'] == 'full_text' else None,
               'final_coverage': coverage.get('answer_context'),
               'citation_correctness': reviewed['citation_correctness'], 'severe': reviewed['severe']}
        metric_rows.append(row)
        trigger = ('execution_failure' if item['status'] == 'failed' else
                   'incomplete_execution' if item['status'] != 'succeeded' else
                   'qa_score_below_one' if score is not None and score < 1 else
                   'reviewed_semantic_failure' if reviewed['type'] != 'Unknown' else None)
        row['review_candidate'] = trigger is not None
        if trigger is None:
            continue
        base_pointer = f'/items/{index}/result/trace'
        pin = run['pins'].get(item['sample_id'])
        build_export = directory / 'builds' / str(pin) / 'export.json'
        original_sources = directory / 'sources' / f"{item['sample_id']}.json"
        initial = trace.get('initial') if isinstance(trace.get('initial'), dict) else trace.get('retrieval')
        channels = initial.get('channels') if isinstance(initial, dict) else None
        lineage = {
            'original_source_turns': artifact(original_sources),
            'build_version': {'build_id': pin, 'artifact': artifact(run_path, f'/builds/{item["sample_id"]}')},
            'extracted_memory': artifact(build_export, '/memories'),
            'memory_source_mapping': artifact(build_export, '/sources'),
            'initial_bm25_dense_rrf': {'observed': channels is not None, 'data': channels,
                                     'rrf_candidates': initial.get('initial_candidates') if isinstance(initial, dict) else None,
                                     'artifact': artifact(run_path, base_pointer + ('/initial' if isinstance(trace.get('initial'), dict) else '/retrieval'))},
            'history_expansion': {'observed': 'expanded' in trace or 'expansion' in trace,
                                  'data': trace.get('expanded', trace.get('expansion'))},
            'final_effective_evidence': {'observed': 'effective_memories' in trace or 'delivered_memories' in trace or 'raw_context' in trace,
                                         'source_sets': source_sets, 'memory_rankings': result.get('memory_rankings')},
            'actual_model_context': {'status': 'exact_wire_not_recorded',
                                     'answer_payload_if_recorded': trace.get('answer_input'),
                                     'notice': 'Saved sources/IDs or reconstructed payload are not proof of exact model delivery'},
            'model_answer': trace.get('answer'),
            'final_citations': (trace.get('answer') or {}).get('citations'),
            'cost_and_trace': {'cost': cost, 'artifact': artifact(run_path, base_pointer),
                               'all_attempts': artifact(run_path, f'/items/{index}/attempts')},
        }
        cases.append({'atlas_version': 'failure-atlas-v1', 'case_id': case_id, 'run_id': run['run_id'],
                      'build_id': pin, 'question_id': item['question_id'], 'qa_index': item.get('qa_index'),
                      'conversation': item['sample_id'], 'category': category, 'strategy': item['strategy'],
                      'execution_status': item['status'], 'trigger': trigger, 'qa_score': score,
                      'diagnosis': reviewed, 'lineage': lineage, 'metrics': row,
                      'run_artifact': artifact(run_path, f'/items/{index}'),
                      'scope': 'development; scoring discrepancy is a review candidate, not a proven root cause'})
    unmatched = set(review_map) - {f"{run['run_id']}:{i['ordinal']}" for i in items}
    if unmatched:
        raise ValueError('Review does not belong to this Run')
    groups = {}
    for dimension in ('conversation', 'category', 'strategy', 'failure_type', 'memory_source_count'):
        grouped = defaultdict(list)
        for row in metric_rows:
            if dimension == 'failure_type' and not row['review_candidate']:
                continue
            grouped[row[dimension]].append(row)
        groups[dimension] = {key: summarize(rows) for key, rows in sorted(grouped.items())}
    patterns = Counter(c['diagnosis']['pattern'] for c in cases if c['diagnosis']['status'] == 'confirmed_by_declared_independent_review')
    summary = {'atlas_version': 'failure-atlas-v1', 'status': 'offline_imported' if items else 'awaiting_baseline',
               'run_id': run.get('run_id'), 'logical_denominator': len(items), 'review_candidates': len(cases),
               'confirmed_failure_types': dict(Counter(c['diagnosis']['type'] for c in cases if c['diagnosis']['status'] == 'confirmed_by_declared_independent_review')),
               'all_items': summarize(metric_rows), 'groups': groups,
               'top_10_confirmed_patterns': [{'pattern': k, 'cases': v} for k, v in patterns.most_common(10)],
               'top_10_status': 'requires_complete_baseline_and_independent_review' if not patterns else 'reviewed_subset_only',
               'exact_wire_available': False, 'live_calls': 0}
    return cases, summary


def summarize(rows):
    return {'planned': len(rows), 'states': dict(Counter(r['status'] for r in rows)),
            'qa_successful_scorable': mean([r['score'] for r in rows if r['status'] == 'succeeded']),
            'initial_retrieval_coverage': mean([r['initial_coverage'] for r in rows]),
            'full_text_input_coverage': mean([r['full_text_input_coverage'] for r in rows]),
            'final_evidence_coverage': mean([r['final_coverage'] for r in rows]),
            'citation_correctness': mean([r['citation_correctness'] for r in rows]),
            'per_item_peak_cny_estimate': mean([r['cost']['complete_usage_peak_cny_estimate'] for r in rows]),
            'known_usage_peak_cny_estimate_sum': sum(r['cost']['known_usage_peak_cny_estimate'] for r in rows),
            'items_with_unknown_usage': sum(not r['cost']['usage_complete'] for r in rows),
            'severe_error_ratio': mean([float(r['severe']) if r['severe'] is not None else None for r in rows])}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, help='Exported run.json; omit to initialize empty atlas')
    parser.add_argument('--directory', type=Path, required=True, help='Experiment directory with sources/ and builds/')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--summary', type=Path, required=True)
    parser.add_argument('--reviews', type=Path, help='Explicit independent review JSON list')
    args = parser.parse_args()
    run = json.loads(args.run.read_text()) if args.run else {'items': [], 'run_id': None}
    reviews = json.loads(args.reviews.read_text()) if args.reviews else []
    cases, summary = make_atlas(run, args.run or args.directory / 'not-executed-run.json', args.directory, reviews)
    for path in (args.output, args.summary):
        if args.run and path.resolve() == args.run.resolve():
            raise ValueError('Never overwrite the source Run')
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            raise ValueError('Choose a fresh output path; preserve earlier atlas revisions')
    args.output.write_text(''.join(json.dumps(c, ensure_ascii=False) + '\n' for c in cases))
    args.summary.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'status': summary['status'], 'logical_denominator': summary['logical_denominator'], 'review_candidates': len(cases), 'live_calls': 0}))
