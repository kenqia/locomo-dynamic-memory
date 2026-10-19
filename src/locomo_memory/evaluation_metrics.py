"""LoCoMo category scoring, adapted from retained upstream evaluation.py.

Source: snap-research/locomo commit 3eb6f2c585f5e1699204e3c3bdf7adc5c28cb376.
Only normalization/Porter F1 and category rules are used; no BERTScore import.
"""
from collections import Counter
import re
import string
from nltk.stem import PorterStemmer

STEMMER = PorterStemmer()


def normalize(text):
    text = text.replace(',', '').lower().translate(str.maketrans('', '', string.punctuation))
    return ' '.join(re.sub(r'\b(a|an|the|and)\b', ' ', text).split())


def f1(prediction, gold):
    p, g = ([STEMMER.stem(w) for w in normalize(s).split()] for s in (prediction, gold))
    shared = sum((Counter(p) & Counter(g)).values())
    return 2 * shared / (len(p) + len(g)) if shared else 0.0


def qa_score(prediction, sample):
    category, gold = sample['category'], sample.get('answer')
    if category == 5:
        return {'value': float(any(s in prediction.lower() for s in ('no information available', 'not mentioned'))),
                'rule': 'official_adversarial_refusal', 'missing_gold': gold is None, 'reason': None}
    if category not in (1, 2, 3, 4):
        return {'value': None, 'reason': 'unknown_category', 'missing_gold': gold is None}
    if gold is None or not gold.strip():
        return {'value': None, 'reason': 'missing_gold', 'missing_gold': True}
    if category == 1:
        values = [max(f1(p, g) for p in prediction.split(',')) for g in gold.split(',')]
        score = sum(values) / len(values)
    else:
        score = f1(prediction, gold.split(';')[0].strip() if category == 3 else gold)
    return {'value': score, 'rule': 'official_category_f1', 'missing_gold': False, 'reason': None}


def map_evidence(original, sources):
    by_dia = {s['dia_id']: s['source_id'] for s in sources}
    mapped, errors = [], []
    for ref in original:
        # Split only a complete sequence of legal IDs. Never repair spelling or IDs.
        if not re.fullmatch(r'D\d+:\d+(?:(?:\s*[,;]\s*|\s+)D\d+:\d+)*', ref):
            errors.append({'reference': ref, 'reason': 'malformed_reference'})
            continue
        for dia in re.split(r'\s*[,;]\s*|\s+', ref):
            if dia not in by_dia:
                errors.append({'reference': dia, 'reason': 'missing_source'})
            elif by_dia[dia] not in mapped:
                mapped.append(by_dia[dia])
    return {'original': original, 'source_ids': mapped, 'errors': errors,
            'scorable': bool(mapped) and not errors, 'reason': 'invalid_reference' if errors else None if mapped else 'empty_evidence'}


def coverage(ids, mapping):
    if not mapping['scorable']:
        return None
    gold = set(mapping['source_ids'])
    return len(set(ids) & gold) / len(gold)


def aggregate(values):
    scored = [v for v in values if v is not None]
    return {'mean': sum(scored) / len(scored) if scored else None, 'scored': len(scored),
            'unscored': len(values) - len(scored), 'coverage': len(scored) / len(values) if values else 0}
