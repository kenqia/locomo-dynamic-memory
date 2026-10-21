"""Read-only BM25 fallback over the full input of one pinned complete build."""
import hashlib
import json

from rank_bm25 import BM25Okapi

from .builds import BuildError
from .imports import canonical_json
from .retrieval import budget_tokens, tokenize, TOKEN_BUDGET_METHOD

RAW_RETRIEVAL_VERSION = 'pinned-turn-bm25-windows-v3-enumeration-possessives'


def pinned_sources(database, build_id):
    with database.connect() as db:
        db.execute('BEGIN')
        build = db.execute('SELECT * FROM build_versions WHERE build_id=?', (build_id,)).fetchone()
        if build is None or build['status'] != 'complete':
            raise BuildError('no_complete_version')
        dataset = db.execute('SELECT * FROM datasets WHERE dataset_id=?', (build['dataset_id'],)).fetchone()
        # Recompute the original conversation-only digest, never load import annotations.
        canonical = []
        for conversation in db.execute('SELECT * FROM conversations WHERE dataset_id=? ORDER BY sample_id', (build['dataset_id'],)):
            turns = [dict(r) for r in db.execute('SELECT * FROM source_turns WHERE dataset_id=? AND sample_id=? ORDER BY position',
                                                (build['dataset_id'], conversation['sample_id']))]
            canonical.append({'sample_id': conversation['sample_id'], 'speaker_a': conversation['speaker_a'],
                'speaker_b': conversation['speaker_b'], 'turns': [{k:v for k,v in r.items() if k not in ('source_id','dataset_id')} for r in turns]})
        digest = hashlib.sha256(canonical_json(canonical).encode()).hexdigest()
        if digest != build['source_sha256'] or digest != dataset['source_sha256']:
            raise BuildError('source_snapshot_changed', 409)
        fragments = list(db.execute('SELECT source_ids_json,status FROM build_fragments WHERE build_id=? ORDER BY ordinal', (build_id,)))
        ids = [sid for f in fragments for sid in json.loads(f['source_ids_json'])]
        sources = [dict(r) for r in db.execute('SELECT * FROM source_turns WHERE dataset_id=? AND sample_id=? ORDER BY position',
                                             (build['dataset_id'], build['sample_id']))]
        if (any(f['status'] != 'succeeded' for f in fragments) or len(set(ids)) != len(ids)
                or set(ids) != {s['source_id'] for s in sources}
                or any(s['source_id'] != f"{build['dataset_id']}/{build['sample_id']}/{s['dia_id']}" for s in sources)):
            raise BuildError('invalid_raw_source_scope', 409)
    return sources, {'source_snapshot_sha256': hashlib.sha256(canonical_json(sources).encode()).hexdigest(),
                     'pinned_source_ids': ids, 'source_sha256': digest, 'source_count': len(sources)}


def retrieve_sources(sources, question, gaps, settings, *, enumeration=False):
    terms = tokenize(question + ' ' + ' '.join(gaps))
    if enumeration:
        terms += [t[:-2] for t in tokenize(question) if t.endswith("'s")]
    # List questions often name a speaker whose own turns only say 'I'. Include
    # that real source field for broader matching, within the same hit/window limits.
    corpus = [tokenize((s['speaker'] + ' ' if enumeration else '') + s['text']) for s in sources]
    scores = BM25Okapi(corpus).get_scores(terms) if any(corpus) else [0.0] * len(sources)
    matches = [i for i,tokens in enumerate(corpus) if set(tokens).intersection(terms)]
    order = sorted(matches, key=lambda i: (-float(scores[i]), sources[i]['position'], sources[i]['source_id']))
    selected, origins, omitted, centers = {}, [], [], 0

    def append(index, center, kind):
        source = sources[index]
        sid = source['source_id']
        if sid in selected:
            origins.append({'source_id':sid,'center_source_id':center,'kind':kind})
            return True
        cost = budget_tokens(canonical_json({'raw_sources':[*selected.values(),source]}))
        reason = 'raw_turn_limit' if len(selected) >= settings.raw_max_turns else 'raw_token_budget' if cost > settings.raw_token_budget else None
        if reason:
            omitted.append({'source_id':sid,'reason':reason,'kind':kind})
            return False
        selected[sid] = source
        origins.append({'source_id':sid,'center_source_id':center,'kind':kind})
        return True

    for i in order:
        if centers >= settings.raw_max_hits:
            break
        if sources[i]['source_id'] in selected:
            continue
        center = sources[i]['source_id']
        if not append(i, center, 'center'):
            continue
        centers += 1
        for j in range(max(0,i-settings.raw_neighbor_turns), min(len(sources),i+settings.raw_neighbor_turns+1)):
            if j != i and sources[j]['session_id'] == sources[i]['session_id']:
                append(j, center, 'neighbor')
    delivered = sorted(selected.values(), key=lambda s: (s['position'],s['source_id']))
    return delivered, {'speaker_matching':enumeration, 'retrieval_version': RAW_RETRIEVAL_VERSION, 'centers':centers,
        'matched_source_count':len(matches), 'source_ids':[s['source_id'] for s in delivered],
        'origins':origins, 'omitted':omitted, 'token_budget_method':TOKEN_BUDGET_METHOD,
        'token_count':budget_tokens(canonical_json({'raw_sources':delivered})) if delivered else 0,
        'budget':settings.raw_token_budget, 'truncated':bool(omitted) or any(sources[i]['source_id'] not in selected for i in matches),
        'ranked_source_ids':[sources[i]['source_id'] for i in order],
        'unselected_match_ids':[sources[i]['source_id'] for i in order if sources[i]['source_id'] not in selected]}
