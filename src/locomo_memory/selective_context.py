"""Explicit lexical predecessor selection from one caller-verified source snapshot.

Ported from 250795a's predecessor_context with delivery budgets and omission audit.
Lexical cues do not establish an antecedent or connect neighboring events.
"""
from copy import deepcopy
import re

from .imports import canonical_json
from .layered_evidence import ContractViolation
from .retrieval import budget_tokens

ANAPHORA = re.compile(r'\b(?:we|us|our|ours|they|them|their|it|its|this|that|these|those)\b', re.I)


def predecessor_context(original, pinned, *, max_turns=60, token_budget=12000):
    """Keep every original; add only a same-session predecessor when it fits.

    Obtain pinned sources from pinned_sources on a complete Build first. This
    function cannot grant citation authority or verify a Build on its own.
    """
    if type(max_turns) is not int or max_turns < 1 or type(token_budget) is not int or token_budget < 1:
        raise ContractViolation('invalid_predecessor_budget')
    originals = {s['source_id']: s for s in original}
    sources = {s['source_id']: s for s in pinned}
    if len(originals) != len(original) or len(sources) != len(pinned):
        raise ContractViolation('duplicate_context_source')
    if any(sources.get(sid) != source for sid, source in originals.items()):
        raise ContractViolation('context_snapshot_mismatch')
    if len({(s['dataset_id'], s['sample_id']) for s in pinned}) != 1:
        raise ContractViolation('context_requires_single_conversation')
    positions = {s['position']: s for s in pinned}
    if len(positions) != len(pinned):
        raise ContractViolation('duplicate_context_position')

    def cost(values):
        return budget_tokens(canonical_json({'raw_sources': list(values)}))

    kept = dict(originals)
    if len(kept) > max_turns or cost(kept.values()) > token_budget:
        raise ContractViolation('original_sources_exceed_predecessor_budget')
    origins, omitted = [], []
    for center in original:
        if not ANAPHORA.search(center['text']):
            continue
        previous = positions.get(center['position'] - 1)
        if previous is None or previous['session_id'] != center['session_id']:
            continue
        sid = previous['source_id']
        origin = {'source_id': sid, 'center_source_id': center['source_id']}
        if sid not in kept:
            if len(kept) >= max_turns or cost([*kept.values(), previous]) > token_budget:
                omitted.append({**origin, 'reason': 'predecessor_delivery_budget'})
                continue
            kept[sid] = previous
        origins.append(origin)
    delivered = sorted(kept.values(), key=lambda s: (s['position'], s['source_id']))
    return deepcopy(delivered), {
        'version': 'anaphoric-predecessor-v2-bounded',
        'original_source_ids': list(originals),
        'added_source_ids': [s['source_id'] for s in delivered if s['source_id'] not in originals],
        'origins': origins, 'omitted': omitted, 'truncated': bool(omitted),
        'token_count': cost(delivered), 'token_budget': token_budget, 'max_turns': max_turns,
        'semantic_antecedent': 'not_established_by_lexical_cue', 'originals_preserved': True,
    }
