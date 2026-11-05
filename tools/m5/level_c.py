"""Prepare/generate/freeze/score the fixed development sample, without reading holdout QA.

Preparation and generation project question fields only. Scoring is a separate
command which cannot read reference answers until every planned item is frozen.
No command creates authorization. Source databases are always opened read-only.
"""
import argparse
from contextlib import contextmanager
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import sqlite3
import resource
import time

import httpx

from locomo_memory.builds import BuildService, BuildError
from locomo_memory.config import Settings
from locomo_memory.database import Database, backend_ownership
from locomo_memory.embeddings import MiniLMEmbedder
from locomo_memory.evaluation import EvaluationService, EvaluationFailure
from locomo_memory.evaluation_metrics import qa_score
from locomo_memory.expansion import ExpansionService
from locomo_memory.exports import ExportService
from locomo_memory.m5_budget import BudgetTransport
from locomo_memory.model import DeepSeekModel
from locomo_memory.queries import QueryService, QueryFailure
from locomo_memory.query_schemas import QueryRequest
from locomo_memory.relations import RelationService
from locomo_memory.retrieval import RetrievalService
from locomo_memory.versions import VersionsService
from tools.m5.extraction_recovery import snapshot
from tools.m5.offline import ROOT, ORIGIN, RUN, DEV, sha, write, paired

PROPOSAL_VERSION = 'm5-level-c-input-v2'
SCOPE = 'Level C input v2; fixed M5 development 80 ordinary + 20 diagnostic questions; Hybrid and Dynamic only; all thinking disabled; no holdout or Bonus'
THINKING_FIELDS = ('extraction_thinking_effort', 'relation_thinking_effort',
                   'query_analysis_thinking_effort', 'resolution_thinking_effort', 'answer_thinking_effort')
V2_SETTINGS = dict(thinking_enabled=False, resolution_input_budget=192000,
                   **{field: 'disabled' for field in THINKING_FIELDS})
MAX_INPUT_BYTES = 640000
ARMS = ('hybrid_no_resolution', 'dynamic')
SAMPLE = ROOT/'experiments/m5-development/replay-v1/fixed-live-sample.json'
TABLES = ('datasets', 'conversations', 'source_turns', 'build_versions', 'build_fragments',
          'memories', 'memory_sources', 'build_indexes', 'index_entries', 'relation_phases',
          'relation_tasks', 'memory_relations', 'current_state_projections', 'active_versions')


class NoProvider:
    def generate(self, *args, **kwargs):
        raise AssertionError('preparation_must_not_call_provider')


def source_storage_identity(path):
    """Freeze bytes, never SQL-decode Gold; checkpoints conservatively invalidate."""
    result = {}
    for label, item in (('main', path), ('wal', path.with_name(path.name+'-wal'))):
        exists = item.exists()
        result[label] = dict(exists=exists, sha256=sha(item) if exists else None)
    if not result['main']['exists']:
        raise FileNotFoundError('reference_database_missing')
    return result


@contextmanager
def readonly(path):
    con = sqlite3.connect(path.resolve().as_uri()+'?mode=ro', uri=True)
    con.row_factory = sqlite3.Row
    try:
        con.execute('PRAGMA query_only=ON')
        con.execute('BEGIN')
        yield con
    finally:
        con.close()


def producer_hashes():
    paths = [*sorted((ROOT/'src/locomo_memory').glob('*.py')), Path(__file__),
             ROOT/'tools/m5/offline.py', ROOT/'tools/m5/extraction_recovery.py']
    return {str(p.relative_to(ROOT)): sha(p) for p in paths}


def identities(sample):
    ordinary, diagnostic = sample['ordinary'], sample['diagnostic']
    if len(ordinary) != 80 or len(diagnostic) != 20 or len(set(ordinary+diagnostic)) != 100:
        raise ValueError('fixed_sample_size_or_overlap')
    for group, expected in ((ordinary, 20), (diagnostic, 5)):
        if any(sum(q.split(':qa:')[0] == conv for q in group) != expected for conv in DEV):
            raise ValueError('fixed_sample_conversation_counts')
    return [(qid, 'ordinary' if qid in ordinary else 'diagnostic') for qid in ordinary+diagnostic]


def projected_inputs(con, run, selected):
    # SQLite returns only these paths; Python never loads the run document or Gold.
    rows = con.execute('''SELECT json_extract(i.value,'$.question_id') AS qid,
        json_extract(s.value,'$.sample_id') AS sample_id,
        json_extract(s.value,'$.question') AS question
        FROM evaluation_runs r, json_each(r.result_json,'$.input.question_identities') i,
        json_each(r.result_json,'$.input.samples') s
        WHERE r.run_id=? AND i.key=s.key
        AND json_extract(s.value,'$.sample_id') IN (?,?,?,?)''', (run, *DEV)).fetchall()
    by_id = {r['qid']: dict(r) for r in rows}
    result = []
    for qid, stratum in selected:
        row = by_id[qid]
        if row['sample_id'] not in DEV or qid.split(':qa:')[0] != row['sample_id']:
            raise ValueError('question_outside_development')
        result.append(dict(question_id=qid, sample_id=row['sample_id'], question=row['question'], stratum=stratum))
    return result


def policy_for(count, settings):
    if (count != 100 or settings.model_name != 'deepseek-flash' or settings.model_retries != 2
        or settings.model_max_tokens != 32768 or settings.thinking_enabled is not False
        or settings.resolution_input_budget != V2_SETTINGS['resolution_input_budget']
        or any(getattr(settings, field) != 'disabled' for field in THINKING_FIELDS)):
        raise ValueError('query_settings_outside_proposal')
    requests = count*5*(settings.model_retries+1)  # Hybrid analysis+answer; Dynamic analysis+resolve+answer.
    maximum = (Decimal(MAX_INPUT_BYTES)*Decimal('.30')+Decimal(32768)*Decimal('1.20'))/1000000*requests
    return dict(model='deepseek-flash', input_usd_per_million='0.30', output_usd_per_million='1.20',
                max_input_bytes=MAX_INPUT_BYTES, max_output_tokens=32768, max_requests=requests, max_usd=str(maximum))


def copy_development(con, target, dataset, pins):
    """Copy only allowlisted Build tables, without evaluation or import annotations."""
    with sqlite3.connect(target) as dst:
        for table in TABLES:
            schema = con.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()[0]
            dst.execute(schema)
            columns = {r[1] for r in con.execute('PRAGMA table_info('+table+')')}
            if table == 'memory_sources':
                condition = 'memory_id IN (SELECT memory_id FROM memories WHERE build_id IN (?,?,?,?))'
                args = list(pins.values())
            elif 'build_id' in columns:
                condition, args = 'build_id IN (?,?,?,?)', list(pins.values())
            elif 'sample_id' in columns:
                condition, args = 'dataset_id=? AND sample_id IN (?,?,?,?)', [dataset, *DEV]
            else:
                condition, args = 'dataset_id=?', [dataset]
            rows = con.execute('SELECT * FROM '+table+' WHERE '+condition, args).fetchall()
            if rows:
                dst.executemany('INSERT INTO '+table+' VALUES ('+','.join('?'*len(rows[0]))+')', [tuple(r) for r in rows])
        if dst.execute('PRAGMA foreign_key_check').fetchall():
            raise ValueError('copied_database_foreign_key_failure')
    target.chmod(0o600)


def services(target, settings, model, embedder=None):
    builds = BuildService(Database(target), settings, model)
    retrieval = RetrievalService(builds, settings, embedder or MiniLMEmbedder(settings), model)
    relations = RelationService(builds, NoProvider())
    return QueryService(VersionsService(builds), retrieval, ExpansionService(relations), model)


def prepare(output, origin=ORIGIN, sample_file=SAMPLE, run=RUN):
    output, origin = output.resolve(), origin.resolve()
    original_storage = source_storage_identity(origin)
    original_sha = original_storage['main']['sha256']
    selected = identities(json.loads(sample_file.read_text()))
    output.mkdir(parents=True, exist_ok=False)
    output.chmod(0o700)
    with readonly(origin) as con:
        row = con.execute("SELECT json_extract(result_json,'$.config'), json_extract(result_json,'$.pins'), json_extract(result_json,'$.input.dataset_id') FROM evaluation_runs WHERE run_id=?", (run,)).fetchone()
        source_settings, pins, dataset = Settings.model_validate_json(row[0]), json.loads(row[1]), row[2]
        settings = Settings.model_validate({**source_settings.snapshot(), **V2_SETTINGS})
        if set(pins) != set(DEV):
            raise ValueError('frozen_development_pins_changed')
        inputs = projected_inputs(con, run, selected)
        copy_development(con, output/'memory.sqlite3', dataset, pins)
    write(output/'settings.json', settings.snapshot())
    write(output/'inputs.json', inputs)
    write(output/'sample.json', json.loads(sample_file.read_text()))
    q = services(output/'memory.sqlite3', settings, NoProvider())
    builds = []
    for conv, bid in pins.items():
        q.versions.pin(dataset, conv, bid)
        bundle = ExportService(q.versions).export(bid)
        builds.append(dict(sample_id=conv, build_id=bid, fingerprint=bundle.build.fingerprint,
            memories=len(bundle.memories), cited_sources=len(bundle.sources), relations=len(bundle.relations),
            index_fingerprint=bundle.index.fingerprint, projection_fingerprint=bundle.projection.fingerprint))
    write(output/'build-identities.json', builds)
    policy = policy_for(len(inputs), settings)
    BudgetTransport(output/'physical-requests.sqlite3', None, **policy)
    if source_storage_identity(origin) != original_storage:
        raise ValueError('source_changed_during_preparation')
    plan = dict(status='prepared_not_authorized', proposal_version=PROPOSAL_VERSION, scope=SCOPE, source=str(origin), source_sha256=original_sha, source_storage_identity=original_storage,
        source_run=run, dataset_id=dataset, pins=pins, arms=list(ARMS), questions=len(inputs), planned_items=2*len(inputs),
        strata=dict(ordinary=80, diagnostic=20), settings_sha256=sha(output/'settings.json'),
        inputs_sha256=sha(output/'inputs.json'), build_identities_sha256=sha(output/'build-identities.json'), sample_sha256=sha(output/'sample.json'),
        original_sample_sha256=sha(sample_file), policy=policy, implementation_sha256=producer_hashes(),
        database_snapshot=snapshot(output/'memory.sqlite3'), ledger_snapshot=snapshot(output/'physical-requests.sqlite3'),
        gold_read=False, provider_calls=0, holdout_read=False, bonus_enabled=False,
        settings_changes={field: dict(source=getattr(source_settings, field), prepared=value)
                          for field, value in V2_SETTINGS.items() if getattr(source_settings, field) != value},
        model_identity=dict(requested_alias='deepseek-flash', published_model='DeepSeek-V4.1-Flash-1017',
                            immutable_provider_pin_verified=False, recheck_alias_before_execution=True),
        authorization_boundary='new input-v2 plan and ledger only; no v1 authorization, recovery or budget reuse',
        price_basis='2026-11-04 official peak cache-miss .30 input/1.20 output USD per million; recheck before execution',
        failure_policy='each planned item runs once; bounded internal retries only; no truncation or strategy substitution; freeze all items including failures',
        scoring_policy='separate command after complete generation freeze; failure zero only with scorable Gold; ordinary/diagnostic separate')
    write(output/'plan.json', plan)
    return plan


def expected_authorization(output):
    plan = json.loads((output/'plan.json').read_text())
    return dict(approved=True, proposal_version=PROPOSAL_VERSION, scope=SCOPE,
                policy=plan['policy'], plan_sha256=sha(output/'plan.json'))


def verify_plan(output):
    plan = json.loads((output/'plan.json').read_text())
    settings = Settings.model_validate_json((output/'settings.json').read_text())
    if (plan.get('proposal_version') != PROPOSAL_VERSION or plan['scope'] != SCOPE
        or plan['status'] != 'prepared_not_authorized' or plan['arms'] != list(ARMS)
        or plan['implementation_sha256'] != producer_hashes()
        or plan['settings_sha256'] != sha(output/'settings.json')
        or plan['inputs_sha256'] != sha(output/'inputs.json')
        or plan['build_identities_sha256'] != sha(output/'build-identities.json')
        or plan['sample_sha256'] != sha(output/'sample.json')
        or plan['policy'] != policy_for(plan['questions'], settings)):
        raise ValueError('level_c_plan_changed')
    inputs = json.loads((output/'inputs.json').read_text())
    if [(r['question_id'], r['stratum']) for r in inputs] != identities(json.loads((output/'sample.json').read_text())):
        raise ValueError('level_c_sample_changed')
    return plan, settings, inputs


def execute(output, delegate=None, embedder=None):
    output = output.resolve()
    if (output/'execution-started.json').exists():
        raise FileExistsError('level_c_already_started')
    if json.loads((output/'authorization.json').read_text()) != expected_authorization(output):
        raise ValueError('level_c_authorization_mismatch')
    plan, settings, inputs = verify_plan(output)
    start, cpu = time.perf_counter(), time.process_time()
    with backend_ownership(output/'memory.sqlite3'):
        if (snapshot(output/'memory.sqlite3') != plan['database_snapshot']
            or snapshot(output/'physical-requests.sqlite3') != plan['ledger_snapshot']):
            raise ValueError('level_c_prepared_state_changed')
        write(output/'execution-started.json', dict(scope=SCOPE, plan_sha256=sha(output/'plan.json')))
        own = delegate is None
        delegate = httpx.HTTPTransport(retries=0) if own else delegate
        try:
            guard = BudgetTransport(output/'physical-requests.sqlite3', delegate, **plan['policy'])
            q = services(output/'memory.sqlite3', settings, DeepSeekModel(settings, transport=guard), embedder)
            evaluation = EvaluationService(q)
            hashes = {}
            for index, item in enumerate(inputs):
                for arm in ARMS:
                    request = QueryRequest(dataset_id=plan['dataset_id'], sample_id=item['sample_id'],
                        build_id=plan['pins'][item['sample_id']], question=item['question'])
                    result = dict(question_id=item['question_id'], sample_id=item['sample_id'], stratum=item['stratum'], arm=arm)
                    try:
                        trace = q.query(request) if arm == 'dynamic' else evaluation.baseline(request, arm)
                        result.update(outcome='succeeded', trace=trace, prediction=trace['answer']['answer'])
                    except (QueryFailure, EvaluationFailure, BuildError) as error:
                        result.update(outcome='failed', error_code=error.code)
                        if isinstance(error, QueryFailure):
                            result['trace'] = q.get(error.trace_id)
                        elif isinstance(error, EvaluationFailure):
                            result['trace'] = error.trace
                    name = f'items/{index:03d}-{arm}.json'
                    write(output/name, result)
                    hashes[name] = sha(output/name)
            freeze = dict(status='generation_complete', plan_sha256=sha(output/'plan.json'), item_hashes=hashes,
                          planned_items=plan['planned_items'], gold_read=False, automatic_recovery=False,
                          resources=dict(wall_seconds=time.perf_counter()-start, cpu_seconds=time.process_time()-cpu,
                          process_peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss, gpu_used=False),
                          cost=ledger_summary(output/'physical-requests.sqlite3'))
            write(output/'generation-freeze.json', freeze)
        finally:
            if own:
                delegate.close()
    return freeze


def ledger_summary(path):
    with readonly(path) as con:
        rows = con.execute('SELECT reserved_usd,status,usage_json FROM physical_requests').fetchall()
    usage = [json.loads(r['usage_json']) for r in rows]
    unknown = sum(not isinstance(u, dict) or 'prompt_tokens' not in u or 'completion_tokens' not in u for u in usage)
    prompt = sum(u.get('prompt_tokens', 0) for u in usage if isinstance(u, dict))
    completion = sum(u.get('completion_tokens', 0) for u in usage if isinstance(u, dict))
    return dict(physical_requests=len(rows), reserved_usd=str(sum((Decimal(r['reserved_usd']) for r in rows), Decimal(0))),
        usage_unknown_requests=unknown, reported_prompt_tokens=prompt, reported_completion_tokens=completion,
        reported_usage_peak_miss_upper_usd=str((Decimal(prompt)*Decimal('.30')+Decimal(completion)*Decimal('1.20'))/1000000),
        actual_invoice='not_accessed', unknown_reservations_retained=True)


def review_units(output):
    """Prepare source-only semantic review; never invent reviewed truth."""
    output = output.resolve()
    plan, items = frozen_items(output)
    inputs = {r['question_id']:r for r in json.loads((output/'inputs.json').read_text())}
    with readonly(output/'memory.sqlite3') as con:
        sources = {conv:[dict(r) for r in con.execute('SELECT * FROM source_turns WHERE dataset_id=? AND sample_id=? ORDER BY position', (plan['dataset_id'],conv))] for conv in DEV}
    units = []
    for item in items:
        units.append(dict(question_id=item['question_id'], arm=item['arm'], sample_id=item['sample_id'],
            question=inputs[item['question_id']]['question'], outcome=item['outcome'],
            prediction=item.get('prediction'), answer=item.get('trace',{}).get('answer'),
            full_conversation_sources=sources[item['sample_id']],
            rubric=['answer source support','correct/wrong abstention','wrong person','wrong event','wrong time','list omission'],
            labels=None, reference_status='pending_independent_review'))
    result = dict(generation_freeze_sha256=sha(output/'generation-freeze.json'), units=units, gold_read=False,
        instruction='Review every factual claim and abstention against original source turns; cite source IDs and verbatim quotes; use undetermined for ambiguous evidence; independent source review is not teacher truth.')
    write(output/'semantic-review-units.json', result)
    return dict(units=len(units), gold_read=False, reference_status='pending_independent_review')


def frozen_items(output):
    plan, _, inputs = verify_plan(output)
    freeze = json.loads((output/'generation-freeze.json').read_text())
    expected = [f'items/{i:03d}-{arm}.json' for i in range(len(inputs)) for arm in ARMS]
    if (freeze['status'] != 'generation_complete' or freeze['plan_sha256'] != sha(output/'plan.json')
        or set(freeze['item_hashes']) != set(expected) or len(expected) != plan['planned_items']):
        raise ValueError('generation_not_completely_frozen')
    items = []
    for i, question in enumerate(inputs):
        for arm in ARMS:
            name = f'items/{i:03d}-{arm}.json'
            if sha(output/name) != freeze['item_hashes'][name]:
                raise ValueError('generation_item_changed')
            item = json.loads((output/name).read_text())
            if (item['question_id'] != question['question_id'] or item['sample_id'] != question['sample_id']
                or item['stratum'] != question['stratum'] or item['arm'] != arm
                or item['outcome'] not in ('succeeded', 'failed')):
                raise ValueError('generation_item_identity_or_outcome_changed')
            items.append(item)
    return plan, items


def score(output):
    output = output.resolve()
    plan, items = frozen_items(output)  # MUST precede opening the reference database.
    source = Path(plan['source'])
    if source_storage_identity(source) != plan['source_storage_identity']:
        raise ValueError('reference_source_changed')
    with readonly(source) as con:
        rows = con.execute('''SELECT json_extract(i.value,'$.question_id') AS qid,
          json_extract(s.value,'$.answer') AS answer, json_extract(s.value,'$.category') AS category
          FROM evaluation_runs r, json_each(r.result_json,'$.input.question_identities') i,
          json_each(r.result_json,'$.input.samples') s WHERE r.run_id=? AND i.key=s.key
          AND json_extract(s.value,'$.sample_id') IN (?,?,?,?)''', (plan['source_run'], *DEV)).fetchall()
        references = {r['qid']: dict(r) for r in rows}
    if source_storage_identity(source) != plan['source_storage_identity']:
        raise ValueError('reference_source_changed_during_scoring')
    scored = []
    for item in items:
        reference = references[item['question_id']]
        value = qa_score(item.get('prediction', ''), reference)
        if item['outcome'] == 'failed' and value['value'] is not None:
            value['value'] = 0.0
        scored.append({k:item[k] for k in ('question_id','sample_id','stratum','arm','outcome')} | dict(qa=value, category=reference['category']))
    summary = {}
    for stratum in ('ordinary', 'diagnostic'):
        for arm in ARMS:
            group = [r for r in scored if r['arm'] == arm and r['stratum'] == stratum]
            scores = [r['qa']['value'] for r in group if r['qa']['value'] is not None]
            success = [r['qa']['value'] for r in group if r['outcome'] == 'succeeded' and r['qa']['value'] is not None]
            summary[stratum+'/'+arm] = dict(planned=len(group), scorable=len(scores),
                succeeded=sum(r['outcome']=='succeeded' for r in group),
                all_scorable_failure_zero_mean=sum(scores)/len(scores) if scores else None,
                successful_only_mean=sum(success)/len(success) if success else None)
    comparisons = {}
    differences = []
    by_question = {}
    for row in scored:
        by_question.setdefault(row['question_id'], {})[row['arm']] = row
    for qid, arms in by_question.items():
        h, d = (arms[arm] for arm in ARMS)
        delta = None if h['qa']['value'] is None or d['qa']['value'] is None else d['qa']['value']-h['qa']['value']
        differences.append(dict(question_id=qid, sample_id=h['sample_id'], stratum=h['stratum'], category=h['category'], dynamic_minus_hybrid=delta))
    for stratum in ('ordinary','diagnostic'):
        group = [r for r in differences if r['stratum'] == stratum]
        comparisons[stratum] = dict(overall=paired([r['dynamic_minus_hybrid'] for r in group if r['dynamic_minus_hybrid'] is not None]),
            per_conversation={conv:paired([r['dynamic_minus_hybrid'] for r in group if r['sample_id']==conv and r['dynamic_minus_hybrid'] is not None]) for conv in DEV},
            per_category={str(cat):paired([r['dynamic_minus_hybrid'] for r in group if r['category']==cat and r['dynamic_minus_hybrid'] is not None]) for cat in sorted({r['category'] for r in group if r['category'] is not None})})
    result = dict(generation_freeze_sha256=sha(output/'generation-freeze.json'), summary=summary, items=scored, paired_comparisons=comparisons, per_question_differences=differences,
                  scope=SCOPE, teacher_hidden_score=False, dynamic_truth_evaluated=False,
                  semantic_source_support='not_measured_pending_independent_review',
                  abstention_correctness='not_measured_pending_independent_review',
                  person_event_time_list_errors='not_measured_pending_independent_review')
    write(output/'scores.json', result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'execute-authorized', 'score', 'review-units'))
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = prepare(args.output) if args.action == 'prepare' else execute(args.output) if args.action == 'execute-authorized' else review_units(args.output) if args.action == 'review-units' else score(args.output)
    print(json.dumps(result))
