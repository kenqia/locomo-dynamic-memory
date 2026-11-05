"""Deterministic provenance and conservative time parsing for candidate contracts."""
from datetime import date, datetime, timedelta
import re

from .layered_contracts import FactCandidate
from .memory_schemas import MemoryDraft
from .temporal import session_datetime


class ContractViolation(ValueError):
    """A safe static diagnostic; never embeds rejected text."""


def excerpt(source, start, end):
    if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(source['text']):
        raise ContractViolation('invalid_source_span')
    text = source['text'][start:end]
    if not text.strip():
        raise ContractViolation('blank_source_span')
    return text


def fact_evidence(candidate: FactCandidate, sources):
    ids, selections = [], []
    for span in candidate.evidence:
        if span.source_id not in sources:
            raise ContractViolation('unknown_fact_source')
        text = excerpt(sources[span.source_id], span.start, span.end)
        if span.source_id not in ids:
            ids.append(span.source_id)
        selection = span.model_dump()
        if selection in [s['span'] for s in selections]:
            raise ContractViolation('duplicate_fact_span')
        selections.append({'span': selection, 'text': text})
    anchor = None
    parts = []
    previous_end = -1
    for span in candidate.time_spans:
        # Never patch provenance by adding an anchor to evidence.
        if span.source_id not in ids:
            raise ContractViolation('time_anchor_not_fact_evidence')
        if anchor is not None and span.source_id != anchor:
            raise ContractViolation('multiple_time_anchors')
        if span.start < previous_end:
            raise ContractViolation('overlapping_or_unsorted_time_spans')
        anchor, previous_end = span.source_id, span.end
        parts.append(excerpt(sources[anchor], span.start, span.end))
    return ids, selections, anchor, parts


def parse_time(expression, session_time):
    """Closed grammar; ambiguous, partial and unsupported expressions stay unknown.

    Never searches a long sentence for a date (which could modify another fact).
    No numeric slash dates, year inference, host clock or guessed state duration.
    """
    value = re.sub(r'\s+', ' ', expression.strip())
    for pattern, formats in (
        (r'\d{4}-\d{2}-\d{2}', ('%Y-%m-%d',)),
        (r'\d{1,2} [A-Za-z]+,? \d{4}', ('%d %B %Y', '%d %b %Y')),
        (r'[A-Za-z]+ \d{1,2},? \d{4}', ('%B %d %Y', '%b %d %Y')),
    ):
        if re.fullmatch(pattern, value):
            for fmt in formats:
                try:
                    day = datetime.strptime(value.replace(',', ''), fmt).date()
                    return day, day
                except ValueError:
                    continue
            return None, None
    rel = value.casefold()
    supported = {'today', 'yesterday', 'tomorrow', 'this week', 'last week', 'next week',
                 'this month', 'last month', 'next month', 'this year', 'last year', 'next year'}
    weekdays = [x.casefold() for x in ('Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday')]
    if rel not in supported and not (rel.startswith('last ') and rel[5:] in weekdays):
        return None, None
    anchor = session_datetime(session_time).date()
    if rel in {'today','yesterday','tomorrow'}:
        day = anchor + timedelta(days={'today':0,'yesterday':-1,'tomorrow':1}[rel])
        return day, day
    if rel.endswith('week'):
        start = anchor - timedelta(days=anchor.weekday()) + timedelta(days={'this week':0,'last week':-7,'next week':7}[rel])
        return start, start + timedelta(days=6)
    if rel.endswith('year'):
        year = anchor.year + {'this year':0,'last year':-1,'next year':1}[rel]
        if not 1 <= year <= 9999:
            return None, None
        return date(year,1,1), date(year,12,31)
    if rel.endswith('month'):
        month = anchor.year * 12 + anchor.month - 1 + {'this month':0,'last month':-1,'next month':1}[rel]
        if not 12 <= month < 9999*12-1:
            return None, None
        start = date(month // 12, month % 12 + 1, 1)
        after = date((month+1)//12, (month+1)%12+1, 1)
        return start, after-timedelta(days=1)
    day = anchor-timedelta(days=(anchor.weekday()-weekdays.index(rel[5:]))%7 or 7)
    return day, day


def materialize_fact(candidate, sources):
    """Call only AFTER raw-source semantic support is accepted by the verifier."""
    ids, selections, anchor, parts = fact_evidence(candidate, sources)
    timing = {}
    audit = {'source_spans': selections, 'time_spans': [s.model_dump() for s in candidate.time_spans],
             'time_parts': parts, 'time_precision': 'unknown'}
    if anchor is not None:
        # Persist a real continuous enclosing slice for legacy readers. The parser
        # uses only the selected parts; joining disjoint excerpts never creates a date.
        first, last = candidate.time_spans[0], candidate.time_spans[-1]
        original = sources[anchor]['text'][first.start:last.end]
        start, end = parse_time(parts[0], sources[anchor]['session_time']) if len(parts)==1 else (None,None)
        timing = {'original_expression':original, 'anchor_source_id':anchor,
                  'event_start':start, 'event_end':end,
                  'basis':'Program parsed selected source expression against its session; unknown precision preserved' if start else 'Source wording retained; date ambiguous or outside closed grammar'}
        audit['time_precision'] = 'day' if start and start==end else 'interval' if start else 'unknown'
    data = candidate.model_dump(exclude={'evidence','time_spans'})
    draft = MemoryDraft.model_validate({**data, 'source_ids':ids, 'time':timing}, context={'sources':sources})
    return draft, audit


def bind_answer(candidate, memories, sources, *, raw_sources=None):
    """Bind each claim to the exact delivered Memory->SourceTurn edge and excerpt."""
    bound = []
    for claim in candidate.claims:
        supports, seen = [], set()
        for selection in claim.supports:
            memory = memories.get(selection.memory_id)
            if raw_sources is not None and selection.memory_id is None:
                ids = list(raw_sources)
            elif memory is not None:
                ids = memory['source_ids']
            else:
                raise ContractViolation('undelivered_memory')
            if selection.source_index >= len(ids):
                raise ContractViolation('unknown_source_position')
            sid = ids[selection.source_index]
            if sid not in sources:
                raise ContractViolation('undelivered_memory_source')
            key = (selection.memory_id, sid, selection.start, selection.end)
            if key in seen:
                raise ContractViolation('duplicate_answer_span')
            seen.add(key)
            supports.append({'memory_id':selection.memory_id, 'source_id':sid,
                             'start':selection.start, 'end':selection.end,
                             'text':excerpt(sources[sid], selection.start, selection.end)})
        bound.append({'text':claim.text, 'supports':supports})
    return bound
