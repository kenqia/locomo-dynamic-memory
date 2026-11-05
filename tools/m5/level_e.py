"""One-shot held-out H/D evaluation, after an independently supplied final lock.

No command creates the final lock or authorization. Prepare reads six strict
exports, copies annotation-free Build databases separately, and SQL-projects only
questions. Gold is opened only by score, after every planned item is frozen.
"""
import argparse
from contextlib import ExitStack, contextmanager
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re
import sqlite3

import httpx

from locomo_memory.builds import BuildError
from locomo_memory.config import Settings
from locomo_memory.database import backend_ownership
from locomo_memory.evaluation import EvaluationService, EvaluationFailure
from locomo_memory.evaluation_metrics import qa_score, map_evidence, coverage
from locomo_memory.export_schemas import MemoryExport
from locomo_memory.exports import ExportService
from locomo_memory.m5_budget import BudgetTransport
from locomo_memory.model import DeepSeekModel
from locomo_memory.queries import QueryFailure
from locomo_memory.query_schemas import QueryRequest
from tools.m5.level_c import (ARMS, TABLES, NoProvider, ledger_summary, producer_hashes,
                              readonly, services, source_storage_identity)
from tools.m5.offline import ROOT, DEV, HOLDOUT, paired, sha, write

VERSION = 'm5-level-e-v1'
SCOPE = 'one held-out evaluation; all conv-43/44 questions; Hybrid/Dynamic; no Bonus'
EFFORTS = ('extraction_thinking_effort', 'relation_thinking_effort',
           'query_analysis_thinking_effort', 'resolution_thinking_effort', 'answer_thinking_effort')
MUTABLE = {'candidate_queries', 'candidate_expansions', 'query_traces'}
EVALUATION = {'evaluation_inputs', 'evaluation_runs', 'evaluation_run_items'}
ALLOWED = set(TABLES) | MUTABLE | EVALUATION | {'import_artifacts', 'relation_attempts', 'relation_provider_calls'}


def require(condition, code):
    if not condition:
        raise ValueError(code)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    separators=(',', ':')).encode()).hexdigest()


def implementation_hashes():
    return {**producer_hashes(), str(Path(__file__).relative_to(ROOT)): sha(Path(__file__))}


@contextmanager
def frozen_readonly(path, identity):
    """Avoid creating empty WAL sidecars on locked, quiescent source snapshots.

    A nonempty committed WAL must still be read by ordinary SQLite. Immutable
    mode is used only when the locked WAL is absent/empty; byte guards surround
    every source transaction. Never use this helper on a running producer.
    """
    wal = identity['wal']
    if wal['exists'] and wal['sha256'] != hashlib.sha256(b'').hexdigest():
        with readonly(path) as con:
            yield con
    else:
        con = sqlite3.connect(path.resolve().as_uri()+'?mode=ro&immutable=1', uri=True)
        con.row_factory = sqlite3.Row
        try:
            con.execute('PRAGMA query_only=ON')
            con.execute('BEGIN')
            yield con
        finally:
            con.close()


def policy_for(count, settings):
    require(type(count) is int and count > 0 and settings.model_name == 'deepseek-flash'
            and settings.model_retries == 2 and settings.model_max_tokens == 32768
            and settings.model_temperature == 0 and settings.thinking_enabled is False
            and all(getattr(settings, field) == 'disabled' for field in EFFORTS)
            and settings.resolution_input_budget == 192000, 'level_e_settings_not_locked')
    requests = count * 15
    maximum = (Decimal(640000)*Decimal('.30') + Decimal(32768)*Decimal('1.20'))/1000000*requests
    return dict(model='deepseek-flash', max_input_bytes=640000, max_output_tokens=32768,
                input_usd_per_million='.30', output_usd_per_million='1.20',
                max_requests=requests, max_usd=str(maximum))


def check_lock(lock):
    commit = lock.get('implementation_commit')
    require(isinstance(commit, str) and re.fullmatch(r'[0-9a-fA-F]{40}', commit) is not None,
            'level_e_implementation_commit_required')
    require(lock.get('version') == VERSION and lock.get('status') == 'locked'
            and lock.get('scope') == SCOPE and lock.get('arms') == list(ARMS)
            and lock.get('bonus_enabled') is False and lock.get('question_selection') == 'all_original_ordinals'
            and lock.get('implementation_sha256') == implementation_hashes(), 'level_e_final_lock_required')
    require(set(lock['exports']) == set((*DEV, *HOLDOUT))
            and set(lock['build_sources']) == set(HOLDOUT)
            and set(lock['reference']['questions']) == set(HOLDOUT), 'level_e_six_exports_and_two_builds_required')
    require(Path(lock['reference']['path']).is_absolute(), 'level_e_reference_path_required')
    count = 0
    for conv in HOLDOUT:
        metadata = lock['reference']['questions'][conv]
        n = metadata['count']
        require(type(n) is int and n > 0 and metadata['identity_sha256'] == digest(
            [f'{conv}:qa:{index}' for index in range(n)]), 'level_e_all_question_identities_required')
        count += n
    settings = Settings.model_validate(lock['settings'])
    return settings, count, policy_for(count, settings)


def clean_build_database(con, *, allow_queries=False):
    """Only this annotation-free database may be backed up or logically hashed."""
    names = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    require(names <= ALLOWED and set(TABLES) <= names, 'level_e_build_tables_invalid')
    for name in names & EVALUATION:
        require(con.execute('SELECT COUNT(*) FROM '+name).fetchone()[0] == 0,
                'level_e_evaluation_rows_forbidden')
    if not allow_queries:
        for name in names & MUTABLE:
            require(con.execute('SELECT COUNT(*) FROM '+name).fetchone()[0] == 0,
                    'level_e_previous_queries_forbidden')
    if 'import_artifacts' in names:
        # These are SQL-only shape checks, not annotation values returned to Python.
        for field in ('qa', 'event_summary', 'observation', 'session_summary'):
            nonempty = con.execute('''SELECT COUNT(*) FROM import_artifacts a,
                json_each(a.annotations_json) s WHERE
                COALESCE(json_type(s.value, ?),'null') != 'null'
                AND NOT (json_type(s.value, ?)='array' AND json_array_length(s.value, ?)=0)''',
                ('$.'+field,)*3).fetchone()[0]
            require(nonempty == 0, 'level_e_build_annotations_forbidden')
    require({r[0] for r in con.execute('SELECT DISTINCT sample_id FROM source_turns')} <= set(HOLDOUT)
            and {r[0] for r in con.execute('SELECT DISTINCT sample_id FROM build_versions')} <= set(HOLDOUT),
            'level_e_build_conversation_scope')
    return names


def protected_identity(path):
    with readonly(path) as con:
        names = clean_build_database(con, allow_queries=True)
        result = {name: sorted(json.dumps(tuple(row), ensure_ascii=False, default=str)
                               for row in con.execute('SELECT * FROM '+name))
                  for name in sorted(names - MUTABLE - EVALUATION)}
    return digest(result)


def projected_inputs(con, reference):
    result = []
    for conv in HOLDOUT:
        matches = con.execute('''SELECT COUNT(*), MIN(json_type(s.value,'$.qa')) FROM import_artifacts a,
            json_each(a.annotations_json) s WHERE a.dataset_id=? AND a.artifact_sha256=?
            AND json_extract(s.value,'$.sample_id')=?''',
            (reference['dataset_id'], reference['artifact_sha256'], conv)).fetchone()
        require(tuple(matches) == (1, 'array'), 'level_e_reference_sample_not_unique')
        rows = con.execute('''SELECT CAST(q.key AS INTEGER) AS ordinal,
            json_extract(q.value,'$.question') AS question
            FROM import_artifacts a, json_each(a.annotations_json) s, json_each(s.value,'$.qa') q
            WHERE a.dataset_id=? AND a.artifact_sha256=?
            AND json_extract(s.value,'$.sample_id')=? ORDER BY CAST(q.key AS INTEGER)''',
            (reference['dataset_id'], reference['artifact_sha256'], conv)).fetchall()
        require([r['ordinal'] for r in rows] == list(range(reference['questions'][conv]['count']))
                and all(isinstance(r['question'], str) and r['question'].strip() for r in rows),
                'level_e_question_count_or_shape')
        result.extend(dict(question_id=f'{conv}:qa:{r["ordinal"]}', sample_id=conv,
                           qa_index=r['ordinal'], question=r['question']) for r in rows)
    return result


def source_content_identity(con, dataset, conv):
    rows = [tuple(r) for r in con.execute('''SELECT session_id,dia_id,speaker,session_time,text,position
        FROM source_turns WHERE dataset_id=? AND sample_id=? ORDER BY position''', (dataset, conv))]
    require(bool(rows), 'level_e_reference_conversation_missing')
    return digest(rows)


def prepare(output, final_lock):
    output, final_lock = Path(output).resolve(), Path(final_lock).resolve()
    require(final_lock.name == 'final-system-lock.json', 'level_e_final_lock_filename')
    lock = json.loads(final_lock.read_text())
    settings, count, policy = check_lock(lock)
    exports = {}
    for conv, item in lock['exports'].items():
        path = Path(item['path'])
        require(path.is_absolute() and sha(path) == item['sha256'], 'level_e_export_identity_changed')
        bundle = MemoryExport.model_validate_json(path.read_text())
        require(bundle.schema_version == 'memory-export-v2' and bundle.build.sample_id == conv
                and bundle.build.build_id == item['build_id'] and bundle.build.dataset_id == item['dataset_id'],
                'level_e_export_scope')
        exports[conv] = bundle.model_dump(mode='json')
    ref = lock['reference']
    require(source_storage_identity(Path(ref['path'])) == ref['storage_identity'], 'level_e_reference_changed')
    output.mkdir(parents=True, exist_ok=False)
    output.chmod(0o700)
    snapshots = {}
    for conv in HOLDOUT:
        source = Path(lock['build_sources'][conv]['path'])
        require(source.is_absolute() and source.resolve() != Path(ref['path']).resolve(),
                'level_e_reference_is_not_build_database')
        require(source_storage_identity(source) == lock['build_sources'][conv]['storage_identity'],
                'level_e_build_source_changed')
        target = output/(conv+'.sqlite3')
        with frozen_readonly(source, lock['build_sources'][conv]['storage_identity']) as con:
            clean_build_database(con)
            with sqlite3.connect(target) as dest:
                con.backup(dest)
        require(source_storage_identity(source) == lock['build_sources'][conv]['storage_identity'],
                'level_e_build_source_changed')
        target.chmod(0o600)
        q = services(target, settings.model_copy(update={'db_path': target}), NoProvider())
        bundle = ExportService(q.versions).export(lock['exports'][conv]['build_id'])
        require(bundle.model_dump(mode='json') == exports[conv], 'level_e_build_export_mismatch')
        snapshots[conv] = protected_identity(target)
    # All six exports and actual Build copies are checked before question access.
    with frozen_readonly(Path(ref['path']), ref['storage_identity']) as con:
        for conv in HOLDOUT:
            with readonly(output/(conv+'.sqlite3')) as build:
                require(source_content_identity(con, ref['dataset_id'], conv) == source_content_identity(
                    build, lock['exports'][conv]['dataset_id'], conv), 'level_e_reference_conversation_changed')
        inputs = projected_inputs(con, ref)
    require(source_storage_identity(Path(ref['path'])) == ref['storage_identity'], 'level_e_reference_changed')
    require(len(inputs) == count, 'level_e_denominator_changed')
    write(output/'final-system-lock.json', lock)
    write(output/'inputs.json', inputs)
    BudgetTransport(output/'physical-requests.sqlite3', None, **policy)
    plan = dict(version=VERSION, scope=SCOPE, status='prepared_not_authorized', stage_path=str(output), questions=count,
                planned_items=2*count, arms=list(ARMS), policy=policy, build_snapshots=snapshots,
                final_lock_sha256=sha(output/'final-system-lock.json'), inputs_sha256=sha(output/'inputs.json'),
                ledger_identity=source_storage_identity(output/'physical-requests.sqlite3'),
                gold_read=False, bonus_enabled=False, selection='all_original_ordinals')
    write(output/'plan.json', plan)
    return plan


def verify_plan(output):
    output = Path(output).resolve()
    plan = json.loads((output/'plan.json').read_text())
    require(plan.get('version') == VERSION and plan.get('scope') == SCOPE
            and plan.get('status') == 'prepared_not_authorized'
            and plan.get('stage_path') == str(output)
            and plan['final_lock_sha256'] == sha(output/'final-system-lock.json')
            and plan['inputs_sha256'] == sha(output/'inputs.json'), 'level_e_plan_changed')
    lock = json.loads((output/'final-system-lock.json').read_text())
    settings, count, policy = check_lock(lock)
    inputs = json.loads((output/'inputs.json').read_text())
    expected = [(conv, i) for conv in HOLDOUT for i in range(lock['reference']['questions'][conv]['count'])]
    require(plan['policy'] == policy and plan['questions'] == count and plan['planned_items'] == 2*count
            and plan['arms'] == list(ARMS) and plan['bonus_enabled'] is False
            and plan['gold_read'] is False and plan['selection'] == 'all_original_ordinals'
            and [(r['sample_id'], r['qa_index']) for r in inputs] == expected
            and all(set(r) == {'sample_id', 'qa_index', 'question_id', 'question'}
                    and r['question_id'] == f'{r["sample_id"]}:qa:{r["qa_index"]}' for r in inputs),
            'level_e_plan_scope_changed')
    for conv in HOLDOUT:
        require(protected_identity(output/(conv+'.sqlite3')) == plan['build_snapshots'][conv],
                'level_e_build_changed')
    return plan, lock, settings, inputs


def expected_authorization(output):
    plan = json.loads((Path(output)/'plan.json').read_text())
    return dict(approved=True, version=VERSION, scope=SCOPE, plan_sha256=sha(Path(output)/'plan.json'),
                policy=plan['policy'])


def check_trace(trace, conv, build_id):
    stack = [trace]
    while stack:
        item = stack.pop()
        if isinstance(item, dict):
            require(('build_id' not in item or item['build_id'] == build_id)
                    and ('sample_id' not in item or item['sample_id'] == conv)
                    and not any(str(k).startswith('m5_') for k in item), 'level_e_trace_scope_changed')
            stack.extend(item.values())
        elif isinstance(item, list):
            stack.extend(item)


@contextmanager
def execution_guard(output):
    """An interrupted invocation has no complete freeze and cannot resume itself."""
    try:
        yield
    except BaseException as error:
        if not (output/'generation-freeze.json').exists():
            write(output/'execution-aborted.json', dict(status='aborted_no_generation_freeze',
                error_type=type(error).__name__, plan_sha256=sha(output/'plan.json'),
                ledger_storage_identity=source_storage_identity(output/'physical-requests.sqlite3'),
                automatic_recovery=False, gold_read=False))
        raise


def execute(output, delegate=None, embedder=None):
    output = Path(output).resolve()
    require(not (output/'execution-started.json').exists(), 'level_e_already_started')
    require(json.loads((output/'authorization.json').read_text()) == expected_authorization(output),
            'level_e_authorization_mismatch')
    plan, lock, settings, inputs = verify_plan(output)
    with ExitStack() as contexts:
        for conv in HOLDOUT:
            contexts.enter_context(backend_ownership(output/(conv+'.sqlite3')))
        require(source_storage_identity(output/'physical-requests.sqlite3') == plan['ledger_identity'],
                'level_e_initial_ledger_changed')
        write(output/'execution-started.json', dict(plan_sha256=sha(output/'plan.json')))
        contexts.enter_context(execution_guard(output))
        if delegate is None:
            delegate = contexts.enter_context(httpx.HTTPTransport(retries=0))
        guard = BudgetTransport(output/'physical-requests.sqlite3', delegate, **plan['policy'])
        model = DeepSeekModel(settings, transport=guard)
        queries = {conv: services(output/(conv+'.sqlite3'), settings.model_copy(
            update={'db_path': output/(conv+'.sqlite3')}), model, embedder) for conv in HOLDOUT}
        baselines = {conv: EvaluationService(q) for conv, q in queries.items()}
        hashes = {}
        for index, item in enumerate(inputs):
            conv = item['sample_id']
            identity = lock['exports'][conv]
            for arm in ARMS:
                result = {**item, 'arm': arm}
                request = QueryRequest(dataset_id=identity['dataset_id'], sample_id=conv,
                                       build_id=identity['build_id'], question=item['question'])
                try:
                    trace = queries[conv].query(request) if arm == 'dynamic' else baselines[conv].baseline(request, arm)
                    check_trace(trace, conv, identity['build_id'])
                    result.update(outcome='succeeded', trace=trace, prediction=trace['answer']['answer'])
                except (QueryFailure, EvaluationFailure, BuildError) as error:
                    result.update(outcome='failed', error_code=error.code)
                    if isinstance(error, QueryFailure):
                        result['trace'] = queries[conv].get(error.trace_id)
                    elif isinstance(error, EvaluationFailure):
                        result['trace'] = error.trace
                except Exception as error:
                    # No exception text, input, credential or provider response is emitted.
                    result.update(outcome='unknown', error_code=type(error).__name__)
                name = f'items/{index:05d}-{arm}.json'
                write(output/name, result)
                hashes[name] = sha(output/name)
        for conv in HOLDOUT:
            require(protected_identity(output/(conv+'.sqlite3')) == plan['build_snapshots'][conv],
                    'level_e_build_changed')
        freeze = dict(status='generation_complete', plan_sha256=sha(output/'plan.json'),
                      item_hashes=hashes, planned_items=plan['planned_items'], gold_read=False,
                      authorization_sha256=sha(output/'authorization.json'),
                      execution_started_sha256=sha(output/'execution-started.json'),
                      ledger_storage_identity=source_storage_identity(output/'physical-requests.sqlite3'),
                      automatic_recovery=False, cost=ledger_summary(output/'physical-requests.sqlite3'))
        write(output/'generation-freeze.json', freeze)
    return freeze


def frozen_items(output):
    output = Path(output).resolve()
    plan, lock, _, inputs = verify_plan(output)
    freeze = json.loads((output/'generation-freeze.json').read_text())
    expected = {f'items/{i:05d}-{arm}.json' for i in range(len(inputs)) for arm in ARMS}
    require(freeze['status'] == 'generation_complete' and freeze['plan_sha256'] == sha(output/'plan.json')
            and set(freeze['item_hashes']) == expected and freeze['planned_items'] == plan['planned_items'],
            'level_e_generation_not_frozen')
    require(freeze['gold_read'] is False and freeze['automatic_recovery'] is False
            and not (output/'execution-aborted.json').exists()
            and sha(output/'authorization.json') == freeze['authorization_sha256']
            and json.loads((output/'authorization.json').read_text()) == expected_authorization(output)
            and sha(output/'execution-started.json') == freeze['execution_started_sha256']
            and json.loads((output/'execution-started.json').read_text()) == {'plan_sha256': sha(output/'plan.json')}
            and source_storage_identity(output/'physical-requests.sqlite3') == freeze['ledger_storage_identity']
            and ledger_summary(output/'physical-requests.sqlite3') == freeze['cost'],
            'level_e_execution_receipt_changed')
    items = []
    for i, question in enumerate(inputs):
        for arm in ARMS:
            name = f'items/{i:05d}-{arm}.json'
            require(sha(output/name) == freeze['item_hashes'][name], 'level_e_generation_item_changed')
            item = json.loads((output/name).read_text())
            require(all(item[k] == v for k, v in question.items()) and item['arm'] == arm
                    and item['outcome'] in ('succeeded', 'failed', 'unknown'), 'level_e_item_identity_changed')
            check_trace(item.get('trace', {}), item['sample_id'], lock['exports'][item['sample_id']]['build_id'])
            items.append(item)
    return plan, lock, items


def score(output):
    output = Path(output).resolve()
    plan, lock, items = frozen_items(output)  # Must finish before any Gold database is opened.
    reference = lock['reference']
    source = Path(reference['path'])
    require(source_storage_identity(source) == reference['storage_identity'], 'level_e_reference_changed')
    rows = []
    with frozen_readonly(source, reference['storage_identity']) as con:
        for item in items:
            # Exact sample and original ordinal; never SELECT annotations_json or the full QA object.
            matches = con.execute('''SELECT json_extract(q.value,'$.answer') AS answer,
                json_extract(q.value,'$.category') AS category, json_extract(q.value,'$.evidence') AS evidence
                FROM import_artifacts a, json_each(a.annotations_json) s, json_each(s.value,'$.qa') q
                WHERE a.dataset_id=? AND a.artifact_sha256=? AND json_extract(s.value,'$.sample_id')=?
                AND q.key=?''', (reference['dataset_id'], reference['artifact_sha256'],
                                item['sample_id'], item['qa_index'])).fetchall()
            require(len(matches) == 1, 'level_e_reference_identity_changed')
            gold = dict(matches[0])
            value = qa_score(item.get('prediction', ''), gold)
            if item['outcome'] != 'succeeded' and value['value'] is not None:
                value['value'] = 0.0
            with readonly(output/(item['sample_id']+'.sqlite3')) as build:
                sources = [dict(r) for r in build.execute('SELECT * FROM source_turns WHERE dataset_id=? AND sample_id=?',
                    (lock['exports'][item['sample_id']]['dataset_id'], item['sample_id']))]
            mapping = map_evidence(json.loads(gold['evidence']) if gold['evidence'] else [], sources)
            trace = item.get('trace', {})
            dynamic = item['arm'] == 'dynamic'
            initial = trace.get('initial', {}).get('initial_candidates', []) if dynamic else trace.get('retrieval', {}).get('initial_candidates', [])
            expanded = trace.get('expanded', {}).get('candidates', []) if dynamic else trace.get('expansion', {}).get('candidates', [])
            expanded_memories = [candidate['memory'] for candidate in expanded]
            effective = [m for m in expanded_memories if m['memory_id'] in trace.get('resolution', {}).get('effective_memory_ids', [])]
            stages = dict(initial=[c['memory'] for c in initial], expanded=expanded_memories,
                          effective=effective, answer_delivered=trace.get('effective_memories', []) if dynamic else trace.get('delivered_memories', []))
            recalls = {name: {str(k): None if (name == 'effective' and not dynamic) else
                coverage([sid for memory in memories[:k] for sid in memory['source_ids']], mapping)
                if item['outcome'] == 'succeeded' else 0.0 if mapping['scorable'] else None
                for k in (5, 10, 20)} for name, memories in stages.items()}
            rows.append({k: item[k] for k in ('question_id', 'sample_id', 'arm', 'outcome')} |
                        dict(qa=value, category=gold['category'], source_recall=recalls,
                             k_unit='Memory rank; unique Source Turn coverage; not atomic facts'))
    require(source_storage_identity(source) == reference['storage_identity'], 'level_e_reference_changed')
    def summarize(group):
        summary = {}
        for arm in ARMS:
            selected = [r for r in group if r['arm'] == arm]
            scorable = [r for r in selected if r['qa']['value'] is not None]
            successful = [r for r in scorable if r['outcome'] == 'succeeded']
            summary[arm] = dict(planned=len(selected), scorable=len(scorable), not_scorable=len(selected)-len(scorable),
                succeeded=sum(r['outcome'] == 'succeeded' for r in selected), failed=sum(r['outcome'] == 'failed' for r in selected),
                unknown=sum(r['outcome'] == 'unknown' for r in selected), successful_scorable=len(successful),
                failure_zero_mean=sum(r['qa']['value'] for r in scorable)/len(scorable) if scorable else None,
                successful_only_mean=sum(r['qa']['value'] for r in successful)/len(successful) if successful else None)
        return summary
    summary = summarize(rows)
    differences = [dict(question_id=h['question_id'], sample_id=h['sample_id'], category=h['category'],
        dynamic_minus_hybrid=d['qa']['value']-h['qa']['value'] if h['qa']['value'] is not None and d['qa']['value'] is not None else None)
        for h, d in zip(rows[::2], rows[1::2])]
    def comparison(group):
        return paired([r['dynamic_minus_hybrid'] for r in group if r['dynamic_minus_hybrid'] is not None]) | dict(
            scope='paired question bootstrap within the selected stratum of two held-out conversations (conv-43/44); '
                  'does not support conversation-level generalization')
    category_metrics = {}
    for name, categories, rule in (
            ('factual_f1', (1, 2, 3, 4), 'official_category_f1'),
            ('adversarial_literal_refusal', (5,), 'official_adversarial_refusal')):
        category_metrics[name] = dict(categories=list(categories), rule=rule,
            summary=summarize([r for r in rows if r['category'] in categories]),
            paired_dynamic_minus_hybrid=comparison([r for r in differences if r['category'] in categories]))
    result = dict(scope=SCOPE, generation_freeze_sha256=sha(output/'generation-freeze.json'),
                  summary=summary, category_metrics=category_metrics,
                  summary_composition='Mixed official category 1-4 token F1 and category 5 literal refusal; not factual correctness',
                  items=rows, per_question_differences=differences,
                  paired_dynamic_minus_hybrid=comparison(differences),
                  per_conversation={conv:comparison([r for r in differences if r['sample_id']==conv]) for conv in HOLDOUT},
                  per_category={str(cat):comparison([r for r in differences if r['category']==cat]) for cat in sorted({r['category'] for r in differences}, key=str)},
                  dynamic_relation_accuracy='not_measured', effective_selection_accuracy='not_measured',
                  atomic_fact_recall='not_measured', answer_source_support='not_measured',
                  reporting_scope='Official category F1 and separate literal refusal, with stage Source proxies; not a complete experiment report',
                  pending_frozen_output_audit={metric:'not_measured' for metric in (
                      'arm_cost_ratio', 'latency_p50_p95', 'resources', 'token_efficiency',
                      'correct_wrong_abstention', 'wrong_person_event_time', 'atomic_fact_retention')},
                  failure_rate_difference=(summary['dynamic']['failed']+summary['dynamic']['unknown']
                      -summary['hybrid_no_resolution']['failed']-summary['hybrid_no_resolution']['unknown'])/plan['questions'],
                  runtime_cost=json.loads((output/'generation-freeze.json').read_text())['cost'],
                  independent_once_only=True, teacher_hidden_score=False)
    write(output/'scores.json', result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'execute-authorized', 'score'))
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--final-lock', type=Path)
    args = parser.parse_args()
    result = prepare(args.output, args.final_lock) if args.action == 'prepare' else execute(args.output) if args.action == 'execute-authorized' else score(args.output)
    print(json.dumps(result if args.action == 'prepare' else {'status': 'completed', 'action': args.action}))
