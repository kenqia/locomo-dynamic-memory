"""Question focus and distinct-item ordering before safety groups are packed."""
import re

from nltk.stem import PorterStemmer

from .retrieval import tokenize

FOCUS_VERSION = 'named-question-components-v2'
# Function words and temporal phrasing must not make unrelated facts look relevant.
STOP_WORDS = set('a an the and or to of in on at for from by with as is are was were be been being do does did has have had what which who where when how why can could would should will may might now current currently before after then today yesterday tomorrow date time'.split())


def focus_memories(question, memories, sources, groups):
    """Fall back to all candidates if the original question has no lexical anchor.

    Dates, inferred analysis and recency never exclude evidence. A match keeps every
    same-key and persisted-relation endpoint in its component, including undetermined.
    """
    stemmer = PorterStemmer()
    names = {t for m in memories for t in tokenize(m['entity_id'].replace('_', ' '))}

    def terms(text):
        return {stemmer.stem(t) for t in tokenize(text) if t not in STOP_WORDS and t not in names and not t.isdigit()}

    anchors = terms(question)
    direct = set()
    for m in memories:
        text = ' '.join([m['content'], m['state_dimension'].replace('_', ' '), m.get('state_value') or '',
                         *[sources[sid]['text'] for sid in m['source_ids']]])
        if anchors & terms(text):
            direct.add(m['memory_id'])
    question_tokens = tokenize(question)
    named_entities = {m['entity_id'] for m in memories
        if re.search(r'(?<![a-z0-9])' + re.escape(m['entity_id'].replace('_',' ').replace('-',' ').lower())
                     + r'(?![a-z0-9])', question.lower())}
    named_ids = {m['memory_id'] for m in memories if m['entity_id'] in named_entities}
    # Partial lexical coverage cannot establish that every subquestion is covered.
    compound = bool(re.search(r'\b(and|or|also)\b|;', question, re.I)) or question.count('?') > 1
    indirect = bool(set(question_tokens) & set('who whose he she they his her their them spouse wife husband partner friend parent child sibling mother father son daughter brother sister'.split()))
    fallback_reason = ('compound_or_indirect_question' if compound or indirect else
                       'ambiguous_named_entity' if len(named_entities) != 1 else
                       'no_reliable_original_question_anchor' if not direct.intersection(named_ids) else None)
    keep = set()
    for group in groups:
        ids = {identity for kind,identity in group if kind == 'memory'}
        if ids & (direct | named_ids):
            keep.update(ids)
    fallback = fallback_reason is not None
    if fallback:
        keep = {m['memory_id'] for m in memories}
    selected = [m for m in memories if m['memory_id'] in keep]
    return selected, {'algorithm_version':FOCUS_VERSION, 'profile':'focused', 'fallback_to_expanded':fallback, 'fallback_reason':fallback_reason,
        'retained':[{'memory_id':m['memory_id'], 'reason':fallback_reason if fallback else
                     'direct_original_question_match' if m['memory_id'] in direct else 'named_entity_or_connected_history'} for m in selected],
        'omitted':[{'memory_id':m['memory_id'],'reason':'no_original_question_match_or_connected_history'}
                   for m in memories if m['memory_id'] not in keep]}


def rank_core_memories(question, memories):
    """Original-question lexical focus; existing hybrid/expansion order breaks ties.

    Score atomic claims, not whole relation components or long source windows.
    Stemming connects research/researching without another model call.
    """
    stemmer = PorterStemmer()
    names = {t for m in memories for t in tokenize(m['entity_id'].replace('_', ' '))}
    def terms(text):
        return {stemmer.stem(t) for t in tokenize(text)
                if t not in STOP_WORDS and t not in names and not t.isdigit()}
    anchors = terms(question)
    question_tokens = {t.removesuffix("'s") for t in tokenize(question)}

    # Broad list nouns rarely occur in individual facts. Expand intent verbs and
    # dimensions, never answer items; use the existing retrieval order for ties.
    multi_item = bool(question_tokens & {'activities', 'events', 'instruments', 'locations', 'places', 'hobbies'})
    if question_tokens & {'activities', 'hobbies'}:
        anchors |= terms('hobby activity play enjoy practice')
    if 'events' in question_tokens:
        anchors |= terms('attend attendance participate join visit volunteer event')

    def relevance(memory):
        text = memory['content'] + ' ' + memory['state_dimension'].replace('_', ' ')
        overlap = len(anchors & terms(text))
        named = any(t in question_tokens for t in tokenize(memory['entity_id'].replace('_', ' ')))
        return named, overlap
    if not multi_item:
        return sorted(memories, key=relevance, reverse=True)
    pending = list(memories)
    ordered, seen_terms, dimensions = [], [], {}
    participation = 'events' in question_tokens and bool(question_tokens & {'participated', 'attended', 'joined'})
    asks_plans = bool(question_tokens & {'plans', 'planned', 'planning', 'will', 'future'})
    while pending:
        def coverage_score(memory):
            named, overlap = relevance(memory)
            dimension = memory['state_dimension']
            claim = terms(memory.get('state_value') or memory['content'])
            similarity = max((len(claim & old) / max(1, len(claim | old)) for old in seen_terms), default=0)
            # Saturate lexical overlap so repeated generic words cannot dominate
            # distinct supported categories; safety groups are constructed later.
            fact = memory.get('statement_type', 'fact') == 'fact' or asks_plans
            direct = bool(re.search(r'\b(went|joined|attended|participated|volunteered|spoke)\b', memory['content'], re.I))
            return named, bool(overlap), fact, direct if participation else False, 1 / (1 + dimensions.get(dimension, 0)) - similarity
        chosen = max(pending, key=coverage_score)
        pending.remove(chosen)
        ordered.append(chosen)
        seen_terms.append(terms(chosen.get('state_value') or chosen['content']))
        dimension = chosen['state_dimension']
        dimensions[dimension] = dimensions.get(dimension, 0) + 1
    return ordered
