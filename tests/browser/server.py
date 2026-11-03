"""Local browser-only factory with explicit controlled LLM/Embedding boundaries.

Never used by the production factory or selected by a production fallback.
"""
import json
import time

import httpx
import numpy as np

from locomo_memory.api import create_app
from locomo_memory.config import load_settings
from locomo_memory.model import DeepSeekModel
from test_builds import completion, draft
from test_queries import query_provider
from test_relations import relation
from test_retrieval import ControlledEmbedder

_failed_first_extraction = False


class BrowserEmbedder(ControlledEmbedder):
    def encode(self, texts):
        vectors = super().encode(texts)
        for index, text in enumerate(texts):
            if 'birth' in text.lower():
                vectors[index] = np.zeros(384, dtype=np.float32)
                vectors[index, 2] = 1
        return vectors


def provider(request):
    global _failed_first_extraction
    payload = json.loads(json.loads(request.content)['messages'][1]['content'])
    if 'sources' in payload and 'new_memory' not in payload and 'operation' not in payload:
        time.sleep(1)  # Makes persisted running/progress observable.
        if not _failed_first_extraction:
            _failed_first_extraction = True
            return httpx.Response(503)
        sources = payload['sources']
        return completion({'memories': [
            draft([sources[0]['source_id']]),
            draft([sources[2]['source_id']], content='Alex lives in Rome.', state_value='Rome'),
            *[draft([sources[index]['source_id']], content=f"Sam's reported birth year is {year}.", entity_id='Sam', state_dimension='birth_year', state_value=year) for index, year in [(3, '1990'), (4, '1992')]],
        ]})
    if 'new_memory' in payload and payload['new_memory']['entity_id'] == 'Sam':
        new = payload['new_memory']
        return completion({'judgments': [relation(old, new, label='CONFLICT', reason='Same birth attribute has incompatible unconditional reports, explicitly unresolved in source.', support_quote='My birth year is 1992. These reports are contradictory and unresolved.') for old in payload['history']]})
    operation = payload.get('operation')
    question = payload.get('question', '')
    if operation is None and 'question' in payload:
        # Give real BM25 a discriminating term; all-zero ties depend on random IDs.
        birth = 'birth year' in question.lower()
        return completion({'entities': ['Sam' if birth else 'Alex'],
                           'topic': 'birth_year' if birth else 'residence', 'time': None,
                           'keywords': ['1990' if birth else 'Rome']})
    if operation == 'resolve' and ('birth year' in question or 'passport' in question):
        selected = [m for m in payload['memories'] if m['entity_id'] == 'Sam' and m['state_dimension'] == 'birth_year'] if 'birth year' in question else []
        return completion({'status': 'conflict' if selected else 'insufficient',
                           'effective_memory_ids': [m['memory_id'] for m in selected],
                           'decisions': [{'memory_id': m['memory_id'], 'selected': m in selected, 'reason': 'Unresolved incompatible birth reports' if m in selected else 'No passport information in evidence'} for m in payload['memories']],
                           'supplemental_relations': [], 'explanation': 'Controlled external response based on the synthetic raw evidence; not model quality evidence'})
    if operation == 'answer':
        if 'failure' in question:
            return completion({'invalid': 'deliberately invalid external response'})
        if payload['status'] in {'conflict', 'insufficient'}:
            return completion({'status': payload['status'], 'answer': "Sam reports birth years 1990 and 1992; the contradiction remains unresolved." if payload['status'] == 'conflict' else 'Insufficient evidence for the passport number.',
                               'citations': [{'memory_id': m['memory_id'], 'source_ids': m['source_ids']} for m in payload['memories']]})
        if not payload['memories']:
            return completion({'status': payload['status'], 'answer': 'Alex lives in Rome.', 'citations': [{'memory_id': None, 'source_ids': [s['source_id'] for s in payload['sources']]}]})
    return query_provider(request)


def app_factory():
    settings = load_settings()
    return create_app(settings, model=DeepSeekModel(settings, api_key='synthetic-browser-only', transport=httpx.MockTransport(provider)), embedder=BrowserEmbedder())
