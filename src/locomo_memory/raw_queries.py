"""One bounded raw fallback and joint resolution; never updates the memory store."""
import hashlib
import time
import re

from pydantic import ValidationError

from .builds import BuildError
from .imports import canonical_json
from .model import ModelFailure, request_token_estimate
from .query_schemas import EvidenceAnswer
from .raw_schemas import MixedResolution, RAW_RESOLUTION_VERSION, RAW_ANSWER_VERSION, ANSWER_BOUNDARY_VERSION
from .raw_retrieval import retrieve_sources, RAW_RETRIEVAL_VERSION
from .retrieval import budget_tokens, TOKEN_BUDGET_METHOD


def record_delivery(delivery, metadata, *, accepted, error_code=None):
    calls = metadata.get('calls', [])
    attempted = accepted or bool(calls)
    received = accepted or any(c.get('response_received') for c in calls)
    ids = delivery['expected_source_ids']
    delivery.update(attempted_source_ids=ids if attempted else [],
                    delivered_source_ids=ids if received else [],
                    status='accepted' if accepted else 'request_attempted' if attempted else 'not_sent',
                    provider_accepted=True if accepted else False if error_code=='context_length_exceeded' else None)


PACKING_VERSION = "core-source-distinct-items-v2"


def required_relation_labels(question):
    labels = {'CONFLICT', 'SUPERSEDE'}
    if re.search(r"\b(before|after|changed?|changes|history|stages|progress|previous|used to)\b", question, re.I):
        labels.add('UPDATE')
    return labels


def evidence_groups(memories, raw, relations, coverage, *, include_undetermined=False, question=""):
    """Only safety-critical relationships are indivisible, never a state_key."""
    nodes = [('raw',s['source_id']) for s in raw] + [('memory',m['memory_id']) for m in memories]
    parent = {n:n for n in nodes}

    def root(n):
        while parent[n] != n:
            n = parent[n]
        return n

    def link(group):
        present = [n for n in group if n in parent]
        for n in present[1:]:
            parent[root(n)] = root(present[0])

    required = required_relation_labels(question)
    for r in relations:
        if r['label'] in required or include_undetermined:
            link([('memory',r['old_memory_id']),('memory',r['new_memory_id'])])
    for item in coverage:
        if item['status'] == 'conflict':
            link([('memory', mid) for mid in item['memory_ids']] +
                 [('raw', sid) for sid in item['source_ids']])
    groups = {}
    for n in nodes:
        groups.setdefault(root(n), []).append(n)
    return list(groups.values())


def evidence_payload(base, memories, raw, sources):
    raw_ids = {s['source_id'] for s in raw}
    mids = {m['memory_id'] for m in memories}
    ids = sorted({sid for m in memories for sid in m['source_ids']} - raw_ids)
    payload = {**base, 'memories':memories, 'raw_sources':raw, 'sources':[sources[sid] for sid in ids]}
    if 'relations' in base:
        payload['relations'] = [r for r in base['relations'] if {r['old_memory_id'],r['new_memory_id']} <= mids]
        payload['incomplete_relations'] = [
            {'old_memory_id':r['old_memory_id'], 'new_memory_id':r['new_memory_id'], 'label':r['label'],
             'missing_memory_ids':sorted({r['old_memory_id'],r['new_memory_id']} - mids)}
            for r in base['relations']
            if r['label'] in ('UPDATE','CONFLICT','SUPERSEDE')
            and {r['old_memory_id'],r['new_memory_id']} & mids
            and not {r['old_memory_id'],r['new_memory_id']} <= mids]
    return payload


def pack_payload(base, memories, raw, sources, settings, *, final=False):
    operation, schema = ('answer_raw',EvidenceAnswer) if final else ('resolve_raw',MixedResolution)
    selected_m, selected_s, omitted = [], [], []
    empty = evidence_payload(base, [], [], sources)
    if request_token_estimate(operation, empty, schema) > settings.resolution_input_budget:
        raise BuildError('fixed_query_input_budget_exceeded', 422)
    by_memory, by_source = {m['memory_id']:m for m in memories}, {s['source_id']:s for s in raw}
    from .evidence_selection import rank_core_memories
    ordered = rank_core_memories(base.get('question',''), memories)
    coverage = base.get('previous_coverage', []) or base.get('coverage', [])
    groups = evidence_groups(ordered,raw,base.get('relations',[]),coverage,question=base.get('question',''))
    previous = base.get('previous_coverage', [])
    priority = previous or base.get('coverage', [])
    protected = {('memory', mid) for c in priority for mid in c['memory_ids']}
    protected |= {('raw', sid) for c in priority for sid in c['source_ids']}
    # Reserve prior support together before any optional new window or candidate.
    required = [g for g in groups if protected.intersection(g)]
    optional = [g for g in groups if not protected.intersection(g)]
    prior_ids = set(base.get('retained_memory_ids', []))
    required.sort(key=lambda g: not any(kind == 'memory' and mid in prior_ids for kind,mid in g))
    groups = ([sum(required, [])] if previous and required else required) + optional
    for group in groups:
        candidate_m = selected_m + [by_memory[n] for kind,n in group if kind=='memory']
        candidate_s = selected_s + [by_source[n] for kind,n in group if kind=='raw']
        payload = evidence_payload(base,candidate_m,candidate_s,sources)
        evidence_cost = budget_tokens(canonical_json({k:payload[k] for k in ('memories','sources','raw_sources')})) if candidate_m or candidate_s else 0
        if (request_token_estimate(operation,payload,schema) > settings.resolution_input_budget
                or (final and evidence_cost > settings.evidence_token_budget)):
            if previous and protected.intersection(group):
                raise BuildError('previous_evidence_budget_exceeded', 422)
            omitted.append({'endpoints':[list(n) for n in group], 'reason':'shared_evidence_budget' if final else 'resolution_input_budget'})
        else:
            selected_m,selected_s = candidate_m,candidate_s
    payload = evidence_payload(base,selected_m,selected_s,sources)
    return payload, {'packing_version':PACKING_VERSION, 'incomplete_relations':payload.get('incomplete_relations',[]), 'omitted_groups':omitted, 'truncated':bool(omitted),
        'input_token_count':request_token_estimate(operation,payload,schema), 'input_budget':settings.resolution_input_budget,
        'token_budget_method':TOKEN_BUDGET_METHOD}


def retrieval_limitations(audit):
    # Full ID lists remain in Trace; they are audit data, not evidence for the LLM.
    return {'truncated':audit['truncated'], 'omitted_window_count':len(audit['omitted']),
            'unselected_match_count':len(audit['unselected_match_ids'])}


def evidence_status(resolution):
    if resolution.status == 'insufficient' or any(c.status=='insufficient' for c in resolution.coverage):
        return 'insufficient'
    return 'conflict' if resolution.status=='conflict' or any(c.status=='conflict' for c in resolution.coverage) else 'sufficient'


def run_raw_query(service, request, trace, memories, sources, snapshot):
    settings = service.settings
    all_raw, snapshot_audit = snapshot
    from .evidence_selection import FOCUS_VERSION, focus_memories
    profile = request.evidence_profile
    trace['strategy'] = 'dynamic_raw_fallback'
    trace['evidence_selection'] = {'profile':profile, 'algorithm_version':FOCUS_VERSION,
                                  'retained_memory_ids':list(memories), 'omitted':[]}
    if profile == 'focused':
        grouped = evidence_groups(list(memories.values()),[],trace['relations'],[],include_undetermined=True)
        selected,trace['evidence_selection'] = focus_memories(request.question,list(memories.values()),sources,grouped)
        memories = {m['memory_id']:m for m in selected}

    trace['prompts'].update(resolve=RAW_RESOLUTION_VERSION,answer=RAW_ANSWER_VERSION)
    trace['schemas'].update(resolve=RAW_RESOLUTION_VERSION,answer=RAW_ANSWER_VERSION)
    trace['query_fingerprint'] = hashlib.sha256(canonical_json({'legacy_fingerprint':trace['query_fingerprint'],
        'raw_retrieval':RAW_RETRIEVAL_VERSION,'resolve_schema':MixedResolution.model_json_schema(),
        'source_snapshot':snapshot_audit,'strategy':trace['strategy'],
        'evidence_profile':profile,'selection_version':FOCUS_VERSION,
        'packing_version':PACKING_VERSION, 'answer_schema':EvidenceAnswer.model_json_schema(), 'answer_boundary_version':ANSWER_BOUNDARY_VERSION}).encode()).hexdigest()
    from .raw_schemas import RAW_RESOLUTION_PROMPT, RAW_ANSWER_PROMPT
    trace['query_fingerprint'] = hashlib.sha256(canonical_json({'fingerprint':trace['query_fingerprint'],
        'resolve_prompt':RAW_RESOLUTION_PROMPT,'answer_prompt':RAW_ANSWER_PROMPT}).encode()).hexdigest()
    trace['raw_fallback'] = {**snapshot_audit,'triggered':False,'source_ids':[], 'token_count':0}
    base = {'operation':'resolve_raw','question':request.question,'time':trace['time'],
            'analysis':{k:trace['initial']['analysis'][k] for k in ('status','result')}, 'relations':trace['relations'], 'evidence_profile':profile,
            'candidates_truncated':trace['initial']['initial_truncated'] or trace['expanded']['truncated']}

    def resolve(stage, raw, previous=None):
        trace['_active_stage'] = stage
        started = time.perf_counter()
        trace['_stage_started'] = started
        current_base = {**base, **({'previous_coverage':previous} if previous is not None else {})}
        if raw:
            current_base['raw_retrieval_limitations'] = retrieval_limitations(trace['raw_fallback'])
        try:
            payload,audit = pack_payload(current_base,list(memories.values()),raw,sources,settings)
        except BuildError as error:
            trace.setdefault('resolution_budgets',{})[stage] = {
                'packing_version':PACKING_VERSION, 'error_code':error.code,
                'source_delivery':{'expected_source_ids':[], 'attempted_source_ids':[],
                                   'delivered_source_ids':[], 'status':'not_sent'}}
            raise
        payload['candidates_truncated'] |= audit['truncated']
        mids = {m['memory_id']:m for m in payload['memories']}
        raw_map = {s['source_id']:s for s in payload['raw_sources']}
        delivered_sources = {s['source_id']:s for s in payload['sources'] + payload['raw_sources']}
        context = {'memories':mids,'sources':delivered_sources,'raw_sources':raw_map,
                   'previous_coverage':previous or [], 'required_relation_labels':required_relation_labels(request.question),
                   'incomplete_relations':payload.get('incomplete_relations',[]),
                   'input_budget':settings.resolution_input_budget}
        if previous is not None:
            audit['omitted_previous_evidence'] = [
                {'question':item['question'],
                 'memory_ids':[mid for mid in item['memory_ids'] if mid not in mids],
                 'source_ids':[sid for sid in item['source_ids'] if sid not in raw_map]}
                for item in previous
                if not set(item['memory_ids']) <= set(mids) or not set(item['source_ids']) <= set(raw_map)]
        delivery = {'expected_source_ids':list(delivered_sources), 'attempted_source_ids':[],
                    'delivered_source_ids':[], 'status':'not_sent'}
        audit['source_delivery'] = delivery
        trace.setdefault('resolution_budgets',{})[stage] = audit
        try:
            result = service.model.generate('resolve_raw',payload,MixedResolution,context=context)
        except ModelFailure as error:
            record_delivery(delivery, error.metadata, accepted=False, error_code=error.code)
            raise
        record_delivery(delivery, result.metadata, accepted=True)
        resolution = MixedResolution.model_validate(result.value.model_dump(mode='json'), context=context)
        trace['operations'][stage] = result.metadata
        trace.setdefault('resolution_budgets',{})[stage] = audit
        trace['stage_seconds'][stage] = time.perf_counter()-started
        return resolution, payload

    resolution, resolved_payload = resolve('resolve', [])
    trace['initial_resolution'] = resolution.model_dump(mode='json')
    if evidence_status(resolution)=='insufficient':
        gaps = [c.gap for c in resolution.coverage if c.status=='insufficient' and c.gap]
        raw,audit = retrieve_sources(all_raw,request.question,gaps,settings)
        trace['raw_fallback'].update(audit,triggered=True,trigger_reasons=gaps or ['overall_insufficient'])
        if raw:
            sources.update({s['source_id']:s for s in raw})
            previous_resolution, previous_payload = resolution, resolved_payload
            try:
                resolution,resolved_payload = resolve('joint_resolve',raw,[c.model_dump(mode='json') for c in resolution.coverage])
            except (ModelFailure, ValidationError, BuildError) as error:
                if not (previous_resolution.effective_memory_ids or previous_resolution.effective_source_ids):
                    raise
                code = error.code if hasattr(error, 'code') else 'invalid_output'
                if isinstance(error, ModelFailure):
                    trace['operations']['joint_resolve'] = error.metadata
                trace['stage_seconds']['joint_resolve'] = time.perf_counter() - trace['_stage_started']
                trace['raw_fallback']['recovery'] = {'code':code, 'action':'retain_prior_support',
                    'unassessed_source_ids':[s['source_id'] for s in raw]}
                # No invalid new judgment is accepted. Unassessed corrections may matter,
                # so retained facts are partial support, never a confident current state.
                resolution = previous_resolution.model_copy(deep=True)
                resolution.status = 'insufficient'
                for item in resolution.coverage:
                    item.status = 'insufficient'
                    item.gap = ((item.gap + '; ') if item.gap else '') + 'New raw evidence remains unassessed; prior support retained with uncertain applicability'
                resolution.explanation += '; supplemental raw evidence could not be safely assessed'
                resolved_payload = previous_payload
    trace['resolution'] = resolution.model_dump(mode='json')
    selected = [m for m in resolved_payload['memories'] if m['memory_id'] in resolution.effective_memory_ids]
    raw_selected = [s for s in resolved_payload['raw_sources'] if s['source_id'] in resolution.effective_source_ids]
    status = 'insufficient' if trace['time']['beyond_cutoff'] else evidence_status(resolution)
    coverage = [c.model_dump(mode='json') for c in resolution.coverage]
    answer_base = {'operation':'answer_raw','question':request.question,'time':trace['time'], 'status':status,
                   'coverage':coverage, 'evidence_profile':profile, 'relations':base['relations'] + [r.model_dump(mode='json') for r in resolution.supplemental_relations],
                   'resolution_explanation':resolution.explanation, 'evidence_truncated':False,
                   'retained_memory_ids':[mid for mid in trace['initial_resolution']['effective_memory_ids']
                                          if mid in resolution.effective_memory_ids]}
    selected_ids = {m['memory_id'] for m in selected}
    answer_base['relations'] = [r for r in answer_base['relations']
                               if {r['old_memory_id'],r['new_memory_id']} <= selected_ids]
    payload,audit = pack_payload(answer_base,selected,raw_selected,sources,settings,final=True)
    delivered_mids = {m['memory_id'] for m in payload['memories']}
    delivered_sids = {s['source_id'] for s in payload['raw_sources']}
    for item in coverage:
        if not set(item['memory_ids'])<=delivered_mids or not set(item['source_ids'])<=delivered_sids:
            item.update(status='insufficient', gap='Supporting evidence omitted by delivery budget',
                        memory_ids=[m for m in item['memory_ids'] if m in delivered_mids],
                        source_ids=[s for s in item['source_ids'] if s in delivered_sids])
            status = 'insufficient'
    if not (payload['memories'] or payload['raw_sources']):
        status = 'insufficient'
    payload.update(status=status,coverage=coverage,evidence_truncated=audit['truncated'])
    audit['input_token_count'] = request_token_estimate('answer_raw',payload,EvidenceAnswer)
    if audit['input_token_count'] > settings.resolution_input_budget:
        raise BuildError('final_query_input_budget_exceeded', 422)
    evidence = {k:payload[k] for k in ('memories','sources','raw_sources')}
    trace['evidence_budget'] = {**audit,'token_count':budget_tokens(canonical_json(evidence)) if payload['memories'] or payload['raw_sources'] else 0,
        'budget':settings.evidence_token_budget,'scope':'mixed_memory_raw_evidence'}
    trace['effective_memories'] = payload['memories']
    trace['answer_context_sources'] = list({s['source_id']:s for s in payload['sources']+payload['raw_sources']}.values())
    trace['delivered_coverage'] = coverage
    trace['raw_fallback']['delivered_source_ids'] = sorted(delivered_sids)
    trace['source_delivery'] = {'expected_source_ids':[s['source_id'] for s in trace['answer_context_sources']],
                              'attempted_source_ids':[], 'delivered_source_ids':[], 'status':'not_sent'}
    context = {'status':status,'memories':{m['memory_id']:m for m in payload['memories']},
               'raw_sources':{s['source_id']:s for s in payload['raw_sources']},'input_budget':settings.resolution_input_budget}
    trace['_active_stage'] = 'answer'
    started = time.perf_counter()
    trace['_stage_started'] = started
    try:
        result = service.model.generate('answer_raw',payload,EvidenceAnswer,context=context)
    except ModelFailure as error:
        record_delivery(trace['source_delivery'], error.metadata, accepted=False, error_code=error.code)
        if error.code == 'context_length_exceeded':
            trace['evidence_budget']['context_limit_exceeded'] = True
        raise
    trace['answer'] = EvidenceAnswer.model_validate(result.value.model_dump(mode='json'),context=context).model_dump(mode='json')
    if trace['time']['beyond_cutoff'] or trace['time']['origin']=='conversation_cutoff':
        scope = 'The requested date exceeds the known conversation cutoff' if trace['time']['beyond_cutoff'] else 'Known only as of the conversation cutoff'
        boundary = f"{scope} ({trace['time']['cutoff']}); later reality is unknown."
        trace['answer_boundary'] = {'version':ANSWER_BOUNDARY_VERSION, 'applied_by':'controller', 'text':boundary}
    trace['operations']['answer'] = result.metadata
    trace['stage_seconds']['answer'] = time.perf_counter()-started
    record_delivery(trace['source_delivery'], result.metadata, accepted=True)
    trace['raw_fallback']['effective_source_ids'] = resolution.effective_source_ids
    trace['raw_fallback']['cited_source_ids'] = sorted({sid for c in trace['answer']['citations'] if c['memory_id'] is None for sid in c['source_ids']})
    trace.pop('_active_stage',None)
    trace.pop('_stage_started',None)
