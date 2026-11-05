"""Read-only, bounded graph views of a validated immutable MemoryExport."""
from collections import deque
from datetime import date

from .export_schemas import MemoryExport
from .imports import canonical_json
from .retrieval import budget_tokens


def graph_view(bundle: MemoryExport) -> dict:
    """Structural edges assert membership only; relation edges retain provenance."""
    nodes, edges = {}, []
    statuses = {item.memory_id: item.status for group in (
        bundle.projection.current_states, bundle.projection.historical_states,
        bundle.projection.events, bundle.projection.nonfactual) for item in group}
    conflicts = {mid for c in bundle.projection.conflicts for mid in c.memory_ids}
    for memory in bundle.memories:
        mid = memory.memory_id
        eid = 'entity:' + memory.entity_id
        nodes[eid] = dict(id=eid, kind='Entity', label=memory.entity_id)
        nodes[mid] = dict(id=mid, kind='Memory', label=memory.content,
                          status='conflict' if mid in conflicts else statuses[mid],
                          memory=memory.model_dump(mode='json'))
        edges.append(dict(source=eid, target=mid, type='HAS_MEMORY',
                          basis='Memory.entity_id; structural membership only', source_ids=memory.source_ids))
        for sid in memory.source_ids:
            edges.append(dict(source=mid, target=sid, type='SUPPORTED_BY',
                              basis='Memory.source_ids; stored attribution, not independent verification', source_ids=[sid]))
    for source in bundle.sources:
        nodes[source.source_id] = dict(id=source.source_id, kind='Source Turn',
            label=f'{source.speaker} / {source.dia_id}', source=source.model_dump(mode='json'))
    for relation in bundle.relations:
        edges.append(dict(source=relation.old_memory_id, target=relation.new_memory_id,
            type=relation.label, relation_id=relation.relation_id, basis=relation.reason,
            source_ids=relation.source_ids, applicability=relation.applicability.model_dump(mode='json')))
    return dict(schema_version='m5-graph-v1', build_id=bundle.build.build_id,
                nodes=list(nodes.values()), edges=edges)


def neighborhood(bundle: MemoryExport, roots: list[str], *, depth: int = 1,
                 at: date | None = None, max_nodes: int = 150) -> dict:
    if not 0 <= depth <= 2 or not 1 <= max_nodes <= 500:
        raise ValueError('graph_bounds_required')
    graph = graph_view(bundle)
    nodes = {node['id']: node for node in graph['nodes']}
    if not set(roots) <= nodes.keys() or len(set(roots)) > max_nodes:
        raise ValueError('graph_roots_out_of_scope')
    adjacency = {node: [] for node in nodes}
    for edge in graph['edges']:
        adjacency[edge['source']].append(edge['target'])
        adjacency[edge['target']].append(edge['source'])
    selected = set(roots)
    queue = deque((root, 0) for root in sorted(selected))
    truncated = False
    while queue:
        node, level = queue.popleft()
        if level == depth:
            continue
        for other in sorted(adjacency[node]):
            if other in selected:
                continue
            memory = nodes[other].get('memory')
            # Filter only explicit validity, preserving unknown dates. Event dates
            # do not establish a state's validity interval.
            if at and memory:
                timing = memory['time']
                if ((timing.get('valid_from') and str(at) < timing['valid_from']) or
                        (timing.get('valid_to') and str(at) > timing['valid_to'])):
                    continue
            if len(selected) == max_nodes:
                truncated = True
                continue
            selected.add(other)
            queue.append((other, level + 1))
    return {**graph, 'nodes': [nodes[key] for key in sorted(selected)],
            'edges': [edge for edge in graph['edges'] if {edge['source'], edge['target']} <= selected],
            'truncated': truncated, 'at': str(at) if at else None}


def expand_relations(bundle: MemoryExport, initial_ids: list[str], *, depth: int = 0,
                     max_candidates: int = 60, token_budget: int = 12000) -> dict:
    """BFS over stored MemoryRelation edges only, without any semantic inference.

    Undetermined edges are retained for browsing but do not expand retrieval.
    The budget counts complete serialized Memory objects, not their short labels.
    Seeds must fit: this interface never silently discards the original retrieval.
    """
    if not 0 <= depth <= 3 or not 1 <= max_candidates <= 500 or token_budget < 1:
        raise ValueError('graph_bounds_required')
    memories = {m.memory_id: m.model_dump(mode='json') for m in bundle.memories}
    if len(set(initial_ids)) != len(initial_ids) or not set(initial_ids) <= memories.keys():
        raise ValueError('graph_seeds_out_of_scope')
    selected = list(initial_ids)
    def cost(ids):
        return budget_tokens(canonical_json([memories[mid] for mid in ids]))
    if len(selected) > max_candidates or cost(selected) > token_budget:
        raise ValueError('graph_initial_budget_exceeded')
    adjacency = {mid: [] for mid in memories}
    for relation in sorted(bundle.relations, key=lambda r: r.relation_id):
        if relation.label == 'undetermined':
            continue
        for start, end in ((relation.old_memory_id, relation.new_memory_id),
                           (relation.new_memory_id, relation.old_memory_id)):
            adjacency[start].append((end, relation))
    paths = {mid: [] for mid in selected}
    queue = deque((mid, 0) for mid in selected)
    omitted = set()
    while queue:
        mid, level = queue.popleft()
        if level == depth:
            continue
        for other, relation in adjacency[mid]:
            if other in paths or other in omitted:
                continue
            if len(selected) == max_candidates or cost(selected + [other]) > token_budget:
                omitted.add(other)
                continue
            selected.append(other)
            paths[other] = paths[mid] + [dict(from_memory_id=mid, to_memory_id=other,
                relation_id=relation.relation_id, label=relation.label, source_ids=relation.source_ids,
                applicability=relation.applicability.model_dump(mode='json'))]
            queue.append((other, level + 1))
    return dict(build_id=bundle.build.build_id, memory_ids=selected, paths=paths,
        memories=[memories[mid] for mid in selected], omitted_ids=sorted(omitted),
        token_count=cost(selected), token_budget=token_budget, depth=depth,
        token_budget_method='regex-word-punctuation-v1-complete-memory-json',
        semantic_warning='Graph connectivity does not establish query-specific applicability or truth.')
