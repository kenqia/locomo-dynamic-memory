"""Opt-in extraction scope; neighboring text is evidence, not a new target."""

WINDOW_VERSION = 'same-session-target-window-v1'
WINDOW_GUIDANCE = """
target_source_ids identify the turns to extract in this fragment. Other supplied
sources are context only: use them to resolve a uniquely supported referent or
event, and cite them when needed. Each memory must cite at least one target turn.
Do not extract a fact found only in context. A target citation must support the
claim, not merely serve as a permission marker. Adjacency does not establish that
two people or events are identical. Preserve ambiguity when identity is unknown.
"""


def extraction_sources(turns, target_ids, radius):
    targets = [turn for turn in turns if turn['source_id'] in target_ids]
    return [turn for turn in turns if turn['source_id'] in target_ids or any(
        turn['session_id'] == target['session_id']
        and abs(turn['position'] - target['position']) <= radius for target in targets)]
