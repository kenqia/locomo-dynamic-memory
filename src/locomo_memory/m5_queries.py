"""Explicit research query service reusing production resolution and answer paths.

Call only with an independently owned database and an authorized model budget.
Neither the default QueryService nor its settings are modified.
"""
from datetime import date
import hashlib
import uuid

from .exports import ExportService
from .builds import BuildError
from .imports import canonical_json
from .m5_adaptive import route, query_interval, prioritize
from .m5_graph import expand_relations
from .queries import QueryService
from .m5_wire_compression import CompressionModel


class BonusRetrieval:
    def __init__(self, base, bundle, *, adaptive=False, temporal=False, requested_date=None):
        self.base, self.bundle = base, bundle
        self.adaptive, self.temporal = adaptive, temporal
        self.requested_date = requested_date
        self.settings = base.settings
        self.database = base.database

    def query(self, build_id, question):
        initial = self.base.query(build_id, question)
        if not (self.adaptive or self.temporal):
            return initial
        analysis = initial['analysis'].get('result') or {}
        decision = route(question, analysis) if self.adaptive else route(question)
        if not self.adaptive:
            decision.update(entities=[], graph_depth=0, channels=['bm25', 'dense', 'rrf', 'temporal_priority'])
        interval = query_interval(question, date.fromisoformat(self.bundle.projection.cutoff[:10]))
        if self.requested_date is not None:
            interval.update(start=self.requested_date.isoformat(), end=self.requested_date.isoformat(),
                            basis='explicit_request_date')
        items = {x['memory']['memory_id']: x for x in initial['initial_candidates']}
        order = prioritize(list(items), {mid: item['memory'] for mid, item in items.items()}, decision, interval)
        result = {**initial, 'query_id': uuid.uuid4().hex,
                  'initial_candidates': [items[mid] for mid in order],
                  'm5_route': {**decision, 'execution_scope': 'priority over existing hybrid candidates; not new retrieval',
                               'executed_channels': ['bm25', 'dense', 'rrf', 'priority']},
                  'm5_interval': interval}
        # The original retrieval is preserved. A new candidate identity records the variant.
        with self.base.database.connect() as db:
            db.execute('INSERT INTO candidate_queries VALUES (?,?,?)',
                       (result['query_id'], build_id, canonical_json(result)))
        return result


class BonusExpansion:
    def __init__(self, base, bundle, retrieval, *, graph_depth=0, adaptive=False,
                 graph_token_budget=24000):
        self.base, self.bundle, self.retrieval = base, bundle, retrieval
        self.graph_depth, self.adaptive = graph_depth, adaptive
        self.graph_token_budget = graph_token_budget

    def expand(self, query_id, **kwargs):
        import json
        expanded = self.base.expand(query_id, **kwargs)
        with self.base.database.connect() as db:
            initial = json.loads(db.execute('SELECT result_json FROM candidate_queries WHERE query_id=?',
                                           (query_id,)).fetchone()[0])
        depth = self.graph_depth
        if self.adaptive:
            depth = max(depth, initial.get('m5_route', {}).get('graph_depth', 0))
        if not depth:
            return expanded
        seeds = [item['memory']['memory_id'] for item in expanded['candidates']]
        try:
            graph = expand_relations(self.bundle, seeds, depth=depth,
                max_candidates=self.base.settings.expansion_max_candidates,
                token_budget=self.graph_token_budget)
        except ValueError:
            raise BuildError('m5_graph_scope_or_budget_invalid', 422) from None
        added = [dict(memory=m, is_initial=False, origins=[dict(kind='m5_stored_relation_path',
                 path=graph['paths'][m['memory_id']])]) for m in graph['memories'] if m['memory_id'] not in seeds]
        result = {**expanded, 'candidates': expanded['candidates'] + added,
                  'added_candidates': expanded['added_candidates'] + added,
                  'm5_graph': {key: value for key, value in graph.items() if key != 'memories'},
                  'truncated': expanded['truncated'] or bool(graph['omitted_ids'])}
        # Persist the complete graph trace for read-only replay of the saved result.
        with self.base.database.connect() as db:
            db.execute('UPDATE candidate_expansions SET result_json=? WHERE expansion_id=?',
                       (canonical_json(result), result['expansion_id']))
        return result


class BonusQueryService(QueryService):
    def query_date(self, request, cutoff):
        if getattr(self, 'preserve_temporal_operator', False):
            return None, 'm5_temporal_operator_preserved'
        if getattr(self, 'relative_query_date', None):
            return self.relative_query_date, 'm5_relative_to_conversation_cutoff'
        return super().query_date(request, cutoff)

    def _save(self, trace):
        trace['m5_variant'] = self.variant
        if hasattr(self, 'temporal_intent'):
            trace['m5_temporal_intent'] = self.temporal_intent
        trace['query_fingerprint'] = hashlib.sha256(canonical_json(dict(
            base_fingerprint=trace['query_fingerprint'], m5_variant=self.variant)).encode()).hexdigest()
        super()._save(trace)


def query(base: QueryService, request, *, graph_depth=0, adaptive=False, temporal=False, compression=False,
          graph_token_budget=24000):
    """Run an explicitly selected variant; resolution always keeps production safeguards."""
    if not (graph_depth or adaptive or temporal or compression):
        return base.query(request)
    if request.strategy != 'dynamic':
        raise BuildError('m5_requires_dynamic_strategy', 422)
    if type(graph_depth) is not int or not 0 <= graph_depth <= 3 or graph_token_budget < 1:
        raise BuildError('m5_graph_bounds_invalid', 422)
    build_id = base.versions.pin(request.dataset_id, request.sample_id, request.build_id)
    bundle = ExportService(base.versions).export(build_id)
    retrieval = BonusRetrieval(base.retrieval, bundle, adaptive=adaptive, temporal=temporal,
                               requested_date=request.requested_date)
    expansion = BonusExpansion(base.expansion, bundle, retrieval, graph_depth=graph_depth,
                               adaptive=adaptive, graph_token_budget=graph_token_budget)
    service = BonusQueryService(base.versions, retrieval, expansion,
                                CompressionModel(base.model) if compression else base.model)
    service.variant = dict(version='m5-variant-v1', graph_depth=graph_depth, adaptive=adaptive,
                           temporal=temporal, compression=compression, graph_token_budget=graph_token_budget)
    if temporal and request.requested_date is None:
        interval = query_interval(request.question, date.fromisoformat(bundle.projection.cutoff[:10]))
        service.temporal_intent = dict(original_question=request.question, **interval)
        if interval['start'] is None and interval['basis'] in ('temporal_operator_preserved_in_question', 'ambiguous_range_preserved_in_question'):
            service.preserve_temporal_operator = True
        elif interval['start'] and interval['start'] == interval['end'] and interval['basis'] != 'explicit_question_date':
            service.relative_query_date = date.fromisoformat(interval['start'])
    return service.query(request.model_copy(update={'build_id': build_id}))
