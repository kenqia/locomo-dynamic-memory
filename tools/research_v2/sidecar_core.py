"""Deterministic, conservative English diagnostics over a supplied pinned snapshot.

No expected answers, network, SQLite writes, clock reads, or model calls.
Rule coverage is deliberately narrower than general English understanding.
"""
from __future__ import annotations

import calendar
import re
from datetime import date, timedelta
from itertools import combinations
from typing import Literal

from pydantic import Field
from locomo_memory.temporal import MONTHS
from tools.research_v2.sidecar_schema import (
    Contract, EventLink, SidecarInput, SidecarRecord, StateClaim, TimeInterval,
)

RULE_VERSION = 'deterministic-sidecar-v0.5-research'
MONTH = '(?:' + '|'.join(MONTHS) + ')'
DAY_PATTERN = rf'\b(?:\d{{4}}-\d{{2}}-\d{{2}}|{MONTH}\s+\d{{1,2}}(?:,?\s+\d{{4}})?)\b'
MONTH_PATTERN = rf'\b{MONTH}\s+\d{{4}}\b'
REL_PATTERN = r'\b(?:yesterday|this week|last week|last (?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)|recently|next month)\b'
TIME_QUALIFIER = r'before|after|around|by|about|circa|approximately|since|until|through|between|near|no later than|no earlier than|at least|at most'
PLACE = r'[A-Za-z]+(?: [A-Za-z]+)*?'

class ClaimDiagnostic(Contract):
    memory_id: str
    source_ids: tuple[str, ...]
    reported_at: tuple[str, ...]
    event_time: TimeInterval
    statement_type: str
    polarity: str
    completed: Literal['supported', 'denied', 'unknown'] = 'unknown'
    completion_support_source_ids: tuple[str, ...] = ()
    completion_denial_source_ids: tuple[str, ...] = ()
    attended: Literal['supported', 'denied', 'unknown'] = 'unknown'
    attendance_support_source_ids: tuple[str, ...] = ()
    attendance_denial_source_ids: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

class QueryDiagnostic(Contract):
    evidence_status: Literal['sufficient', 'conflict', 'insufficient', 'unknown']
    reason: str
    as_of: date | None = None
    cutoff: date | None = None
    answer: str | None = None
    memory_ids: tuple[str, ...] = ()
    source_ids: tuple[str, ...] = ()
    assumptions: tuple[str, ...] = ()

class SidecarDiagnostics(Contract):
    diagnostic_schema: Literal['sidecar-diagnostics-v0.5-research'] = 'sidecar-diagnostics-v0.5-research'
    rule_version: Literal['deterministic-sidecar-v0.5-research'] = RULE_VERSION
    mode: Literal['diagnostic_only'] = 'diagnostic_only'
    record: SidecarRecord
    claims: tuple[ClaimDiagnostic, ...] = ()
    query: QueryDiagnostic | None = None
    retained_memory_ids: tuple[str, ...] = ()
    global_mutation: Literal[False] = False
    links_truncated: bool = False


def _dedup(values):
    return tuple(dict.fromkeys(values))


def _reported_sources(snapshot, claim):
    sources = {s.source_id: s for s in snapshot.sources}
    return [sources[sid] for sid in claim.source_ids]


def _assertion(text, entity):
    """Recognize a single assertion and retain its object, phase and polarity."""
    text = ' '.join(text.casefold().split()).rstrip('.!?')
    dates = rf'(?:{DAY_PATTERN}|{MONTH_PATTERN}|{REL_PATTERN})'
    text = re.sub(rf'^on {dates},? ', '', text)
    text = re.sub(r',? (?:a |on a )second trip$', '', text)
    keynote = text.endswith(' had a keynote')
    if keynote:
        text = text.removesuffix(' had a keynote')
    text = re.sub(rf' (?:on |in |(?:{TIME_QUALIFIER}) )?{dates}(?: (?:last|next) year)?$', '', text)
    text = re.sub(rf'^(?:i |{re.escape(entity.casefold())} )', '', text)
    if keynote:
        match = re.fullmatch(r'(?:that|the) same (.+)', text)
        if match:
            return 'keynote', match[1], 'fact', 'positive'

    patterns = (
        ('attendance', r'attended the (.+ conference)', 'fact', 'positive'),
        ('attendance', r'(?:did not|have not) attend the (.+ conference)', 'fact', 'negative'),
        ('visit', rf'visited ({PLACE})(?: again)?', 'fact', 'positive'),
        ('move', rf'(?:moved|completed (?:my|the) move) ((?:from {PLACE} )?to {PLACE})', 'fact', 'positive'),
        ('move', rf'(?:did not|have not) (?:move|complete (?:my|the) move) ((?:from {PLACE} )?to {PLACE})', 'fact', 'negative'),
        ('move', rf'plans? to move ((?:from {PLACE} )?to {PLACE})', 'plan', 'positive'),
        ('residence', rf'lives? in ({PLACE})', 'fact', 'positive'),
        ('birth_year', r'(?:my )?birth year is (\d{4})', 'fact', 'positive'),
        ('arrival', r'(arrived)', 'fact', 'positive'),
        ('graduation', r'(graduated)', 'fact', 'positive'),
        ('travel', r'(travelled|traveled)', 'fact', 'positive'),
    )
    for kind, pattern, phase, polarity in patterns:
        match = re.fullmatch(pattern, text)
        if match:
            return kind, match[1], phase, polarity
    return None


def _owned_text(snapshot, claim, *, include_conflicts=False):
    # Only narrow first-person assertions by the cited speaker are eligible for
    # automatic rules. Quoted/reported speech and narrator claims stay unknown.
    expected = _assertion(claim.content, claim.entity_id)
    if not expected or expected[2:] != (claim.statement_type, claim.polarity):
        return []
    texts = []
    for source in _reported_sources(snapshot, claim):
        if source.speaker.casefold() != claim.entity_id.casefold():
            continue
        if any(x in source.text for x in ('"', '“', '”')):
            continue
        if re.search(r'\b(?:if|unless|might|maybe|possibly|perhaps|not sure)\b', source.text, re.I):
            continue
        if not re.match(r'^\s*(?:I\b|My\b|On\b|That same\b)', source.text, re.I):
            continue
        # Multiple clauses can attach dates and negation to the wrong predicate.
        # Handle only one claim-bearing sentence (allow an explicit dispute note).
        parts = re.split(r'(?<=[.!?])\s+', source.text.strip())
        if len(parts) > 1 and not all(re.fullmatch(
            r'(?:These reports conflict and remain unresolved|It was a second trip)[.!?]?', p, re.I
        ) for p in parts[1:]):
            continue
        actual = _assertion(parts[0], claim.entity_id)
        if not actual or actual[0] != expected[0] or actual[2] != expected[2]:
            continue
        # A reference-only keynote may borrow the named event only when the
        # source explicitly identifies it as the same conference.
        same_object = actual[1] == expected[1] or (
            expected[:2] == ('keynote', 'conference') and actual[1].endswith(' conference')
        )
        if not same_object and not (include_conflicts and actual[0] == 'birth_year'):
            continue
        if actual[3] != expected[3] and not (include_conflicts and actual[0] in ('move', 'attendance')):
            continue
        # A dated Memory must agree with the cited source, including month and
        # relative expressions. Different forms remain unverified, not silently
        # replaced by the source date. Undated summaries may still use source time.
        broad_time = rf'(?:{DAY_PATTERN}|{MONTH_PATTERN}|{REL_PATTERN})'
        claim_times = re.findall(broad_time, claim.content, re.I)
        if claim_times and not re.search(DAY_PATTERN, claim.content, re.I):
            source_times = re.findall(broad_time, parts[0], re.I)
            if [v.casefold() for v in claim_times] != [v.casefold() for v in source_times]:
                continue
        claim_days = list(re.finditer(DAY_PATTERN, claim.content, re.I))
        if claim_days:
            source_days = list(re.finditer(DAY_PATTERN, parts[0], re.I))
            anchor = source.reported_at.date()
            if len(claim_days) != 1 or len(source_days) != 1:
                continue
            claim_day = _parse_day(claim_days[0].group(), anchor)
            if claim_day is None or claim_day != _parse_day(source_days[0].group(), anchor):
                continue
            qualifiers = []
            for text, match in ((claim.content, claim_days[0]), (parts[0], source_days[0])):
                q = re.search(rf'\b({TIME_QUALIFIER})\s*$', text[:match.start()], re.I)
                qualifiers.append(q[1].casefold() if q else '')
            if qualifiers[0] != qualifiers[1]:
                continue
        texts.append((source, parts[0]))
    return texts


def _parse_day(expression, anchor):
    if re.fullmatch(r'\d{4}-\d{2}-\d{2}', expression):
        try: return date.fromisoformat(expression)
        except ValueError: return None
    m = re.fullmatch(rf'({MONTH})\s+(\d{{1,2}})(?:,?\s+(\d{{4}}))?', expression, re.I)
    if not m: return None
    year = int(m[3]) if m[3] else anchor.year
    try: return date(year, MONTHS[m[1].lower()], int(m[2]))
    except ValueError: return None


def _resolve_expression(expression, source):
    anchor = source.reported_at.date()
    low = expression.casefold().strip()
    start = end = None
    basis = ''
    parsed = _parse_day(expression, anchor)
    if parsed:
        if not re.search(r'\b\d{4}\b', expression) and parsed > anchor:
            return TimeInterval(original_expression=expression, anchor_source_id=source.source_id,
                                basis='Omitted year crosses the report boundary; event year unknown.')
        start = end = parsed
        basis = 'Explicit date; omitted year, if any, interpreted within source report year.'
    elif re.fullmatch(MONTH_PATTERN, expression, re.I):
        name, year = expression.split()
        year, month = int(year), MONTHS[name.casefold()]
        if year == 0:
            return TimeInterval(original_expression=expression, anchor_source_id=source.source_id,
                                basis='Invalid calendar year.')
        start, end = date(year,month,1), date(year,month,calendar.monthrange(year,month)[1])
        basis = 'Explicit month preserved as calendar range; no exact day asserted.'
    elif low == 'yesterday':
        start = end = anchor - timedelta(days=1)
        basis = 'Yesterday anchored to source report calendar day, not query or host time.'
    elif low in ('this week','last week'):
        start = anchor - timedelta(days=anchor.weekday() + (7 if low=='last week' else 0))
        end = start + timedelta(days=6)
        basis = 'Source-anchored calendar week, Monday through Sunday; day unknown.'
    elif low.startswith('last '):
        weekdays = {v:i for i,v in enumerate(('monday','tuesday','wednesday','thursday','friday','saturday','sunday'))}
        weekday = weekdays.get(low[5:])
        if weekday is not None:
            start = end = anchor - timedelta(days=(anchor.weekday()-weekday)%7 or 7)
            basis = 'Last weekday strictly earlier than source report day.'
    if start is None:
        return TimeInterval(original_expression=expression,anchor_source_id=source.source_id,
                            basis='Unsupported or ambiguous expression; exact dates remain unknown.')
    return TimeInterval(status='known' if start==end else 'range',start=start,end=end,
        original_expression=expression,anchor_source_id=source.source_id,basis=basis)


def _time(snapshot, claim):
    if len(_owned_text(snapshot, claim, include_conflicts=True)) != len(claim.source_ids):
        return TimeInterval(basis='Not all cited assertions support the claim and its time.')
    candidates = []
    for source,text in _owned_text(snapshot,claim,include_conflicts=True):
        expressions = list(re.finditer(DAY_PATTERN, text, re.I))
        expressions += list(re.finditer(MONTH_PATTERN, text, re.I))
        expressions += list(re.finditer(REL_PATTERN, text, re.I))
        # Do not attach one of several dates to an arbitrary predicate.
        if len(expressions) != 1:
            continue
        expression = expressions[0].group()
        prefix = text[:expressions[0].start()]
        qualifier = re.search(rf'\b(?:{TIME_QUALIFIER})\s*$', prefix, re.I)
        if qualifier:
            candidates.append(TimeInterval(
                original_expression=text[qualifier.start():expressions[0].end()],
                anchor_source_id=source.source_id,
                basis='Qualified date; the supported grammar does not resolve this interval.',
            ))
            continue
        if re.search(r'\b(?:last|next)\s*$',prefix,re.I) or re.search(r'\b(?:last|next) year\b',text,re.I):
            continue
        try:
            candidates.append(_resolve_expression(expression,source))
        except (OverflowError, ValueError):
            candidates.append(TimeInterval(original_expression=expression, anchor_source_id=source.source_id,
                                           basis='Calendar arithmetic outside supported range.'))
    if candidates:
        identities = {(v.status,v.start,v.end) for v in candidates}
        if len(identities) == 1:
            return min(candidates, key=lambda interval: interval.anchor_source_id or '')
        return TimeInterval(basis='Cited source times disagree; no single event interval inferred.')
    return TimeInterval(original_expression=claim.event_time.original_expression,
        anchor_source_id=claim.event_time.anchor_source_id,
        basis='No unique supported time expression; existing derived dates not trusted as source proof.')


def _claim_diagnostic(snapshot, claim):
    support, denial = set(), set()
    attendance_support, attendance_denial = set(), set()
    attended = 'unknown'
    warnings = []
    if claim.statement_type != 'fact':
        warnings.append('plan_intention_or_uncertain_is_not_completed_fact')
    else:
        for source, text in _owned_text(snapshot, claim, include_conflicts=True):
            kind, _, _, polarity = _assertion(text, claim.entity_id)
            if kind == 'move':
                (support if polarity == 'positive' else denial).add(source.source_id)
            elif kind == 'attendance':
                (attendance_support if polarity == 'positive' else attendance_denial).add(source.source_id)
    if attendance_support and attendance_denial:
        warnings.append('conflicting_attendance_evidence')
    elif attendance_support:
        attended = 'supported'
    elif attendance_denial:
        attended = 'denied'
    audited = _owned_text(snapshot, claim, include_conflicts=True)
    if len(audited) != len(claim.source_ids):
        warnings.append('unverified_cited_source')
        attended = 'unknown'
        support, denial = set(), set()
    completed = 'unknown'
    if support and denial:
        warnings.append('conflicting_move_completion_evidence')
    elif support and claim.polarity == 'positive':
        completed = 'supported'
    elif denial:
        completed = 'denied'
    sources = sorted(_reported_sources(snapshot, claim), key=lambda source: source.source_id)
    return ClaimDiagnostic(memory_id=claim.memory_id,source_ids=tuple(s.source_id for s in sources),
        reported_at=tuple(s.reported_at.isoformat() for s in sources),
        event_time=_time(snapshot,claim),statement_type=claim.statement_type,
        polarity=claim.polarity,completed=completed,attended=attended,warnings=tuple(warnings),
        completion_support_source_ids=tuple(sorted(support)),completion_denial_source_ids=tuple(sorted(denial)),
        attendance_support_source_ids=tuple(sorted(attendance_support)),
        attendance_denial_source_ids=tuple(sorted(attendance_denial)))


def _event_anchor(snapshot,claim):
    values=[]
    if len(_owned_text(snapshot,claim)) != len(claim.source_ids):
        return None
    for source,text in _owned_text(snapshot,claim):
        # Identifiable conference occurrence with explicit calendar identity.
        m=re.match(r'^(?:I attended the|That same) (.+? conference)(?: on (.+?))?(?: had a keynote)?[.!?]?$',text,re.I)
        if m:
            when = _time(snapshot,claim)
            values.append((m[1].casefold(),when.start,when.end))
    return values[0] if len(values)==1 else None


def _link(snapshot,left,right,_allow_reverse=True):
    sources=_dedup((*left.source_ids,*right.source_ids))
    decision,code,reason='unknown','identity_not_established','Same person, topic or wording does not establish a unique event.'
    if left.entity_id != right.entity_id:
        code,reason='different_entities','Distinct entities do not prove distinct events; shared events are possible.'
    elif left.memory_type!='event' or right.memory_type!='event':
        code,reason='not_two_event_claims','State similarity is not proof of a shared event.'
    elif left.statement_type != 'fact' or right.statement_type != 'fact' or left.polarity != 'positive' or right.polarity != 'positive':
        code,reason='nonpositive_or_nonfactual','Plan, uncertainty or negation is not a positive completed event identity.'
    elif any(len(_owned_text(snapshot,c)) != len(c.source_ids) for c in (left,right)):
        code,reason='unverified_cited_assertion','Every cited assertion must support the event before connecting it.'
    else:
        la,ra=_event_anchor(snapshot,left),_event_anchor(snapshot,right)
        right_text=' '.join(t for _,t in _owned_text(snapshot,right))
        left_text=' '.join(t for _,t in _owned_text(snapshot,left))
        if (la and ra and la==ra and la[1] is not None
                and (re.match(r'^That same\b',right_text,re.I) or re.match(r'^That same\b',left_text,re.I))):
            decision,code,reason='same_event','explicit_same_dated_event','Explicit same-event reference with matching named conference and date.'
        else:
            # Different dates alone may describe a multi-day event; require an
            # explicit repeat occurrence and matching travel destination.
            lm=re.match(r'^I visited (.+?) on ',left_text,re.I)
            rm=re.match(r'^I visited (.+?) again on .*\bsecond trip\b',right_text,re.I)
            lt,rt=_time(snapshot,left),_time(snapshot,right)
            if (lm and rm and lm[1].casefold()==rm[1].casefold()
                    and lt.start and rt.start and lt.end<rt.start):
                decision,code,reason='different_event','explicit_repeat_occurrence','Explicit second trip with a separate date, not merely the same topic.'
            elif _allow_reverse and re.match(r'^I visited .+? again on .*\bsecond trip\b',left_text,re.I) and re.match(r'^I visited .+? on ',right_text,re.I):
                reverse=_link(snapshot,right,left,_allow_reverse=False)
                decision,code,reason=reverse.decision,reverse.reason_code,reverse.reason
    if decision != 'unknown':
        sources = tuple(sorted({source.source_id for claim in (left, right)
                                for source, _ in _owned_text(snapshot, claim)}))
    return EventLink(left_memory_id=left.memory_id,right_memory_id=right.memory_id,
        decision=decision,reason_code=code,reason=reason,source_ids=sources)


def _query(snapshot, diagnostics):
    cutoff=max((s.reported_at.date() for s in snapshot.sources), default=None)
    question=snapshot.question or ''
    residence_question = re.fullmatch(
        r'Where (does|did) (.+?) live(?:(?: on| in| as of) (.+?))?\s*\?', question, re.I
    )
    as_of = snapshot.as_of
    unresolved_time = False
    if as_of is None and residence_question:
        expression = residence_question[3]
        if expression and cutoff:
            as_of = _parse_day(expression, cutoff)
        unresolved_time = as_of is None and (
            expression is not None or residence_question[1].casefold() == 'did'
        )
    if as_of is None and not unresolved_time:
        as_of = cutoff
    def q(status,reason,**kwargs):
        return QueryDiagnostic(evidence_status=status,reason=reason,as_of=as_of,cutoff=cutoff,**kwargs)
    if unresolved_time:
        return q('unknown','Historical residence needs a supported exact calendar date or explicit as_of.')
    if not snapshot.claims:
        return q('insufficient','No extracted claims supplied; not a contradiction.')
    if as_of and cutoff and as_of>cutoff:
        return q('insufficient','Requested date is beyond known report cutoff; plans do not establish future reality.')
    # Reject multi-entity and out-of-scope questions rather than pick a convenient
    # claim. Supported questions must identify one existing entity explicitly.
    entities={c.entity_id for c in snapshot.claims}
    selected=[e for e in entities if re.search(r'(?<!\w)'+re.escape(e)+r'(?!\w)',question,re.I)]
    if len(selected)!=1:
        return q('unknown','Question entity is absent or ambiguous; no general language resolver.')
    entity=selected[0]
    relevant=[c for c in snapshot.claims if c.entity_id==entity]
    times={c.memory_id:c.event_time for c in diagnostics}
    if re.fullmatch(r'What is .+?\b(?:birth year|year of birth)\s*\?',question,re.I):
        values=[]
        value_mismatch = False
        if any(c.state_dimension=='birth_year' and (c.statement_type!='fact' or c.polarity!='positive' or len(_owned_text(snapshot,c,include_conflicts=True)) != len(c.source_ids)) for c in relevant):
            return q('unknown','Birth-year qualification or source attribution is outside supported rules.')
        for c in relevant:
            if c.statement_type!='fact' or c.polarity!='positive' or c.state_dimension!='birth_year':continue
            for source,text in _owned_text(snapshot,c,include_conflicts=True):
                m=re.fullmatch(r'My birth year is (\d{4})[.]?',text,re.I)
                if m:
                    values.append((m[1],c.memory_id,source.source_id))
                    value_mismatch |= c.state_value != m[1]
                else:return q('unknown','Birth-year evidence is outside exact assertion grammar or conflicts with extracted value.')
        if len({v[0] for v in values})>1:
            return q('conflict','Incompatible birth-year assertions with no supported correction rule.',
                memory_ids=_dedup(v[1] for v in values),source_ids=_dedup(v[2] for v in values))
        if value_mismatch:
            return q('unknown','Extracted birth-year value disagrees with source.')
        if values:
            return q('sufficient','Explicit birth-year assertion only.',answer=values[0][0],
                memory_ids=_dedup(v[1] for v in values),source_ids=_dedup(v[2] for v in values))
        return q('insufficient','No supported birth-year assertion.')
    if residence_question:
        if residence_question[2].casefold() != entity.casefold():
            return q('unknown','Residence question is outside the supported entity grammar.')
        conflicting = [c for c in diagnostics if c.memory_id in {
            r.memory_id for r in relevant if r.state_dimension == 'residence'
        } and c.completion_support_source_ids and c.completion_denial_source_ids
            and (not c.event_time.start or not as_of or c.event_time.start <= as_of)]
        if conflicting:
            return q('conflict','Cited sources disagree about completion of the same residence move.',
                memory_ids=tuple(sorted(c.memory_id for c in conflicting)),
                source_ids=tuple(sorted({sid for c in conflicting
                    for sid in (*c.completion_support_source_ids, *c.completion_denial_source_ids)})))
        states=[]
        if any(c.state_dimension=='residence' and (c.statement_type=='uncertain' or (c.statement_type=='fact' and (c.polarity!='positive' or len(_owned_text(snapshot,c,include_conflicts=True)) != len(c.source_ids)))) for c in relevant):
            return q('unknown','Residence evidence contains unsupported uncertainty, negation or attribution.')
        for c in relevant:
            if c.statement_type!='fact' or c.polarity!='positive' or c.state_dimension!='residence':continue
            for source,text in _owned_text(snapshot,c):
                t=times[c.memory_id]
                if t.status!='known' or not as_of:
                    return q('unknown','Residence timing is unknown or ambiguous.')
                if t.start>as_of:continue
                m=re.match(rf'^I live in ({PLACE}) on ',text,re.I)
                move=re.match(rf'^I moved from ({PLACE}) to ({PLACE}) on ',text,re.I)
                value=m[1] if m else move[2] if move else None
                if value and c.state_value and value.casefold()==c.state_value.casefold():
                    states.append((t.start,value,c.memory_id,source.source_id,move[1] if move else None))
                else:return q('unknown','Residence claim is outside explicit state/move grammar or value differs.')
        if not states:return q('insufficient','No supported dated residence at or before requested date.')
        states.sort(key=lambda v:(v[0],v[2]))
        initial=[v for v in states if v[4] is None]
        if not initial:return q('unknown','No initial state; explicit move alone is not a complete history here.')
        current=initial[0]
        for row in states:
            if row==current:continue
            if row[0]==current[0] and row[1].casefold()!=current[1].casefold():
                return q('conflict','Incompatible dated residence assertions without an ordered transition.',
                    memory_ids=(current[2],row[2]),source_ids=_dedup((current[3],row[3])))
            if row[1].casefold()==current[1].casefold():continue
            if row[4] and row[4].casefold()==current[1].casefold():current=row
            else:return q('unknown','Residence changed without a supported matching from/to transition.')
        return q('sufficient','Residence follows explicit dated assertions and matched move chain.',
            answer=current[1],memory_ids=(current[2],),source_ids=(current[3],),
            assumptions=('Carry last supported residence until next supplied transition, within known report cutoff; diagnostic assumption, not proof of unreported real-world continuity.',))
    return q('unknown','Question is outside conservative residence/birth-year rules.')


def diagnose(snapshot: SidecarInput, *, enabled: bool = False, max_event_pairs: int = 1000) -> SidecarDiagnostics:
    """Pure diagnostic; never accepts a manifest or expected-behavior labels."""
    if not isinstance(snapshot,SidecarInput):raise TypeError('Supply validated SidecarInput, not a case/manifest')
    if not isinstance(max_event_pairs,int) or isinstance(max_event_pairs,bool) or max_event_pairs<0:
        raise ValueError('Pair budget must be a nonnegative integer')
    retained=tuple(c.memory_id for c in snapshot.claims)
    if not enabled:
        return SidecarDiagnostics(record=SidecarRecord(snapshot=snapshot),retained_memory_ids=retained)
    diagnostics=tuple(_claim_diagnostic(snapshot,c) for c in snapshot.claims)
    links=[]
    for i,(left,right) in enumerate(combinations(snapshot.claims,2)):
        if i>=max_event_pairs:break
        links.append(_link(snapshot,left,right))
    record=SidecarRecord(enabled=True,snapshot=snapshot,event_links=tuple(links))
    return SidecarDiagnostics(record=record,claims=diagnostics,
        query=_query(snapshot,diagnostics) if snapshot.question else None,
        retained_memory_ids=retained,
        links_truncated=len(snapshot.claims)*(len(snapshot.claims)-1)//2>max_event_pairs)
