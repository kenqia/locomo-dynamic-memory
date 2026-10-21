"""Parse original session timestamps without substituting the host clock."""

from datetime import datetime
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
