"""Compare acceptance with main, preserving scope, polarity and temporal rules.

Uses synthetic cases only. This is contract compatibility, not semantic evaluation.
"""
from copy import deepcopy
from itertools import product
import json
from pathlib import Path
import subprocess
import sys
from types import ModuleType

from pydantic import ValidationError
from locomo_memory.query_schemas import EvidenceAnswer, EffectiveResolution
from locomo_memory.memory_schemas import MemoryDraft

ROOT = Path(__file__).resolve().parents[2]
BASE = 'f5a5dfdec5235d1c411cb5d4b525467e40fef415'


def frozen_module(filename):
    name = 'locomo_memory._integration_baseline_' + filename
    module = ModuleType(name)
    module.__package__ = 'locomo_memory'
    sys.modules[name] = module
    source = subprocess.check_output(['git', 'show', BASE + ':src/locomo_memory/' + filename + '.py'], cwd=ROOT, text=True)
    exec(compile(source, name, 'exec'), module.__dict__)
    return module


def outcome(schema, value, context):
    try:
        return schema.model_validate(deepcopy(value), context=deepcopy(context)).model_dump(mode='json')
    except ValidationError:
        return None


def run():
    old_query = frozen_module('query_schemas')
    old_memory = frozen_module('memory_schemas')
    assert old_query.EvidenceAnswer.model_json_schema() == EvidenceAnswer.model_json_schema()
    assert old_memory.MemoryDraft.model_json_schema() == MemoryDraft.model_json_schema()
    contexts = [None]
    for status, raw in product(('sufficient', 'conflict', 'insufficient'), (None, {}, {'s1': {}, 's2': {}})):
        context = dict(status=status, memories={'m1': {'source_ids': ['s1']}, 'm2': {'source_ids': ['s2']}})
        if raw is not None:
            context['raw_sources'] = raw
        contexts.append(context)
    citations = [[], [{'memory_id': 'm1', 'source_ids': ['s1']}],
                 [{'memory_id': 'm1', 'source_ids': ['s2']}],
                 [{'memory_id': 'm1', 'source_ids': ['s1', 's1']}],
                 [{'memory_id': 'foreign', 'source_ids': ['s1']}],
                 [{'memory_id': None, 'source_ids': ['s1']}],
                 [{'memory_id': 'm1', 'source_ids': ['s1']}, {'memory_id': 'm2', 'source_ids': ['s2']}],
                 [{'memory_id': None, 'source_ids': ['s1']}, {'memory_id': None, 'source_ids': ['s2']}]]
    counts = {'answers': 0, 'extractions': 0, 'resolutions': 0}
    for context, status, text, refs in product(contexts, ('sufficient', 'conflict', 'insufficient'), ('Synthetic.', ' ', '', 12), citations):
        value = dict(status=status, answer=text, citations=refs)
        assert outcome(old_query.EvidenceAnswer, value, context) == outcome(EvidenceAnswer, value, context)
        counts['answers'] += 1
    sources = {'s1': {'text': 'I did not move yesterday.'}, 's2': {'text': 'Tomorrow I plan to move.'}}
    for statement, polarity, ids, anchor, expression, start in product(
            ('fact', 'plan', 'intention', 'uncertain'), ('positive', 'negative'),
            (['s1'], ['s2'], ['s1', 's2'], ['foreign']), (None, 's1', 's2'),
            (None, 'yesterday', 'Tomorrow', 'invented'), (None, '2023-01-01')):
        value = dict(content='Synthetic source claim.', memory_type='event', statement_type=statement,
                     polarity=polarity, entity_id='Alex', state_dimension='residence', source_ids=ids,
                     time=dict(anchor_source_id=anchor, original_expression=expression, event_start=start))
        assert outcome(old_memory.MemoryDraft, value, {'sources': sources}) == outcome(MemoryDraft, value, {'sources': sources})
        counts['extractions'] += 1
    context = dict(memories={'m1': {}, 'm2': {}}, sources={})
    for status, ids, selected, reason in product(('sufficient', 'conflict', 'insufficient'),
            ([], ['m1'], ['m1', 'm2'], ['m1', 'm1'], ['foreign']),
            (False, True), ('Evidence.', ' ')):
        value = dict(status=status, effective_memory_ids=ids,
                     decisions=[dict(memory_id=mid, selected=selected, reason=reason) for mid in ('m1', 'm2')],
                     explanation='Scope.')
        assert outcome(old_query.EffectiveResolution, value, context) == outcome(EffectiveResolution, value, context)
        counts['resolutions'] += 1
    return dict(baseline_commit=BASE, synthetic_cases=counts, changed_legacy_outcomes=0,
                new_incomplete_relation_guard='Covered separately by test_dynamic_resolution_budget.py',
                semantic_gain_established=False, live_calls=0)


if __name__ == '__main__':
    print(json.dumps(run(), ensure_ascii=False, indent=2))
