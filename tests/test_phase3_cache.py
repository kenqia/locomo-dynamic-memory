from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json

import httpx
import numpy as np
import pytest
from fastapi.testclient import TestClient

from locomo_memory.api import create_app
from locomo_memory.embeddings import EmbeddingFailure
from locomo_memory.model import DeepSeekModel
from locomo_memory.query_schemas import QueryRequest
from tools.research_v2.embedding_cache import (CachedRetrieval, ENCODING_CONFIG, ExactQueryEmbeddingCache, cache_key)
from test_queries import complete_build, query_provider
from test_retrieval import ControlledEmbedder


class CountingEncoder(ControlledEmbedder):
    def __init__(self):self.calls=0
    def encode(self,texts):self.calls+=1;return super().encode(texts)


def identity_args():
    return dict(build_id='b1',index_fingerprint='i1',embedding_identity=ControlledEmbedder().identity(),
        question='Paris',text_schema_version='text-v1',encoding_config=ENCODING_CONFIG)


@pytest.mark.parametrize('field,value',[
    ('build_id','b2'),('index_fingerprint','i2'),('question','Paris '),('question','paris'),
    ('question','Pa\u0301ris'),('text_schema_version','text-v2'),
    ('embedding_identity',{'model':'other','revision':'new','dimensions':384}),
    ('encoding_config',{'precision':'other'})])
def test_every_cache_identity_axis_prevents_a_false_hit(field,value):
    original=identity_args();changed={**original,field:value}
    assert cache_key(**original)!=cache_key(**changed)


def test_embedding_revision_and_full_encoding_configuration_bind_key():
    original=identity_args()
    for k,v in [('revision','rev2'),('max_tokens',128),('normalized',False),('device','other')]:
        modified=deepcopy(original);modified['embedding_identity'][k]=v
        assert cache_key(**original)!=cache_key(**modified)
    changed={**original,'question':'Páris'}
    decomposed={**original,'question':'Pa\u0301ris'}
    assert cache_key(**changed)!=cache_key(**decomposed)


def test_hit_is_byte_identical_and_caller_cannot_corrupt_value():
    encoder=CountingEncoder();cache=ExactQueryEmbeddingCache()
    args=dict(build_id='b1',index_fingerprint='i1',text_schema_version='v1')
    cold,miss=cache.vector(encoder,'Paris',**args);expected=cold.tobytes();cold[0]=-7
    hit,meta=cache.vector(encoder,'Paris',**args)
    assert hit.tobytes()==expected
    assert not miss['cache_hit'] and meta['cache_hit']
    assert encoder.calls==1
    assert cache.snapshot()['vector_bytes']==384*4


def test_lru_eviction_cross_build_clear_and_restart():
    encoder=CountingEncoder();cache=ExactQueryEmbeddingCache(1)
    def run(bid,fp='i1'):return cache.vector(encoder,'Paris',build_id=bid,index_fingerprint=fp,text_schema_version='v1')[1]
    assert not run('b1')['cache_hit']
    assert not run('b2')['cache_hit']
    assert not run('b1')['cache_hit']
    assert run('b1')['cache_hit']
    cache.clear();assert not run('b1')['cache_hit']
    assert not run('b1','i2')['cache_hit']
    assert cache.snapshot()['evictions']==3
    assert ExactQueryEmbeddingCache().snapshot()['entries']==0


def test_failed_encoding_is_not_cached_and_retry_remains_a_miss():
    class Broken(CountingEncoder):
        def encode(self,texts):self.calls+=1;return np.zeros((1,384))
    encoder=Broken();cache=ExactQueryEmbeddingCache()
    for _ in range(2):
        with pytest.raises(EmbeddingFailure):cache.vector(encoder,'Paris',build_id='b1',index_fingerprint='i1',text_schema_version='v1')
    assert encoder.calls==2 and cache.snapshot()['entries']==0


def test_concurrent_exact_requests_encode_once():
    encoder=CountingEncoder();cache=ExactQueryEmbeddingCache()
    def run(_):return cache.vector(encoder,'Paris',build_id='b1',index_fingerprint='i1',text_schema_version='v1')[0].tobytes()
    with ThreadPoolExecutor(max_workers=4) as executor:results=list(executor.map(run,range(12)))
    assert len(set(results))==1 and encoder.calls==1
    assert cache.snapshot()['hits']==11


def test_real_retrieval_hook_preserves_channels_candidates_and_answer_payload(settings,sample):
    answer_inputs=[]
    def provider(request):
        payload=json.loads(json.loads(request.content)['messages'][1]['content'])
        if payload.get('operation')=='answer':answer_inputs.append(payload)
        return query_provider(request)
    encoder=CountingEncoder()
    model=DeepSeekModel(settings,api_key='synthetic-test-key',transport=httpx.MockTransport(provider))
    with TestClient(create_app(settings,model=model,embedder=encoder)) as client:
        dataset,bid=complete_build(client,sample);q=client.app.state.queries
        req=QueryRequest(dataset_id=dataset,sample_id='conv-a',build_id=bid,question='Where does Alex live?')
        original=q.query(req);calls=encoder.calls
        original_retrieval=q.retrieval;cache=ExactQueryEmbeddingCache()
        q.retrieval=CachedRetrieval(original_retrieval,cache)
        cold=q.query(req);warm=q.query(req)
        assert encoder.calls==calls+1
        for trace in (cold,warm):
            for field in ('channels','initial_candidates'):
                assert original['initial'][field]==trace['initial'][field]
            assert original['answer']==trace['answer']
            assert 'research_routing' not in trace
        assert answer_inputs[0]==answer_inputs[1]==answer_inputs[2]
        assert not cold['initial']['research_embedding_cache']['cache_hit']
        assert warm['initial']['research_embedding_cache']['cache_hit']
        q.retrieval=original_retrieval
        assert 'research_embedding_cache' not in q.query(req)['initial']
