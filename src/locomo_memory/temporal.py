"""Parse original session timestamps without substituting the host clock."""

from datetime import datetime, timedelta
import re


MONTHS = {name.lower(): number for number, name in enumerate(("January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"), 1)}


def session_datetime(value: str) -> datetime:
    match = re.fullmatch(r"(\d{1,2}):(\d{2})\s+(am|pm)\s+on\s+(\d{1,2})\s+([A-Za-z]+),\s+(\d{4})", value.strip(), re.IGNORECASE)
    try:
        if match:
            hour, minute, meridiem, day, month, year = match.groups()
            hour = int(hour)
            if not 1 <= hour <= 12:
                raise ValueError
            return datetime(int(year), MONTHS[month.lower()], int(day), hour % 12 + (12 if meridiem.lower() == "pm" else 0), int(minute))
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is not None:
            # The raw dataset has no timezone; reject mixed assumptions explicitly.
            raise ValueError
        return parsed
    except (ValueError, KeyError):
        from .builds import BuildError
        raise BuildError("invalid_session_time", 422) from None


def conversation_cutoff(db, dataset_id: str, sample_id: str) -> tuple[datetime, str]:
    times = [row[0] for row in db.execute("SELECT DISTINCT session_time FROM source_turns WHERE dataset_id=? AND sample_id=?", (dataset_id, sample_id))]
    if not times:
        from .builds import BuildError
        raise BuildError("not_found", 404)
    raw = max(times, key=session_datetime)
    return session_datetime(raw), raw


def explicit_question_date(question):
    """Recognize one exact date; ambiguous ranges stay in the original question."""
    matches = []
    patterns = [
        (r"\b\d{4}-\d{2}-\d{2}\b", ("%Y-%m-%d",)),
        (r"\b\d{1,2} [A-Za-z]+,? \d{4}\b", ("%d %B %Y", "%d %b %Y")),
        (r"\b[A-Za-z]+ \d{1,2},? \d{4}\b", ("%B %d %Y", "%b %d %Y")),
    ]
    for pattern, formats in patterns:
        for match in re.finditer(pattern, question):
            for format in formats:
                try:
                    matches.append(datetime.strptime(match.group().replace(",", ""), format).date())
                    break
                except ValueError:
                    continue
    unique = set(matches)
    return matches[0] if len(unique) == 1 else None


RELATIVE_TIME_GUIDANCE = """Resolve relative time against the cited source session time,
not the query cutoff or host clock. "this week" is the week containing that source
date, never the previous week. Keep an interval or the anchored original expression
when the day is unknown; do not invent an exact date. Prefer original source text
and its anchor when a derived Memory date contradicts that expression.
"""

QUERY_TIME_GUIDANCE = """Anchor relative time to the cited source session_time, never cutoff or host clock.
SourceTurn text and original_expression outrank derived time.basis and relation time descriptions.
"this week" is the week containing that source date, never the previous week.
Keep ranges and unknown precision; never invent a day.
Synthetic example: a 2024-04-10 source saying "this week" means 2024-04-08 through 2024-04-14.
"""


TIME_AUTHORITY_VERSION = "source-relative-time-v1"


def query_memory_times(memories, sources):
    """Normalize known relative forms on query copies, leaving persisted history intact.

    Weeks use Monday through Sunday. A weekday qualified by last is strictly
    earlier than the source date. Unknown expressions retain their precision.
    """
    normalized, diagnostics = {}, []
    weekdays = {name.lower(): i for i, name in enumerate(
        ('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'))}
    for mid, memory in memories.items():
        timing = memory.get('time', {})
        expression = (timing.get('original_expression') or '').strip()
        source = sources.get(timing.get('anchor_source_id'))
        if (not source or source['source_id'] not in memory['source_ids']
                or not expression or not re.search(r'(?<!\w)' + re.escape(expression) + r'(?!\w)',
                                                   source['text'], re.I)):
            normalized[mid] = memory
            continue
        anchor = session_datetime(source['session_time']).date()
        relative = expression.casefold()
        start = end = None
        if relative in ('this week', 'last week'):
            start = anchor - timedelta(days=anchor.weekday() + (7 if relative == 'last week' else 0))
            end = start + timedelta(days=6)
        elif relative == 'yesterday':
            start = end = anchor - timedelta(days=1)
        elif relative.startswith('last ') and relative[5:] in weekdays:
            offset = (anchor.weekday() - weekdays[relative[5:]]) % 7 or 7
            start = end = anchor - timedelta(days=offset)
        if start is None:
            normalized[mid] = memory
            continue
        basis = f'Source expression "{expression}" anchored to {anchor.isoformat()}; {start.isoformat()}'
        if start != end:
            basis += f' through {end.isoformat()}; calendar weeks run Monday through Sunday; exact day unknown'
        corrected = {**timing, 'event_start':start.isoformat(), 'event_end':end.isoformat(), 'basis':basis}
        # An event's week does not establish how long a state remains valid.
        if any(timing.get(k) for k in ('valid_from', 'valid_to')):
            corrected.update(valid_from=None, valid_to=None)
        normalized[mid] = {**memory, 'time':corrected}
        if any(timing.get(k) != corrected.get(k) for k in ('event_start', 'event_end', 'basis', 'valid_from', 'valid_to')):
            diagnostics.append({'memory_id':mid, 'anchor_source_id':source['source_id'],
                'original_expression':expression, 'session_time':source['session_time'],
                'reason':'source_relative_time_overrides_derived_time',
                'derived_time':timing, 'query_time':corrected})
    return normalized, diagnostics
