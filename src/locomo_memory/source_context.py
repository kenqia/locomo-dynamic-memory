"""Bounded neighboring raw turns from an independently verified source snapshot."""
from copy import deepcopy

from .imports import canonical_json
from .layered_evidence import ContractViolation
from .retrieval import budget_tokens


def source_window(pinned, selected, *, radius=1, max_turns=60, token_budget=12000):
    """Retain all selected turns; add same-session neighbors without inference.

    Callers must obtain pinned turns from pinned_sources for a complete Build.
    Raw citation authority is declared by the caller after actual delivery.
    Positions identify adjacency; absent positions are not guessed or bridged.
    """
    if type(radius) is not int or not 0 <= radius <= 3:
        raise ContractViolation('invalid_source_window_radius')
    by_id = {s['source_id']: s for s in pinned}
    if len(by_id) != len(pinned) or len({s['source_id'] for s in selected}) != len(selected):
        raise ContractViolation('duplicate_window_source')
    if any(by_id.get(s['source_id']) != s for s in selected):
        raise ContractViolation('selected_source_snapshot_mismatch')
    scope = {(s['dataset_id'], s['sample_id']) for s in pinned}
    if len(scope) != 1:
        raise ContractViolation('window_requires_single_conversation')
    ordered = sorted(pinned, key=lambda s: (s['position'], s['source_id']))
    if len({s['position'] for s in ordered}) != len(ordered):
        raise ContractViolation('duplicate_source_position')
    retained = {s['source_id']: s for s in selected}
    def cost(values):
        return budget_tokens(canonical_json({'raw_sources': list(values)}))
    if len(retained) > max_turns or cost(retained.values()) > token_budget:
        raise ContractViolation('original_sources_exceed_window_budget')
    origins, omitted = [], []
    for center in selected:
        for neighbor in ordered:
            distance = abs(neighbor['position'] - center['position'])
            if (distance > radius or distance == 0 or neighbor['session_id'] != center['session_id']):
                continue
            sid = neighbor['source_id']
            origin = {'source_id': sid, 'center_source_id': center['source_id'], 'distance': distance}
            if sid in retained:
                origins.append(origin)
            elif len(retained) >= max_turns or cost([*retained.values(), neighbor]) > token_budget:
                omitted.append(origin)
            else:
                retained[sid] = neighbor
                origins.append(origin)
    delivered = sorted(retained.values(), key=lambda s: (s['position'], s['source_id']))
    return deepcopy(delivered), {'version': 'selected-source-same-session-window-v1',
        'radius': radius, 'original_source_ids': [s['source_id'] for s in selected],
        'added_source_ids': [s['source_id'] for s in delivered if s['source_id'] not in {t['source_id'] for t in selected}],
        'origins': origins, 'omitted': omitted, 'truncated': bool(omitted),
        'token_budget': token_budget, 'max_turns': max_turns,
        'semantic_event_identity': 'not_established_by_adjacency'}
