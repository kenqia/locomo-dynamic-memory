from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

from locomo_memory.api import create_app
from locomo_memory.export_schemas import MemoryExport
from locomo_memory.m5_graph import graph_view, neighborhood, expand_relations
from locomo_memory.m5_compression import pack, expand
from test_retrieval import ControlledEmbedder
from test_versions import complete, model


@pytest.fixture
def bundle(settings, sample):
    with TestClient(create_app(settings, model=model(settings), embedder=ControlledEmbedder())) as client:
        build_id = complete(client, sample)
        yield MemoryExport.model_validate(client.get(f'/builds/{build_id}/export').json())


def test_graph_structural_edges_and_sources(bundle):
    graph = graph_view(bundle)
    assert {n['kind'] for n in graph['nodes']} == {'Entity', 'Memory', 'Source Turn'}
    assert {e['type'] for e in graph['edges']} >= {'HAS_MEMORY', 'SUPPORTED_BY', 'undetermined'}
    assert all(e['source_ids'] and e['basis'] for e in graph['edges'])
    view = neighborhood(bundle, ['entity:Alex'], depth=2)
    assert any(n['kind'] == 'Source Turn' for n in view['nodes'])
    assert len(neighborhood(bundle, ['entity:Alex'], depth=0)['nodes']) == 1


def test_graph_disabled_identity_and_scope(bundle):
    seeds = [bundle.memories[0].memory_id]
    assert expand_relations(bundle, seeds)['memory_ids'] == seeds
    assert expand_relations(bundle, seeds, depth=2)['memory_ids'] == seeds  # undetermined is not inference
    for kwargs in ({'depth': 4}, {'token_budget': 1}, {'max_candidates': 0}):
        with pytest.raises(ValueError):
            expand_relations(bundle, seeds, **kwargs)
    with pytest.raises(ValueError):
        expand_relations(bundle, ['other-build/memory'])
    with pytest.raises(ValueError):
        neighborhood(bundle, ['other-build/entity'])


def test_graph_exact_path_and_budget(bundle):
    # Explicit synthetic relation, not a claim about the original corpus.
    relation = bundle.relations[0].model_copy(update={'label': 'CONFLICT'})
    fixture = bundle.model_copy(update={'relations': [relation]})
    old, new = relation.old_memory_id, relation.new_memory_id
    result = expand_relations(fixture, [old], depth=1)
    assert result['memory_ids'] == [old, new]
    assert result['paths'][new][0]['relation_id'] == relation.relation_id
    capped = expand_relations(fixture, [old], depth=1, max_candidates=1)
    assert capped['memory_ids'] == [old] and capped['omitted_ids'] == [new]
    assert result['token_count'] <= result['token_budget']


def test_graph_two_hops_cycle_and_disconnected_node(bundle):
    # Synthetic graph fixture with three evidence-backed endpoints; no model claim.
    old, middle = bundle.memories
    third = middle.model_copy(update={'memory_id': 'synthetic-third'})
    isolated = middle.model_copy(update={'memory_id': 'synthetic-isolated'})
    first = bundle.relations[0].model_copy(update={'old_memory_id': old.memory_id,
        'new_memory_id': middle.memory_id, 'label': 'RETAIN', 'relation_id': 'r1'})
    second = first.model_copy(update={'old_memory_id': middle.memory_id,
        'new_memory_id': third.memory_id, 'relation_id': 'r2'})
    cycle = first.model_copy(update={'old_memory_id': third.memory_id,
        'new_memory_id': old.memory_id, 'relation_id': 'r3', 'label': 'undetermined'})
    fixture = bundle.model_copy(update={'memories': [old, middle, third, isolated],
                                       'relations': [first, second, cycle]})
    one = expand_relations(fixture, [old.memory_id], depth=1)
    two = expand_relations(fixture, [old.memory_id], depth=2)
    assert third.memory_id not in one['memory_ids']
    assert two['memory_ids'] == [old.memory_id, middle.memory_id, third.memory_id]
    assert [p['relation_id'] for p in two['paths'][third.memory_id]] == ['r1', 'r2']
    assert isolated.memory_id not in two['memory_ids']


def test_compression_roundtrip_preserves_every_field_and_order(bundle):
    memories = [m.model_dump(mode='json') for m in bundle.memories]
    frozen = deepcopy(memories)
    packed = pack(memories)
    assert expand(packed['package']) == memories == frozen
    assert packed['metrics']['memory_coverage'] == 1
    assert packed['metrics']['atomic_fact_retention'] == 'not_measured'
    assert expand(pack([])['package']) == []


@pytest.mark.parametrize('mutation', ['content', 'order', 'shared'])
def test_compression_tampering_rejected(bundle, mutation):
    package = pack([m.model_dump(mode='json') for m in bundle.memories])['package']
    if mutation == 'content':
        package['groups'][0]['members'][0]['content'] = 'Changed person or fact'
    elif mutation == 'order':
        package['order'] = []
    else:
        package['groups'][0]['members'][0]['entity_id'] = 'SomeoneElse'
    with pytest.raises(ValueError):
        expand(package)


def test_compression_scope_rejected(bundle):
    memories = [m.model_dump(mode='json') for m in bundle.memories]
    memories[1]['build_id'] = 'another-build'
    with pytest.raises(ValueError):
        pack(memories)
