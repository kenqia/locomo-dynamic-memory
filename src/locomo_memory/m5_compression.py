"""Reversible fact-preserving grouping; no summaries or persistent mutations."""
import hashlib

from .imports import canonical_json
from .memory_schemas import Memory
from .retrieval import budget_tokens

SHARED = ('build_id', 'dataset_id', 'sample_id', 'entity_id', 'state_dimension', 'state_key')


def pack(memories: list[dict]) -> dict:
    parsed = [Memory.model_validate(memory).model_dump(mode='json') for memory in memories]
    ids = [m['memory_id'] for m in parsed]
    if len(set(ids)) != len(ids) or len({(m['build_id'], m['dataset_id'], m['sample_id']) for m in parsed}) > 1:
        raise ValueError('compression_identity_mismatch')
    groups = {}
    order = []
    for memory in parsed:
        key = tuple(memory[field] for field in SHARED)
        if key not in groups:
            groups[key] = dict(shared={field: memory[field] for field in SHARED}, members=[])
        index = len(groups[key]['members'])
        groups[key]['members'].append({k: v for k, v in memory.items() if k not in SHARED})
        order.append((list(groups).index(key), index))
    original = canonical_json(parsed)
    package = dict(schema_version='m5-lossless-grouping-v1', groups=list(groups.values()),
                   order=order, expanded_sha256=hashlib.sha256(original.encode()).hexdigest())
    packed = canonical_json(package)
    return dict(package=package, metrics=dict(original_tokens=budget_tokens(original),
        packed_tokens=budget_tokens(packed), token_reduction=1 - budget_tokens(packed) / max(1, budget_tokens(original)),
        memory_coverage=1.0 if parsed else None, reversible=True,
        atomic_fact_retention='not_measured', person_event_time_correctness='not_measured',
        semantic_scope='Exact field preservation; does not independently verify extracted facts',
        token_method='regex-word-punctuation-v1', provider_tokens='not_measured'))


def expand(package: dict) -> list[dict]:
    if package.get('schema_version') != 'm5-lossless-grouping-v1':
        raise ValueError('compression_version_mismatch')
    groups = package['groups']
    expected = {(i, j) for i, g in enumerate(groups) for j in range(len(g['members']))}
    order = [tuple(item) for item in package['order']]
    if len(set(order)) != len(order) or set(order) != expected:
        raise ValueError('compression_membership_mismatch')
    for group in groups:
        if set(group['shared']) != set(SHARED) or any(set(member) & set(SHARED) for member in group['members']):
            raise ValueError('compression_shared_field_override')
    memories = [Memory.model_validate({**groups[i]['shared'], **groups[i]['members'][j]}).model_dump(mode='json')
                for i, j in order]
    if hashlib.sha256(canonical_json(memories).encode()).hexdigest() != package['expanded_sha256']:
        raise ValueError('compression_integrity_mismatch')
    # Reuse identity and duplicate checks at the packing boundary.
    pack(memories)
    return memories
