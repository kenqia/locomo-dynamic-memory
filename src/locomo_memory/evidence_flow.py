"""Observable evidence transitions; ID coverage never proves semantic support."""

EVIDENCE_FLOW_VERSION = 'memory-source-stage-flow-v1'


def evidence_flow(trace):
    initial = trace.get('initial', trace.get('retrieval', {})).get('initial_candidates')
    expanded = trace.get('expanded', trace.get('expansion', {})).get('candidates')
    initial = [item['memory'] for item in initial] if initial is not None else None
    expanded = [item['memory'] for item in expanded] if expanded is not None else None
    resolution = trace.get('resolution', {})
    selected = resolution.get('effective_memory_ids')
    effective = ([m for m in (expanded or []) if m['memory_id'] in selected]
                 if selected is not None else None)
    complete = trace.get('resolution_budgets', {}).get('resolve', {}).get('complete_memory_ids')
    resolver_input = ([m for m in (expanded or []) if m['memory_id'] in complete]
                      if complete is not None else None)
    # Hybrid uses answer_context_items; its effective set is explicitly not applicable.
    hybrid = trace.get('strategy') == 'hybrid_no_resolution' or resolution.get('status') == 'not_applied'
    delivered = trace.get('answer_context_items', trace.get('delivered_memories')) if hybrid else trace.get('effective_memories')

    def stage(memories):
        if memories is None:
            return None
        return dict(memory_ids=[m['memory_id'] for m in memories],
                    source_ids=list(dict.fromkeys(s for m in memories for s in m['source_ids'])))

    losses = []
    decisions = {d['memory_id']: d for d in resolution.get('decisions', [])}
    delivered_ids = {m['memory_id'] for m in delivered or []}
    omitted = set(trace.get('evidence_budget', {}).get('omitted_memory_ids', []))
    for memory in expanded or []:
        mid = memory['memory_id']
        decision = decisions.get(mid)
        if complete is not None and mid not in complete:
            location, kind, reason = 'resolve_input', 'resolution_input_omitted', 'not_in_recorded_resolution_input'
        elif decision and not decision['selected']:
            location, kind, reason = 'resolution', 'resolver_rejected', decision['reason']
        elif selected is not None and mid in selected and mid not in delivered_ids:
            location, kind, reason = 'answer', ('answer_budget' if mid in omitted else 'delivery_unobserved'), (
                'evidence_token_budget' if mid in omitted else 'no_recorded_delivery')
        else:
            continue
        losses.append(dict(memory_id=mid, source_ids=memory['source_ids'], stage=location, kind=kind, reason=reason))
    return dict(version=EVIDENCE_FLOW_VERSION, stages={name: stage(items) for name, items in (
        ('initial', initial), ('expanded', expanded), ('resolver_input', resolver_input),
        ('effective', effective), ('delivered', delivered))}, losses=losses,
        delivery_scope='recorded_answer_context; provider acceptance requires operation metadata',
        semantic_support='not_measured')
