"""E1 opt-in deterministic routing. No scorer, labels, answers or provider imports.

The gate establishes narrow lexical support eligibility, never semantic truth.
Independent source review remains mandatory before adopting this research policy.
"""
from dataclasses import asdict, dataclass
import hashlib
import json
import re
import time

VERSION = 'e1-source-gated-router-v1'
STOP = set('a an the is are was were be been being do does did has have had of to in on at for from with and or by it its his her their what which where who when how why s'.split())
SLOTS = {
    'live': ('live','lives','living','residence','resides','moved'),
    'work': ('work','works','working','job','occupation','employment','profession'),
    'name': ('name','named','called'),
    'favorite': ('favorite','favourite','prefer','prefers'),
    'study': ('study','studies','studied','education','degree','major'),
    'pet': ('pet','pets','dog','dogs','cat','cats','turtle','turtles'),
}
TEMPORAL = re.compile(r'\b(before|after|as of|used to|previous|previously|formerly|currently|latest|now|last|ago|since|until|during|when|change|changed|became|still)\b|\b(?:19|20)\d{2}\b',re.I)
COMPLEX = re.compile(r'\b(why|how|all|both|compare|relationship|different|conflict|instead|plan|plans|planned|hope|hopes|would|will)\b',re.I)


def terms(text):
    return set(re.findall(r'[a-z0-9]+',text.lower()))


def fingerprint(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()


@dataclass(frozen=True)
class RoutingDecision:
    path: str
    reason_codes: tuple[str,...]
    observed_features: dict
    uncertainty: str
    estimated_extra_cost: dict
    router_version: str = VERSION

    def to_dict(self):
        return asdict(self)


def observe(question, initial, sources, relations=(), time_condition=None):
    """Project an explicit pre-generation allowlist; extra Trace fields are ignored.

    Sources are the original texts attached to initial candidates; stored relations
    exist at Build time. A relation label is observed metadata, not a proven fact.
    """
    candidates=(initial or {}).get('initial_candidates') or []
    analysis=((initial or {}).get('analysis') or {})
    parsed=analysis.get('result') or {}
    question_terms=terms(question)-STOP
    slots={key for key,aliases in SLOTS.items() if question_terms & set(aliases)}
    entities=parsed.get('entities') or []
    scope={(c['memory']['build_id'],c['memory']['sample_id']) for c in candidates}
    eligible=[];relevant=[];missing_sources=0
    for c in candidates:
        m=c['memory'];entity=terms(m['entity_id'].replace('_',' '))
        if not entity or not entity<=terms(question):continue
        slot_aliases={alias for key in slots for alias in SLOTS[key]}
        if not (terms(m['state_dimension'].replace('_',' ')) | terms(m['content'])) & slot_aliases:continue
        relevant.append(m)
        if m.get('statement_type')!='fact' or m.get('polarity')!='positive' or not m.get('state_value'):continue
        value=m['state_value'].casefold();supported=[]
        for sid in m.get('source_ids',[]):
            s=sources.get(sid)
            if s is None:missing_sources+=1;continue
            if s.get('sample_id',m['sample_id'])!=m['sample_id']:continue
            for sentence in re.split(r'(?<=[.!?])\s+',s['text']):
                # A mention in a question is never an assertion. Exact state value
                # and slot predicate must occur in the same source sentence.
                if '?' in sentence or not re.search(r'(?<!\w)'+re.escape(value)+r'(?!\w)',sentence,re.I):continue
                speaker_bound=terms(s.get('speaker',''))==entity and bool(re.search(r'\b(I|my|we|our)\b',sentence,re.I))
                named_bound=bool(re.match(r'^'+re.escape(m['entity_id'].replace('_',' '))+r"(?:\b|'s)",sentence,re.I))
                if not (speaker_bound or named_bound):continue
                if not terms(sentence)&slot_aliases:continue
                if re.search(r"\b(not|never|no|might|maybe|hope|plan|want|wish|if|unless|would|could|but|and)\b|n['’]t\b",sentence,re.I):continue
                supported.append(dict(source_id=sid,source_sha256=hashlib.sha256(s['text'].encode()).hexdigest(),
                    sentence_sha256=hashlib.sha256(sentence.encode()).hexdigest()))
        if supported:
            content_terms=(terms(m['content']) | set().union(*(terms(sources[s['source_id']]['text']) for s in supported)))
            coverage=len(question_terms & content_terms)/len(question_terms) if question_terms else 0
            eligible.append(dict(memory_id=m['memory_id'],support=supported,lexical_coverage=coverage))
    relevant_ids={m['memory_id'] for m in relevant}
    state_values={m.get('state_value') for m in relevant if m.get('state_value')}
    edges=[r for r in relations if {r['old_memory_id'],r['new_memory_id']} & relevant_ids]
    linked_changes=[r for r in edges if r.get('label') in ('UPDATE','SUPERSEDE','CONFLICT')]
    time_condition=time_condition or {}
    feature=dict(question_sha256=hashlib.sha256(question.encode()).hexdigest(),
        initial_fingerprint=fingerprint({k:initial.get(k) for k in
            ('build_id','index_fingerprint','question','initial_candidates','channels') } | {
                'analysis':{'status':analysis.get('status'),'result':{k:parsed.get(k) for k in ('entities','topic','time','keywords')}}}) if initial else None,
        source_scope_fingerprint=fingerprint([
            (sid,hashlib.sha256(sources[sid]['text'].encode()).hexdigest())
            for sid in sorted({sid for c in candidates for sid in c['memory']['source_ids']}) if sid in sources]),
        candidate_count=len(candidates),single_build_scope=len(scope)==1,analysis_available=analysis.get('status')=='succeeded',
        analysis_entities=entities,analysis_has_time=bool(parsed.get('time')),
        explicit_date=bool(time_condition.get('requested_date')),beyond_cutoff=bool(time_condition.get('beyond_cutoff')),
        temporal_query=bool(TEMPORAL.search(question)),complex_query=bool(COMPLEX.search(question)),
        requested_slots=sorted(slots),relevant_count=len(relevant),distinct_relevant_values=len(state_values),
        missing_sources=missing_sources,eligible_claims=eligible,
        best_lexical_coverage=max((e['lexical_coverage'] for e in eligible),default=0),
        observed_change_relation_ids=[r.get('relation_id') for r in linked_changes],
        observed_conflict=any(r.get('label')=='CONFLICT' for r in linked_changes),
        relation_warning='Stored relation labels are fallible; same state_key alone never implies conflict.',
        sufficiency_scope='Exact source value + predicate + speaker/subject; lexical eligibility only. Not semantic verification.')
    return feature


class QueryComplexityRouter:
    def __init__(self, coverage_threshold=.75):
        if coverage_threshold not in (.5,.75,1.):raise ValueError('Unregistered threshold')
        self.coverage_threshold=coverage_threshold

    def route(self, *, question, initial, sources, relations=(), time_condition=None, complete_budget=None):
        start=time.perf_counter();cpu=time.process_time()
        features=observe(question,initial,sources,relations,time_condition)
        reasons=[]
        for key,reason in [('temporal_query','temporal_scope'),('explicit_date','explicit_cutoff'),
                           ('analysis_has_time','analysis_time'),('beyond_cutoff','future_scope'),
                           ('complex_query','multi_part_or_event_or_plan'),('observed_conflict','stored_conflict_signal')]:
            if features[key]:reasons.append(reason)
        if features['observed_change_relation_ids']:reasons.append('stored_state_evolution_signal')
        if not features['analysis_available']:reasons.append('analysis_unavailable')
        if not features['single_build_scope']:reasons.append('scope_not_established')
        if not features['requested_slots']:reasons.append('requested_predicate_not_recognized')
        if features['distinct_relevant_values']!=1:reasons.append('value_ambiguity_or_missing')
        if features['missing_sources'] or not features['eligible_claims']:reasons.append('evidence_sufficiency_gate_failed')
        if features['best_lexical_coverage']<self.coverage_threshold:reasons.append('lexical_support_below_threshold')
        features['coverage_threshold']=self.coverage_threshold
        # Optional exact preflight is computed locally after expansion and before
        # any Resolution HTTP. It never reads a Resolution result or failure.
        features['dynamic_complete_input_budget']=complete_budget
        path='dynamic' if reasons else 'hybrid'
        if complete_budget is not None and not complete_budget['within_budget']:
            reasons.append('dynamic_complete_input_budget_risk')
        if not reasons:reasons=['source_sufficiency_gate_eligible']
        return RoutingDecision(path=path,reason_codes=tuple(reasons),observed_features=features,
            uncertainty='high' if path=='dynamic' else 'uncalibrated_source_eligibility',
            estimated_extra_cost=dict(router_cpu_seconds=time.process_time()-cpu,
                router_wall_seconds=time.perf_counter()-start,provider_calls=0,
                incremental_provider_cny=0,selected_path_provider_cny=None,
                note='Analysis/retrieval/expansion and preflight are charged separately; downstream billing unknown.'))


def query_opt_in(service, request, *, enabled=False, coverage_threshold=.75):
    """Research Python entry. Off returns ordinary Dynamic with no Router field."""
    if request.strategy!='dynamic':raise ValueError('E1 supports ordinary Dynamic only')
    if not enabled:return service.query(request)
    return service.query(request,research_router=QueryComplexityRouter(coverage_threshold))
