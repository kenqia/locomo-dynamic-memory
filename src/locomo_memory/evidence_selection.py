"""Conservative question focus, preserving whole state/relationship components."""
from nltk.stem import PorterStemmer

from .retrieval import tokenize

FOCUS_VERSION = 'original-question-components-v1'
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
    keep = set()
    for group in groups:
        ids = {identity for kind,identity in group if kind == 'memory'}
        if ids & direct:
            keep.update(ids)
    fallback = not direct
    if fallback:
        keep = {m['memory_id'] for m in memories}
    selected = [m for m in memories if m['memory_id'] in keep]
    return selected, {'algorithm_version':FOCUS_VERSION, 'profile':'focused', 'fallback_to_expanded':fallback,
        'retained':[{'memory_id':m['memory_id'], 'reason':'no_reliable_original_question_anchor' if fallback else
                     'direct_original_question_match' if m['memory_id'] in direct else 'same_state_or_relation_component'} for m in selected],
        'omitted':[{'memory_id':m['memory_id'],'reason':'no_original_question_match_or_connected_history'}
                   for m in memories if m['memory_id'] not in keep]}
