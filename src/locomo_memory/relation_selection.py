"""Bounded comparison candidates. Ranking does not establish a memory relation."""
import math

from rank_bm25 import BM25Okapi

SELECTION_VERSION = "same-key-factual-and-cross-key-v1"


def select_history(new, previous, settings):
    from .retrieval import tokenize

    cap = settings.relation_history_limit
    same_quota = max(1, int(cap * settings.relation_same_key_fraction))
    cross_quota = cap - same_quota
    entity_terms = set(tokenize(new["entity_id"]))

    def terms(memory):
        return [t for t in tokenize(memory["content"] + " " + (memory["state_value"] or "")) if t not in entity_terms]

    corpus = [terms(m) for m in previous]
    scores = BM25Okapi(corpus).get_scores(terms(new)) if any(corpus) else [0.0] * len(previous)
    by_id = {m["memory_id"]: (float(scores[i]), i) for i, m in enumerate(previous)}

    def rank(items):
        return sorted(items, key=lambda m: (-by_id[m["memory_id"]][0], -by_id[m["memory_id"]][1], m["memory_id"]))

    same = rank([m for m in previous if m["state_key"] == new["state_key"]])
    cross = rank([m for m in previous if m["state_key"] != new["state_key"]])
    same_count = min(len(same), same_quota + max(0, cross_quota - len(cross)))
    cross_count = min(len(cross), cap - same_count)
    facts = [m for m in same if m["memory_type"] == "state" and m["statement_type"] == "fact"]
    protected = facts[:min(same_count, math.ceil(same_quota * settings.relation_fact_fraction))]
    protected_ids = {m["memory_id"] for m in protected}
    selected = protected + [m for m in same if m["memory_id"] not in protected_ids][:same_count - len(protected)]
    selected += cross[:cross_count]
    audit = {"algorithm_version": SELECTION_VERSION, "input_count": len(previous),
             "same_key_quota": same_quota, "cross_key_quota": cross_quota,
             "same_key_available": len(same), "cross_key_available": len(cross),
             "same_key_selected": same_count, "cross_key_selected": cross_count,
             "borrowed_same_key_seats": max(0, same_count - same_quota),
             "borrowed_cross_key_seats": max(0, cross_count - cross_quota),
             "omitted_count": len(previous) - len(selected),
             "selected": [{"memory_id": m["memory_id"], "score": by_id[m["memory_id"]][0],
                           "pool": "protected_factual_state" if m["memory_id"] in protected_ids else "same_key" if m["state_key"] == new["state_key"] else "cross_key_lexical_candidate"}
                          for m in selected]}
    return selected, audit
