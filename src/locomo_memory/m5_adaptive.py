"""Deterministic question-only routing and conservative temporal priorities."""
from datetime import date, timedelta
import re

from .temporal import explicit_question_date


def route(question: str, analysis: dict | None = None) -> dict:
    analysis = analysis or {}
    text = question.lower()
    temporal = bool(explicit_question_date(question) or analysis.get('time') or
                    re.search(r'\b(when|before|after|during|yesterday|last week|currently|now)\b', text))
    state = bool(re.search(r'\b(still|currently|now|status|changed|cancelled|canceled)\b', text))
    multihop = bool(re.search(r'\b(both|together|relationship|related|connect)\b', text))
    entities = list(dict.fromkeys(analysis.get('entities', [])))
    kind = 'state' if state else 'temporal' if temporal else 'multi_hop' if multihop else 'entity' if entities else 'general'
    return dict(version='m5-question-router-v1', kind=kind,
        reasons=[name for name, yes in [('state_expression', state), ('temporal_expression', temporal),
                 ('multi_hop_expression', multihop), ('analysis_entities', bool(entities))] if yes] or ['general_fallback'],
        channels=['bm25', 'dense', 'rrf'] + (['stored_relations'] if state or multihop else []) +
                 (['temporal_priority'] if temporal else []),
        entities=entities, graph_depth=2 if multihop else 1 if state else 0,
        entity_policy='priority only; preserve other people and pronoun evidence')


def query_interval(question: str, cutoff: date) -> dict:
    explicit = explicit_question_date(question)
    text = question.lower()
    start = end = explicit
    basis = 'explicit_question_date' if explicit else 'unknown'
    relational = bool(re.search(r'\b(before|after|between|from|until|since|through)\b', text))
    # QueryRequest represents a point, not a temporal operator or interval.
    # Preserve those operators in the original question for the resolver.
    if relational:
        return dict(start=None, end=None, basis='temporal_operator_preserved_in_question',
                    cutoff=str(cutoff), modifies_stored_time=False)
    if not explicit:
        if re.search(r'\byesterday\b', text):
            start = end = cutoff - timedelta(days=1)
            basis = 'yesterday_relative_to_conversation_cutoff'
        elif re.search(r'\blast week\b', text):
            start = cutoff - timedelta(days=cutoff.weekday() + 7)
            end = start + timedelta(days=6)
            basis = 'calendar_week_relative_to_conversation_cutoff'
        elif re.search(r'\b(now|currently|current|today)\b', text):
            start = end = cutoff
            basis = 'conversation_cutoff'
    # Multiple distinct explicit dates are deliberately not replaced by a point.
    if len(set(re.findall(r'\b\d{4}-\d{2}-\d{2}\b', question))) > 1:
        start = end = None
        basis = 'ambiguous_range_preserved_in_question'
    return dict(start=str(start) if start else None, end=str(end) if end else None,
                basis=basis, cutoff=str(cutoff), modifies_stored_time=False)


def prioritize(ids: list[str], memories: dict, decision: dict, interval: dict) -> list[str]:
    """Stable soft priority: never infer event identity or remove unknown evidence."""
    entities = {e.casefold() for e in decision.get('entities', [])}
    def key(mid):
        memory = memories[mid]
        entity = memory['entity_id'].casefold() in entities if entities else False
        timing = memory['time']
        start, end = interval.get('start'), interval.get('end')
        overlap = bool(start and end and timing.get('valid_from') and
                       timing['valid_from'] <= end and
                       (not timing.get('valid_to') or timing['valid_to'] >= start))
        return (-int(overlap), -int(entity))
    return sorted(ids, key=key)
