"""E6-A exact column encoding and evidence preservation; research only, no I/O.

The inverse reconstructs every supplied JSON field, including unknown fields.
Passing the gate proves representation coverage, never semantic sufficiency.
"""
from collections import defaultdict
from copy import deepcopy
from dataclasses import asdict, dataclass
import hashlib
import json
import re

from locomo_memory.model import Generation, request_messages
from locomo_memory.query_schemas import EffectiveResolution

VERSION = 'e6a-exact-columns-v1'
PROMPT_VERSION = 'e6a-resolution-columns-prompt-v1'
GUIDANCE = """E6 exact column representation v1. Reconstruct each input table before reasoning.
Each table has keys and columns in matching order, and size rows. A column with
values supplies its row values directly. Otherwise dictionary[indices[row]]
supplies the value. Optional present lists row indices where the field exists;
absence differs from null. context supplies every other original input field.
Repeated identical values share storage only, never merge facts or events.
All original memory IDs, source links, polarity, modality, time, unknowns and
relation endpoints remain authoritative. Shared state_key does not prove event
identity or conflict; plans do not prove completion. Preserve unresolved event
identity and relative time precision. Return the original response schema using
original IDs. Coverage means this supplied packet only, not all history.
"""


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def tokens(value):
    return len(re.findall(r'\w+|[^\w\s]', json.dumps(value, ensure_ascii=False, allow_nan=False)))


def encode(payload):
    """Dictionary-code exact equal column values only when serialized size falls."""
    tables = {}
    for name in ('memories', 'sources', 'relations'):
        if name not in payload:
            continue
        rows = payload[name]
        keys = list(dict.fromkeys(k for row in rows for k in row))
        columns = []
        for key in keys:
            present = [i for i, row in enumerate(rows) if key in row]
            values = [deepcopy(rows[i][key]) for i in present]
            dictionary, lookup, indices = [], {}, []
            for value in values:
                identity = canonical(value)
                if identity not in lookup:
                    lookup[identity] = len(dictionary)
                    dictionary.append(value)
                indices.append(lookup[identity])
            direct = {'values': values}
            coded = {'dictionary': dictionary, 'indices': indices}
            column = coded if tokens(coded) < tokens(direct) else direct
            if len(present) != len(rows):
                column['present'] = present
            columns.append(column)
        tables[name] = {'keys': keys, 'columns': columns, 'size': len(rows)}
    return {'format': VERSION, 'context': deepcopy({k: v for k, v in payload.items() if k not in tables}),
            'tables': tables}


def decode(representation):
    if representation['format'] != VERSION:
        raise ValueError('unknown_representation')
    restored = deepcopy(representation['context'])
    for name, table in representation['tables'].items():
        rows = [{} for _ in range(table['size'])]
        if len(table['keys']) != len(table['columns']) or len(set(table['keys'])) != len(table['keys']):
            raise ValueError('invalid_columns')
        for key, column in zip(table['keys'], table['columns']):
            positions = column.get('present', list(range(table['size'])))
            values = column.get('values')
            if values is None:
                if any(type(i) is not int or i < 0 or i >= len(column['dictionary']) for i in column['indices']):
                    raise ValueError('invalid_dictionary_reference')
                values = [column['dictionary'][i] for i in column['indices']]
            if len(values) != len(positions) or len(set(positions)) != len(positions):
                raise ValueError('invalid_presence')
            for i, value in zip(positions, values):
                if type(i) is not int or not 0 <= i < len(rows):
                    raise ValueError('invalid_row_reference')
                rows[i][key] = deepcopy(value)
        restored[name] = rows
    return restored


def preservation_gate(original, restored):
    """Fail closed on any field loss or dangling dependency in the supplied set."""
    errors = []
    if canonical(original) != canonical(restored):
        errors.append('roundtrip_field_mismatch')
    memories = original.get('memories', [])
    sources = original.get('sources', [])
    relations = original.get('relations', [])
    mids = {m['memory_id'] for m in memories}
    sids = {s['source_id'] for s in sources}
    for name, rows, key in (('memory', memories, 'memory_id'), ('source', sources, 'source_id'),
                            ('relation', relations, 'relation_id')):
        ids = [r[key] for r in rows if key in r]
        if len(set(ids)) != len(rows):
            errors.append('duplicate_or_missing_' + name + '_id')
    dependencies = []
    groups = defaultdict(list)
    for m in memories:
        mid = m['memory_id']
        if not m.get('source_ids') or not set(m['source_ids']) <= sids:
            errors.append('missing_memory_source')
        anchor = (m.get('time') or {}).get('anchor_source_id')
        if anchor and anchor not in sids:
            errors.append('missing_memory_time_anchor')
        dependencies.append({'memory_id': mid, 'source_ids': m.get('source_ids', []), 'time_anchor': anchor})
        groups['state:' + str(m.get('state_key', mid))].append(mid)
        # Each event identity remains separate until sources prove a linkage.
        groups['event_identity_unverified:' + mid] = [mid]
    for i, r in enumerate(relations):
        ends = [r['old_memory_id'], r['new_memory_id']]
        if not set(ends) <= mids:
            errors.append('missing_relation_endpoint')
        app = r.get('applicability') or {}
        refs = set(r.get('source_ids', [])) | set(app.get('condition_source_ids', []))
        if app.get('time_anchor_source_id'):
            refs.add(app['time_anchor_source_id'])
        if not refs <= sids:
            errors.append('missing_relation_source_or_anchor')
        dependencies.append({'relation_index': i, 'endpoints': ends, 'source_ids': sorted(refs), 'label': r.get('label')})
        groups[('conflict:' if r.get('label') == 'CONFLICT' else 'relation:') + str(i)] = ends
    return {'passed': not errors, 'errors': sorted(set(errors)),
            'coverage_boundary': 'all_supplied_objects_only; semantic relevance and extraction completeness unverified',
            'input_candidates_truncated': original.get('candidates_truncated'),
            'semantic_correctness': 'not_evaluated',
            'original_counts': {'memories': len(memories), 'sources': len(sources), 'relations': len(relations)},
            'all_original_fields_reconstructed': 'roundtrip_field_mismatch' not in errors,
            'uncovered_dependencies': sorted(set(errors)),
            'dependencies': dependencies, 'protection_groups': dict(groups),
            'protected_fields': ['all_fields_including_unknowns', 'event_identity_not_inferred',
                                 'time', 'polarity', 'statement_type', 'source_ids', 'relations']}


def messages(representation):
    base = request_messages('resolve', {}, EffectiveResolution)
    return [{'role': 'system', 'content': base[0]['content'] + '\n' + GUIDANCE},
            {'role': 'user', 'content': json.dumps(representation, ensure_ascii=False)}]


@dataclass
class ResolutionPlan:
    planner_version: str
    config: dict
    original_sha256: str
    inventories: dict
    representation: dict
    representation_sha256: str
    preservation: dict
    estimated_input_tokens: int
    within_budget: bool
    status: str
    failure_reasons: list
    request_identity: str

    def to_dict(self):
        return asdict(self)


def plan(payload, *, input_budget=96000):
    if type(input_budget) is not int or input_budget < 1:
        raise ValueError('positive_input_budget_required')
    representation = encode(payload)
    restored = decode(representation)
    gate = preservation_gate(payload, restored)
    estimate = tokens(messages(representation))
    reasons = list(gate['errors'])
    if estimate > input_budget:
        reasons.append('complete_representation_over_budget')
    config = {'input_budget': input_budget, 'estimator': 'regex-word-punctuation-v1-not-provider',
              'prompt_version': PROMPT_VERSION, 'response_schema': digest(EffectiveResolution.model_json_schema())}
    inventories = {name: [{'id': r.get(key), 'sha256': digest(r)} for r in payload.get(name, [])]
                   for name, key in (('memories', 'memory_id'), ('sources', 'source_id'), ('relations', 'relation_id'))}
    identity = digest({'planner': VERSION, 'config': config, 'messages': messages(representation)})
    return ResolutionPlan(VERSION, config, digest(payload), inventories, representation, digest(representation),
                          gate, estimate, estimate <= input_budget,
                          'ready_for_mock' if not reasons else 'incomplete', reasons, identity)


def plan_opt_in(payload, *, enabled=False, input_budget=96000):
    """Disabled returns the original object; no global configuration or mutation."""
    return plan(payload, input_budget=input_budget) if enabled else payload


def execute_mock(original, resolution_plan, resolver):
    """Explicit offline contract: injected resolver must declare mock_only=True."""
    if getattr(resolver, 'mock_only', False) is not True:
        raise ValueError('mock_resolver_required')
    if digest(original) != resolution_plan.original_sha256:
        raise ValueError('original_identity_changed')
    if digest(resolution_plan.representation) != resolution_plan.representation_sha256:
        raise ValueError('representation_identity_changed')
    expected_identity = digest({'planner': VERSION, 'config': resolution_plan.config,
                                'messages': messages(resolution_plan.representation)})
    if expected_identity != resolution_plan.request_identity:
        raise ValueError('request_identity_changed')
    restored = decode(resolution_plan.representation)
    gate = preservation_gate(original, restored)
    fits = tokens(messages(resolution_plan.representation)) <= resolution_plan.config['input_budget']
    if not gate['passed'] or not fits or not resolution_plan.within_budget or resolution_plan.status != 'ready_for_mock':
        return {'status': 'incomplete', 'errors': gate['errors'] or resolution_plan.failure_reasons, 'calls': 0}
    result = resolver(messages(resolution_plan.representation), restored)
    return {'status': 'mock_completed', 'result': result, 'calls': 1, 'semantic_correctness': 'not_evaluated'}


class MockResolutionPlanner:
    """Python-only QueryService adapter. Live execution deliberately unavailable."""
    offline_mock_only = True

    def __init__(self, resolver):
        if getattr(resolver, 'mock_only', False) is not True:
            raise ValueError('mock_resolver_required')
        self.resolver = resolver

    def prepare(self, payload, *, input_budget):
        return plan(payload, input_budget=input_budget)

    def generate(self, payload, resolution_plan, *, context):
        outcome = execute_mock(payload, resolution_plan, self.resolver)
        if outcome['status'] != 'mock_completed':
            raise ValueError('incomplete_resolution_plan')
        value = EffectiveResolution.model_validate(outcome['result'], context=context)
        return Generation(value=value, metadata={'calls': [], 'execution_kind': 'offline_e6a_mock',
            'request_identity': resolution_plan.request_identity, 'physical_http': 0})
