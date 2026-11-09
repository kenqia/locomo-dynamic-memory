"""Execute pinned upstream pure methods with synthetic inputs; no installation/API."""
import ast
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
from types import SimpleNamespace

import numpy as np

from tools.m5.offline import ROOT, write, sha


def run():
    source = ROOT/'var/m5-development/propmem-source'
    manifest = json.loads((source/'manifest.json').read_text())
    for name, digest in manifest['files'].items():
        if sha(source/name) != digest:
            raise ValueError('upstream_source_changed')
    tree = ast.parse((source/'src/agents_memory/propmem.py').read_text())
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'PropMemSystem')
    names = ('_identify_entity', '_apply_knowledge_updates')
    nodes = [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name in names]
    # Execute exact, checked pure method bodies without importing OpenAI or workers.
    calls = []
    def embeddings(texts, model):
        calls.append(dict(kind='synthetic_embedding', count=len(texts)))
        return [np.array([1., 0.]) for _ in texts]
    namespace = dict(re=re, embed_texts=embeddings, cosine_similarity=lambda a,b: float(a@b))
    module = ast.Module(body=[ast.ImportFrom(module='__future__', names=[ast.alias(name='annotations')], level=0), *nodes], type_ignores=[])
    exec(compile(ast.fix_missing_locations(module), 'pinned-propmem-pure-methods', 'exec'), namespace)
    identify = namespace['_identify_entity']
    multi = identify(SimpleNamespace(entity_names=['Ada','Ben']), 'What did Ada and Ben do together?')
    collision = identify(SimpleNamespace(entity_names=['Ann','Ben']), 'What did Joanna enjoy?')
    old = SimpleNamespace(text='Ada planned the spring race.', entity='Ada', date_ordinal=10)
    newer = SimpleNamespace(text='Ada completed a different autumn race.', entity='Ada', date_ordinal=20)
    rank = namespace['_apply_knowledge_updates'](SimpleNamespace(embedding_model='synthetic-no-provider'), [(old,1.), (newer,1.)])
    proposition = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'Proposition')
    fields = [n.target.id for n in proposition.body if isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name)]
    out = dict(commit=manifest['commit'], license='Apache-2.0', source_manifest=manifest,
        validation='exact pinned AST methods only; not full backend or model extraction',
        model_defaults=dict(extraction='gpt-4.1', embedding='text-embedding-3-small'),
        synthetic_results=dict(multi_person_target=multi, substring_target=collision,
            proposition_fields=fields, native_source_turn_fields=[f for f in fields if 'source' in f or 'turn' in f],
            similarity_only_update_scores=[dict(text=p.text, score=s) for p,s in rank], calls=calls),
        findings=['Single entity selection loses the second named participant in a joint question',
                  'Full-name substring match assigns Ann to Joanna',
                  'Similarity and report recency penalize old statements without contradiction or event identity evidence',
                  'Native propositions retain session identity but no per-fact original Source Turn IDs',
                  'Session extraction accepts recovered truncated output; incomplete facts require explicit Build status'],
        decision='REJECT direct upstream adoption under current source/participant/temporal contracts',
        adapter='not implemented: safe turn-attribution and participant handling would materially change the upstream method; no extraction-quality gain established',
        canary='not run; no full backend installation or paid extraction',
        provider_requests=0, new_builds=0, qa_f1='not_measured')
    write(ROOT/'experiments/m5-development/propmem-audit.json', out)
    print(json.dumps(out['synthetic_results']))


if __name__ == '__main__':
    run()
