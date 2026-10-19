"""Separate evaluation annotations, pinned comparisons and persisted reports."""
import hashlib
import json
import time
import uuid
import platform
from pathlib import Path
from importlib.metadata import version
from typing import Literal

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field, model_validator

from .builds import BuildError
from .embeddings import EmbeddingFailure
from .evaluation_metrics import aggregate, coverage, map_evidence, qa_score
from .imports import canonical_json
from .model import ANSWER_PROMPT, QUERY_ANALYSIS_PROMPT, RESOLUTION_PROMPT, KNOWN_MODEL_VERSION, ModelFailure, utc_now
from .queries import QueryFailure, explicit_question_date
from .query_schemas import EvidenceAnswer, EffectiveResolution, QueryRequest
from .retrieval import TOKEN_BUDGET_METHOD, budget_tokens, indexing_text
from .temporal import conversation_cutoff

Strategy = Literal['dynamic', 'full_text', 'vector', 'hybrid_no_resolution']


class RelationTruth(BaseModel):
    model_config = ConfigDict(extra='forbid')
    old_memory_id: str = Field(min_length=1)
    new_memory_id: str = Field(min_length=1)
    label: Literal['RETAIN', 'UPDATE', 'SUPERSEDE', 'CONFLICT', 'undetermined']


class DynamicTruth(BaseModel):
    model_config = ConfigDict(extra='forbid')
    provenance: str = Field(min_length=1)
    effective_memory_ids: list[str] | None = None
    relation_labels: list[RelationTruth] = Field(default_factory=list)

    @model_validator(mode='after')
    def independent_labels(self):
        if not self.provenance.strip() or (self.effective_memory_ids is None and not self.relation_labels):
            raise ValueError('Provide independent labels and provenance')
        if self.effective_memory_ids is not None and len(set(self.effective_memory_ids)) != len(self.effective_memory_ids):
            raise ValueError('Duplicate truth IDs')
        pairs = [(r.old_memory_id, r.new_memory_id) for r in self.relation_labels]
        if len(set(pairs)) != len(pairs):
            raise ValueError('Duplicate relation truth')
        return self


class Sample(BaseModel):
    model_config = ConfigDict(extra='forbid')
    sample_id: str = Field(min_length=1)
    question: str = Field(min_length=1, max_length=10000)
    answer: str | None = None
    category: int | None = None
    evidence: list[str] = Field(default_factory=list)
    # Independent, human/course supplied semantic truth, never inferred from source IDs.
    dynamic_truth: DynamicTruth | None = None

    @model_validator(mode='after')
    def validate_truth(self):
        QueryRequest(dataset_id='validation', sample_id=self.sample_id, question=self.question)
        return self


class EvaluationInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    dataset_id: str
    kind: Literal['synthetic', 'official_structure_only', 'course'] = 'synthetic'
    samples: list[Sample] = Field(min_length=1, max_length=3000)
    course_split: dict[str, list[str]] | None = None

    @model_validator(mode='after')
    def split(self):
        if self.course_split is not None:
            split = self.course_split
            if set(split) != {'dev', 'test'} or len(split['dev']) != 4 or len(split['test']) != 2 or len(set(split['dev'] + split['test'])) != 6:
                raise ValueError('Course split requires six unique IDs: four dev and two test')
            if not {s.sample_id for s in self.samples} <= set(split['dev'] + split['test']):
                raise ValueError('Samples outside course split')
        return self


class RunRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    input_id: str
    strategies: list[Strategy] = Field(min_length=1, max_length=4)
    build_ids: dict[str, str] = Field(default_factory=dict)
    partition: Literal['dev', 'test'] | None = None

    @model_validator(mode='after')
    def unique(self):
        if len(set(self.strategies)) != len(self.strategies):
            raise ValueError('Duplicate strategies')
        return self


class EvaluationFailure(BuildError):
    def __init__(self, error, trace):
        super().__init__(error.code if hasattr(error, 'code') else 'invalid_output', 502)
        self.trace = trace


class EvaluationService:
    def __init__(self, queries):
        self.queries = queries
        self.database = queries.database
        with self.database.connect() as db:
            db.executescript('CREATE TABLE IF NOT EXISTS evaluation_inputs(input_id TEXT PRIMARY KEY, result_json TEXT NOT NULL); CREATE TABLE IF NOT EXISTS evaluation_runs(run_id TEXT PRIMARY KEY, result_json TEXT NOT NULL);')

    def get(self, table, identity):
        # Table selected by the caller, never user input.
        with self.database.connect() as db:
            row = db.execute(f'SELECT result_json FROM {table} WHERE {"input_id" if table == "evaluation_inputs" else "run_id"}=?', (identity,)).fetchone()
        if row is None:
            raise BuildError('not_found', 404)
        return json.loads(row[0])

    def sources(self, dataset_id, sample_id):
        with self.database.connect() as db:
            return [dict(row) for row in db.execute('SELECT * FROM source_turns WHERE dataset_id=? AND sample_id=? ORDER BY position', (dataset_id, sample_id))]

    def add_input(self, request):
        value = request.model_dump(mode='json')
        with self.database.connect() as db:
            known = {r[0] for r in db.execute('SELECT sample_id FROM conversations WHERE dataset_id=?', (request.dataset_id,))}
        ids = {s.sample_id for s in request.samples}
        if request.course_split:
            ids |= set(request.course_split['dev'] + request.course_split['test'])
        if not ids <= known:
            raise BuildError('unknown_evaluation_conversation', 422)
        value['input_id'] = uuid.uuid4().hex
        value['created_at'] = utc_now()
        value['mappings'] = [map_evidence(s.evidence, self.sources(request.dataset_id, s.sample_id)) for s in request.samples]
        with self.database.connect() as db:
            db.execute('INSERT INTO evaluation_inputs VALUES (?,?)', (value['input_id'], canonical_json(value)))
        return value

    def baseline(self, request, strategy):
        trace = {'strategy': strategy, 'resolution': {'status': 'not_applied'}, 'operations': {}, 'initial': [], 'expanded': [], 'effective': None, 'raw_context': [], 'embedding_calls': 0}
        started = time.perf_counter()
        try:
            return self._baseline(request, strategy, trace)
        except (BuildError, ModelFailure, EmbeddingFailure) as error:
            if isinstance(error, ModelFailure):
                trace['operations']['failed_operation'] = error.metadata
            trace['outcome'] = 'failed'
            trace['elapsed_seconds'] = time.perf_counter() - started
            raise EvaluationFailure(error, trace) from None
        finally:
            # Shared generator's audit field is answer context, not verified effective evidence.
            if 'effective_memories' in trace:
                trace['answer_context_items'] = trace.pop('effective_memories')

    def _baseline(self, request, strategy, trace):
        q = self.queries
        started = time.perf_counter()
        trace['stage_seconds'] = {}
        sources = self.sources(request.dataset_id, request.sample_id)
        source_map = {s['source_id']: s for s in sources}
        with self.database.connect() as db:
            cutoff, raw = conversation_cutoff(db, request.dataset_id, request.sample_id)
        requested = explicit_question_date(request.question)
        condition = {'requested_date': requested.isoformat() if requested else None, 'anchor_date': (requested or cutoff.date()).isoformat(), 'cutoff': cutoff.isoformat(), 'cutoff_source_time': raw, 'beyond_cutoff': bool(requested and requested > cutoff.date())}
        if strategy == 'full_text':
            tick = time.perf_counter()
            answer, delivered, budget = q.generate_answer(request.question, condition, [], source_map, 'insufficient' if condition['beyond_cutoff'] else 'sufficient', raw_sources=sources, audit=trace)
            trace['raw_context'] = delivered
            trace['answer_context'] = [s['source_id'] for s in delivered]
            trace['initial_source_ids'] = [s['source_id'] for s in sources]
            trace['expanded_source_ids'] = trace['initial_source_ids']
            trace['k_unit'] = 'SourceTurn; original conversation order'
        else:
            tick = time.perf_counter()
            initial = q.retrieval.query(request.build_id, request.question)
            trace['stage_seconds']['retrieval'] = time.perf_counter() - tick
            trace['retrieval'] = initial
            trace['embedding_calls'] = int(bool(initial['channels']['dense']))
            trace['operations']['query_analysis_unused_by_vector_selection' if strategy == 'vector' else 'query_analysis'] = initial['analysis']['model_metadata']
            if strategy == 'vector':
                with self.database.connect() as db:
                    memories = {r['memory_id']: json.loads(r['memory_json']) for r in db.execute('SELECT memory_id,memory_json FROM memories WHERE build_id=?', (request.build_id,))}
                selected, used = [], 0
                for item in initial['channels']['dense']:
                    memory = memories[item['memory_id']]
                    cost = budget_tokens(indexing_text(memory))
                    if len(selected) >= q.settings.initial_k or used + cost > q.settings.candidate_token_budget:
                        break
                    selected.append(memory)
                    used += cost
                trace['selection'] = {'channel': 'dense_only', 'analysis_used': False, 'expansion_used': False, 'candidate_token_count': used, 'truncated': len(selected) < len(memories)}
                trace['initial'] = selected
                trace['expanded'] = selected
            else:
                tick = time.perf_counter()
                expanded = q.expansion.expand(initial['query_id'])
                trace['stage_seconds']['expansion'] = time.perf_counter() - tick
                trace['expansion'] = expanded
                trace['initial'] = [c['memory'] for c in initial['initial_candidates']]
                trace['expanded'] = [c['memory'] for c in expanded['candidates']]
            tick = time.perf_counter()
            answer, delivered, budget = q.generate_answer(request.question, condition, trace['expanded'], source_map, 'insufficient' if condition['beyond_cutoff'] else 'sufficient', audit=trace)
            trace['answer_context'] = list(dict.fromkeys(sid for m in delivered for sid in m['source_ids']))
            trace['delivered_memories'] = delivered
            trace['k_unit'] = 'Memory rank; SourceTurn coverage deduplicated'
        trace['stage_seconds']['answer'] = time.perf_counter() - tick
        trace.update(outcome='succeeded', answer=answer, evidence_budget=budget, time=condition, elapsed_seconds=time.perf_counter() - started)
        trace['operations']['answer'] = budget['model_metadata']
        return trace

    def run(self, request):
        inputs = self.get('evaluation_inputs', request.input_id)
        if inputs['kind'] == 'official_structure_only':
            raise BuildError('official_structure_only_no_generation', 422)
        if inputs['kind'] == 'course' and (not inputs['course_split'] or not request.partition):
            raise BuildError('course_split_and_partition_required', 422)
        selected = [(i, s) for i, s in enumerate(inputs['samples']) if not request.partition or inputs['course_split'] and s['sample_id'] in inputs['course_split'][request.partition]]
        if not selected:
            raise BuildError('empty_evaluation_partition', 422)
        # Pin ALL conversations before any model call so comparisons share versions.
        pins = {s['sample_id']: self.queries.versions.pin(inputs['dataset_id'], s['sample_id'], request.build_ids.get(s['sample_id'])) for _, s in selected}
        run = {'run_id': uuid.uuid4().hex, 'input_id': request.input_id, 'kind': inputs['kind'], 'partition': request.partition, 'started_at': utc_now(), 'config': self.queries.settings.snapshot(),
               'builds': {sid: self.queries.versions.builds.get(bid) for sid, bid in pins.items()}, 'answer_prompt': ANSWER_PROMPT, 'answer_schema': EvidenceAnswer.model_json_schema(), 'resolution_prompt': RESOLUTION_PROMPT, 'resolution_schema': EffectiveResolution.model_json_schema(), 'query_analysis_prompt': QUERY_ANALYSIS_PROMPT, 'known_service_version': KNOWN_MODEL_VERSION,
               'results': [], 'course_metrics': {'status': 'available' if inputs['kind'] == 'course' and inputs['course_split'] and all(s.get('dynamic_truth') for _, s in selected) else 'unavailable', 'reason': 'synthetic_or_structure_data_only' if inputs['kind'] != 'course' else 'course_split_missing' if not inputs['course_split'] else 'independent_dynamic_truth_missing' if not all(s.get('dynamic_truth') for _, s in selected) else None}, 'metric_version': 'locomo-official-category-v1', 'token_budget_method': TOKEN_BUDGET_METHOD}
        run['runtime'] = {'python': platform.python_version(), 'packages': {name: version(name) for name in ('locomo-dynamic-memory', 'nltk', 'numpy', 'rank-bm25', 'pydantic', 'fastapi')}}
        run['implementation_sha256'] = hashlib.sha256(b''.join(p.name.encode() + p.read_bytes() for p in sorted(Path(__file__).parent.glob('*.py')))).hexdigest()
        start = time.perf_counter()
        for index, sample in selected:
            mapping = inputs['mappings'][index]
            for strategy in request.strategies:
                item = {'sample_index': index, 'sample_id': sample['sample_id'], 'strategy': strategy, 'mapping': mapping, 'qa': {'value': None, 'reason': 'execution_failed'}, 'source_coverage': {s: None for s in ('initial', 'expanded', 'effective', 'answer_context')}, 'dynamic_metric': {'value': None, 'reason': 'independent_truth_missing'}}
                try:
                    query = QueryRequest(dataset_id=inputs['dataset_id'], sample_id=sample['sample_id'], build_id=pins[sample['sample_id']], question=sample['question'])
                    trace = self.queries.query(query) if strategy == 'dynamic' else self.baseline(query, strategy)
                    item['trace'] = trace
                    item['ranking_units'] = {'initial': 'SourceTurn' if strategy == 'full_text' else 'Memory', 'expanded': 'SourceTurn' if strategy == 'full_text' else 'Memory', 'effective': 'Memory' if strategy == 'dynamic' else 'not_applicable', 'answer_context': 'SourceTurn' if strategy == 'full_text' else 'Memory', 'source_coverage': 'unique SourceTurn IDs per stage; K is actual delivered rank count'}
                    calls = [call for operation in trace['operations'].values() for call in operation.get('calls', [])]
                    item['usage_summary'] = {'generation_calls': len(calls), 'calls_without_reported_usage': sum(not c.get('usage') for c in calls), 'reported_tokens': {field: sum(c.get('usage', {}).get(field, 0) for c in calls) for field in ('prompt_tokens', 'completion_tokens', 'total_tokens')}, 'embedding_calls': trace.get('embedding_calls', int(bool(trace.get('initial', {}).get('channels', {}).get('dense'))) if isinstance(trace.get('initial'), dict) else 0)}
                    item['qa'] = qa_score(trace['answer']['answer'], sample)
                    if strategy == 'dynamic':
                        stages = {'initial': [c['memory'] for c in trace['initial']['initial_candidates']], 'expanded': [c['memory'] for c in trace['expanded']['candidates']], 'effective': trace['effective_memories'], 'answer_context': trace['effective_memories']}
                    else:
                        stages = {'initial': trace['initial'], 'expanded': trace['expanded'], 'answer_context': trace.get('delivered_memories', [])}
                    item['memory_rankings'] = {stage: [m['memory_id'] for m in ms] for stage, ms in stages.items()}
                    item['source_sets'] = {stage: list(dict.fromkeys(sid for m in ms for sid in m['source_ids'])) for stage, ms in stages.items()}
                    if strategy == 'full_text':
                        item['source_sets'] = {'initial': trace['initial_source_ids'], 'answer_context': trace['answer_context']}
                    if strategy == 'vector':
                        item['source_sets'].pop('expanded', None)
                    for stage, ids in item['source_sets'].items():
                        item['source_coverage'][stage] = coverage(ids, mapping)
                    item['rank_counts'] = {stage: len(ids) for stage, ids in item['memory_rankings'].items()}
                    item['source_counts'] = {stage: len(ids) for stage, ids in item['source_sets'].items()}
                    truth = sample.get('dynamic_truth')
                    if strategy == 'dynamic' and truth and truth.get('effective_memory_ids') is not None:
                        expected = set(truth['effective_memory_ids'])
                        with self.database.connect() as db:
                            allowed = {r[0] for r in db.execute('SELECT memory_id FROM memories WHERE build_id=?', (query.build_id,))}
                        item['dynamic_metric'] = {'value': float(set(item['memory_rankings']['effective']) == expected) if expected <= allowed else None, 'reason': None if expected <= allowed else 'truth_outside_pinned_build', 'provenance': truth['provenance']}
                    item['relation_metric'] = {'value': None, 'reason': 'independent_relation_truth_missing'}
                    if truth and truth.get('relation_labels'):
                        with self.database.connect() as db:
                            relations = [json.loads(r[0]) for r in db.execute('SELECT relation_json FROM memory_relations WHERE build_id=?', (query.build_id,))]
                            all_ids = {r[0] for r in db.execute('SELECT memory_id FROM memories WHERE build_id=?', (query.build_id,))}
                        expected = truth['relation_labels']
                        valid = all(r['old_memory_id'] in all_ids and r['new_memory_id'] in all_ids for r in expected)
                        actual = {(r['old_memory_id'], r['new_memory_id']): r['label'] for r in relations}
                        item['relation_metric'] = {'value': sum(actual.get((r['old_memory_id'], r['new_memory_id'])) == r['label'] for r in expected) / len(expected) if valid else None, 'reason': None if valid else 'truth_outside_pinned_build', 'unit': 'independently labelled persisted relation; same build for all strategies', 'provenance': truth['provenance']}
                    item['diagnosis'] = {'certainty': 'possible_causes_only', 'note': 'Source coverage does not establish that the semantic fact was extracted or correctly resolved.'}
                except (QueryFailure, BuildError, ModelFailure, EmbeddingFailure) as error:
                    item['error'] = {'code': error.code}
                    if isinstance(error, EvaluationFailure):
                        item['trace'] = error.trace
                    elif isinstance(error, QueryFailure):
                        item['trace'] = self.queries.get(error.trace_id)
                    elif isinstance(error, ModelFailure):
                        item['model_metadata'] = error.metadata
                calls = [call for operation in item.get('trace', {}).get('operations', {}).values() for call in operation.get('calls', [])]
                item['usage_summary'] = {'generation_calls': len(calls), 'calls_without_reported_usage': sum(not c.get('usage') for c in calls), 'reported_tokens': {field: sum(c.get('usage', {}).get(field, 0) for c in calls) for field in ('prompt_tokens', 'completion_tokens', 'total_tokens')}, 'embedding_calls': item.get('usage_summary', {}).get('embedding_calls', item.get('trace', {}).get('embedding_calls', 0))}
                run['results'].append(item)
        run['summary'] = {strategy: {'qa': aggregate([r['qa']['value'] for r in run['results'] if r['strategy'] == strategy]), 'source_coverage': {stage: aggregate([r['source_coverage'][stage] for r in run['results'] if r['strategy'] == strategy]) for stage in ('initial', 'expanded', 'effective', 'answer_context')}, 'dynamic': aggregate([r['dynamic_metric']['value'] for r in run['results'] if r['strategy'] == strategy]), 'relations': aggregate([r.get('relation_metric', {}).get('value') for r in run['results'] if r['strategy'] == strategy]), 'missing_gold': sum(s.get('answer') is None or not s.get('answer', '').strip() for _, s in selected), 'unknown_category': sum(s.get('category') not in (1,2,3,4,5) for _, s in selected), 'invalid_evidence': sum(not inputs['mappings'][i]['scorable'] for i, _ in selected)} for strategy in request.strategies}
        run['usage_summary'] = {'generation_calls': sum(r['usage_summary']['generation_calls'] for r in run['results']), 'calls_without_reported_usage': sum(r['usage_summary']['calls_without_reported_usage'] for r in run['results']), 'embedding_calls': sum(r['usage_summary']['embedding_calls'] for r in run['results']), 'reported_tokens': {field: sum(r['usage_summary']['reported_tokens'][field] for r in run['results']) for field in ('prompt_tokens', 'completion_tokens', 'total_tokens')}}
        run['elapsed_seconds'], run['completed_at'] = time.perf_counter() - start, utc_now()
        run['fingerprint'] = hashlib.sha256(canonical_json({'input': inputs, 'pins': pins, 'config': run['config'], 'prompt': ANSWER_PROMPT}).encode()).hexdigest()
        with self.database.connect() as db:
            db.execute('INSERT INTO evaluation_runs VALUES (?,?)', (run['run_id'], canonical_json(run)))
        return run


def register_evaluation_routes(app, queries):
    service = EvaluationService(queries)
    app.state.evaluation = service

    def execute(fn, *args):
        try:
            return fn(*args)
        except BuildError as error:
            raise HTTPException(error.status, detail={'code': error.code, 'message': 'Evaluation operation failed'}) from None

    @app.post('/evaluation-inputs', status_code=201)
    def create_input(request: EvaluationInput):
        return execute(service.add_input, request)

    @app.get('/evaluation-inputs/{input_id}')
    def get_input(input_id: str):
        return execute(service.get, 'evaluation_inputs', input_id)

    @app.post('/evaluation-runs', status_code=201)
    def create_run(request: RunRequest):
        return execute(service.run, request)

    @app.get('/evaluation-runs/{run_id}')
    def get_run(run_id: str):
        return execute(service.get, 'evaluation_runs', run_id)
