"""Conservative question focus, preserving whole state/relationship components."""
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


PACKING_VERSION = 'original-question-whole-group-v1'


def rank_evidence_groups(question, memories, raw, sources, groups):
    """Order whole groups by their best lexical match, keeping stable ties.

    This only changes delivery priority. It does not filter candidates or decide
    whether evidence answers the question. Reuse English stemming and stop words.
    """
    stemmer = PorterStemmer()

    def terms(text):
        return {stemmer.stem(t) for t in tokenize(text) if t not in STOP_WORDS}

    names = set().union(*(terms(m['entity_id'].replace('_', ' ')) for m in memories))
    question_terms = terms(question)
    anchors = question_terms - names
    scores = {}
    for m in memories:
        text = ' '.join([m['content'], m['state_dimension'].replace('_', ' '), m.get('state_value') or '',
                         *[sources[sid]['text'] for sid in m['source_ids']]])
        scores[('memory', m['memory_id'])] = (len(anchors & terms(text)),
                                              len(question_terms & terms(m['entity_id'].replace('_', ' '))))
    for source in raw:
        scores[('raw', source['source_id'])] = (len(anchors & terms(source['text'])),
                                               len(question_terms & names & terms(source.get('speaker', ''))))
    return sorted(groups, key=lambda group: max(scores[n] for n in group), reverse=True)
